from tetherlens_ingest.adapters import MilwaukeeAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType


def _identity():
    return ProductIdentity(
        manufacturer="Milwaukee",
        name="M18 1/2 in Hammer Drill/Driver",
        sku="2607-20",
        product_type=ProductType.TOOL,
        url="https://www.milwaukeetool.com/Products/2607-20",
    )


def _secondary_tool():
    url = "https://thepowertoolstore.com/products/milwaukee-2607-20"
    return SourceArtifact(
        url=url,
        source_type=SourceType.SECONDARY_WEBPAGE,
        content_type="text/html",
        body="<h1>Milwaukee 2607-20</h1><div>Weight: 3.0 lb (Tool Only)</div>",
        metadata={
            "role": "secondary_tool_mass",
            "requested_sku": "2607-20",
            "subject_ref": "self",
            "evidence_page_kind": "product_detail",
            "expected_detail_url": url,
        },
    )


def _battery():
    return SourceArtifact(
        url="https://www.milwaukeetool.com/products/details/m18-redlithium-xc-extended-capacity-battery/48-11-1828",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="<h1>48-11-1828 Battery</h1><div>Battery Weight 1.6 lb</div>",
        metadata={"role": "battery", "battery_model": "48-11-1828"},
    )


def test_search_redirect_cannot_create_manufacturer_priority_mass():
    adapter = MilwaukeeAdapter()
    search_fallback = SourceArtifact(
        url="https://www.milwaukeetool.com/search?q=2607-20",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="""
            <article>Milwaukee 2607-20 Hammer Drill/Driver</article>
            <article>Milwaukee 9999-20 Other Tool - Tool Body Weight 9.9 lb</article>
        """,
    )

    claims = adapter.extract(_identity(), [search_fallback, _secondary_tool(), _battery()])

    tool_claims = [c for c in claims if c.property_key == "tool_body_mass_kg"]
    assert len(tool_claims) == 1
    assert tool_claims[0].evidence_method == "qualified_secondary_exact_sku"
    assert tool_claims[0].value == 1.360777

    profile = next(c for c in claims if c.property_key == "operational_mass_kg")
    assert profile.value == 2.086525
    assert profile.evidence_method == "derived_cross_source"


def test_canonical_milwaukee_detail_route_is_accepted():
    adapter = MilwaukeeAdapter()
    primary = SourceArtifact(
        url="https://www.milwaukeetool.com/products/details/m18-1-2-hammer-drill-driver/2607-20",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="<h1>2607-20 M18 Hammer Drill</h1><div>Tool Body Weight 3.0 lb</div>",
    )

    claims = adapter.extract(_identity(), [primary, _battery()])
    tool_claim = next(c for c in claims if c.property_key == "tool_body_mass_kg")
    assert tool_claim.evidence_method == "manufacturer_stated"
    assert tool_claim.value == 1.360777
