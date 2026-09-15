from __future__ import annotations

import pytest

from tetherlens_ingest.adapters import ErgodyneAdapter, FallTechAdapter
from tetherlens_ingest.compatibility import (
    ComparisonOperator,
    EligibilityStatus,
    FeatureKind,
    ToolInterfaceFeature,
    evaluate_attachment_eligibility,
)
from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
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


SOURCE = "https://example.test/attachment"


def _artifact(body: str, *, url: str) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def _claim(
    property_key: str,
    value,
    *,
    source_url: str = SOURCE,
    subject_ref: str = "tool_side_fit",
    unit: str | None = None,
    operator: ConstraintOperator | None = None,
    claim_type: ClaimType | None = None,
) -> CandidateClaim:
    return CandidateClaim(
        subject_type=(
            ClaimSubjectType.PRODUCT
            if property_key == "attachment_selection_class"
            else ClaimSubjectType.PHYSICAL_INTERFACE
        ),
        subject_ref=("self" if property_key == "attachment_selection_class" else subject_ref),
        property_key=property_key,
        value=value,
        unit=unit,
        source_url=source_url,
        extractor="test.v0",
        claim_type=(
            claim_type
            if claim_type is not None
            else (ClaimType.DECLARED_CONSTRAINT if operator else ClaimType.DIRECT)
        ),
        constraint_operator=operator,
    )


def test_generic_fit_profiles_accept_equivalent_source_local_units() -> None:
    claims = [
        _claim("attachment_selection_class", "handle_attachment"),
        _claim("attachment_eligibility.feature_kind", "handle", source_url="https://example.test/a"),
        _claim(
            "attachment_eligibility.dimension.section_diameter",
            1.0,
            unit="in",
            operator=ConstraintOperator.GTE,
            source_url="https://example.test/a",
        ),
        _claim(
            "attachment_eligibility.dimension.section_diameter",
            1.28,
            unit="in",
            operator=ConstraintOperator.LTE,
            source_url="https://example.test/a",
        ),
        _claim("attachment_eligibility.feature_kind", "handle", source_url="https://example.test/b"),
        _claim(
            "attachment_eligibility.dimension.section_diameter",
            25.4,
            unit="mm",
            operator=ConstraintOperator.GTE,
            source_url="https://example.test/b",
        ),
        _claim(
            "attachment_eligibility.dimension.section_diameter",
            32.512,
            unit="mm",
            operator=ConstraintOperator.LTE,
            source_url="https://example.test/b",
        ),
    ]

    eligibility = resolve_attachment_eligibility(claims)

    assert eligibility is not None
    predicates = eligibility.paths[0].requirements
    assert [
        (predicate.property_key, predicate.operator, predicate.value)
        for predicate in predicates[1:]
    ] == [
        ("dimension:section_diameter", ComparisonOperator.GTE, pytest.approx(25.4)),
        ("dimension:section_diameter", ComparisonOperator.LTE, pytest.approx(32.512)),
    ]


def test_generic_fit_profiles_reject_bounds_split_across_sources() -> None:
    claims = [
        _claim("attachment_selection_class", "handle_attachment"),
        _claim("attachment_eligibility.feature_kind", "handle", source_url="https://example.test/min"),
        _claim(
            "attachment_eligibility.dimension.section_diameter",
            1.0,
            unit="in",
            operator=ConstraintOperator.GTE,
            source_url="https://example.test/min",
        ),
        _claim("attachment_eligibility.feature_kind", "handle", source_url="https://example.test/max"),
        _claim(
            "attachment_eligibility.dimension.section_diameter",
            1.28,
            unit="in",
            operator=ConstraintOperator.LTE,
            source_url="https://example.test/max",
        ),
    ]

    with pytest.raises(ClaimResolutionError, match="conflicting accepted feature-bound dimensional"):
        resolve_attachment_eligibility(claims)


def test_generic_fit_profiles_require_explicit_comparison_direction() -> None:
    claims = [
        _claim("attachment_selection_class", "handle_attachment"),
        _claim("attachment_eligibility.feature_kind", "handle"),
        _claim(
            "attachment_eligibility.dimension.section_diameter",
            1.28,
            unit="in",
        ),
    ]

    with pytest.raises(ClaimResolutionError, match="requires an explicit eq/lt/lte/gt/gte operator"):
        resolve_attachment_eligibility(claims)


