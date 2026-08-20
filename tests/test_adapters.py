from tetherlens_ingest.adapters import HiltiAdapter, MilwaukeeAdapter, NLGAdapter, StopDropAdapter
from tetherlens_ingest.models import ClaimSubjectType, IngestionResult, ProductIdentity, ProductType, SourceArtifact, SourceType


def artifact(body: str, url="https://example.test/product") -> SourceArtifact:
    return SourceArtifact(url=url, source_type=SourceType.MANUFACTURER_WEBPAGE, content_type="text/html", body=body)


def identity(manufacturer: str, product_type=ProductType.UNKNOWN, name: str | None = None) -> ProductIdentity:
    return ProductIdentity(manufacturer=manufacturer, product_type=product_type, name=name, url="https://example.test/product")


def values(claims):
    return {c.property_key: c.value for c in claims}


def keyed_values(claims):
    return {(c.subject_type.value, c.subject_ref, c.property_key): c.value for c in claims}


def test_nlg_extracts_load_length_and_heterogeneous_endpoint_features():
    html = """
    <h1>Bungee Tool Lanyard</h1>
    <div>Max Load: 5 KG / 11 LBS</div>
    <div>Dimensions: Extends 80cm to120cm</div>
    <div>360° Rotobiner with two-stage locking gate</div>
    <div>climbing cord loop</div>
    """
    claims = NLGAdapter().extract(identity("NLG", ProductType.TETHER), [artifact(html)])
    out = values(claims)
    keyed = keyed_values(claims)
    assert out["rated_capacity_kg"] == 5.0
    assert out["min_length_mm"] == 800.0
    assert out["max_length_mm"] == 1200.0
    assert out["tether.connection_count"] == 2
    assert keyed[("tether_connection_point", "connection_point_1", "connection_point.interface_type")] == "carabiner"
    assert keyed[("tether_connection_point", "connection_point_1", "connection_point.connector_spec_ref")] == "rotobiner"
    assert keyed[("tether_connection_point", "connection_point_2", "connection_point.interface_type")] == "loop"
    assert keyed[("connector_spec", "rotobiner", "connector.opening_action_count")] == 2
    assert keyed[("connector_spec", "rotobiner", "connector.swivel")] is True
    assert not any(c.property_key == "connection_point.role" for c in claims)


def test_nlg_marks_explicitly_reversible_rotobiner_and_loop_as_either():
    html = """
    <h1>Bungee Tool Lanyard</h1>
    <div>The Rotobiner can be attached to a tool or anchor point.</div>
    <div>The climbing cord loop can be attached to an anchor point or directly to the tool.</div>
    """
    claims = NLGAdapter().extract(identity("NLG", ProductType.TETHER), [artifact(html)])
    keyed = keyed_values(claims)
    assert keyed[("tether_connection_point", "connection_point_1", "connection_point.role")] == "either"
    assert keyed[("tether_connection_point", "connection_point_2", "connection_point.role")] == "either"


def test_nlg_extracts_explicit_endpoint_roles_and_distinct_connector_specs():
    html = """
    <h1>Heavy Duty Retractable Lanyard, Double Carabiner</h1>
    <div>Max Load: 3 KG</div>
    <div>Integral carabiner for belt or anchor and 360° Rotobiner for tool attachment.</div>
    """
    claims = NLGAdapter().extract(
        identity("NLG", ProductType.TETHER, "Heavy Duty Retractable Lanyard, Double Carabiner"),
        [artifact(html)],
    )
    keyed = keyed_values(claims)
    assert values(claims)["tether.connection_count"] == 2
    assert keyed[("tether_connection_point", "anchor_side", "connection_point.role")] == "anchor_side"
    assert keyed[("tether_connection_point", "anchor_side", "connection_point.interface_type")] == "carabiner"
    assert keyed[("tether_connection_point", "anchor_side", "connection_point.connector_spec_ref")] == "anchor_carabiner"
    assert keyed[("tether_connection_point", "tool_side", "connection_point.role")] == "tool_side"
    assert keyed[("tether_connection_point", "tool_side", "connection_point.connector_spec_ref")] == "tool_rotobiner"
    assert keyed[("connector_spec", "tool_rotobiner", "connector.swivel")] is True
    assert ("connector_spec", "anchor_carabiner", "connector.swivel") not in keyed


def test_nlg_extracts_360_degree_quick_clip_swivel_without_rotation_keyword():
    html = """
    <h1>Extended Bungee Tool Lanyard</h1>
    <div>Dual 360 degrees Quick Clip connectors at each end.</div>
    """
    claims = NLGAdapter().extract(
        identity("NLG", ProductType.TETHER, "Extended Bungee Tool Lanyard"),
        [artifact(html)],
    )
    keyed = keyed_values(claims)
    assert keyed[("connector_spec", "quick_clip", "connector.swivel")] is True


