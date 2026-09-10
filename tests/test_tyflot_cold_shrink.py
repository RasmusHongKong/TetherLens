from __future__ import annotations

import pytest

from tetherlens_ingest.adapters import TyFlotAdapter
from tetherlens_ingest.compatibility import (
    EligibilityStatus,
    FeatureKind,
    ToolInterfaceFeature,
    evaluate_attachment_eligibility,
)
from tetherlens_ingest.constraints import resolve_product_constraints
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ConstraintOperator,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.resolution import (
    ClaimResolutionError,
    resolve_attachment_eligibility,
    resolve_connection_interfaces,
)
from tetherlens_ingest.runner import IngestionRunner


PRODUCT_URL = "https://guardianfall.com/product/cold-shrink-series/COLDSH41X35"
GUIDE_INDEX_URL = "https://guardianfall.com/media/catalog/dropped-object-prevention-product-guide"
GUIDE_URL = "https://guardianfall.com/assets/current-dop-guide"


class _ArtifactMapFetcher:
    def __init__(self, artifacts: dict[str, SourceArtifact]):
        self.artifacts = artifacts
        self.calls: list[tuple[str, SourceType]] = []

    def get(self, url: str, source_type: SourceType) -> SourceArtifact:
        self.calls.append((url, source_type))
        artifact = self.artifacts[url].model_copy(deep=True)
        assert artifact.source_type == source_type
        return artifact


def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Ty-Flot",
        product_type=ProductType.TOOL_ATTACHMENT,
        name='Cold Shrink Attachment, 4.1 in by 3.5 in',
        sku="COLDSH41X35",
        url=PRODUCT_URL,
    )


