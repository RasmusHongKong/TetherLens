from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)


def artifact(body: str) -> SourceArtifact:
    return SourceArtifact(
        url="https://neverletgo.com/products/example",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def identity(product_type: ProductType, name: str) -> ProductIdentity:
    return ProductIdentity(
        manufacturer="NLG",
        product_type=product_type,
        name=name,
        sku="example",
        url="https://neverletgo.com/products/example",
    )


def test_related_360_d_ring_title_does_not_materialize_hundreds_of_container_interfaces():
    html = """
    <p>Max Load: 30 KG / 66 LBS.</p>
    <p>Internal Anchor Point / Daisy Chain Max Load: 5 KG / 11 LBS (each).</p>
    <p>Max Lanyard Length: 200 CM.</p>
    <div>360 D Ring Loop Tool Tether for attaching tools.</div>
    """

    claims = NLGAdapter().extract(identity(ProductType.CONTAINER, "MEWP Bag"), [artifact(html)])

    anonymous_anchor_claims = [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
        and claim.subject_ref.startswith("anchor_")
    ]
    assert anonymous_anchor_claims == []
    assert any(
        claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
        and claim.subject_ref == "internal_anchor"
        and claim.property_key == "rated_capacity_kg"
        and claim.value == 5.0
        for claim in claims
    )


def test_plural_counted_d_rings_remain_valid_container_topology():
    html = """
    <p>6 integrated D Rings for tool lanyard attachment.</p>
    <p>Internal Anchor Point / Daisy Chain Max Load: 5 KG / 11 LBS (each).</p>
    """

    claims = NLGAdapter().extract(identity(ProductType.CONTAINER, "Tool Bag"), [artifact(html)])

    refs = {
        claim.subject_ref
        for claim in claims
        if claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
        and claim.property_key == "interface.role"
        and claim.value == "container_connection"
    }
    assert refs == {f"anchor_{index}" for index in range(1, 7)}


def test_related_loop_tool_tether_copy_does_not_create_container_loop_interface():
    html = """
    <p>MEWP Bag with secure internal tether points.</p>
    <div>360 D Ring Loop Tool Tether — secure tether point for tools.</div>
    """

    claims = NLGAdapter().extract(identity(ProductType.CONTAINER, "MEWP Bag"), [artifact(html)])

    assert not any(
        claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
        and claim.subject_ref == "loop_interface"
        and claim.property_key == "interface.loop_present"
        for claim in claims
    )


def test_named_loop_tool_attachment_preserves_legacy_loop_interface():
    html = "<p>360 D Ring Loop Tool Tether creates a secure tether point.</p>"

    claims = NLGAdapter().extract(
        identity(ProductType.TOOL_ATTACHMENT, "360 D Ring Loop Tool Tether"),
        [artifact(html)],
    )

    assert any(
        claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
        and claim.subject_ref == "loop_interface"
        and claim.property_key == "interface.loop_present"
        and claim.value is True
        for claim in claims
    )


def test_related_loop_copy_does_not_create_unnamed_anchor_attachment_loop():
    html = """
    <p>Safety Tool Belt with multiple D-ring anchor points.</p>
    <div>360 D Ring Loop Tool Tether — secure tether point for tools.</div>
    """

    claims = NLGAdapter().extract(
        identity(ProductType.ANCHOR_ATTACHMENT, "Superlight Safety Tool Belt"),
        [artifact(html)],
    )

    assert not any(
        claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
        and claim.subject_ref == "loop_interface"
        and claim.property_key == "interface.loop_present"
        for claim in claims
    )
