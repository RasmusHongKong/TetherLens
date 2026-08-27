from tetherlens_ingest.compatibility import ManufacturerPosition
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionManufacturerAssessment,
    ConnectionStatus,
    TetherSide,
    evaluate_endpoint_engagement,
)


def _manufacturer_compatible() -> ConnectionManufacturerAssessment:
    return ConnectionManufacturerAssessment(
        issuer_manufacturer="Example Manufacturer",
        scope="endpoint -> target",
        position=ManufacturerPosition.EXPLICITLY_COMPATIBLE,
    )


def test_manufacturer_declaration_cannot_override_anchor_side_endpoint_on_tool_target():
    endpoint = ConnectionInterface(
        interface_id="anchor_endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=TetherSide.ANCHOR_SIDE,
    )
    target = ConnectionInterface(
        interface_id="tool_target",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )

    result = evaluate_endpoint_engagement(
        endpoint,
        target,
        manufacturer_assessments=[_manufacturer_compatible()],
    )

    assert result.status == ConnectionStatus.INCOMPATIBLE
    assert result.basis == CompatibilityBasis.VALIDATED_INTERFACE_CLASS
    assert result.manufacturer_assessments == [_manufacturer_compatible()]
    assert result.contradiction_type is None
    assert result.review_required is False
    assert result.reason == "anchor-side-only tether endpoint cannot serve the tool side"


def test_manufacturer_declaration_cannot_override_tool_side_endpoint_on_anchor_target():
    endpoint = ConnectionInterface(
        interface_id="tool_endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=TetherSide.TOOL_SIDE,
    )
    target = ConnectionInterface(
        interface_id="anchor_target",
        role=ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )

    result = evaluate_endpoint_engagement(
        endpoint,
        target,
        manufacturer_assessments=[_manufacturer_compatible()],
    )

    assert result.status == ConnectionStatus.INCOMPATIBLE
    assert result.basis == CompatibilityBasis.VALIDATED_INTERFACE_CLASS
    assert result.reason == "tool-side-only tether endpoint cannot serve the anchor side"
