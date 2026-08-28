import pytest

from tetherlens_ingest.adapters import KleinAdapter, NLGAdapter
from tetherlens_ingest.compatibility import (
    EligibilityEvaluation,
    EligibilityMatch,
    EligibilityStatus,
    PolicyStatus,
    evaluate_attachment_eligibility,
)
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionEvaluation,
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    TetherSide,
    evaluate_endpoint_engagement,
)
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.recommendation import (
    CandidateAttachmentMode,
    CandidateCheckStatus,
    CandidateConfiguration,
    LanyardLengthConstraint,
    LoadBearingComponent,
    PolicyApplicability,
    RecommendationState,
    evaluate_candidate_configuration,
)
from tetherlens_ingest.resolution import (
    resolve_attachment_eligibility,
    resolve_connection_interfaces,
    resolve_connector_specs,
    resolve_tool_interface_features,
)


def connection(
    status: ConnectionStatus = ConnectionStatus.COMPATIBLE,
    *,
    endpoint_id: str,
    target_id: str,
    target_role: ConnectionInterfaceRole,
    endpoint_tether_side: TetherSide = TetherSide.EITHER,
    review_required: bool = False,
) -> ConnectionEvaluation:
    basis = (
        CompatibilityBasis.RUNTIME_VERIFICATION
        if status == ConnectionStatus.REQUIRES_VERIFICATION
        else CompatibilityBasis.VALIDATED_INTERFACE_CLASS
        if status in {ConnectionStatus.COMPATIBLE, ConnectionStatus.INCOMPATIBLE}
        else CompatibilityBasis.NONE
    )
    return ConnectionEvaluation(
        status=status,
        basis=basis,
        endpoint_id=endpoint_id,
        target_interface_id=target_id,
        endpoint_tether_side=endpoint_tether_side,
        target_role=target_role,
        reason=f"test connection is {status.value}",
        review_required=review_required,
    )


def tool_connection(
    status: ConnectionStatus = ConnectionStatus.COMPATIBLE,
    *,
    endpoint_id: str = "tool_endpoint",
    target_id: str = "attachment_ring",
    target_role: ConnectionInterfaceRole = ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
    endpoint_tether_side: TetherSide = TetherSide.EITHER,
    review_required: bool = False,
) -> ConnectionEvaluation:
    return connection(
        status,
        endpoint_id=endpoint_id,
        target_id=target_id,
        target_role=target_role,
        endpoint_tether_side=endpoint_tether_side,
        review_required=review_required,
    )


def anchor_connection(
    status: ConnectionStatus = ConnectionStatus.COMPATIBLE,
    *,
    endpoint_id: str = "anchor_endpoint",
    target_id: str = "container_ring",
    target_role: ConnectionInterfaceRole = ConnectionInterfaceRole.CONTAINER_CONNECTION,
    endpoint_tether_side: TetherSide = TetherSide.EITHER,
    review_required: bool = False,
) -> ConnectionEvaluation:
    return connection(
        status,
        endpoint_id=endpoint_id,
        target_id=target_id,
        target_role=target_role,
        endpoint_tether_side=endpoint_tether_side,
        review_required=review_required,
    )


def eligible_attachment() -> EligibilityEvaluation:
    return EligibilityEvaluation(
        status=EligibilityStatus.ELIGIBLE,
        matches=[
            EligibilityMatch(
                path_index=0,
                binding_name="opening",
                feature_id="tool_opening",
            )
        ],
    )


def base_candidate(**overrides) -> CandidateConfiguration:
    values = {
        "candidate_id": "candidate-a",
        "object_mass_kg": 2.0,
        "load_bearing_components": [
            LoadBearingComponent(component_id="attachment", rated_capacity_kg=3.0),
            LoadBearingComponent(component_id="tether", rated_capacity_kg=5.0),
            LoadBearingComponent(component_id="container_anchor", rated_capacity_kg=5.0),
        ],
        "tether_max_length_mm": 1200.0,
        "lanyard_length_constraints": [
            LanyardLengthConstraint(
                constraint_id="attachment_lanyard_limit",
                max_lanyard_length_mm=2000.0,
            ),
            LanyardLengthConstraint(
                constraint_id="container_lanyard_limit",
                max_lanyard_length_mm=2000.0,
            ),
        ],
        "attachment_mode": CandidateAttachmentMode.TOOL_ATTACHMENT,
        "attachment_eligibility": eligible_attachment(),
        "tool_side_connection": tool_connection(),
        "anchor_side_connection": anchor_connection(),
        "policy_applicability": PolicyApplicability.APPLICABLE,
        "policy_status": PolicyStatus.PERMITTED,
    }
    values.update(overrides)
    return CandidateConfiguration(**values)


