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


def _secondary(url, role, sku, body, subject_ref=None):
    return SourceArtifact(
        url=url,
        source_type=SourceType.SECONDARY_WEBPAGE,
        content_type="text/html",
        body=body,
        metadata={
            "role": role,
            "requested_sku": sku,
            "subject_ref": subject_ref or sku,
            "evidence_page_kind": "product_detail",
            "expected_detail_url": url,
        },
    )


def test_wrong_primary_manufacturer_page_does_not_outrank_verified_secondary_mass():
    adapter = MilwaukeeAdapter()
    wrong_primary = SourceArtifact(
        url="https://www.milwaukeetool.com/Products/9999-20",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="<h1>9999-20 Other Tool</h1><div>Tool Body Weight 4.0 lb</div>",
    )
    retailer_tool = _secondary(
        "https://example.test/milwaukee-2607-20",
        "secondary_tool_mass",
        "2607-20",
        "<h1>Milwaukee 2607-20</h1><div>Weight: 3.0 lb (Tool Only)</div>",
        "self",
    )
    battery = SourceArtifact(
        url="https://www.milwaukeetool.com/Products/48-11-1828",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="<h1>48-11-1828 Battery</h1><div>Battery Weight 1.6 lb</div>",
        metadata={"role": "battery", "battery_model": "48-11-1828"},
    )

    claims = adapter.extract(_identity(), [wrong_primary, retailer_tool, battery])

    tool_claims = [c for c in claims if c.property_key == "tool_body_mass_kg"]
    assert len(tool_claims) == 1
    assert tool_claims[0].evidence_method == "qualified_secondary_exact_sku"
    assert tool_claims[0].value == 1.360777

    profile = next(c for c in claims if c.property_key == "operational_mass_kg")
    assert profile.value == 2.086525
    assert profile.evidence_method == "derived_cross_source"


def test_wrong_manufacturer_battery_page_does_not_outrank_verified_secondary_battery_mass():
    adapter = MilwaukeeAdapter()
    primary = SourceArtifact(
        url="https://www.milwaukeetool.com/Products/2607-20",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="<h1>2607-20 M18 Hammer Drill</h1><div>Tool Body Weight 3.0 lb</div>",
    )
    wrong_battery = SourceArtifact(
        url="https://www.milwaukeetool.com/Products/48-11-1850",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="<h1>48-11-1850 Battery</h1><div>Battery Weight 2.2 lb</div>",
        metadata={"role": "battery", "battery_model": "48-11-1828"},
    )
    retailer_battery = _secondary(
        "https://example.test/milwaukee-48-11-1828",
        "secondary_battery_mass",
        "48-11-1828",
        "<h1>Milwaukee 48-11-1828</h1><div>Battery Weight 1.6 lb</div>",
    )

    claims = adapter.extract(_identity(), [primary, wrong_battery, retailer_battery])

    battery_claims = [c for c in claims if c.property_key == "battery_mass_kg"]
    assert len(battery_claims) == 1
    assert battery_claims[0].evidence_method == "qualified_secondary_exact_sku"
    assert battery_claims[0].value == 0.725748

    profile = next(c for c in claims if c.property_key == "operational_mass_kg")
    assert profile.value == 2.086525
    assert profile.evidence_method == "derived_cross_source"


def test_redirected_kit_page_must_resolve_to_expected_kit_identity_before_expansion():
    adapter = MilwaukeeAdapter()
    redirected_kit = SourceArtifact(
        url="https://www.milwaukeetool.com/Products/9999-22",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="""
            <h1>2607-22 M18 Hammer Drill/Driver Kit</h1>
            <h2>In The Box (5)</h2>
            <div>2607-20</div><div>48-11-1828</div>
            <h2>Specs</h2>
        """,
        metadata={"role": "kit", "kit_sku": "2607-22"},
    )

    assert adapter.related_sources(_identity(), redirected_kit) == []
