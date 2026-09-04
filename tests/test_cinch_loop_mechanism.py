import pytest

from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.connection import (
    CinchLoopClosedInterfaceVerification,
    CompatibilityBasis,
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    ConnectorSpec,
    RuntimeVerificationStatus,
    TetherSide,
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
        url="https://neverletgo.example/bungee-tool-lanyard",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def tether_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TETHER,
        name="Bungee Tool Lanyard",
        sku="101372",
        url="https://neverletgo.example/bungee-tool-lanyard",
    )


def positive_body() -> str:
    return (
        "<p>The tough climbing cord loop allows easy and secure attachment to an anchor "
        "point or directly to a captive hole or handle on the tool itself.</p>"
        "<p>The rugged climbing cord loop allows quick and secure cinching.</p>"
        "<p>The Rotobiner allows attachment to a tool or anchor.</p>"
    )


def cinch_claims():
    return NLGAdapter().extract(tether_identity(), [artifact(positive_body())])


def has_cinch_mechanism(claims) -> bool:
    return any(
        claim.subject_type == ClaimSubjectType.CONNECTOR_SPEC
        and claim.property_key == "connector.attribute.engagement_method"
        and claim.value == "cinch"
        for claim in claims
    )


def test_nlg_cinch_loop_extracts_endpoint_mechanism_without_retyping_loop():
    claims = cinch_claims()

    loop_type_claims = [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT
        and claim.property_key == "connection_point.interface_type"
        and claim.value == "loop"
    ]
    assert len(loop_type_claims) == 1

    loop_ref = loop_type_claims[0].subject_ref
    connector_ref_claims = [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT
        and claim.subject_ref == loop_ref
        and claim.property_key == "connection_point.connector_spec_ref"
    ]
    assert len(connector_ref_claims) == 1
    assert connector_ref_claims[0].value == "cinch_loop"

    mechanism_claims = [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.CONNECTOR_SPEC
        and claim.subject_ref == "cinch_loop"
        and claim.property_key == "connector.attribute.engagement_method"
    ]
    assert len(mechanism_claims) == 1
    assert mechanism_claims[0].value == "cinch"


def test_nlg_cinch_words_near_loop_do_not_establish_loop_mechanism():
    bodies = (
        "<p>The climbing cord loop allows attachment to a tool or anchor.</p>"
        "<p>A separate cinching strap secures the storage pouch.</p>"
        "<p>The Rotobiner allows attachment to a tool or anchor.</p>",
        "<p>The climbing cord loop sits beside a cinching strap.</p>"
        "<p>The Rotobiner allows attachment to a tool or anchor.</p>",
        "<p>The climbing cord loop allows attachment to a tool or anchor.</p>"
        "<p>Does the loop allow secure cinching?</p>"
        "<p>The Rotobiner allows attachment to a tool or anchor.</p>",
    )

    for body in bodies:
        claims = NLGAdapter().extract(tether_identity(), [artifact(body)])
        assert not has_cinch_mechanism(claims), body


def test_cinch_loop_resolves_as_loop_plus_separate_engagement_primitive():
    claims = cinch_claims()
    interfaces = resolve_connection_interfaces(claims)
    specs = resolve_connector_specs(claims)

    loop_endpoint = next(interface for interface in interfaces if interface.interface_type == "loop")

    assert loop_endpoint.connector_spec_ref == "cinch_loop"
    assert loop_endpoint.tether_side == TetherSide.EITHER
    assert specs["cinch_loop"].opening_action_count is None
    assert specs["cinch_loop"].attributes["engagement_method"] == "cinch"


def test_plain_loop_does_not_activate_cinch_verification_family():
    endpoint = ConnectionInterface(
        interface_id="loop",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="loop",
        tether_side=TetherSide.EITHER,
    )
    target = ConnectionInterface(
        interface_id="anchor_ring",
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="ring",
    )

    result = evaluate_endpoint_engagement(endpoint, target)

    assert result.status == ConnectionStatus.UNRESOLVED
    assert result.basis == CompatibilityBasis.NONE
    assert result.verification_family is None


def test_cinch_loop_to_closed_anchor_enters_bounded_runtime_verification():
    claims = cinch_claims()
    interfaces = resolve_connection_interfaces(claims)
    specs = resolve_connector_specs(claims)
    endpoint = next(interface for interface in interfaces if interface.interface_type == "loop")
    target = ConnectionInterface(
        interface_id="container_ring",
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="ring",
    )

    result = evaluate_endpoint_engagement(endpoint, target, connector_specs=specs)

    assert result.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert result.basis == CompatibilityBasis.RUNTIME_VERIFICATION
    assert result.verification_family == "cinch_loop_to_closed_interface.v1"
    assert result.verification_status == RuntimeVerificationStatus.PENDING
    assert result.verification_connector_spec == specs["cinch_loop"]


