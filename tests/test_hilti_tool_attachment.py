from tetherlens_ingest.adapters.hilti_tool_attachment import HiltiAdapter
from tetherlens_ingest.connection import ConnectionInterfaceRole
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.resolution import resolve_connection_interfaces


def _identity(sku="2293133"):
    return ProductIdentity(
        manufacturer="Hilti",
        name="Retaining strap 15lb cordl.",
        sku=sku,
        product_type=ProductType.TOOL_ATTACHMENT,
        url=f"https://www.hilti.com/c/CLS_HEALTH_SAFETY/CLS_SAFETY_GEAR/{sku}",
    )


def _artifact(body: str):
    return SourceArtifact(
        url="https://www.hilti.com/c/CLS_HEALTH_SAFETY/CLS_SAFETY_GEAR/2293133",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def test_hilti_retaining_strap_extracts_metric_capacity_from_exact_product_option():
    claims = HiltiAdapter().extract(_identity(), [_artifact("""
        <h1>Retaining strap 15lb cordl.</h1>
        <div>#2293133</div>
        <div>Product options</div>
        <div>1x 15lb (6.8kg) Retaining strap assy</div>
    """)])
    by_key = {claim.property_key: claim for claim in claims}

    assert by_key["manufacturer_item_code"].value == "2293133"
    assert by_key["rated_capacity_kg"].value == 6.8
    assert by_key["rated_capacity_kg"].raw_value == "6.8kg"
    assert by_key["rated_capacity_kg"].evidence_method == "manufacturer_stated"


def test_hilti_retaining_strap_normalizes_only_functional_tether_attachment_point():
    claims = HiltiAdapter().extract(_identity(), [_artifact("""
        <h1>Retaining strap 15lb cordl.</h1>
        <div>#2293133</div>
        <p>Accessory for connecting compatible power tools to a Hilti tool lanyard</p>
    """)])

    interfaces = resolve_connection_interfaces(claims)
    assert len(interfaces) == 1
    interface = interfaces[0]
    assert interface.interface_id == "tether_attachment_point"
    assert interface.role == ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
    assert interface.interface_type == "attachment_point"
    assert interface.dimensions_mm == {}
    assert interface.attributes == {}

    assert not any(
        claim.property_key in {
            "feature.kind",
            "feature.captive_state",
            "interface.dimension.opening_width",
            "interface.attribute.manufacturer_item_code",
        }
        for claim in claims
    )


def test_hilti_retaining_strap_capacity_requires_expected_sku_on_resolved_page():
    claims = HiltiAdapter().extract(_identity("9999999"), [_artifact("""
        <h1>Retaining strap 15lb cordl.</h1>
        <div>#2293133</div>
        <div>1x 15lb (6.8kg) Retaining strap assy</div>
    """)])

    assert not any(claim.property_key == "rated_capacity_kg" for claim in claims)
    assert not resolve_connection_interfaces(claims)
