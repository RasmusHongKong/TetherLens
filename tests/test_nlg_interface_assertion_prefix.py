from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.connection import ConnectionInterfaceRole
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.resolution import resolve_connection_interfaces


def _interfaces(body: str):
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            name="Mini Adhesive D Ring",
            sku="example",
            url="https://example.test/nlg/attachment",
        ),
        [
            SourceArtifact(
                url="https://example.test/product",
                source_type=SourceType.MANUFACTURER_WEBPAGE,
                content_type="text/html",
                body=f"<p>{body}</p>",
            )
        ],
    )
    return resolve_connection_interfaces(claims)


def test_neutral_intro_and_modified_d_ring_subject_preserve_positive_assertion():
    interfaces = _interfaces(
        "Utilising trusted 3M® adhesive technology the Mini Adhesive D Ring creates "
        "an ultra-secure tether point to attach a tool lanyard even on curved surfaces."
    )

    assert len(interfaces) == 1
    assert interfaces[0].role == ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
    assert interfaces[0].interface_type == "ring"


def test_competing_interface_prefix_is_not_treated_as_neutral_intro():
    interfaces = _interfaces(
        "The reinforced loop connects a tool lanyard and the Mini Adhesive D Ring "
        "creates a secure tether point."
    )

    assert interfaces == []


def test_non_ring_head_before_d_ring_is_not_bound_as_ring_subject():
    ambiguous = (
        "The strap behind the D Ring creates a secure tether point.",
        "The cord above the D Ring creates a secure tether point.",
        "The bracket around the D Ring connects to a tool lanyard.",
    )

    for body in ambiguous:
        assert _interfaces(body) == [], body


def test_epistemic_or_denied_wrapper_is_not_treated_as_affirmative_intro():
    denied_or_uncertain = (
        "It cannot be assumed that the D Ring creates a secure tether point.",
        "It is unclear whether the D Ring creates a secure tether point.",
        "It may be possible that the D Ring creates a secure tether point.",
    )

    for body in denied_or_uncertain:
        assert _interfaces(body) == [], body


def test_affirmative_intro_allowlist_preserves_other_bounded_marketing_forms():
    positive = (
        "Featuring reinforced polymer technology the Mini Adhesive D Ring creates a secure tether point.",
        "Built with reinforced polymer technology the Mini Adhesive D Ring creates a secure tether point.",
    )

    for body in positive:
        interfaces = _interfaces(body)
        assert len(interfaces) == 1, body
        assert interfaces[0].role == ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
        assert interfaces[0].interface_type == "ring"
