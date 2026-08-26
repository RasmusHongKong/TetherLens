import pytest
from pydantic import ValidationError

from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.compatibility import ManufacturerPosition
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionManufacturerAssessment,
    ConnectionRuleResult,
    ConnectionStatus,
    ConnectorSpec,
    ContradictionType,
    GatedConnectorClosedInterfaceVerification,
    RuntimeVerificationStatus,
    TetherSide,
    evaluate_endpoint_engagement,
)
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.resolution import resolve_connection_interfaces, resolve_connector_specs


def endpoint(*, side: TetherSide = TetherSide.TOOL_SIDE, connector_ref: str = "connector") -> ConnectionInterface:
    return ConnectionInterface(
        interface_id="endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=side,
        connector_spec_ref=connector_ref,
    )


def ring(*, section_diameter: float | None = None) -> ConnectionInterface:
    dimensions = {}
    if section_diameter is not None:
        dimensions["feature_section_diameter"] = section_diameter
    return ConnectionInterface(
        interface_id="ring",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
        dimensions_mm=dimensions,
    )


def gated_spec(*, gate_opening: float | None = None, action_count: int = 2) -> ConnectorSpec:
    dimensions = {}
    if gate_opening is not None:
        dimensions["gate_opening"] = gate_opening
    return ConnectorSpec(
        connector_spec_id="connector",
        opening_action_count=action_count,
        dimensions_mm=dimensions,
    )


def completed_verification(
    *,
    locking_mechanism_engaged: bool | None = True,
    gate_unobstructed: bool = True,
) -> GatedConnectorClosedInterfaceVerification:
    return GatedConnectorClosedInterfaceVerification(
        target_fully_captured=True,
        gate_closed_completely=True,
        locking_mechanism_engaged=locking_mechanism_engaged,
        gate_unobstructed=gate_unobstructed,
        intended_loaded_orientation=True,
        stable_seating_no_cross_loading=True,
        no_adjacent_interference=True,
    )


def manufacturer(
    position: ManufacturerPosition,
    *,
    issuer: str = "Maker",
    scope: str = "endpoint -> ring",
    technical: bool = False,
) -> ConnectionManufacturerAssessment:
    return ConnectionManufacturerAssessment(
        issuer_manufacturer=issuer,
        scope=scope,
        position=position,
        technical_causal_scope_established=technical,
    )


def test_manufacturer_declaration_precedes_ordinary_derived_rule_disagreement():
    result = evaluate_endpoint_engagement(
        endpoint(),
        ring(),
        connector_specs={"connector": gated_spec()},
        manufacturer_assessments=[manufacturer(ManufacturerPosition.EXPLICITLY_COMPATIBLE)],
        derived_results=[
            ConnectionRuleResult(
                rule_id="generic_interface_rule.v1",
                basis=CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
                status=ConnectionStatus.INCOMPATIBLE,
                reason="generic class rejects pairing",
            )
        ],
    )
    assert result.status == ConnectionStatus.COMPATIBLE
    assert result.basis == CompatibilityBasis.MANUFACTURER_DECLARED
    assert result.contradiction_type == ContradictionType.DERIVED_RULE_DISAGREEMENT
    assert result.review_required is True


def test_hard_physical_contradiction_blocks_manufacturer_declared_compatibility():
    result = evaluate_endpoint_engagement(
        endpoint(),
        ring(section_diameter=15),
        connector_specs={"connector": gated_spec(gate_opening=8)},
        manufacturer_assessments=[manufacturer(ManufacturerPosition.EXPLICITLY_COMPATIBLE)],
    )
    assert result.status == ConnectionStatus.UNRESOLVED
    assert result.basis == CompatibilityBasis.NONE
    assert result.contradiction_type == ContradictionType.HARD_PHYSICAL_CONTRADICTION
    assert result.blocked is True