def artifact(body: str, *, url: str) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def test_candidate_is_recommended_when_every_hard_check_passes():
    result = evaluate_candidate_configuration(base_candidate())

    assert result.recommendation_state == RecommendationState.RECOMMENDED
    assert result.recommended is True
    assert result.blocked is False
    assert result.requires_verification is False
    assert all(check.status == CandidateCheckStatus.PASSED for check in result.checks)
    assert result.pending_verification_connection_ids == []


def test_required_connection_sides_validate_retained_target_roles():
    with pytest.raises(ValueError, match="anchor-side connection must target"):
        base_candidate(
            anchor_side_connection=tool_connection(
                endpoint_id="second_tool_endpoint",
                target_id="second_attachment_ring",
            )
        )


def test_required_connection_sides_validate_retained_endpoint_side():
    with pytest.raises(ValueError, match="tool-capable tether endpoint"):
        base_candidate(
            tool_side_connection=tool_connection(
                endpoint_tether_side=TetherSide.ANCHOR_SIDE,
            )
        )


def test_attachment_mode_must_match_tool_side_target_role():
    with pytest.raises(ValueError, match="target role must match"):
        base_candidate(
            attachment_mode=CandidateAttachmentMode.DIRECT,
            attachment_eligibility=None,
        )


def test_pending_connection_verification_produces_recommended_with_constraints():
    result = evaluate_candidate_configuration(
        base_candidate(
            tool_side_connection=tool_connection(ConnectionStatus.REQUIRES_VERIFICATION)
        )
    )

    assert result.recommendation_state == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    assert result.requires_verification is True
    assert result.pending_verification_connection_ids == [
        "connection:tool_endpoint->attachment_ring"
    ]
    assert any(
        check.status == CandidateCheckStatus.REQUIRES_VERIFICATION for check in result.checks
    )


def test_multiple_pending_connections_remain_one_conditional_recommendation():
    result = evaluate_candidate_configuration(
        base_candidate(
            tool_side_connection=tool_connection(ConnectionStatus.REQUIRES_VERIFICATION),
            anchor_side_connection=anchor_connection(ConnectionStatus.REQUIRES_VERIFICATION),
        )
    )

    assert result.recommendation_state == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    assert result.pending_verification_connection_ids == [
        "connection:tool_endpoint->attachment_ring",
        "connection:anchor_endpoint->container_ring",
    ]


def test_blocked_candidate_does_not_request_runtime_verification():
    result = evaluate_candidate_configuration(
        base_candidate(
            tool_side_connection=tool_connection(ConnectionStatus.REQUIRES_VERIFICATION),
            anchor_side_connection=anchor_connection(ConnectionStatus.UNRESOLVED),
        )
    )

    assert result.recommendation_state is None
    assert result.pending_verification_connection_ids == []
    assert any(
        check.status == CandidateCheckStatus.REQUIRES_VERIFICATION for check in result.checks
    )


def test_unresolved_or_incompatible_connection_blocks_candidate():
    for status in (ConnectionStatus.UNRESOLVED, ConnectionStatus.INCOMPATIBLE):
        result = evaluate_candidate_configuration(
            base_candidate(anchor_side_connection=anchor_connection(status))
        )

        assert result.recommendation_state is None
        assert result.blocked is True


def test_missing_or_insufficient_component_capacity_blocks_candidate():
    missing = evaluate_candidate_configuration(
        base_candidate(
            load_bearing_components=[
                LoadBearingComponent(component_id="tether", rated_capacity_kg=None)
            ]
        )
    )
    insufficient = evaluate_candidate_configuration(
        base_candidate(
            load_bearing_components=[
                LoadBearingComponent(component_id="tether", rated_capacity_kg=1.0)
            ]
        )
    )

    assert missing.recommendation_state is None
    assert insufficient.recommendation_state is None
    assert any(check.status == CandidateCheckStatus.UNRESOLVED for check in missing.checks)
    assert any(check.status == CandidateCheckStatus.FAILED for check in insufficient.checks)


def test_missing_operational_mass_blocks_every_load_check_without_assuming_zero():
    result = evaluate_candidate_configuration(base_candidate(object_mass_kg=None))

    assert result.recommendation_state is None
    load_checks = [check for check in result.checks if check.check_id.startswith("load_capacity:")]
    assert load_checks
    assert all(check.status == CandidateCheckStatus.UNRESOLVED for check in load_checks)


