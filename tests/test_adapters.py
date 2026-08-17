from tetherlens_ingest.adapters import HiltiAdapter, MilwaukeeAdapter, NLGAdapter, StopDropAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType


def artifact(body: str, url="https://example.test/product") -> SourceArtifact:
    return SourceArtifact(url=url, source_type=SourceType.MANUFACTURER_WEBPAGE, content_type="text/html", body=body)


def identity(manufacturer: str, product_type=ProductType.UNKNOWN) -> ProductIdentity:
    return ProductIdentity(manufacturer=manufacturer, product_type=product_type, url="https://example.test/product")


def values(claims):
    return {c.property_key: c.value for c in claims}


def test_nlg_extracts_load_length_and_connector_features():
    html = """
    <h1>Bungee Tool Lanyard</h1>
    <div>Max Load: 5 KG / 11 LBS</div>
    <div>Dimensions: Extends 80cm to120cm</div>
    <div>360° Rotobiner with two-stage locking gate</div>
    <div>climbing cord loop</div>
    """
    out = values(NLGAdapter().extract(identity("NLG", ProductType.TETHER), [artifact(html)]))
    assert out["rated_capacity_kg"] == 5.0
    assert out["min_length_mm"] == 800.0
    assert out["max_length_mm"] == 1200.0
    assert out["connector.opening_action_count"] == 2
    assert out["connector.swivel"] is True
    assert out["interface.loop_present"] is True


def test_hilti_extracts_tether_rating_and_connector():
    html = """
    <h1>Tool lanyard</h1><div>#2261970</div>
    <div>Maximum load</div><div>14.99 lb</div>
    <div>Self-locking carabiner</div><div>double carabiner</div>
    """
    out = values(HiltiAdapter().extract(identity("Hilti", ProductType.TETHER), [artifact(html)]))
    assert out["rated_capacity_kg"] == 6.79935
    assert out["manufacturer_item_code"] == "2261970"
    assert out["connector.locking_mode"] == "auto_locking"
    assert out["tether.connection_count"] == 2


def test_hilti_operational_mass_includes_battery():
    assert HiltiAdapter.operational_mass(1.30, 0.55) == 1.85
    assert HiltiAdapter.operational_mass(1.30, 0.76) == 2.06


def test_stopdrop_extracts_sparse_variant_pair():
    html = """
    <h1>BLACK WIRE COIL TOOL LANYARD</h1>
    <div>with 2 locking screwgate carabiner</div>
    <div>Weight 1M Max. Weight 3KG Clear</div>
    """
    claims = StopDropAdapter().extract(identity("StopDrop", ProductType.TETHER), [artifact(html)])
    out = values(claims)
    assert out["variant.length_mm"] == 1000.0
    assert out["variant.rated_capacity_kg"] == 3.0
    assert out["connector.locking_mode"] == "manual_locking"


def test_milwaukee_separates_dynamic_acquisition_state_from_product_claims():
    html = """
    <h1>2602-20 M18 Cordless Hammer Drill Driver</h1>
    <div>Specs</div><div>Loading</div>
    <div>Runs on M18 XC Extended Capacity Battery and M18 Compact Battery</div>
    """
    adapter = MilwaukeeAdapter()
    art = artifact(html)
    claims = adapter.extract(identity("Milwaukee", ProductType.TOOL), [art])
    observations = adapter.observe(identity("Milwaukee", ProductType.TOOL), [art])
    out = values(claims)
    assert out["manufacturer_item_code"] == "2602-20"
    assert out["battery_platform"] == "M18"
    assert "acquisition.dynamic_specs_detected" not in out
    observation_codes = {o.code for o in observations}
    assert "BATTERY_CONFIGURATION_REQUIRED" in observation_codes
    assert "DYNAMIC_SPECS_DETECTED" in observation_codes
    codes = {i.code for i in adapter.readiness_issues(claims, observations)}
    assert "MISSING_OPERATIONAL_MASS" in codes
    assert "DYNAMIC_SPECS_UNRESOLVED" in codes
