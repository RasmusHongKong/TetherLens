from tetherlens_ingest.adapters import KleinAdapter, NLGAdapter
from tetherlens_ingest.compatibility import EligibilityStatus, evaluate_attachment_eligibility
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    TetherSide,
    evaluate_endpoint_engagement,
)
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.resolution import (
    resolve_attachment_eligibility,
    resolve_connection_interfaces,
    resolve_tool_interface_features,
)


def artifact(body: str, *, url: str = "https://example.test/product") -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def test_nlg_tool_attachment_extracts_explicit_provided_ring_interface():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            name="360 D Ring Loop Tool Tether",
            sku="101363",
            url="https://example.test/nlg/101363",
        ),
        [
            artifact(
                "Create a tether point on any tool with a captive hole or handle and cinch it around the tool. "
                "The D Ring provides a connection point for a tool lanyard."
            )
        ],
    )

    interfaces = resolve_connection_interfaces(claims)
    assert len(interfaces) == 1
    interface = interfaces[0]
    assert interface.interface_id == "tether_side_ring"
    assert interface.role == ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
    assert interface.interface_type == "ring"


def test_nlg_does_not_invent_provided_ring_from_product_name_alone():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            name="360 D Ring Loop Tool Tether",
            sku="101363",
            url="https://example.test/nlg/101363",
        ),
        [artifact("Create a tether point on any tool with a captive hole or handle.")],
    )

    assert resolve_connection_interfaces(claims) == []


def test_tether_endpoint_claims_resolve_to_runtime_connection_interfaces():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TETHER,
            name="Retractable Tool Lanyard",
            sku="example",
            url="https://example.test/nlg/tether",
        ),
        [
            artifact(
                "Integral carabiner connects to the belt anchor while the Rotobiner provides tool attachment. "
                "Max Load: 3 kg."
            )
        ],
    )

    interfaces = resolve_connection_interfaces(claims)
    by_id = {interface.interface_id: interface for interface in interfaces}

    assert by_id["anchor_side"].role == ConnectionInterfaceRole.TETHER_CONNECTION
    assert by_id["anchor_side"].tether_side == TetherSide.ANCHOR_SIDE
    assert by_id["tool_side"].role == ConnectionInterfaceRole.TETHER_CONNECTION
    assert by_id["tool_side"].tether_side == TetherSide.TOOL_SIDE
    assert by_id["tool_side"].interface_type == "carabiner"
    assert by_id["tool_side"].connector_spec_ref == "tool_rotobiner"


def test_tool_side_endpoint_to_attachment_ring_is_unresolved_without_geometry():
    endpoint = ConnectionInterface(
        interface_id="tool_endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=TetherSide.TOOL_SIDE,
        connector_spec_ref="rotobiner",
    )
    target = ConnectionInterface(
        interface_id="provided_ring",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )

    result = evaluate_endpoint_engagement(endpoint, target)

    assert result.status == ConnectionStatus.UNRESOLVED
    assert result.compatible is False
    assert "geometry" in result.reason


def test_anchor_side_only_endpoint_cannot_serve_tool_attachment_interface():
    endpoint = ConnectionInterface(
        interface_id="anchor_endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=TetherSide.ANCHOR_SIDE,
    )
    target = ConnectionInterface(
        interface_id="provided_ring",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )

    result = evaluate_endpoint_engagement(endpoint, target)

    assert result.status == ConnectionStatus.INCOMPATIBLE
    assert "anchor-side-only" in result.reason


def test_connection_evaluation_is_identity_agnostic_for_equivalent_topology():
    target = ConnectionInterface(
        interface_id="generic_ring",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )
    first = ConnectionInterface(
        interface_id="brand_a_endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=TetherSide.EITHER,
    )
    second = ConnectionInterface(
        interface_id="brand_b_endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=TetherSide.EITHER,
    )

    assert evaluate_endpoint_engagement(first, target).status == ConnectionStatus.UNRESOLVED
    assert evaluate_endpoint_engagement(second, target).status == ConnectionStatus.UNRESOLVED


def test_klein_nlg_attachment_tether_vertical_slice_stops_at_missing_engagement_geometry():
    tool_claims = KleinAdapter().extract(
        ProductIdentity(
            manufacturer="Klein Tools",
            product_type=ProductType.TOOL,
            name="Insulated Screwdriver",
            sku="6826INS",
            url="https://example.test/klein/6826ins",
        ),
        [artifact("The tether hole in the handle provides added safety when working at height.")],
    )
    features = resolve_tool_interface_features(tool_claims)

    attachment_claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            name="360 D Ring Loop Tool Tether",
            sku="101363",
            url="https://example.test/nlg/101363",
        ),
        [
            artifact(
                "Create a tether point on any tool with a captive hole or handle and cinch it around the tool. "
                "The D Ring provides a connection point for a tool lanyard."
            )
        ],
    )
    eligibility = resolve_attachment_eligibility(attachment_claims)
    assert eligibility is not None
    assert evaluate_attachment_eligibility(eligibility, features).status == EligibilityStatus.ELIGIBLE

    tether_claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TETHER,
            name="Retractable Tool Lanyard",
            sku="example",
            url="https://example.test/nlg/tether",
        ),
        [
            artifact(
                "Integral carabiner connects to the belt anchor while the Rotobiner provides tool attachment. "
                "Max Load: 3 kg."
            )
        ],
    )

    attachment_interface = resolve_connection_interfaces(attachment_claims)[0]
    tether_interfaces = resolve_connection_interfaces(tether_claims)
    tool_endpoint = next(
        interface for interface in tether_interfaces if interface.tether_side == TetherSide.TOOL_SIDE
    )

    engagement = evaluate_endpoint_engagement(tool_endpoint, attachment_interface)
    assert engagement.status == ConnectionStatus.UNRESOLVED
    assert engagement.reason == (
        "interface topology is plausible but no validated geometry rule proves engagement"
    )