def test_tether_exceeding_applicable_lanyard_limit_blocks_candidate():
    result = evaluate_candidate_configuration(
        base_candidate(
            tether_max_length_mm=2100.0,
            lanyard_length_constraints=[
                LanyardLengthConstraint(
                    constraint_id="attachment_lanyard_limit",
                    max_lanyard_length_mm=2000.0,
                )
            ],
        )
    )

    assert result.recommendation_state is None
    assert any(
        check.check_id == "lanyard_length:attachment_lanyard_limit"
        and check.status == CandidateCheckStatus.FAILED
        for check in result.checks
    )


def test_missing_length_fact_is_unresolved_when_a_length_constraint_applies():
    result = evaluate_candidate_configuration(base_candidate(tether_max_length_mm=None))

    assert result.recommendation_state is None
    assert any(
        check.check_id.startswith("lanyard_length:")
        and check.status == CandidateCheckStatus.UNRESOLVED
        for check in result.checks
    )


def test_attachment_ineligible_or_unresolved_blocks_candidate():
    for eligibility_status in (EligibilityStatus.INELIGIBLE, EligibilityStatus.UNRESOLVED):
        result = evaluate_candidate_configuration(
            base_candidate(
                attachment_eligibility=EligibilityEvaluation(status=eligibility_status)
            )
        )
        assert result.recommendation_state is None


def test_missing_attachment_eligibility_is_unresolved_when_tool_attachment_is_required():
    result = evaluate_candidate_configuration(
        base_candidate(attachment_eligibility=None)
    )

    assert result.recommendation_state is None
    assert any(
        check.check_id == "attachment_eligibility"
        and check.status == CandidateCheckStatus.UNRESOLVED
        for check in result.checks
    )


def test_direct_tethering_explicitly_has_no_attachment_eligibility_axis():
    result = evaluate_candidate_configuration(
        base_candidate(
            attachment_mode=CandidateAttachmentMode.DIRECT,
            attachment_eligibility=None,
            tool_side_connection=tool_connection(
                target_id="tool_tether_hole",
                target_role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
            ),
        )
    )

    assert result.recommendation_state == RecommendationState.RECOMMENDED
    assert not any(check.check_id == "attachment_eligibility" for check in result.checks)


def test_eligible_attachment_without_bound_match_fails_closed():
    result = evaluate_candidate_configuration(
        base_candidate(
            attachment_eligibility=EligibilityEvaluation(status=EligibilityStatus.ELIGIBLE)
        )
    )

    assert result.recommendation_state is None
    assert any(
        check.check_id == "attachment_eligibility"
        and check.status == CandidateCheckStatus.UNRESOLVED
        for check in result.checks
    )


def test_policy_prohibited_or_unresolved_blocks_candidate_when_policy_applies():
    for policy_status in (PolicyStatus.PROHIBITED, PolicyStatus.UNRESOLVED):
        result = evaluate_candidate_configuration(base_candidate(policy_status=policy_status))
        assert result.recommendation_state is None


def test_missing_policy_result_is_unresolved_when_policy_applies():
    result = evaluate_candidate_configuration(base_candidate(policy_status=None))

    assert result.recommendation_state is None
    assert any(
        check.check_id == "policy" and check.status == CandidateCheckStatus.UNRESOLVED
        for check in result.checks
    )


def test_policy_not_applicable_explicitly_has_no_policy_axis():
    result = evaluate_candidate_configuration(
        base_candidate(
            policy_applicability=PolicyApplicability.NOT_APPLICABLE,
            policy_status=None,
        )
    )

    assert result.recommendation_state == RecommendationState.RECOMMENDED
    assert not any(check.check_id == "policy" for check in result.checks)


def test_policy_not_applicable_rejects_supplied_policy_result():
    with pytest.raises(ValueError, match="must not supply a policy evaluation"):
        base_candidate(policy_applicability=PolicyApplicability.NOT_APPLICABLE)


def test_connection_review_signal_is_preserved_without_automatically_blocking_candidate():
    result = evaluate_candidate_configuration(
        base_candidate(
            tool_side_connection=tool_connection(review_required=True),
        )
    )

    assert result.recommendation_state == RecommendationState.RECOMMENDED
    assert result.review_required is True


