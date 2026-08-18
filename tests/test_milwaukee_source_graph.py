from tetherlens_ingest.adapters import MilwaukeeAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.runner import IngestionRunner


class FakeFetcher:
    def __init__(self):
        self.calls = []

    def get(self, url, source_type=SourceType.MANUFACTURER_WEBPAGE):
        self.calls.append((url, source_type))
        if url.endswith("/2607-20"):
            body = """
            <h1>2607-20 M18 1/2 in Hammer Drill/Driver</h1>
            <div>Specs</div><div>Loading</div>
            <img alt="2607-22 kit"><img alt="2607-22CT kit">
            """
        elif url.endswith("/2607-22"):
            body = """
            <h1>2607-22 M18 Hammer Drill/Driver Kit</h1>
            <div>In The Box</div>
            <a href="/Products/2607-20">2607-20 M18 Hammer Drill/Driver</a>
            <a href="/Products/48-11-1828">48-11-1828 M18 REDLITHIUM XC Extended Capacity Battery</a>
            """
        elif url.endswith("/2607-22CT"):
            body = """
            <h1>2607-22CT M18 Compact Hammer Drill/Driver Kit</h1>
            <div>In The Box</div>
            <a href="/Products/2607-20">2607-20 M18 Hammer Drill/Driver</a>
            <a href="/Products/48-11-1815">48-11-1815 M18 Compact Battery</a>
            """
        elif url.endswith("/48-11-1828"):
            body = "<h1>48-11-1828 M18 REDLITHIUM XC Battery</h1><div>Specs Loading</div>"
        elif url.endswith("/48-11-1815"):
            body = "<h1>48-11-1815 M18 Compact Battery</h1><div>Specs Loading</div>"
        elif "grainger.com" in url and "2607-20" in url:
            body = "<h1>Milwaukee 2607-20</h1><div>Tool Weight 3 lb</div>"
        elif "homedepot.com" in url and "2607-20" in url:
            raise RuntimeError("retailer blocked test request")
        elif "grainger.com" in url and "48-11-1828" in url:
            body = "<h1>Milwaukee 48-11-1828</h1><div>Shipping Weight 1.45 lb</div>"
        elif "homedepot.com" in url and "48-11-1828" in url:
            body = "<h1>Milwaukee 48-11-1828</h1><div>Individual Battery Weight | 1.54 lb</div>"
        elif "48-11-1815" in url:
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


def test_milwaukee_graph_joins_first_party_kit_relationship_to_exact_sku_secondary_masses():
    result = IngestionRunner(FakeFetcher()).ingest(_identity(), MilwaukeeAdapter())
    claims = {(c.subject_type.value, c.subject_ref, c.property_key): c for c in result.claims}

    assert claims[("product", "self", "tool_body_mass_kg")].value == 1.360777
    assert claims[("product", "self", "tool_body_mass_kg")].evidence_method == "qualified_secondary_exact_sku"
    assert claims[("related_product", "48-11-1828", "battery_mass_kg")].value == 0.698532
    assert claims[("related_product", "48-11-1828", "battery_mass_kg")].evidence_method == "qualified_secondary_exact_sku"

    profile = claims[("operational_profile", "2607-20+48-11-1828", "operational_mass_kg")]
    assert profile.value == 2.059309
    assert profile.evidence_method == "derived_cross_source"
    assert len(profile.supporting_source_urls) == 2

    assert ("related_product", "48-11-1815", "battery_mass_kg") not in claims
    assert result.readiness_assessed is True
    assert result.issues == []

    observation_codes = [o.code for o in result.acquisition_observations]
    assert "RELATED_KIT_SOURCES_DISCOVERED" in observation_codes
    assert "BATTERY_RELATIONSHIP_DISCOVERED" in observation_codes
    assert "QUALIFIED_SECONDARY_SOURCES_VERIFIED" in observation_codes
    assert "SECONDARY_NON_PRODUCT_MASS_IGNORED" in observation_codes
    assert "RELATED_SOURCE_FETCH_FAILED" in observation_codes


def test_milwaukee_secondary_mass_requires_exact_sku_identity():
    adapter = MilwaukeeAdapter()
    artifact = SourceArtifact(
        url="https://www.homedepot.com/s/48-11-1828",
        source_type=SourceType.SECONDARY_WEBPAGE,
        content_type="text/html",
        body="<h1>Different battery 48-11-1850</h1><div>Individual Battery Weight 1.54 lb</div>",
        metadata={
            "role": "secondary_battery_mass",
            "requested_sku": "48-11-1828",
            "subject_ref": "48-11-1828",
        },
    )
    claims = adapter.extract(_identity(), [artifact])
    assert not any(c.property_key == "battery_mass_kg" for c in claims)


def test_milwaukee_shipping_weight_is_not_accepted_as_battery_mass():
    adapter = MilwaukeeAdapter()
    artifact = SourceArtifact(
        url="https://www.grainger.com/search?searchQuery=48-11-1828",
        source_type=SourceType.SECONDARY_WEBPAGE,
        content_type="text/html",
        body="<h1>Milwaukee 48-11-1828</h1><div>Shipping Weight 1.45 lb</div>",
        metadata={
            "role": "secondary_battery_mass",
            "requested_sku": "48-11-1828",
            "subject_ref": "48-11-1828",
        },
    )
    claims = adapter.extract(_identity(), [artifact])
    assert not any(c.property_key == "battery_mass_kg" for c in claims)
    observations = adapter.observe(_identity(), [artifact])
    assert any(o.code == "SECONDARY_NON_PRODUCT_MASS_IGNORED" for o in observations)
