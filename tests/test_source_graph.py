from tetherlens_ingest.adapters import HiltiAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.runner import IngestionRunner


class FakeFetcher:
    def __init__(self):
        self.calls = []

    def get(self, url, source_type=SourceType.MANUFACTURER_WEBPAGE):
        self.calls.append(url)
        if "r13275669" in url:
            body = "<div>#2253847</div><div>Tool body weight</div><div>2.9 lb</div>"
        elif "r13250264" in url:
            body = "<h1>B 22-55 Nuron battery</h1><div>Weight: 1.21 lb</div>"
        elif "r13250303" in url:
            body = "<h1>B 22-85 Nuron battery</h1><div>Weight: 1.67 lb</div>"
        else:
            raise AssertionError(url)
        return SourceArtifact(url=url, source_type=source_type, content_type="text/html", body=body)


def test_hilti_source_graph_derives_operational_mass_profiles():
    identity = ProductIdentity(
        manufacturer="Hilti",
        name="SF 4-22 Cordless drill driver",
        sku="2253847",
        product_type=ProductType.TOOL,
        url="https://www.hilti.com/c/example/r13275669",
        manufacturer_ids={"technical_family": "r13275669"},
    )
    result = IngestionRunner(FakeFetcher()).ingest(identity, HiltiAdapter())

    assert len(result.artifacts) == 3
    claims = {(claim.subject_type.value, claim.subject_ref, claim.property_key): claim for claim in result.claims}

    assert claims[("related_product", "B 22-55", "battery_mass_kg")].value == 0.548847
    assert claims[("related_product", "B 22-85", "battery_mass_kg")].value == 0.757499
    assert claims[("operational_profile", "2253847+B 22-55", "operational_mass_kg")].value == 1.864265
    assert claims[("operational_profile", "2253847+B 22-85", "operational_mass_kg")].value == 2.072917
    assert claims[("operational_profile", "2253847+B 22-55", "operational_mass_kg")].evidence_method == "derived"
    assert len(claims[("operational_profile", "2253847+B 22-55", "operational_mass_kg")].supporting_source_urls) == 1
    assert result.readiness_assessed is True
    assert result.issues == []
    assert {observation.code for observation in result.acquisition_observations} == {"RELATED_SOURCES_SEEDED"}