def test_authoritative_source_conflict_is_unresolved_and_blocked():
    result = evaluate_endpoint_engagement(
        endpoint(),
        ring(),
        connector_specs={"connector": gated_spec()},
        manufacturer_assessments=[
            manufacturer(ManufacturerPosition.EXPLICITLY_COMPATIBLE, issuer="Maker A"),
            manufacturer(ManufacturerPosition.EXPLICITLY_PROHIBITED, issuer="Maker A"),
        ],
    )
    assert result.status == ConnectionStatus.UNRESOLVED
    assert result.contradiction_type == ContradictionType.AUTHORITATIVE_SOURCE_CONFLICT
    assert result.blocked is True


def test_nontechnical_manufacturer_restriction_is_preserved_but_does_not_create_incompatibility():
    restriction = manufacturer(ManufacturerPosition.EXPLICITLY_PROHIBITED, technical=False)
    result = evaluate_endpoint_engagement(
        endpoint(),
        ring(),
        connector_specs={"connector": gated_spec()},
        manufacturer_assessments=[restriction],
    )
    assert result.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert result.manufacturer_assessments == [restriction]


def test_geometry_inconclusive_falls_through_to_runtime_verification():
    result = evaluate_endpoint_engagement(
        endpoint(),
        ring(),
        connector_specs={"connector": gated_spec()},
    )
    assert result.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert result.basis == CompatibilityBasis.RUNTIME_VERIFICATION
    assert result.verification_status == RuntimeVerificationStatus.PENDING
    assert any(
        rule.basis == CompatibilityBasis.VALIDATED_GEOMETRY and rule.status is None
        for rule in result.rule_results
    )


def test_geometry_pass_is_partial_and_still_falls_through_to_runtime_verification():
    result = evaluate_endpoint_engagement(
        endpoint(),
        ring(section_diameter=8),
        connector_specs={"connector": gated_spec(gate_opening=15)},
    )
    assert result.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert result.basis == CompatibilityBasis.RUNTIME_VERIFICATION


def test_runtime_verification_status_is_derived_from_structured_observations():
    pending = evaluate_endpoint_engagement(
        endpoint(), ring(), connector_specs={"connector": gated_spec()}
    )
    incomplete = evaluate_endpoint_engagement(
        endpoint(),
        ring(),
        connector_specs={"connector": gated_spec()},
        verification_observations=GatedConnectorClosedInterfaceVerification(
            target_fully_captured=True,
            gate_closed_completely=True,
        ),
    )
    passed_observations = completed_verification()
    passed = evaluate_endpoint_engagement(
        endpoint(),
        ring(),
        connector_specs={"connector": gated_spec()},
        verification_observations=passed_observations,
    )
    failed_observations = completed_verification(gate_unobstructed=False)
    failed = evaluate_endpoint_engagement(
        endpoint(),
        ring(),
        connector_specs={"connector": gated_spec()},
        verification_observations=failed_observations,
    )

    assert pending.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert pending.verification_status == RuntimeVerificationStatus.PENDING
    assert incomplete.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert incomplete.verification_status == RuntimeVerificationStatus.PENDING
    assert passed.status == ConnectionStatus.COMPATIBLE
    assert passed.verification_status == RuntimeVerificationStatus.PASSED
    assert passed.verification_observations == passed_observations
    assert failed.status == ConnectionStatus.INCOMPATIBLE
    assert failed.verification_status == RuntimeVerificationStatus.FAILED
    assert failed.verification_observations == failed_observations
    assert {pending.basis, incomplete.basis, passed.basis, failed.basis} == {
        CompatibilityBasis.RUNTIME_VERIFICATION
    }


def test_lock_observation_is_required_for_multi_action_connector():
    result = evaluate_endpoint_engagement(
        endpoint(),
        ring(),
        connector_specs={"connector": gated_spec(action_count=2)},
        verification_observations=completed_verification(locking_mechanism_engaged=None),
    )
    assert result.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert result.verification_status == RuntimeVerificationStatus.PENDING


