import json

from tetherlens_ingest.adapters import HiltiAdapter, MilwaukeeAdapter, NLGAdapter, StopDropAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType


def artifact(body: str, url="https://example.test/product") -> SourceArtifact:
    return SourceArtifact(url=url, source_type=SourceType.MANUFACTURER_WEBPAGE, content_type="text/html", body=body)


def identity(manufacturer: str, product_type=ProductType.UNKNOWN) -> ProductIdentity:
    return ProductIdentity(manufacturer=manufacturer, product_type=product_type, url="https://example.test/product")


def values(claims):
    return {c.property_key: c.value for c in claims}


def test_nlg_discovers_shopify_variant_skus():
    payload = {
        "products": [
            {
                "id": 1001,
                "title": "Example Lanyard",
                "handle": "example-lanyard",
                "variants": [
                    {"id": 2001, "sku": "101001"},
                    {"id": 2002, "sku": "101002"},
                ],
            }
        ]
    }
    source = SourceArtifact(
        url="https://neverletgo.com/collections/tool-lanyards/products.json?limit=250",
        source_type=SourceType.MANUFACTURER_JSON,
        content_type="application/json",
        body=json.dumps(payload),
    )

    identities = NLGAdapter().discover_collection(source)

    assert [item.sku for item in identities] == ["101001", "101002"]
    assert all(item.url == "https://neverletgo.com/products/example-lanyard" for item in identities)
    assert identities[0].manufacturer_ids == {"id": "1001", "variant_id": "2001"}
    assert identities[1].manufacturer_ids == {"id": "1001", "variant_id": "2002"}


def test_nlg_collection_discovery_falls_back_to_product_level_sku_and_dedupes():
    payload = {
        "products": [
            {
                "id": 1001,
                "title": "Example Tether Point",
                "url": "/products/example-tether-point",
                "sku": "101010",
            },
            {
                "id": 1001,
                "title": "Example Tether Point",
                "url": "/products/example-tether-point",
                "sku": "101010",
            },
        ]
    }
    source = SourceArtifact(
        url="https://neverletgo.com/collections/tether-points/products.json",
        source_type=SourceType.MANUFACTURER_JSON,
        content_type="application/json",
        body=json.dumps(payload),
    )

    identities = NLGAdapter().discover_collection(source)

    assert len(identities) == 1
    assert identities[0].sku == "101010"
    assert identities[0].url == "https://neverletgo.com/products/example-tether-point"


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


def test_nlg_extracts_reusable_tether_endpoint_and_auto_locking_patterns():
    html = """
    <h1>Heavy Duty Bungee Tool Lanyard</h1>
    <div>Max Load: 20 KG / 44 LBS</div>
    <div>Dimensions: Extends 80cm to 130cm</div>
    <p>At one end is a Dyneema loop. At the other end it features an automatic twistlock carabiner.</p>
    """
    claims = NLGAdapter().extract(identity("NLG", ProductType.TETHER), [artifact(html)])
    assert any(c.property_key == "tether.connection_count" and c.value == 2 for c in claims)
    endpoint_types = {
        (c.subject_ref, c.value)
        for c in claims
        if c.property_key == "interface.type"
    }
    assert ("tether_endpoint_1", "loop") in endpoint_types
    assert ("tether_endpoint_2", "carabiner") in endpoint_types
    assert any(c.property_key == "connector.locking_mode" and c.value == "auto_locking" for c in claims)


def test_nlg_extracts_tool_attachment_geometry_and_lanyard_limit():
    html = """
    <h1>Tether Choke</h1>
    <div>Max Load: 20 KG / 44 LBS</div>
    <div>Dimensions: 340 mm (L) x 25 mm (W)</div>
    <div>Max Lanyard Length: 2 m</div>
    <p>The Tether Choke cinches around a captive handle or hole and provides a V Ring for connection.</p>
    """
    claims = NLGAdapter().extract(identity("NLG", ProductType.TOOL_ATTACHMENT), [artifact(html)])
    out = values(claims)
    assert out["rated_capacity_kg"] == 20.0
    assert out["dimensions.length_mm"] == 340.0
    assert out["dimensions.width_mm"] == 25.0
    assert out["max_lanyard_length_mm"] == 2000.0
    assert any(c.property_key == "interface.type" and c.value == "v_ring" for c in claims)
    assert any(c.property_key == "interface.attachment_method" and c.value == "cinch" for c in claims)
    features = {c.value for c in claims if c.property_key == "interface.compatible_tool_feature"}
    assert {"captive_handle", "captive_hole"} <= features


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
