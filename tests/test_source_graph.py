from tetherlens_ingest.adapters import HiltiAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.runner import IngestionRunner


class FakeFetcher:
    def __init__(self):
        self.calls = []

    def get(self, url, source_type=SourceType.MANUFACTURER_WEBPAGE):
        self.calls.append(url)
        if "r13275669" in url:
            body = """
            <div>#2253847</div><div>Tool body weight</div><div>2.9 lb</div>
            <a href="/c/CLS_POWER_TOOLS_7125/CLS_BATT_CHARGERS_POWER_STATIONS_7125/r13250264">B 22-55 Nuron battery</a>
            <a href="/c/CLS_POWER_TOOLS_7125/CLS_BATT_CHARGERS_POWER_STATIONS_7125/r13250303">B 22-85 Nuron battery</a>
            """
        elif "r13250264" in url:
            body = "<h1>B 22-55 Nuron battery</h1><div>Weight: 1.21 lb</div>"
        elif "r13250303" in url:
            body = '<h1>B 22-85 Nuron battery</h1><script>{"label":"Weight","value":"1.67 lb"}</script>'
        else:
            raise AssertionError(url)
        return SourceArtifact(url=url, source_type=source_type, content_type="text/html", body=body)


def test_hilti_source_graph_discovers_and_derives_operational_mass_profiles():
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

    observations = {observation.code: observation.value for observation in result.acquisition_observations}
    assert observations["RELATED_SOURCES_DISCOVERED"] == 2
    assert "RELATED_SOURCES_SEEDED" not in observations
    assert "RELATED_SOURCE_FACT_MISSING" not in observations


def test_hilti_source_graph_falls_back_to_verified_seed_when_link_is_missing():
    primary = SourceArtifact(
        url="https://www.hilti.com/c/example/r13275669",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body='<a href="/c/CLS_POWER_TOOLS_7125/CLS_BATT_CHARGERS_POWER_STATIONS_7125/r13250264">B 22-55 Nuron battery</a>',
    )
    requests = HiltiAdapter().related_sources(
        ProductIdentity(
            manufacturer="Hilti",
            sku="2253847",
            product_type=ProductType.TOOL,
            url=primary.url,
            manufacturer_ids={"technical_family": "r13275669"},
        ),
        primary,
    )
    by_model = {request.metadata["battery_model"]: request for request in requests}
    assert by_model["B 22-55"].metadata["relationship_basis"] == "page_link"
    assert by_model["B 22-85"].metadata["relationship_basis"] == "benchmark_seed"
