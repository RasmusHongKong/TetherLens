from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    ConnectorSpec,
    GatedConnectorClosedInterfaceVerification,
    RuntimeVerificationStatus,
    TetherSide,
    evaluate_endpoint_engagement,
    evaluate_gated_connector_closed_interface_verification,
)
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.resolution import resolve_connection_interfaces, resolve_connector_specs


def artifact(body: str) -> SourceArtifact:
    return SourceArtifact(
        url="https://neverletgo.example/extended-bungee-tool-lanyard",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def tether_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TETHER,
        name="Extended Bungee Tool Lanyard",
        sku="101434",
        url="https://neverletgo.example/extended-bungee-tool-lanyard",
    )


def test_nlg_quick_clip_trigger_extracts_mechanism_without_inventing_action_count():
    claims = NLGAdapter().extract(
        tether_identity(),
        [
            artifact(
                "<p>Dual Quick Clips provide effortless and secure attachment.</p>"
                "<p>Quick Clips are ergonomically designed for quick connection and "
                "disconnection with a built-in trigger to facilitate use when wearing gloves.</p>"
            )
        ],
    )

    mechanism = [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.CONNECTOR_SPEC
        and claim.subject_ref == "quick_clip"
        and claim.property_key == "connector.attribute.opening_mechanism"
    ]
    assert len(mechanism) == 1
    assert mechanism[0].value == "trigger_operated"
    assert not any(
        claim.subject_type == ClaimSubjectType.CONNECTOR_SPEC
        and claim.subject_ref == "quick_clip"
        and claim.property_key == "connector.opening_action_count"
        for claim in claims
    )


def test_nlg_unrelated_tool_trigger_does_not_establish_quick_clip_mechanism():
    bodies = (
        "<p>Dual Quick Clips provide effortless attachment.</p>"
        "<p>The connected power tool has a built-in trigger.</p>",
        "<p>Quick Clips attach to the belt while the connected power tool has a built-in trigger.</p>",
    )
    for body in bodies:
        claims = NLGAdapter().extract(tether_identity(), [artifact(body)])
        assert not any(
            claim.subject_type == ClaimSubjectType.CONNECTOR_SPEC
            and claim.subject_ref == "quick_clip"
            and claim.property_key == "connector.attribute.opening_mechanism"
            for claim in claims
        ), body


def test_trigger_operated_quick_clip_resolves_into_existing_connector_attributes():
    claims = NLGAdapter().extract(
        tether_identity(),
        [
            artifact(
                "<p>Dual Quick Clips provide effortless attachment.</p>"
                "<p>Quick Clips are ergonomically designed for quick connection and "
                "disconnection with a built-in trigger.</p>"
            )
        ],
    )

    specs = resolve_connector_specs(claims)
    assert specs["quick_clip"].opening_action_count is None
    assert specs["quick_clip"].attributes["opening_mechanism"] == "trigger_operated"


def test_trigger_operated_clip_can_use_bounded_closed_interface_verification_family():
    claims = NLGAdapter().extract(
        tether_identity(),
        [
            artifact(
                "<p>Dual Quick Clips provide effortless attachment.</p>"
                "<p>Quick Clips are ergonomically designed for quick connection and "
                "disconnection with a built-in trigger.</p>"
            )
        ],
    )
    interfaces = resolve_connection_interfaces(claims)
    specs = resolve_connector_specs(claims)
    endpoint = next(interface for interface in interfaces if interface.interface_type == "clip")
    target = ConnectionInterface(
        interface_id="tool_ring",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )

    result = evaluate_endpoint_engagement(endpoint, target, connector_specs=specs)

    assert result.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert result.verification_family == "gated_connector_to_closed_interface.v1"
    assert result.verification_status == RuntimeVerificationStatus.PENDING
    assert result.verification_connector_spec is not None
    assert result.verification_connector_spec.connector_spec_id == "quick_clip"


def test_clip_without_established_opening_mechanism_remains_unresolved():
    endpoint = ConnectionInterface(
        interface_id="quick_clip_endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="clip",
        tether_side=TetherSide.EITHER,
        connector_spec_ref="quick_clip",
    )
    target = ConnectionInterface(
        interface_id="tool_ring",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )

    result = evaluate_endpoint_engagement(endpoint, target, connector_specs={})

    assert result.status == ConnectionStatus.UNRESOLVED
    assert result.verification_family is None


def test_clip_label_does_not_activate_carabiner_geometry_rule():
    endpoint = ConnectionInterface(
        interface_id="quick_clip_endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="clip",
        tether_side=TetherSide.EITHER,
        connector_spec_ref="quick_clip",
    )
    target = ConnectionInterface(
        interface_id="tool_ring",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
        dimensions_mm={"feature_section_diameter": 10.0},
    )
    connector_spec = ConnectorSpec(
        connector_spec_id="quick_clip",
        dimensions_mm={"gate_opening": 5.0},
        attributes={"opening_mechanism": "trigger_operated"},
    )

    result = evaluate_endpoint_engagement(
        endpoint,
        target,
        connector_specs={"quick_clip": connector_spec},
    )

    assert result.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert result.basis == CompatibilityBasis.RUNTIME_VERIFICATION
    assert not any(
        rule.basis == CompatibilityBasis.VALIDATED_GEOMETRY
        for rule in result.rule_results
    )


def test_unknown_quick_clip_locking_mode_keeps_lock_observation_conservative():
    claims = NLGAdapter().extract(
        tether_identity(),
        [
            artifact(
                "<p>Dual Quick Clips provide effortless attachment.</p>"
                "<p>Quick Clips are ergonomically designed for quick connection and "
                "disconnection with a built-in trigger.</p>"
            )
        ],
    )
    connector_spec = resolve_connector_specs(claims)["quick_clip"]
    observations = GatedConnectorClosedInterfaceVerification(
        target_fully_captured=True,
        gate_closed_completely=True,
        gate_unobstructed=True,
        intended_loaded_orientation=True,
        stable_seating_no_cross_loading=True,
        no_adjacent_interference=True,
    )

    assert (
        evaluate_gated_connector_closed_interface_verification(connector_spec, observations)
        == RuntimeVerificationStatus.PENDING
    )

    observations.locking_mechanism_engaged = True
    assert (
        evaluate_gated_connector_closed_interface_verification(connector_spec, observations)
        == RuntimeVerificationStatus.PASSED
    )
