from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    ConnectorSpec,
    TetherSide,
    evaluate_endpoint_engagement,
)


def cinch_endpoint() -> ConnectionInterface:
    return ConnectionInterface(
        interface_id="loop",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="loop",
        tether_side=TetherSide.EITHER,
        connector_spec_ref="cinch_loop",
    )


def cinch_spec() -> ConnectorSpec:
    return ConnectorSpec(
        connector_spec_id="cinch_loop",
        attributes={"engagement_method": "cinch"},
    )


def evaluate(target: ConnectionInterface):
    spec = cinch_spec()
    return evaluate_endpoint_engagement(
        cinch_endpoint(),
        target,
        connector_specs={spec.connector_spec_id: spec},
    )


def test_v1_allows_ring_on_container_or_anchor_attachment_side():
    for role in (
        ConnectionInterfaceRole.CONTAINER_CONNECTION,
        ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
    ):
        result = evaluate(
            ConnectionInterface(
                interface_id=f"ring:{role.value}",
                role=role,
                interface_type="ring",
            )
        )
        assert result.status == ConnectionStatus.REQUIRES_VERIFICATION
        assert result.verification_family == "cinch_loop_to_closed_interface.v1"


def test_v1_allows_direct_captive_tool_hole_or_handle():
    for interface_type in ("captive_hole", "closed_handle"):
        result = evaluate(
            ConnectionInterface(
                interface_id=f"tool:{interface_type}",
                role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
                interface_type=interface_type,
            )
        )
        assert result.status == ConnectionStatus.REQUIRES_VERIFICATION
        assert result.verification_family == "cinch_loop_to_closed_interface.v1"


def test_v1_does_not_widen_to_tool_attachment_provided_ring():
    result = evaluate(
        ConnectionInterface(
            interface_id="attachment:ring",
            role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
            interface_type="ring",
        )
    )

    assert result.status == ConnectionStatus.UNRESOLVED
    assert result.verification_family is None


def test_v1_does_not_widen_anchor_point_copy_to_unevidenced_closed_forms():
    for interface_type in ("dedicated_eye", "captive_hole", "closed_handle"):
        result = evaluate(
            ConnectionInterface(
                interface_id=f"anchor:{interface_type}",
                role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
                interface_type=interface_type,
            )
        )
        assert result.status == ConnectionStatus.UNRESOLVED
        assert result.verification_family is None
