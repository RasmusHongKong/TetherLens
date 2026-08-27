from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.connection import ConnectionInterfaceRole
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.resolution import resolve_connection_interfaces


def artifact(body: str) -> SourceArtifact:
    return SourceArtifact(
        url="https://example.test/container",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def identity(product_type: ProductType = ProductType.CONTAINER) -> ProductIdentity:
    return ProductIdentity(
        manufacturer="NLG",
        product_type=product_type,
        name="Container",
        sku="example",
        url="https://example.test/container",
    )


def physical_claims(body: str, product_type: ProductType = ProductType.CONTAINER):
    return [
        claim
        for claim in NLGAdapter().extract(identity(product_type), [artifact(body)])
        if claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
    ]


def keyed(claims):
    return {
        (claim.subject_ref, claim.property_key): claim.value
        for claim in claims
    }


def test_repeated_internal_anchor_points_become_distinct_unknown_form_interfaces():
    html = """
    <p>Internally the pouch features 4 load-rated anchor points that can be used to securely attach tools.</p>
    <p>4 integrated anchor points for multiple tool lanyard attachment.</p>
    <p>Internal Anchor Point / Daisy Chain Max Load: 5 KG / 11 LBS (each)</p>
    """
    claims = physical_claims(html)
    out = keyed(claims)

    assert not any(claim.subject_ref == "internal_anchor" for claim in claims)
    for index in range(1, 5):
        ref = f"internal_anchor_{index}"
        assert out[(ref, "interface.role")] == "container_connection"
        assert out[(ref, "interface.location_description")] == "internal"
        assert out[(ref, "rated_capacity_kg")] == 5.0
        assert (ref, "interface.type") not in out

    interfaces = resolve_connection_interfaces(claims)
    assert len(interfaces) == 4
    assert {interface.interface_id for interface in interfaces} == {
        "internal_anchor_1",
        "internal_anchor_2",
        "internal_anchor_3",
        "internal_anchor_4",
    }
    assert all(interface.role == ConnectionInterfaceRole.CONTAINER_CONNECTION for interface in interfaces)
    assert all(interface.interface_type == "unknown" for interface in interfaces)
    assert all(interface.location_description == "internal" for interface in interfaces)


def test_split_internal_external_counts_and_d_ring_form_resolve_without_holder_false_positive():
    html = """
    <p>Tall Tool Bag with 8 load-rated anchor points — 2 external, 6 internal.</p>
    <p>The 4 external tool holders and 6 integrated D Rings for tool lanyard attachment make this an all-in-one setup.</p>
    <p>Internal Anchor Point / Daisy Chain Max Load: 5 KG / 11 LBS (each)</p>
    """
    claims = physical_claims(html)
    out = keyed(claims)

    for index in range(1, 7):
        ref = f"internal_anchor_{index}"
        assert out[(ref, "interface.role")] == "container_connection"
        assert out[(ref, "interface.location_description")] == "internal"
        assert out[(ref, "interface.type")] == "ring"
        assert out[(ref, "rated_capacity_kg")] == 5.0

    for index in range(1, 3):
        ref = f"external_anchor_{index}"
        assert out[(ref, "interface.role")] == "container_connection"
        assert out[(ref, "interface.location_description")] == "external"
        assert out[(ref, "rated_capacity_kg")] == 5.0
        assert (ref, "interface.type") not in out

    assert not any("holder" in claim.subject_ref for claim in claims)
    interfaces = resolve_connection_interfaces(claims)
    assert len(interfaces) == 8
    internal = [interface for interface in interfaces if interface.location_description == "internal"]
    external = [interface for interface in interfaces if interface.location_description == "external"]
    assert len(internal) == 6
    assert all(interface.interface_type == "ring" for interface in internal)
    assert len(external) == 2
    assert all(interface.interface_type == "unknown" for interface in external)


def test_counted_mounting_d_rings_do_not_become_container_connections():
    html = """
    <p>2 external D Rings on the rear of the pouch allow it to be mounted onto a harness, belt or rail.</p>
    """
    claims = physical_claims(html)
    assert not any(claim.property_key == "interface.role" for claim in claims)
    assert resolve_connection_interfaces(claims) == []


def test_storage_lifting_rope_management_and_structural_features_are_not_promoted():
    html = """
    <p>Internally the bucket features 6 load-rated anchor points for securing tools, as well as colour-coded loops at the base and top to manage main and backup rope.</p>
    <p>Load-rated lifting handle.</p>
    <p>6 integrated anchor points for multiple tool lanyard attachment.</p>
    <p>Removable top ring allows the bag to be packed down for storage.</p>
    <p>Dual colour-coded loops at base and top to easily manage main and backup rope.</p>
    <p>Load-rated external daisy chain for easily attaching items to the bucket.</p>
    <p>Internal Anchor Point / Daisy Chain Max Load: 5 KG / 11 LBS (each)</p>
    """
    claims = physical_claims(html)
    interfaces = resolve_connection_interfaces(claims)

    assert len(interfaces) == 6
    assert {interface.interface_id for interface in interfaces} == {
        f"internal_anchor_{index}" for index in range(1, 7)
    }
    assert all(interface.location_description == "internal" for interface in interfaces)
    assert not any(
        token in claim.subject_ref
        for claim in claims
        for token in ("lifting", "rope", "top_ring", "daisy")
    )


def test_container_layer_does_not_reclassify_anchor_attachment_d_rings():
    html = """
    <p>Top D-rings are to attach braces to.</p>
    <p>Bottom D Rings load rating: 3 KG.</p>
    <p>Integrated D-ring anchors provide secure points to directly tether your tools.</p>
    """
    claims = physical_claims(html, ProductType.ANCHOR_ATTACHMENT)
    assert not any(
        claim.property_key == "interface.role" and claim.value == "container_connection"
        for claim in claims
    )


def test_conflicting_repeated_counts_fail_closed_for_that_location():
    html = """
    <p>Internally the pouch features 4 load-rated anchor points for securing tools.</p>
    <p>Internally the pouch features 6 load-rated anchor points for securing tools.</p>
    <p>Internal Anchor Point / Daisy Chain Max Load: 5 KG / 11 LBS (each)</p>
    """
    claims = physical_claims(html)
    assert not any(
        claim.property_key == "interface.role"
        and claim.subject_ref.startswith("internal_anchor_")
        for claim in claims
    )
