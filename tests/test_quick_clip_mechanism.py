from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    evaluate_endpoint_engagement,
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


def quick_clip_claims():
    return NLGAdapter().extract(
        tether_identity(),
        [
            artifact(
                "<p>Dual Quick Clips provide effortless and secure attachment.</p>"
                "<p>Quick Clips are ergonomically designed for quick connection and "
                "disconnection with a built-in trigger to facilitate use when wearing gloves.</p>"
            )
        ],
    )


def has_quick_clip_mechanism(claims) -> bool:
    return any(
        claim.subject_type == ClaimSubjectType.CONNECTOR_SPEC
        and claim.subject_ref == "quick_clip"
        and claim.property_key == "connector.attribute.opening_mechanism"
        for claim in claims
    )


def test_nlg_quick_clip_trigger_extracts_mechanism_without_inventing_action_count():
    claims = quick_clip_claims()

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
    assert not any(
        claim.subject_type == ClaimSubjectType.CONNECTOR_SPEC
        and claim.subject_ref == "quick_clip"
        and claim.property_key == "connector.locking_mode"
        for claim in claims
    )


def test_nlg_unrelated_tool_trigger_does_not_establish_quick_clip_mechanism():
    bodies = (
        "<p>Dual Quick Clips provide effortless attachment.</p>"
        "<p>The connected power tool has a built-in trigger.</p>",
        "<p>Dual Quick Clips attach to the belt while the connected power tool has a built-in trigger.</p>",
        "<p>Dual Quick Clips permit connection to a tool with a built-in trigger.</p>",
    )
    for body in bodies:
        claims = NLGAdapter().extract(tether_identity(), [artifact(body)])
        assert not has_quick_clip_mechanism(claims), body


def test_nlg_block_boundaries_prevent_cross_paragraph_or_list_mechanism_claims():
    bodies = (
        "<p>Dual Quick Clips allow connection</p><p>Power tools with a built-in trigger</p>",
        "<ul><li>Dual Quick Clips allow connection</li>"
        "<li>Power tools with a built-in trigger</li></ul>",
        "<div><p>Dual Quick Clips allow connection</p>"
        "<p>Power tools with a built-in trigger</p></div>",
    )
    for body in bodies:
        claims = NLGAdapter().extract(tether_identity(), [artifact(body)])
        assert not has_quick_clip_mechanism(claims), body


def test_nlg_quick_clip_ergonomic_trigger_can_be_bound_directly_to_action():
    claims = NLGAdapter().extract(
        tether_identity(),
        [artifact("<p>Dual Quick Clips provide easy connection with an ergonomic trigger design.</p>")],
    )

    assert has_quick_clip_mechanism(claims)


def test_trigger_operated_quick_clip_resolves_into_existing_connector_attributes():
    specs = resolve_connector_specs(quick_clip_claims())

    assert specs["quick_clip"].opening_action_count is None
    assert specs["quick_clip"].locking_mode.value == "unknown"
    assert specs["quick_clip"].attributes["opening_mechanism"] == "trigger_operated"


def test_trigger_mechanism_does_not_promote_clip_to_existing_gated_verification_family():
    claims = quick_clip_claims()
    interfaces = resolve_connection_interfaces(claims)
    specs = resolve_connector_specs(claims)
    endpoint = next(interface for interface in interfaces if interface.interface_type == "clip")
    target = ConnectionInterface(
        interface_id="tool_ring",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )

    result = evaluate_endpoint_engagement(endpoint, target, connector_specs=specs)

    assert result.status == ConnectionStatus.UNRESOLVED
    assert result.verification_family is None
    assert result.verification_status is None
    assert result.rule_results == []


def test_clip_label_does_not_activate_carabiner_geometry_rule_even_with_dimensions():
    claims = quick_clip_claims()
    interfaces = resolve_connection_interfaces(claims)
    specs = resolve_connector_specs(claims)
    endpoint = next(interface for interface in interfaces if interface.interface_type == "clip")
    specs["quick_clip"].dimensions_mm["gate_opening"] = 5.0
    target = ConnectionInterface(
        interface_id="tool_ring",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
        dimensions_mm={"feature_section_diameter": 10.0},
    )

    result = evaluate_endpoint_engagement(endpoint, target, connector_specs=specs)

    assert result.status == ConnectionStatus.UNRESOLVED
    assert result.rule_results == []
