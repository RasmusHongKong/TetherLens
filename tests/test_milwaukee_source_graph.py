from tetherlens_ingest.adapters import MilwaukeeAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.runner import IngestionRunner


class FakeFetcher:
    def __init__(self):
        self.calls = []

    def get(self, url, source_type=SourceType.MANUFACTURER_WEBPAGE):
        self.calls.append((url, source_type))
        if url.endswith("/2607-20") and "thepowertoolstore.com" not in url:
            body = """
            <h1>2607-20 M18 1/2 in Hammer Drill/Driver</h1>
            <div>Specs</div><div>Loading</div>
            <img alt="2607-22 kit"><img alt="2607-22CT kit">
            """
        elif url.endswith("/2607-22"):
            body = """
            <h1>2607-22 M18 Hammer Drill/Driver Kit</h1>
            <h2>In The Box (5)</h2>
            <a href="/Products/2607-20">2607-20 M18 Hammer Drill/Driver</a>
            <a href="/Products/48-11-1828">48-11-1828 M18 REDLITHIUM XC Extended Capacity Battery</a>
            <h2>Specs</h2>
            """
        elif url.endswith("/2607-22CT"):
            body = """
            <h1>2607-22CT M18 Compact Hammer Drill/Driver Kit</h1>
            <h2>In The Box (5)</h2>
            <a href="/Products/2607-20">2607-20 M18 Hammer Drill/Driver</a>
            <a href="/Products/48-11-1815">48-11-1815 M18 Compact Battery</a>
            <h2>Specs</h2>
            """
        elif "milwaukeetool.com" in url and url.endswith("/48-11-1828"):
            body = "<h1>48-11-1828 M18 REDLITHIUM XC Battery</h1><div>Specs Loading</div>"
        elif "milwaukeetool.com" in url and url.endswith("/48-11-1815"):
            body = "<h1>48-11-1815 M18 Compact Battery</h1><div>Specs Loading</div>"
        elif "thepowertoolstore.com" in url and url.endswith("milwaukee-2607-20"):
            body = "<h1>Milwaukee 2607-20</h1><div>Weight: 3.0 lb (Tool Only)</div>"
        elif "thepowertoolstore.com" in url and url.endswith("milwaukee-48-11-1828"):
            body = "<h1>Milwaukee 48-11-1828</h1><div>Weight: 1.6 lb</div>"
        elif "thepowertoolstore.com" in url and url.endswith("milwaukee-48-11-1815"):
            raise RuntimeError("no secondary mass fixture")
        else:
            raise AssertionError(url)
        return SourceArtifact(url=url, source_type=source_type, content_type="text/html", body=body)


def _identity():
    return ProductIdentity(
        manufacturer="Milwaukee",
        name="M18 1/2 in Hammer Drill/Driver",
        sku="2607-20",
        product_type=ProductType.TOOL,
        url="https://www.milwaukeetool.com/Products/2607-20",
    )