def test_cinch_loop_to_captive_direct_tool_interface_uses_same_bounded_family():
    claims = cinch_claims()
    interfaces = resolve_connection_interfaces(claims)
    specs = resolve_connector_specs(claims)
    endpoint = next(interface for interface in interfaces if interface.interface_type == "loop")
    target = ConnectionInterface(
        interface_id="tool_handle",
        role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
        interface_type="closed_handle",
    )

    result = evaluate_endpoint_engagement(endpoint, target, connector_specs=specs)

    assert result.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert result.verification_family == "cinch_loop_to_closed_interface.v1"


def test_cinch_loop_does_not_activate_family_for_open_or_unknown_target_form():
    endpoint = ConnectionInterface(
        interface_id="loop",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="loop",
        tether_side=TetherSide.EITHER,
        connector_spec_ref="loop_spec",
    )
    spec = ConnectorSpec(
        connector_spec_id="loop_spec",
        attributes={"engagement_method": "cinch"},
    )
    target = ConnectionInterface(
        interface_id="anchor",
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="open_hook",
    )

    result = evaluate_endpoint_engagement(
        endpoint,
        target,
        connector_specs={"loop_spec": spec},
    )

    assert result.status == ConnectionStatus.UNRESOLVED
    assert result.verification_family is None


def test_cinch_attribute_does_not_retype_other_endpoint_families():
    endpoint = ConnectionInterface(
        interface_id="clip",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="clip",
        tether_side=TetherSide.EITHER,
        connector_spec_ref="clip_spec",
    )
    spec = ConnectorSpec(
        connector_spec_id="clip_spec",
        attributes={"engagement_method": "cinch"},
    )
    target = ConnectionInterface(
        interface_id="ring",
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="ring",
    )

    result = evaluate_endpoint_engagement(
        endpoint,
        target,
        connector_specs={"clip_spec": spec},
    )

    assert result.status == ConnectionStatus.UNRESOLVED
    assert result.verification_family is None


def test_cinch_runtime_verification_is_derived_only_from_structured_observations():
    endpoint = ConnectionInterface(
        interface_id="loop",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="loop",
        tether_side=TetherSide.EITHER,
        connector_spec_ref="loop_spec",
    )
    spec = ConnectorSpec(
        connector_spec_id="loop_spec",
        attributes={"engagement_method": "cinch"},
    )
    target = ConnectionInterface(
        interface_id="ring",
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="ring",
    )

    incomplete = evaluate_endpoint_engagement(
        endpoint,
        target,
        connector_specs={"loop_spec": spec},
        verification_observations=CinchLoopClosedInterfaceVerification(
            target_fully_captured=True,
        ),
    )
    passed_observations = CinchLoopClosedInterfaceVerification(
        target_fully_captured=True,
        cinch_drawn_tight=True,
    )
    passed = evaluate_endpoint_engagement(
        endpoint,
        target,
        connector_specs={"loop_spec": spec},
        verification_observations=passed_observations,
    )
    failed_observations = CinchLoopClosedInterfaceVerification(
        target_fully_captured=True,
        cinch_drawn_tight=False,
    )
    failed = evaluate_endpoint_engagement(
        endpoint,
        target,
        connector_specs={"loop_spec": spec},
        verification_observations=failed_observations,
    )

    assert incomplete.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert incomplete.verification_status == RuntimeVerificationStatus.PENDING
    assert passed.status == ConnectionStatus.COMPATIBLE
    assert passed.verification_status == RuntimeVerificationStatus.PASSED
    assert passed.verification_observations == passed_observations
    assert failed.status == ConnectionStatus.INCOMPATIBLE
    assert failed.verification_status == RuntimeVerificationStatus.FAILED
    assert failed.verification_observations == failed_observations


def test_cinch_family_rejects_gated_connector_observation_shape():
    endpoint = ConnectionInterface(
        interface_id="loop",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="loop",
        tether_side=TetherSide.EITHER,
        connector_spec_ref="loop_spec",
    )
    spec = ConnectorSpec(
        connector_spec_id="loop_spec",
        attributes={"engagement_method": "cinch"},
    )
    target = ConnectionInterface(
        interface_id="ring",
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="ring",
    )

    from tetherlens_ingest.connection import GatedConnectorClosedInterfaceVerification

    with pytest.raises(ValueError, match="cinch-loop verification requires"):
        evaluate_endpoint_engagement(
            endpoint,
            target,
            connector_specs={"loop_spec": spec},
            verification_observations=GatedConnectorClosedInterfaceVerification(
                target_fully_captured=True,
            ),
        )