def test_generic_fit_profiles_require_declared_constraint_claim_type() -> None:
    claims = [
        _claim("attachment_selection_class", "handle_attachment"),
        _claim("attachment_eligibility.feature_kind", "handle"),
        _claim(
            "attachment_eligibility.dimension.section_diameter",
            1.28,
            unit="in",
            operator=ConstraintOperator.LTE,
            claim_type=ClaimType.MEASURED,
        ),
    ]

    with pytest.raises(ClaimResolutionError, match="requires declared-constraint claims"):
        resolve_attachment_eligibility(claims)


def test_generic_fit_profiles_reject_multiple_subjects_for_same_feature_kind() -> None:
    claims = [
        _claim("attachment_selection_class", "handle_attachment"),
        _claim("attachment_eligibility.feature_kind", "handle", subject_ref="fit_a"),
        _claim(
            "attachment_eligibility.dimension.section_diameter",
            1.0,
            unit="in",
            operator=ConstraintOperator.GTE,
            subject_ref="fit_a",
        ),
        _claim("attachment_eligibility.feature_kind", "handle", subject_ref="fit_b"),
        _claim(
            "attachment_eligibility.dimension.section_height",
            4.5,
            unit="in",
            operator=ConstraintOperator.LTE,
            subject_ref="fit_b",
        ),
    ]

    with pytest.raises(ClaimResolutionError, match="one accepted fit subject per feature kind"):
        resolve_attachment_eligibility(claims)


def test_generic_external_dimensions_cannot_bypass_partial_legacy_diameter_envelope() -> None:
    claims = [
        _claim("attachment_selection_class", "external_section_attachment"),
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="legacy_fit",
            property_key="interface.dimension.min_diameter",
            value=1.0,
            unit="in",
            source_url=SOURCE,
            extractor="test.v0",
        ),
        _claim("attachment_eligibility.feature_kind", "external_section"),
        _claim(
            "attachment_eligibility.dimension.section_length",
            3.5,
            unit="in",
            operator=ConstraintOperator.LTE,
        ),
    ]

    with pytest.raises(ClaimResolutionError, match="complete min/max diameter-fit envelope"):
        resolve_attachment_eligibility(claims)


def test_generic_external_dimensions_reject_cross_subject_legacy_profile_merge() -> None:
    claims = [
        _claim("attachment_selection_class", "external_section_attachment"),
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="legacy_fit",
            property_key="interface.dimension.min_diameter",
            value=1.0,
            unit="in",
            source_url=SOURCE,
            extractor="test.v0",
        ),
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="legacy_fit",
            property_key="interface.dimension.max_diameter",
            value=1.65,
            unit="in",
            source_url=SOURCE,
            extractor="test.v0",
        ),
        _claim(
            "attachment_eligibility.feature_kind",
            "external_section",
            subject_ref="generic_fit",
        ),
        _claim(
            "attachment_eligibility.dimension.section_length",
            3.5,
            unit="in",
            operator=ConstraintOperator.LTE,
            subject_ref="generic_fit",
        ),
    ]

    with pytest.raises(
        ClaimResolutionError,
        match="must share one physical-interface subject",
    ):
        resolve_attachment_eligibility(claims)