def test_evidence_backed_tool_attachment_tether_slice_stays_blocked_when_anchor_link_has_no_basis():
    tool_identity = ProductIdentity(
        manufacturer="Klein Tools",
        product_type=ProductType.TOOL,
        name="Insulated Screwdriver",
        sku="6826INS",
        url="https://example.test/klein/6826ins",
    )
    tool_claims = KleinAdapter().extract(
        tool_identity,
        [
            artifact(
                "The tether hole in the handle provides added safety when working at height.",
                url=tool_identity.url,
            )
        ],
    )
    features = resolve_tool_interface_features(tool_claims)

    attachment_identity = ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="360 D Ring Loop Tool Tether",
        sku="101363",
        url="https://example.test/nlg/101363",
    )
    attachment_claims = NLGAdapter().extract(
        attachment_identity,
        [
            artifact(
                "The D Ring creates a secure tether point to attach a tool lanyard. "
                "Create a tether point on any tool with a captive hole or handle and "
                "cinch it around the tool. Max Load: 3 kg.",
                url=attachment_identity.url,
            )
        ],
    )
    eligibility = resolve_attachment_eligibility(attachment_claims)
    assert eligibility is not None
    eligibility_result = evaluate_attachment_eligibility(eligibility, features)
    assert eligibility_result.status == EligibilityStatus.ELIGIBLE
    attachment_ring = resolve_connection_interfaces(attachment_claims)[0]

    tether_identity = ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TETHER,
        name="Bungee Tool Lanyard",
        sku="101372",
        url="https://example.test/nlg/101372",
    )
    tether_claims = NLGAdapter().extract(
        tether_identity,
        [
            artifact(
                "5kg Bungee Tool Lanyard with Rotobiner and Climbing Cord Loop. "
                "Double action Rotobiner with 360 degree rotation. "
                "Attach to an anchor point or tool. "
                "Climbing cord loop attaches to an anchor point or tool. Max Load: 5 kg.",
                url=tether_identity.url,
            )
        ],
    )
    tether_interfaces = resolve_connection_interfaces(tether_claims)
    specs = resolve_connector_specs(tether_claims)
    carabiner_endpoint = next(
        interface
        for interface in tether_interfaces
        if interface.interface_type == "carabiner"
    )
    loop_endpoint = next(
        interface for interface in tether_interfaces if interface.interface_type == "loop"
    )

    tool_side_result = evaluate_endpoint_engagement(
        carabiner_endpoint,
        attachment_ring,
        connector_specs=specs,
    )
    assert tool_side_result.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert tool_side_result.target_role == ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
    assert tool_side_result.endpoint_tether_side == carabiner_endpoint.tether_side

    container_ring = ConnectionInterface(
        interface_id="container_ring",
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="ring",
    )
    anchor_side_result = evaluate_endpoint_engagement(
        loop_endpoint,
        container_ring,
        connector_specs=specs,
    )
    assert loop_endpoint.tether_side == TetherSide.EITHER
    assert anchor_side_result.status == ConnectionStatus.UNRESOLVED
    assert anchor_side_result.target_role == ConnectionInterfaceRole.CONTAINER_CONNECTION
    assert anchor_side_result.endpoint_tether_side == loop_endpoint.tether_side

    result = evaluate_candidate_configuration(
        CandidateConfiguration(
            candidate_id="klein-attachment-tether-container",
            object_mass_kg=2.0,
            load_bearing_components=[
                LoadBearingComponent(component_id="nlg-101363", rated_capacity_kg=3.0),
                LoadBearingComponent(component_id="nlg-101372", rated_capacity_kg=5.0),
                LoadBearingComponent(component_id="container_ring", rated_capacity_kg=5.0),
            ],
            attachment_mode=CandidateAttachmentMode.TOOL_ATTACHMENT,
            attachment_eligibility=eligibility_result,
            tool_side_connection=tool_side_result,
            anchor_side_connection=anchor_side_result,
            policy_applicability=PolicyApplicability.NOT_APPLICABLE,
        )
    )

    assert result.recommendation_state is None
    assert result.pending_verification_connection_ids == []
    assert any(
        check.status == CandidateCheckStatus.REQUIRES_VERIFICATION
        and check.subject_refs == [
            tool_side_result.endpoint_id,
            tool_side_result.target_interface_id,
        ]
        for check in result.checks
    )
    assert any(
        check.status == CandidateCheckStatus.UNRESOLVED
        and check.subject_refs == [loop_endpoint.interface_id, container_ring.interface_id]
        for check in result.checks
    )
