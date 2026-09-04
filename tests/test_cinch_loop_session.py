import pytest

from tetherlens_ingest.candidate_generation import (
    CandidateComponentRole,
    CandidatePathSelection,
    CandidateSelectedComponent,
    GeneratedCandidate,
    _candidate_id,
)
from tetherlens_ingest.candidate_selection import rank_and_select_candidates
from tetherlens_ingest.connection import (
    CinchLoopClosedInterfaceVerification,
    CompatibilityBasis,
    ConnectionEvaluation,
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    ConnectorSpec,
    GatedConnectorClosedInterfaceVerification,
    TetherSide,
    evaluate_endpoint_engagement,
)
from tetherlens_ingest.recommendation import (
    CandidateAttachmentMode,
    CandidateConfiguration,
    LoadBearingComponent,
    PolicyApplicability,
    evaluate_candidate_configuration,
)
from tetherlens_ingest.recommendation_run import RecommendationRunResult
from tetherlens_ingest.recommendation_session import (
    SessionConditionKind,
    SessionConditionOutcome,
    resolve_recommendation_session,
)
from tetherlens_ingest.recommendation_session_adapter import (
    derive_connection_session_resolution,
)


def compatible_anchor_connection() -> ConnectionEvaluation:
    return ConnectionEvaluation(
        status=ConnectionStatus.COMPATIBLE,
        basis=CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
        endpoint_id="endpoint:other",
        target_interface_id="anchor:other",
        endpoint_tether_side=TetherSide.ANCHOR_SIDE,
        target_role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        reason="test connection is already compatible",
    )


def cinch_candidate() -> GeneratedCandidate:
    endpoint = ConnectionInterface(
        interface_id="endpoint:loop",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="loop",
        tether_side=TetherSide.TOOL_SIDE,
        connector_spec_ref="connector:loop",
    )
    target = ConnectionInterface(
        interface_id="tool:handle",
        role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
        interface_type="closed_handle",
    )
    spec = ConnectorSpec(
        connector_spec_id="connector:loop",
        attributes={"engagement_method": "cinch"},
    )
    pending_connection = evaluate_endpoint_engagement(
        endpoint,
        target,
        connector_specs={spec.connector_spec_id: spec},
    )

    selection = CandidatePathSelection(
        tool_ref="tool:1",
        tether_ref="tether:1",
        anchor_path_ref="anchor:1",
        tool_endpoint_id="endpoint:loop",
        tool_target_interface_id="tool:handle",
        anchor_endpoint_id="endpoint:other",
        anchor_target_interface_id="anchor:other",
        components=[
            CandidateSelectedComponent(
                component_ref="component:tether",
                source_product_ref="tether:1",
                role=CandidateComponentRole.TETHER,
            )
        ],
    )
    candidate_id = _candidate_id(selection)
    return GeneratedCandidate(
        selection=selection,
        configuration=CandidateConfiguration(
            candidate_id=candidate_id,
            object_mass_kg=1.0,
            load_bearing_components=[
                LoadBearingComponent(
                    component_id="component:tether",
                    rated_capacity_kg=5.0,
                )
            ],
            tether_max_length_mm=1200.0,
            attachment_mode=CandidateAttachmentMode.DIRECT,
            tool_side_connection=pending_connection,
            anchor_side_connection=compatible_anchor_connection(),
            policy_applicability=PolicyApplicability.NOT_APPLICABLE,
        ),
    )


def recommendation_session(candidate: GeneratedCandidate):
    evaluation = evaluate_candidate_configuration(candidate.configuration)
    selection = rank_and_select_candidates([candidate], [evaluation])
    run = RecommendationRunResult(
        generated_candidates=[candidate],
        evaluations=[evaluation],
        selection=selection,
    )
    return run, resolve_recommendation_session(run)


def test_cinch_session_adapter_keeps_partial_observations_pending():
    candidate = cinch_candidate()
    run, session = recommendation_session(candidate)
    original_evaluation = run.evaluations[0].model_copy(deep=True)
    condition = session.active_pending_conditions[0]

    resolution = derive_connection_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        observations=CinchLoopClosedInterfaceVerification(
            target_fully_captured=True,
        ),
    )

    assert resolution is None
    assert condition.condition_kind == SessionConditionKind.RUNTIME_VERIFICATION
    assert run.evaluations[0] == original_evaluation


def test_cinch_session_adapter_maps_pass_and_failure_without_mutating_original():
    candidate = cinch_candidate()
    run, session = recommendation_session(candidate)
    original_evaluation = run.evaluations[0].model_copy(deep=True)
    condition = session.active_pending_conditions[0]

    passed = derive_connection_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        observations=CinchLoopClosedInterfaceVerification(
            target_fully_captured=True,
            cinch_drawn_tight=True,
        ),
    )
    failed = derive_connection_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        observations=CinchLoopClosedInterfaceVerification(
            target_fully_captured=False,
            cinch_drawn_tight=True,
        ),
    )

    assert passed is not None
    assert passed.outcome == SessionConditionOutcome.SATISFIED
    assert failed is not None
    assert failed.outcome == SessionConditionOutcome.FAILED
    assert run.evaluations[0] == original_evaluation


def test_cinch_session_adapter_rejects_observations_from_other_verification_family():
    candidate = cinch_candidate()
    _, session = recommendation_session(candidate)
    condition = session.active_pending_conditions[0]

    with pytest.raises(ValueError, match="cinch-loop condition requires"):
        derive_connection_session_resolution(
            session,
            candidate_id=candidate.configuration.candidate_id,
            condition_id=condition.condition_id,
            observations=GatedConnectorClosedInterfaceVerification(
                target_fully_captured=True,
            ),
        )
