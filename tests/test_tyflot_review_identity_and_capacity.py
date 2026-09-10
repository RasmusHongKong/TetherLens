from __future__ import annotations

from tetherlens_ingest.adapters import TyFlotAdapter
from tetherlens_ingest.models import (
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)


PRODUCT_URL = "https://guardianfall.com/product/cold-shrink-series/COLDSH41X35"
OTHER_VARIANT_URL = "https://guardianfall.com/product/cold-shrink-series/COLDSH21X275"
GUIDE_URL = "https://guardianfall.com/assets/current-dop-guide"


def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Ty-Flot",
        product_type=ProductType.TOOL_ATTACHMENT,
        name='Cold Shrink Attachment, 4.1 in by 3.5 in',
        sku="COLDSH41X35",
        url=PRODUCT_URL,
    )


def _primary(
    url: str = PRODUCT_URL,
    capacity: str = "10 lb",
) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=(
            "<h1>Cold Shrink Series</h1>"
            "<p>The durable shrink tubing will collapse onto the tool, fixing it in place.</p>"
            f"<div>Max Tool Weight: {capacity}</div>"
            "<div>Max Tether Length: 48\"</div>"
            "<div>Fits Diameter: 1.65\" to 3.50\"</div>"
        ),
    )


def _guide(capacity_lb: float) -> SourceArtifact:
    return SourceArtifact(
        url=GUIDE_URL,
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        content_type="application/pdf",
        body=(
            "Cold Shrink Part Numbers Description Fits Diameter Rating Qty "
            "COLDSH41X35 Cold Shrink Attachment, 4.1\" X 3.5\" "
            f"1.65\" to 3.50\" up to {capacity_lb:g} lb 5"
        ),
        metadata={"role": "dop_product_guide"},
    )


def test_tyflot_rejects_same_host_primary_for_different_variant() -> None:
    adapter = TyFlotAdapter()
    artifact = _primary(OTHER_VARIANT_URL)

    assert adapter.related_sources(_identity(), artifact) == []
    assert adapter.extract(_identity(), [artifact]) == []
    assert adapter.observe(_identity(), [artifact]) == []


def test_tyflot_matching_capacity_sources_do_not_create_conflict() -> None:
    adapter = TyFlotAdapter()
    artifacts = [_primary(), _guide(10)]
    claims = adapter.extract(_identity(), artifacts)
    observations = adapter.observe(_identity(), artifacts)

    issues = adapter.readiness_issues(claims, observations) or []

    assert not any(issue.property_key == "rated_capacity_kg" for issue in issues)


def test_tyflot_equivalent_rounded_capacity_sources_do_not_create_conflict() -> None:
    adapter = TyFlotAdapter()
    artifacts = [_primary(capacity="4.53 kg"), _guide(10)]
    claims = adapter.extract(_identity(), artifacts)
    observations = adapter.observe(_identity(), artifacts)

    issues = adapter.readiness_issues(claims, observations) or []

    assert not any(issue.property_key == "rated_capacity_kg" for issue in issues)


def test_tyflot_conflicting_capacity_sources_block_readiness() -> None:
    adapter = TyFlotAdapter()
    artifacts = [_primary(), _guide(8)]
    claims = adapter.extract(_identity(), artifacts)
    observations = adapter.observe(_identity(), artifacts)

    issues = adapter.readiness_issues(claims, observations) or []

    capacity_issue = next(
        issue for issue in issues if issue.property_key == "rated_capacity_kg"
    )
    assert capacity_issue.code == "EVIDENCE_CONFLICT"
    assert "no capacity is recommendation-ready" in (capacity_issue.detail or "")
