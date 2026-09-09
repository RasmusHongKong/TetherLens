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


def artifact(body: str, url: str = "https://example.test/container") -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.CONTAINER,
        name="Container",
        sku="example",
        url="https://example.test/container",
    )


def physical_claims(body: str):
    return [
        claim
        for claim in NLGAdapter().extract(identity(), [artifact(body)])
        if claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
    ]


def test_uniquely_bound_repeated_container_d_rings_preserve_form_and_identity():
    html = """
    <p>Tall Tool Bag with 8 load-rated anchor points — 2 external, 6 internal.</p>
    <p>The 4 external tool holders and 6 integrated D Rings for tool lanyard attachment make this an all-in-one setup.</p>
    <p>Internal Anchor Point / Daisy Chain Max Load: 5 KG / 11 LBS (each)</p>
    """
    claims = physical_claims(html)
    form_claims = [
        claim
        for claim in claims
        if claim.property_key == "interface.attribute.ring_form"
    ]

    assert {claim.subject_ref for claim in form_claims} == {
        f"internal_anchor_{index}" for index in range(1, 7)
    }
    assert all(claim.value == "d_ring" for claim in form_claims)
    assert all("D Rings" in (claim.raw_value or "") for claim in form_claims)
    assert all(claim.source_url == "https://example.test/container" for claim in form_claims)

    interfaces = resolve_connection_interfaces(claims)
    internal = [
        interface
        for interface in interfaces
        if interface.location_description == "internal"
    ]
    external = [
        interface
        for interface in interfaces
        if interface.location_description == "external"
    ]

    assert len(internal) == 6
    assert {interface.interface_id for interface in internal} == {
        f"internal_anchor_{index}" for index in range(1, 7)
    }
    assert all(
        interface.role == ConnectionInterfaceRole.CONTAINER_CONNECTION
        for interface in internal
    )
    assert all(interface.interface_type == "ring" for interface in internal)
    assert all(interface.attributes == {"ring_form": "d_ring"} for interface in internal)

    assert len(external) == 2
    assert all(interface.interface_type == "unknown" for interface in external)
    assert all("ring_form" not in interface.attributes for interface in external)


def test_generic_ring_wording_is_not_promoted_to_d_ring_form():
    html = """
    <p>Tall Tool Bag with 8 load-rated anchor points — 2 external, 6 internal.</p>
    <p>6 integrated rings for tool lanyard attachment.</p>
    """
    claims = physical_claims(html)

    assert not any(
        claim.property_key == "interface.attribute.ring_form"
        for claim in claims
    )


def test_ambiguous_equal_count_locations_do_not_receive_d_ring_form():
    html = """
    <p>Tool Bag with 8 load-rated anchor points — 4 external, 4 internal.</p>
    <p>4 integrated D Rings for tool lanyard attachment.</p>
    """
    claims = physical_claims(html)
    interfaces = resolve_connection_interfaces(claims)

    assert len(interfaces) == 8
    assert all(interface.interface_type == "unknown" for interface in interfaces)
    assert all("ring_form" not in interface.attributes for interface in interfaces)
    assert not any(
        claim.property_key == "interface.attribute.ring_form"
        for claim in claims
    )


def test_mounting_d_rings_do_not_gain_container_target_form():
    claims = physical_claims(
        "<p>2 external D Rings on the rear of the pouch allow it to be mounted onto a harness, belt or rail.</p>"
    )

    assert not any(
        claim.property_key == "interface.role"
        and claim.value == "container_connection"
        for claim in claims
    )
    assert not any(
        claim.property_key == "interface.attribute.ring_form"
        for claim in claims
    )