def test_lock_observation_is_not_required_for_single_action_nonlocking_connector():
    result = evaluate_endpoint_engagement(
        endpoint(),
        ring(),
        connector_specs={"connector": gated_spec(action_count=1)},
        verification_observations=completed_verification(locking_mechanism_engaged=None),
    )
    assert result.status == ConnectionStatus.COMPATIBLE
    assert result.verification_status == RuntimeVerificationStatus.PASSED


def test_runtime_verification_observations_are_strict_booleans():
    with pytest.raises(ValidationError):
        GatedConnectorClosedInterfaceVerification(gate_closed_completely="yes")


def test_connector_action_count_rejects_values_above_schema_bound():
    with pytest.raises(ValidationError):
        ConnectorSpec(connector_spec_id="connector", opening_action_count=4)


def test_wrong_side_incompatibility_remains_conclusive_before_verification():
    result = evaluate_endpoint_engagement(
        endpoint(side=TetherSide.ANCHOR_SIDE),
        ring(),
        connector_specs={"connector": gated_spec()},
    )
    assert result.status == ConnectionStatus.INCOMPATIBLE
    assert result.basis == CompatibilityBasis.VALIDATED_INTERFACE_CLASS
    assert result.verification_status is None


def test_carabiner_and_ring_names_alone_still_prove_nothing():
    result = evaluate_endpoint_engagement(endpoint(), ring())
    assert result.status == ConnectionStatus.UNRESOLVED
    assert result.basis == CompatibilityBasis.NONE
    assert result.verification_family is None


def test_explicit_technical_manufacturer_prohibition_is_incompatible():
    result = evaluate_endpoint_engagement(
        endpoint(),
        ring(),
        connector_specs={"connector": gated_spec()},
        manufacturer_assessments=[
            manufacturer(ManufacturerPosition.EXPLICITLY_PROHIBITED, technical=True)
        ],
    )
    assert result.status == ConnectionStatus.INCOMPATIBLE
    assert result.basis == CompatibilityBasis.MANUFACTURER_DECLARED


def test_nlg_101372_to_101363_reaches_generic_requires_verification_without_sku_rule():
    tether_html = """
    <p>5kg Bungee Tool Lanyard with Rotobiner and Climbing Cord Loop.</p>
    <p>Double action Rotobiner with 360 degree rotation.</p>
    <p>Attach to an anchor point or tool.</p>
    <p>Climbing cord loop attaches to an anchor point or tool.</p>
    <p>Max Load: 5 kg.</p>
    """
    attachment_html = """
    <p>The D Ring creates a secure tether point to attach a tool lanyard.</p>
    <p>Create a tether point on any tool with a captive hole or handle and cinch it around the tool.</p>
    """

    tether_identity = ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TETHER,
        name="Bungee Tool Lanyard",
        sku="101372",
        url="https://example.test/nlg/101372",
    )
    attachment_identity = ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="360 D Ring Loop Tool Tether",
        sku="101363",
        url="https://example.test/nlg/101363",
    )
    tether_artifact = SourceArtifact(
        url=tether_identity.url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=tether_html,
    )
    attachment_artifact = SourceArtifact(
        url=attachment_identity.url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=attachment_html,
    )

    tether_claims = NLGAdapter().extract(tether_identity, [tether_artifact])
    attachment_claims = NLGAdapter().extract(attachment_identity, [attachment_artifact])
    tether_interfaces = resolve_connection_interfaces(tether_claims)
    target = resolve_connection_interfaces(attachment_claims)[0]
    specs = resolve_connector_specs(tether_claims)

    rotobiner = next(
        interface
        for interface in tether_interfaces
        if interface.interface_type == "carabiner"
        and interface.connector_spec_ref == "rotobiner"
    )
    result = evaluate_endpoint_engagement(rotobiner, target, connector_specs=specs)

    assert specs["rotobiner"].opening_action_count == 2
    assert result.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert result.basis == CompatibilityBasis.RUNTIME_VERIFICATION
    assert result.verification_family == "gated_connector_to_closed_interface.v1"
