from tetherlens_ingest.adapters import HiltiAdapter, MilwaukeeAdapter, NLGAdapter, StopDropAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType


def artifact(body: str, url="https://example.test/product", source_type=SourceType.MANUFACTURER_WEBPAGE, metadata=None) -> SourceArtifact:
    return SourceArtifact(url=url, source_type=source_type, content_type="text/html", body=body, metadata=metadata or {})


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


def test_milwaukee_discovers_product_and_battery_api_sources_from_rsc_family_data():
    html = '''
    <h1>2602-20 M18 Cordless Hammer Drill Driver</h1>
    <script>self.__next_f.push([1,"2602-22 kit SALEABLE_ITEM 48-11-1828 M18 REDLITHIUM XC Battery; 2602-22CT kit SALEABLE_ITEM 48-11-1815 M18 Compact Battery"])</script>
    '''
    adapter = MilwaukeeAdapter()
    ident = ProductIdentity(manufacturer="Milwaukee", product_type=ProductType.TOOL, sku="2602-20", url="https://www.milwaukeetool.com/products/details/example/2602-20")
    requests = adapter.related_sources(ident, artifact(html, ident.url))
    urls = {request.url for request in requests}
    assert "https://www.milwaukeetool.com/api/v1/products/2602-20?language=en" in urls
    assert "https://www.milwaukeetool.com/api/v1/products/48-11-1815?language=en" in urls
    assert "https://www.milwaukeetool.com/api/v1/products/48-11-1828?language=en" in urls
    assert all(request.source_type == SourceType.MANUFACTURER_JSON for request in requests)


def test_milwaukee_api_closes_acquisition_gap_but_preserves_missing_mass_gap():
    adapter = MilwaukeeAdapter()
    ident = ProductIdentity(manufacturer="Milwaukee", product_type=ProductType.TOOL, sku="2602-20", url="https://www.milwaukeetool.com/products/details/example/2602-20")
    primary = artifact("<h1>2602-20 M18</h1>", ident.url)
    product_api = artifact(
        '{"status":"OK","data":{"result":{"sku":"2602-20","specs":{"batterySystem":{"value":"M18"}},"specs2":[]}}}',
        "https://www.milwaukeetool.com/api/v1/products/2602-20?language=en",
        SourceType.MANUFACTURER_JSON,
        {"role": "product_api", "sku": "2602-20"},
    )
    compact_api = artifact(
        '{"status":"OK","data":{"result":{"sku":"48-11-1815","specs":{"batterySystem":{"value":"M18"}},"specs2":[]}}}',
        "https://www.milwaukeetool.com/api/v1/products/48-11-1815?language=en",
        SourceType.MANUFACTURER_JSON,
        {"role": "battery_api", "sku": "48-11-1815", "relationship_basis": "rsc_family_graph"},
    )
    xc_api = artifact(
        '{"status":"OK","data":{"result":{"sku":"48-11-1828","specs":{"weight":{"value":"1.54 lb"}},"specs2":[{"key":"netWeight","value":"1.6 lb"}]}}}',
        "https://www.milwaukeetool.com/api/v1/products/48-11-1828?language=en",
        SourceType.MANUFACTURER_JSON,
        {"role": "battery_api", "sku": "48-11-1828", "relationship_basis": "rsc_family_graph"},
    )
    artifacts = [primary, product_api, compact_api, xc_api]
    claims = adapter.extract(ident, artifacts)
    observations = adapter.observe(ident, artifacts)

    assert values(claims)["manufacturer_item_code"] == "2602-20"
    assert values(claims)["battery_platform"] == "M18"
    battery_claim = next(claim for claim in claims if claim.property_key == "battery_mass_kg")
    assert battery_claim.subject_ref == "48-11-1828"
    assert battery_claim.value == 0.698532
    assert not any(claim.property_key == "operational_mass_kg" for claim in claims)

    observation_codes = {observation.code for observation in observations}
    assert "PRODUCT_API_ACQUIRED" in observation_codes
    assert "RELATED_SOURCES_DISCOVERED" in observation_codes
    assert "MANUFACTURER_TOOL_MASS_MISSING" in observation_codes
    assert "RELATED_SOURCE_FACT_MISSING" in observation_codes
    assert "CONFLICTING_MANUFACTURER_MASS" in observation_codes
    assert "DYNAMIC_SPECS_DETECTED" not in observation_codes

    issue_codes = {issue.code for issue in adapter.readiness_issues(claims, observations)}
    assert "MISSING_OPERATIONAL_MASS" in issue_codes
    assert "MISSING_TOOL_BODY_MASS" in issue_codes
    assert "DYNAMIC_SPECS_UNRESOLVED" not in issue_codes