def _secondary_artifact(url, role, sku, body, subject_ref=None, resolved_url=None):
    return SourceArtifact(
        url=resolved_url or url,
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


def test_milwaukee_graph_joins_verified_kit_relationship_to_exact_sku_secondary_masses():
    result = IngestionRunner(FakeFetcher()).ingest(_identity(), MilwaukeeAdapter())
    claims = {(c.subject_type.value, c.subject_ref, c.property_key): c for c in result.claims}

    assert claims[("product", "self", "tool_body_mass_kg")].value == 1.360777
    assert claims[("product", "self", "tool_body_mass_kg")].evidence_method == "qualified_secondary_exact_sku"
    assert claims[("related_product", "48-11-1828", "battery_mass_kg")].value == 0.725748
    assert claims[("related_product", "48-11-1828", "battery_mass_kg")].evidence_method == "qualified_secondary_exact_sku"

    profile = claims[("operational_profile", "2607-20+48-11-1828", "operational_mass_kg")]
    assert profile.value == 2.086525
    assert profile.evidence_method == "derived_cross_source"
    assert len(profile.supporting_source_urls) == 2

    assert ("related_product", "48-11-1815", "battery_mass_kg") not in claims
    assert result.readiness_assessed is True
    assert result.issues == []

    observation_codes = [o.code for o in result.acquisition_observations]
    assert "RELATED_KIT_SOURCES_DISCOVERED" in observation_codes
    assert "BATTERY_RELATIONSHIP_DISCOVERED" in observation_codes
    assert "QUALIFIED_SECONDARY_SOURCES_VERIFIED" in observation_codes
    assert "RELATED_SOURCE_FETCH_FAILED" in observation_codes


def test_milwaukee_secondary_mass_requires_exact_sku_identity():
    adapter = MilwaukeeAdapter()
    artifact = _secondary_artifact(
        "https://example.test/milwaukee-48-11-1828",
        "secondary_battery_mass",
        "48-11-1828",
        "<h1>Different battery 48-11-1850</h1><div>Individual Battery Weight 1.54 lb</div>",
    )
    claims = adapter.extract(_identity(), [artifact])
    assert not any(c.property_key == "battery_mass_kg" for c in claims)


def test_milwaukee_search_result_page_cannot_bind_another_products_mass_to_requested_sku():
    adapter = MilwaukeeAdapter()
    artifact = SourceArtifact(
        url="https://www.homedepot.com/s/48-11-1828",
        source_type=SourceType.SECONDARY_WEBPAGE,
        content_type="text/html",
        body="""
            <article>Milwaukee 48-11-1828 battery - see details</article>
            <article>Milwaukee 48-11-1850 battery - Individual Battery Weight 2.1 lb</article>
        """,
        metadata={
            "role": "secondary_battery_mass",
            "requested_sku": "48-11-1828",
            "subject_ref": "48-11-1828",
            "evidence_page_kind": "search_results",
        },
    )
    claims = adapter.extract(_identity(), [artifact])
    assert not any(c.property_key == "battery_mass_kg" for c in claims)


def test_milwaukee_redirected_detail_request_must_resolve_to_expected_detail_url():
    adapter = MilwaukeeAdapter()
    artifact = _secondary_artifact(
        "https://thepowertoolstore.com/products/milwaukee-48-11-1828",
        "secondary_battery_mass",
        "48-11-1828",
        """
            <article>Milwaukee 48-11-1828 battery - see details</article>
            <article>Milwaukee 48-11-1850 battery - Battery Weight 2.1 lb</article>
        """,
        resolved_url="https://thepowertoolstore.com/search?q=48-11-1828",
    )
    claims = adapter.extract(_identity(), [artifact])
    assert not any(c.property_key == "battery_mass_kg" for c in claims)


def test_milwaukee_kit_discovery_ignores_batteries_outside_in_the_box():
    adapter = MilwaukeeAdapter()
    artifact = SourceArtifact(
        url="https://www.milwaukeetool.com/Products/2607-22",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="""
            <h1>2607-22 M18 Hammer Drill/Driver Kit</h1>
            <h2>In The Box (5)</h2>
            <div>2607-20 M18 Hammer Drill/Driver</div>
            <div>48-11-1828 M18 REDLITHIUM XC Battery</div>
            <h2>Specs</h2>
            <h2>Related Products</h2>
            <div>48-11-1850 M18 REDLITHIUM XC5.0 Battery</div>
        """,
        metadata={"role": "kit", "kit_sku": "2607-22"},
    )
    requests = adapter.related_sources(_identity(), artifact)
    requested_batteries = {r.metadata.get("battery_model") for r in requests if r.metadata.get("role") == "battery"}
    assert requested_batteries == {"48-11-1828"}


def test_milwaukee_kit_discovery_requires_expected_kit_identity():
    adapter = MilwaukeeAdapter()
    artifact = SourceArtifact(
        url="https://www.milwaukeetool.com/Products/redirected",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="""
            <h1>Other product</h1>
            <h2>In The Box (3)</h2>
            <div>2607-20</div><div>48-11-1828</div>
            <h2>Specs</h2>
        """,
        metadata={"role": "kit", "kit_sku": "2607-22"},
    )
    assert adapter.related_sources(_identity(), artifact) == []


def test_milwaukee_shipping_weight_is_not_accepted_as_battery_mass():
    adapter = MilwaukeeAdapter()
    artifact = _secondary_artifact(
        "https://example.test/milwaukee-48-11-1828",
        "secondary_battery_mass",
        "48-11-1828",
        "<h1>Milwaukee 48-11-1828</h1><div>Shipping Weight 1.45 lb</div>",
    )
    claims = adapter.extract(_identity(), [artifact])
    assert not any(c.property_key == "battery_mass_kg" for c in claims)
    observations = adapter.observe(_identity(), [artifact])
    assert any(o.code == "SECONDARY_NON_PRODUCT_MASS_IGNORED" for o in observations)


def test_milwaukee_conflicting_battery_mass_blocks_profile_and_marks_readiness_issue():
    adapter = MilwaukeeAdapter()
    tool = _secondary_artifact(
        "https://example.test/milwaukee-2607-20",
        "secondary_tool_mass",
        "2607-20",
        "<h1>Milwaukee 2607-20</h1><div>Weight: 3.0 lb (Tool Only)</div>",
        "self",
    )
    battery_a = _secondary_artifact(
        "https://example.test/source-a/48-11-1828",
        "secondary_battery_mass",
        "48-11-1828",
        "<h1>Milwaukee 48-11-1828</h1><div>Battery Weight 1.54 lb</div>",
    )
    battery_b = _secondary_artifact(
        "https://example.test/source-b/48-11-1828",
        "secondary_battery_mass",
        "48-11-1828",
        "<h1>Milwaukee 48-11-1828</h1><div>Battery Weight 1.60 lb</div>",
    )

    claims = adapter.extract(_identity(), [tool, battery_a, battery_b])
    assert len([c for c in claims if c.property_key == "battery_mass_kg"]) == 2
    assert not any(c.property_key == "operational_mass_kg" for c in claims)

    issues = adapter.readiness_issues(claims, [])
    assert any(
        issue.code == "CONFLICTING_PHYSICAL_FACTS" and issue.property_key == "battery_mass_kg"
        for issue in issues
    )
    assert any(issue.code == "MISSING_OPERATIONAL_MASS" for issue in issues)


def test_milwaukee_lower_priority_rounding_difference_does_not_block_manufacturer_mass():
    adapter = MilwaukeeAdapter()
    primary = SourceArtifact(
        url=_identity().url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="<h1>2607-20 M18 Hammer Drill</h1><div>Tool Body Weight 3.0 lb</div>",
    )
    retailer = _secondary_artifact(
        "https://example.test/milwaukee-2607-20",
        "secondary_tool_mass",
        "2607-20",
        "<h1>Milwaukee 2607-20</h1><div>Weight: 3.1 lb (Tool Only)</div>",
        "self",
    )
    battery = SourceArtifact(
        url="https://www.milwaukeetool.com/Products/48-11-1828",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="<h1>48-11-1828</h1><div>Battery Weight 1.6 lb</div>",
        metadata={"role": "battery", "battery_model": "48-11-1828"},
    )

    claims = adapter.extract(_identity(), [primary, retailer, battery])
    profile = next(c for c in claims if c.property_key == "operational_mass_kg")
    assert profile.value == 2.086525
    assert profile.raw_value.startswith("3.0 lb tool body")

    issues = adapter.readiness_issues(claims, [])
    assert not any(issue.code == "CONFLICTING_PHYSICAL_FACTS" for issue in issues)
