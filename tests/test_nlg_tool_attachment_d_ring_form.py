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
        url="https://example.test/attachment",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def identity(name: str = "Tool Attachment") -> ProductIdentity:
    return ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TOOL_ATTACHMENT,
        name=name,
        sku="example",
        url="https://example.test/attachment",
    )


def test_explicit_tool_attachment_d_ring_preserves_form_on_same_interface_subject():
    claims = NLGAdapter().extract(
        identity(),
        [artifact("<p>The D Ring creates a secure tether point to attach a tool lanyard.</p>")],
    )

    physical_claims = [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
        and claim.subject_ref == "tether_side_ring"
    ]
    by_key = {claim.property_key: claim for claim in physical_claims}

    assert by_key["interface.role"].value == "tool_attachment_tether_side"
    assert by_key["interface.type"].value == "ring"
    form = by_key["interface.attribute.ring_form"]
    assert form.value == "d_ring"
    assert "D Ring" in (form.raw_value or "")
    assert form.source_url == "https://example.test/attachment"

    interfaces = resolve_connection_interfaces(claims)
    assert len(interfaces) == 1
    interface = interfaces[0]
    assert interface.interface_id == "tether_side_ring"
    assert interface.role == ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
    assert interface.interface_type == "ring"
    assert interface.attributes == {"ring_form": "d_ring"}


def test_generic_ring_and_d_ring_product_name_do_not_invent_d_ring_form():
    claims = NLGAdapter().extract(
        identity("Mini Adhesive D Ring"),
        [artifact("<p>The ring creates a secure tether point to attach a tool lanyard.</p>")],
    )

    assert not any(
        claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
        for claim in claims
    )
    assert resolve_connection_interfaces(claims) == []