def test_nlg_does_not_treat_bare_360_degrees_as_tether_swivel():
    html = """
    <h1>Generic tether</h1>
    <div>360 degrees of visibility around the worker.</div>
    """
    claims = NLGAdapter().extract(identity("NLG", ProductType.TETHER), [artifact(html)])
    assert not any(c.property_key == "connector.swivel" for c in claims)


def test_nlg_does_not_treat_double_action_as_two_connectors():
    html = """
    <h1>Single carabiner tether</h1>
    <div>Max Load: 3 KG</div>
    <div>double-action locking gate</div>
    """
    claims = NLGAdapter().extract(identity("NLG", ProductType.TETHER), [artifact(html)])
    out = values(claims)
    assert "tether.connection_count" not in out
    assert not any(c.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT for c in claims)


def test_nlg_preserves_non_tether_loop_as_physical_interface():
    html = """
    <h1>360 D Ring Loop Tool Tether</h1>
    <div>Max Load: 3 KG</div>
    <div>360° rotating interface</div>
    <div>loop tool tether</div>
    """
    claims = NLGAdapter().extract(identity("NLG", ProductType.TOOL_ATTACHMENT), [artifact(html)])
    keyed = keyed_values(claims)
    assert keyed[("physical_interface", "loop_interface", "interface.loop_present")] is True
    assert not any(c.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT for c in claims)


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


def test_hilti_extracts_tether_rating_and_shared_connector_topology():
    html = """
    <h1>Tool lanyard</h1><div>#2261970</div>
    <div>Maximum load</div><div>14.99 lb</div>
    <div>Self-locking carabiner</div><div>double carabiner</div>
    """
    claims = HiltiAdapter().extract(identity("Hilti", ProductType.TETHER), [artifact(html)])
    out = values(claims)
    keyed = keyed_values(claims)
    assert out["rated_capacity_kg"] == 6.79935
    assert out["manufacturer_item_code"] == "2261970"
    assert out["connector.locking_mode"] == "auto_locking"
    assert out["tether.connection_count"] == 2
    for point_ref in ("connection_point_1", "connection_point_2"):
        assert keyed[("tether_connection_point", point_ref, "connection_point.interface_type")] == "carabiner"
        assert keyed[("tether_connection_point", point_ref, "connection_point.connector_spec_ref")] == "tether_connector"
    assert not any(c.property_key == "connection_point.role" for c in claims)


def test_hilti_operational_mass_includes_battery():
    assert HiltiAdapter.operational_mass(1.30, 0.55) == 1.85
    assert HiltiAdapter.operational_mass(1.30, 0.76) == 2.06


def test_stopdrop_extracts_sparse_variant_pair_and_shared_connector_topology():
    html = """
    <h1>BLACK WIRE COIL TOOL LANYARD</h1>
    <div>with 2 locking screwgate carabiner</div>
    <div>Weight 1M Max. Weight 3KG Clear</div>
    """
    claims = StopDropAdapter().extract(identity("StopDrop", ProductType.TETHER), [artifact(html)])
    out = values(claims)
    keyed = keyed_values(claims)
    assert out["variant.length_mm"] == 1000.0
    assert out["variant.rated_capacity_kg"] == 3.0
    assert out["connector.locking_mode"] == "manual_locking"
    for point_ref in ("connection_point_1", "connection_point_2"):
        assert keyed[("tether_connection_point", point_ref, "connection_point.interface_type")] == "carabiner"
        assert keyed[("tether_connection_point", point_ref, "connection_point.connector_spec_ref")] == "tether_connector"


def test_stopdrop_does_not_emit_tether_topology_for_non_tether_product():
    html = """
    <h1>Tool with accessory description</h1>
    <div>Compatible with 2 locking screwgate carabiner</div>
    """
    claims = StopDropAdapter().extract(identity("StopDrop", ProductType.TOOL), [artifact(html)])
    assert not any(c.property_key == "tether.connection_count" for c in claims)
    assert not any(c.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT for c in claims)
    assert not any(c.subject_type == ClaimSubjectType.CONNECTOR_SPEC for c in claims)


def test_ingestion_result_can_select_repeated_endpoint_properties():
    claims = NLGAdapter().extract(
        identity("NLG", ProductType.TETHER),
        [artifact("<div>360° Rotobiner</div><div>climbing cord loop</div>")],
    )
    result = IngestionResult(identity=identity("NLG", ProductType.TETHER), claims=claims)
    interface_claims = result.claims_for(
        "connection_point.interface_type",
        subject_type=ClaimSubjectType.TETHER_CONNECTION_POINT,
    )
    assert {claim.value for claim in interface_claims} == {"carabiner", "loop"}
    assert result.claims_for("connection_point.interface_type", subject_ref="connection_point_2")[0].value == "loop"


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
