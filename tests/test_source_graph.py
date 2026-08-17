import json

from tetherlens_ingest.adapters import HiltiAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.runner import IngestionRunner


APOLLO_STATE = {
    "apollo": {
        "state": {
            "Category:CLS_POWER_TOOLS_7125": {
                "__typename": "Category",
                "id": "CLS_POWER_TOOLS_7125",
            },
            "Category:CLS_BATT_CHARGERS_POWER_STATIONS_7125": {
                "__typename": "Category",
                "id": "CLS_BATT_CHARGERS_POWER_STATIONS_7125",
                "path": [{"__ref": "Category:CLS_POWER_TOOLS_7125"}],
            },
            "Product:r13250264": {
                "__typename": "Product",
                "id": "r13250264",
                "title": "B 22-55 Nuron battery",
                "type": "BATTERIES_AND_CHARGERS",
                "defaultCategory": {"__ref": "Category:CLS_BATT_CHARGERS_POWER_STATIONS_7125"},
            },
            "Product:r13250303": {
                "__typename": "Product",
                "id": "r13250303",
                "title": "B 22-85 Nuron battery",
                "type": "BATTERIES_AND_CHARGERS",
                "defaultCategory": {"__ref": "Category:CLS_BATT_CHARGERS_POWER_STATIONS_7125"},
            },
            "Product:r13275403": {
                "__typename": "Product",
                "id": "r13275403",
                "title": "C 4-22 Nuron compact charger",
                "type": "BATTERIES_AND_CHARGERS",
                "defaultCategory": {"__ref": "Category:CLS_BATT_CHARGERS_POWER_STATIONS_7125"},
            },
            "Product:2253847": {
                "__typename": "Product",
                "id": "2253847",
                "rangeId": "r13275669",
                "relatedProducts": [
                    {
                        "__typename": "RelatedProduct",
                        "product": {"__ref": "Product:r13250264"},
                        "type": "BATTERIES_CHARGERS",
                    },
                    {
                        "__typename": "RelatedProduct",
                        "product": {"__ref": "Product:r13250303"},
                        "type": "BATTERIES_CHARGERS",
                    },
                    {
                        "__typename": "RelatedProduct",
                        "product": {"__ref": "Product:r13275403"},
                        "type": "BATTERIES_CHARGERS",
                    },
                ],
            },
        }
    }
}


class FakeFetcher:
    def __init__(self):
        self.calls = []

    def get(self, url, source_type=SourceType.MANUFACTURER_WEBPAGE):
        self.calls.append(url)
        if "r13275669" in url:
            body = f"""
            <div>#2253847</div><div>Tool body weight</div><div>2.9 lb</div>
            <script id="hdms-website-state" type="application/json">{json.dumps(APOLLO_STATE)}</script>
            """
        elif "r13250264" in url:
            body = "<h1>B 22-55 Nuron battery</h1><div>Weight: 1.21 lb</div>"
        elif "r13250303" in url:
            body = '<h1>B 22-85 Nuron battery</h1><script>{"label":"Weight","value":"1.67 lb"}</script>'
        else:
            raise AssertionError(url)
        return SourceArtifact(url=url, source_type=source_type, content_type="text/html", body=body)


def _identity():
    return ProductIdentity(
        manufacturer="Hilti",
        name="SF 4-22 Cordless drill driver",
        sku="2253847",
        product_type=ProductType.TOOL,
        url="https://www.hilti.com/c/example/r13275669",
        manufacturer_ids={"technical_family": "r13275669"},
    )


def test_hilti_source_graph_discovers_apollo_batteries_and_derives_operational_mass_profiles():
    result = IngestionRunner(FakeFetcher()).ingest(_identity(), HiltiAdapter())

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


def test_hilti_apollo_discovery_excludes_charger_and_prefers_state_over_seed():
    body = f'<script id="hdms-website-state" type="application/json">{json.dumps(APOLLO_STATE)}</script>'
    primary = SourceArtifact(
        url="https://www.hilti.com/c/example/r13275669",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )
    requests = HiltiAdapter().related_sources(_identity(), primary)
    by_model = {request.metadata["battery_model"]: request for request in requests}

    assert set(by_model) == {"B 22-55", "B 22-85"}
    assert by_model["B 22-55"].metadata["relationship_basis"] == "apollo_state"
    assert by_model["B 22-85"].metadata["relationship_basis"] == "apollo_state"
    assert by_model["B 22-55"].url.endswith("/CLS_POWER_TOOLS_7125/CLS_BATT_CHARGERS_POWER_STATIONS_7125/r13250264")
    assert by_model["B 22-85"].url.endswith("/CLS_POWER_TOOLS_7125/CLS_BATT_CHARGERS_POWER_STATIONS_7125/r13250303")


def test_hilti_source_graph_falls_back_to_verified_seed_when_apollo_edge_is_missing():
    partial_state = json.loads(json.dumps(APOLLO_STATE))
    partial_state["apollo"]["state"]["Product:2253847"]["relatedProducts"] = [
        {
            "__typename": "RelatedProduct",
            "product": {"__ref": "Product:r13250264"},
            "type": "BATTERIES_CHARGERS",
        }
    ]
    primary = SourceArtifact(
        url="https://www.hilti.com/c/example/r13275669",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=f'<script id="hdms-website-state" type="application/json">{json.dumps(partial_state)}</script>',
    )
    requests = HiltiAdapter().related_sources(_identity(), primary)
    by_model = {request.metadata["battery_model"]: request for request in requests}
    assert by_model["B 22-55"].metadata["relationship_basis"] == "apollo_state"
    assert by_model["B 22-85"].metadata["relationship_basis"] == "benchmark_seed"
