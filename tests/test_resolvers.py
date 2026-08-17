import json

from tetherlens_ingest.adapters import HiltiAdapter, MilwaukeeAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.resolvers import GraingerToolMassResolver
from tetherlens_ingest.runner import IngestionRunner


class MilwaukeeResolverFetcher:
    def __init__(self):
        self.calls = []

    def get(self, url, source_type=SourceType.MANUFACTURER_WEBPAGE):
        self.calls.append(url)
        if "grainger.ca/en/search" in url:
            body = '<a href="/en/product/M18-CHAD-BARE-TOOL/p/MTL2602-20">MILWAUKEE 2602-20</a>'
        elif "grainger.ca/en/product" in url:
            body = """
            <h1>M18 CHAD BARE TOOL</h1><div>MILWAUKEE</div>
            <div>Mfr. Model # 2602-20</div><div>Shipping Weight 4.0 lbs</div>
            <div>Includes Tool Only</div><div>Tool Weight 3.5 lb.</div>
            """
        elif "/api/v1/products/2602-20" in url:
            body = json.dumps({"status":"OK","data":{"result":{"sku":"2602-20","specs":{"batterySystem":{"value":"M18"}}}}})
        elif "/api/v1/products/48-11-1828" in url:
            body = json.dumps({"status":"OK","data":{"result":{"sku":"48-11-1828","specs":{"weight":{"value":"1.54 lb"}}}}})
        elif "milwaukeetool.com" in url:
            body = '<div>2602-20 M18</div><div>battery 48-11-1828</div>'
        else:
            raise AssertionError(url)
        return SourceArtifact(url=url, source_type=source_type, content_type="text/html", body=body)


def test_missing_manufacturer_mass_is_resolved_by_exact_sku_secondary_and_operational_mass_is_derived():
    identity = ProductIdentity(
        manufacturer="Milwaukee", name="M18 Hammer Drill/Driver", sku="2602-20",
        product_type=ProductType.TOOL,
        url="https://www.milwaukeetool.com/products/details/example/2602-20",
    )
    result = IngestionRunner(MilwaukeeResolverFetcher(), [GraingerToolMassResolver()]).ingest(identity, MilwaukeeAdapter())
    claims = {(c.subject_ref, c.property_key): c for c in result.claims}

    body = claims[("self", "tool_body_mass_kg")]
    assert body.raw_value == "3.5 lb"
    assert body.value == 1.587573
    assert body.evidence_method == "qualified_secondary_exact_sku"
    assert claims[("2602-20+48-11-1828", "operational_mass_kg")].value == 2.286105
    assert result.issues == []
    assert any(o.code == "REQUIRED_FACT_RESOLVED_SECONDARY" for o in result.acquisition_observations)


def test_secondary_record_is_rejected_when_exact_model_identity_does_not_match():
    fetcher = MilwaukeeResolverFetcher()
    original_get = fetcher.get
    def mismatched(url, source_type=SourceType.MANUFACTURER_WEBPAGE):
        artifact = original_get(url, source_type)
        if "grainger.ca/en/product" in url:
            artifact.body = artifact.body.replace("2602-20", "2602-21")
        return artifact
    fetcher.get = mismatched
    identity = ProductIdentity(manufacturer="Milwaukee", sku="2602-20", product_type=ProductType.TOOL, url="https://www.milwaukeetool.com/products/details/example/2602-20")
    result = IngestionRunner(fetcher, [GraingerToolMassResolver()]).ingest(identity, MilwaukeeAdapter())
    assert not any(c.property_key == "tool_body_mass_kg" for c in result.claims)
    assert any(i.code == "MISSING_TOOL_BODY_MASS" for i in result.issues)


def test_resolver_skips_secondary_lookup_when_manufacturer_already_supplies_mass():
    class HiltiFetcher:
        def __init__(self): self.calls = []
        def get(self, url, source_type=SourceType.MANUFACTURER_WEBPAGE):
            self.calls.append(url)
            return SourceArtifact(url=url, source_type=source_type, content_type="text/html", body="#2253847 Tool body weight 2.9 lb")

    fetcher = HiltiFetcher()
    identity = ProductIdentity(manufacturer="Hilti", sku="2253847", product_type=ProductType.TOOL, url="https://www.hilti.com/example")
    result = IngestionRunner(fetcher, [GraingerToolMassResolver()]).ingest(identity, HiltiAdapter())
    assert any(c.property_key == "tool_body_mass_kg" for c in result.claims)
    assert not any("grainger.ca" in url for url in fetcher.calls)
    assert any(o.code == "REQUIRED_FACT_ALREADY_SATISFIED" for o in result.acquisition_observations)