def _primary_artifact() -> SourceArtifact:
    body = """
    <h1>Cold Shrink Series</h1>
    <p>COLD SHRINK ATTACHMENT, 4.1&quot; BY 3.5&quot; (5-Pack)</p>
    <p>Ty-Flot patented Cold-Shrink attachment points provide a simple and secure method.</p>
    <p>Simply select the right size, slip over the tool, and pull the inner core free.</p>
    <p>The durable shrink tubing will collapse onto the tool, fixing it in place, ready for immediate use.</p>
    <h2>Features</h2>
    <div>Max Tool Weight: Up to 10 lb</div>
    <div>Max Tether Length: 48&quot;</div>
    <div>Fits Diameter: 1.00&quot; to 1.65&quot;</div>
    <div>Dimensions before shrinking: 2.1&quot; Dia x 2.75&quot;</div>
    <div>Requires no tools for installation</div>
    """
    return SourceArtifact(
        url=PRODUCT_URL,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def _guide_index_artifact() -> SourceArtifact:
    return SourceArtifact(
        url=GUIDE_INDEX_URL,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=f'<a href="{GUIDE_URL}">Download PDF Version</a>',
    )


def _guide_artifact() -> SourceArtifact:
    return SourceArtifact(
        url=GUIDE_URL,
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        content_type="application/pdf",
        body=(
            'Cold Shrink Part Numbers Description Fits Diameter Rating Qty '
            'COLDSH41X35 Cold Shrink Attachment, 4.1" X 3.5" (10.41 cm x 8.89 cm) '
            '1.65" to 3.50" (4.19 cm to 8.89 cm) up to 10 lb (4.53 kg) 5'
        ),
    )


def _all_artifacts() -> list[SourceArtifact]:
    primary = _primary_artifact()
    guide = _guide_artifact()
    guide.metadata["role"] = "dop_product_guide"
    return [primary, guide]


def test_tyflot_contraction_capture_requires_retention_evidence_not_product_name() -> None:
    adapter = TyFlotAdapter()
    claims = adapter.extract(_identity(), [_primary_artifact()])

    method = next(claim for claim in claims if claim.property_key == "attachment_method_code")
    selection = next(claim for claim in claims if claim.property_key == "attachment_selection_class")
    assert method.value == "contraction_capture"
    assert "collapse onto the tool" in (method.raw_value or "")
    assert selection.value == "external_section_attachment"

    title_only = SourceArtifact(
        url=PRODUCT_URL,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="<h1>Cold Shrink Series</h1><p>COLD SHRINK ATTACHMENT, 4.1 in BY 3.5 in</p>",
    )
    title_claims = adapter.extract(_identity(), [title_only])
    assert not any(claim.property_key == "attachment_method_code" for claim in title_claims)
    assert not any(claim.property_key == "attachment_selection_class" for claim in title_claims)


def test_tyflot_preserves_capacity_and_max_tether_length_in_existing_families() -> None:
    claims = TyFlotAdapter().extract(_identity(), [_primary_artifact()])

    capacity = next(claim for claim in claims if claim.property_key == "rated_capacity_kg")
    assert capacity.value == pytest.approx(4.535924)
    assert capacity.unit == "kg"

    constraints = resolve_product_constraints(
        claims,
        source_product_ref="tyflot:COLDSH41X35",
    )
    max_length = next(
        constraint
        for constraint in constraints
        if constraint.constraint_key == "max_lanyard_length_mm"
    )
    assert max_length.operator == ConstraintOperator.LTE
    assert max_length.value == pytest.approx(1219.2)
    assert max_length.unit == "mm"


def test_tyflot_current_storefront_and_product_guide_conflict_is_retained_and_blocks_readiness() -> None:
    adapter = TyFlotAdapter()
    fetcher = _ArtifactMapFetcher({
        PRODUCT_URL: _primary_artifact(),
        GUIDE_INDEX_URL: _guide_index_artifact(),
        GUIDE_URL: _guide_artifact(),
    })

    result = IngestionRunner(fetcher).ingest(_identity(), adapter)

    assert fetcher.calls == [
        (PRODUCT_URL, SourceType.MANUFACTURER_WEBPAGE),
        (GUIDE_INDEX_URL, SourceType.MANUFACTURER_WEBPAGE),
        (GUIDE_URL, SourceType.MANUFACTURER_DOCUMENT),
    ]
    assert [artifact.metadata.get("role") for artifact in result.artifacts] == [
        None,
        "dop_product_guide_index",
        "dop_product_guide",
    ]

    min_claims = [
        claim
        for claim in result.claims
        if claim.property_key == "interface.dimension.min_diameter"
    ]
    max_claims = [
        claim
        for claim in result.claims
        if claim.property_key == "interface.dimension.max_diameter"
    ]
    assert {(claim.value, claim.unit, claim.source_url) for claim in min_claims} == {
        (1.0, "in", PRODUCT_URL),
        (1.65, "in", GUIDE_URL),
    }
    assert {(claim.value, claim.unit, claim.source_url) for claim in max_claims} == {
        (1.65, "in", PRODUCT_URL),
        (3.5, "in", GUIDE_URL),
    }

    assert any(
        observation.code == "PRODUCT_VARIANT_SCOPE_CONFLICT"
        for observation in result.acquisition_observations
    )
    assert result.readiness_assessed is True
    issues = {(issue.code, issue.property_key) for issue in result.issues}
    assert ("EVIDENCE_CONFLICT", "tool_attachment.variant_geometry") in issues
    assert ("EVIDENCE_CONFLICT", "interface.dimension.diameter_fit") in issues
    diameter_issue = next(
        issue
        for issue in result.issues
        if issue.property_key == "interface.dimension.diameter_fit"
    )
    assert "1-1.65 in" in (diameter_issue.detail or "")
    assert "1.65-3.5 in" in (diameter_issue.detail or "")


def test_external_section_attachment_compiles_existing_diameter_dimensions_without_connection_role() -> None:
    claims = TyFlotAdapter().extract(_identity(), _all_artifacts())
    accepted = [
        claim
        for claim in claims
        if not (
            claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
            and claim.source_url == PRODUCT_URL
        )
    ]

    eligibility = resolve_attachment_eligibility(accepted)
    assert eligibility is not None
    assert resolve_connection_interfaces(accepted) == []

    in_range = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="tool-body",
                feature_kind=FeatureKind.EXTERNAL_SECTION,
                dimensions_mm={"section_diameter": 50.0},
            )
        ],
    )
    assert in_range.status == EligibilityStatus.ELIGIBLE
    assert [match.feature_id for match in in_range.matches] == ["tool-body"]

    too_small = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="small-section",
                feature_kind=FeatureKind.EXTERNAL_SECTION,
                dimensions_mm={"section_diameter": 30.0},
            )
        ],
    )
    assert too_small.status == EligibilityStatus.INELIGIBLE

    wrong_geometry = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="handle",
                feature_kind=FeatureKind.HANDLE,
                dimensions_mm={"section_diameter": 50.0},
            )
        ],
    )
    assert wrong_geometry.status == EligibilityStatus.INELIGIBLE

    missing_diameter = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="unknown-section",
                feature_kind=FeatureKind.EXTERNAL_SECTION,
            )
        ],
    )
    assert missing_diameter.status == EligibilityStatus.UNRESOLVED


def test_external_section_attachment_fails_closed_if_conflicting_diameter_claims_are_treated_as_accepted() -> None:
    claims = TyFlotAdapter().extract(_identity(), _all_artifacts())

    with pytest.raises(ClaimResolutionError, match="conflicting accepted claims"):
        resolve_attachment_eligibility(claims)
