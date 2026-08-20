from tetherlens_ingest.adapters import HiltiAdapter, MilwaukeeAdapter, NLGAdapter, StopDropAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType


def artifact(body: str, url="https://example.test/product") -> SourceArtifact:
    return SourceArtifact(url=url, source_type=SourceType.MANUFACTURER_WEBPAGE, content_type="text/html", body=body)


def identity(manufacturer: str, product_type=ProductType.UNKNOWN, name: str | None = None) -> ProductIdentity:
    return ProductIdentity(manufacturer=manufacturer, product_type=product_type, name=name, url="https://example.test/product")


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


def test_nlg_extracts_tether_connection_count_from_general_connector_wording():
    html = """
    <h1>Heavy Duty Retractable Lanyard, Double Carabiner</h1>
    <div>Max Load: 3 KG</div>
    <div>Integral carabiner for belt or anchor and Rotobiner for tool attachment.</div>
    """
    claims = NLGAdapter().extract(
        identity("NLG", ProductType.TETHER, "Heavy Duty Retractable Lanyard, Double Carabiner"),
        [artifact(html)],
    )
    out = values(claims)
    assert out["tether.connection_count"] == 2


def test_nlg_does_not_treat_double_action_as_two_connectors():
    html = """
    <h1>Single carabiner tether</h1>
    <div>Max Load: 3 KG</div>
    <div>double-action locking gate</div>
    """
    out = values(NLGAdapter().extract(identity("NLG", ProductType.TETHER), [artifact(html)]))
    assert "tether.connection_count" not in out


def test_nlg_extracts_max_lanyard_length_as_pairing_constraint():
    html = """
    <h1>Angle Grinder Bracket</h1>
    <div>Max Load: 3 KG</div>
    <div>Max Lanyard Length: 200 CM / 78 IN</div>
    """
    out = values(NLGAdapter().extract(identity("NLG", ProductType.TOOL_ATTACHMENT), [artifact(html)]))
    assert out["rated_capacity_kg"] == 3.0
    assert out["max_lanyard_length_mm"] == 2000.0
    assert "max_length_mm" not in out


def test_nlg_extracts_interface_scoped_bottom_d_ring_rating():
    html = """
    <h1>Comfort Safety Belt</h1>
    <div>Max Load: 30 KG</div>
    <div>Bottom D Rings load rating: 3 KG</div>
    <div>Dimensions: 76cm to 127cm</div>
    """
    claims = NLGAdapter().extract(identity("NLG", ProductType.ANCHOR_ATTACHMENT), [artifact(html)])
    keyed = {(claim.subject_ref, claim.property_key): claim.value for claim in claims}
    assert keyed[("self", "rated_capacity_kg")] == 30.0
    assert keyed[("bottom_d_ring", "rated_capacity_kg")] == 3.0
    assert ("self", "min_length_mm") not in keyed
    assert ("self", "max_length_mm") not in keyed


def test_nlg_extracts_wrist_use_limit_separately_from_product_rating():
    html = """
    <h1>Adjustable Wristband</h1>
    <div>Max Load: 3 KG</div>
    <div>Expert Tip: Based on medical research, NLG recommend that the maximum weight attached to the wrist is 1kg.</div>
    """
    claims = NLGAdapter().extract(identity("NLG", ProductType.ANCHOR_ATTACHMENT), [artifact(html)])
    keyed = {(claim.subject_ref, claim.property_key): claim.value for claim in claims}
    assert keyed[("self", "rated_capacity_kg")] == 3.0
    assert keyed[("wrist_anchor", "max_recommended_attached_mass_kg")] == 1.0


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


def test_milwaukee_keeps_dynamic_specs_as_observation_not_product_claim():
    html = """
    <h1>2607-20 M18 1/2 in Hammer Drill/Driver</h1>
    <div>Specs</div><div>Loading</div>
    """
    adapter = MilwaukeeAdapter()
    ident = ProductIdentity(
        manufacturer="Milwaukee",
        sku="2607-20",
        product_type=ProductType.TOOL,
        url="https://www.milwaukeetool.com/Products/2607-20",
    )
    art = artifact(html, url=ident.url)
    claims = adapter.extract(ident, [art])
    observations = adapter.observe(ident, [art])
    out = values(claims)
    assert out["manufacturer_item_code"] == "2607-20"
    assert out["battery_platform"] == "M18"
    assert "acquisition.dynamic_specs_detected" not in out
    observation_codes = {o.code for o in observations}
    assert "DYNAMIC_SPECS_DETECTED" in observation_codes
    codes = {i.code for i in adapter.readiness_issues(claims, observations)}
    assert "MISSING_TOOL_BODY_MASS" in codes
    assert "MISSING_BATTERY_MASS" in codes
    assert "MISSING_OPERATIONAL_MASS" in codes