def test_falltech_5401a1_vertical_compiles_three_axis_fit_on_one_external_feature() -> None:
    identity = ProductIdentity(
        manufacturer="FallTech",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="Battery Boot Tool Attachment",
        sku="5401A1",
        url="https://www.falltech.com/product/5401a1/",
    )
    body = """
    <html><body>
      <h1>Battery Boot Tool Attachment</h1>
      <div>SKU: 5401A1</div>
      <p>Fits most cordless power tool batteries, including both low profile and high
      capacity designs, up to 3.5\" L x 2.75\" W x 2.5\" H (9cm L x 7cm W x 6.5cm).</p>
      <p>Steel D-ring provides secure connection point for tool tether.</p>
      <p>For cordless power tool batteries weighing up to 6 lb max.</p>
    </body></html>
    """

    claims = FallTechAdapter().extract(identity, [_artifact(body, url=identity.url)])

    assert any(
        claim.property_key == "attachment_selection_class"
        and claim.value == "external_section_attachment"
        for claim in claims
    )
    fit_claims = [
        claim
        for claim in claims
        if claim.subject_ref == "tool_side_fit"
    ]
    assert {(claim.property_key, claim.constraint_operator) for claim in fit_claims} == {
        ("attachment_eligibility.feature_kind", None),
        ("attachment_eligibility.dimension.section_length", ConstraintOperator.LTE),
        ("attachment_eligibility.dimension.section_width", ConstraintOperator.LTE),
        ("attachment_eligibility.dimension.section_height", ConstraintOperator.LTE),
    }

    eligibility = resolve_attachment_eligibility(claims)
    assert eligibility is not None
    requirements = eligibility.paths[0].requirements
    assert {(item.property_key, item.operator) for item in requirements} == {
        ("feature_kind", ComparisonOperator.EQ),
        ("dimension:section_length", ComparisonOperator.LTE),
        ("dimension:section_width", ComparisonOperator.LTE),
        ("dimension:section_height", ComparisonOperator.LTE),
    }

    eligible = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="battery:inside",
                feature_kind=FeatureKind.EXTERNAL_SECTION,
                dimensions_mm={
                    "section_length": 80.0,
                    "section_width": 65.0,
                    "section_height": 60.0,
                },
            )
        ],
    )
    assert eligible.status == EligibilityStatus.ELIGIBLE
    assert eligible.matches[0].feature_id == "battery:inside"

    cannot_stitch = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="battery:too-wide",
                feature_kind=FeatureKind.EXTERNAL_SECTION,
                dimensions_mm={
                    "section_length": 80.0,
                    "section_width": 75.0,
                    "section_height": 60.0,
                },
            ),
            ToolInterfaceFeature(
                feature_id="battery:too-long",
                feature_kind=FeatureKind.EXTERNAL_SECTION,
                dimensions_mm={
                    "section_length": 95.0,
                    "section_width": 65.0,
                    "section_height": 60.0,
                },
            ),
        ],
    )
    assert cannot_stitch.status == EligibilityStatus.INELIGIBLE

    interfaces = resolve_connection_interfaces(claims)
    assert len(interfaces) == 1
    assert interfaces[0].interface_id == "tether_side_ring"
    assert interfaces[0].interface_type == "ring"
    assert interfaces[0].attributes == {"ring_form": "d_ring"}


def test_ergodyne_3745_vertical_compiles_bounded_handle_fit_on_one_handle() -> None:
    identity = ProductIdentity(
        manufacturer="Ergodyne",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="Tool Grip and Tether Attachment Point (2-Pack)",
        model="Squids 3745",
        sku="19747",
        url="https://www.ergodyne.com/squids-3745-tool-grip-and-tether-attachment-point-2-pack",
    )
    body = """
    <html><body>
      <h1>Squids 3745 Tool Grip and Tether Attachment Point (2-Pack)</h1>
      <div>Item #: 19747</div>
      <p>This tool attachment is compatible with screwdrivers or nut drivers with handles
      ranging from 1in // 2.5cm to 1.28in // 3.2cm in diameter and a handle height of
      4.5in // 11.4cm.</p>
      <p>1lb maximum working capacity.</p>
    </body></html>
    """

    claims = ErgodyneAdapter().extract(identity, [_artifact(body, url=identity.url)])

    assert any(
        claim.property_key == "attachment_selection_class"
        and claim.value == "handle_attachment"
        for claim in claims
    )
    eligibility = resolve_attachment_eligibility(claims)
    assert eligibility is not None
    predicates = eligibility.paths[0].requirements
    assert {(item.property_key, item.operator) for item in predicates} == {
        ("feature_kind", ComparisonOperator.EQ),
        ("dimension:section_diameter", ComparisonOperator.GTE),
        ("dimension:section_diameter", ComparisonOperator.LTE),
        ("dimension:section_height", ComparisonOperator.LTE),
    }

    eligible = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="handle:inside",
                feature_kind=FeatureKind.HANDLE,
                dimensions_mm={
                    "section_diameter": 30.0,
                    "section_height": 110.0,
                },
            )
        ],
    )
    assert eligible.status == EligibilityStatus.ELIGIBLE
    assert eligible.matches[0].feature_id == "handle:inside"

    cannot_stitch = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="handle:too-tall",
                feature_kind=FeatureKind.HANDLE,
                dimensions_mm={
                    "section_diameter": 30.0,
                    "section_height": 120.0,
                },
            ),
            ToolInterfaceFeature(
                feature_id="handle:too-thin",
                feature_kind=FeatureKind.HANDLE,
                dimensions_mm={
                    "section_diameter": 24.0,
                    "section_height": 110.0,
                },
            ),
        ],
    )
    assert cannot_stitch.status == EligibilityStatus.INELIGIBLE
