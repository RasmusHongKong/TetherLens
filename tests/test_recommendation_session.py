import pytest

from tetherlens_ingest.candidate_generation import (
    CandidateComponentRole,
    CandidatePathSelection,
    CandidateSelectedComponent,
    GeneratedCandidate,
    _candidate_id,
)
from tetherlens_ingest.candidate_selection import (
    CandidateRankingContext,
    CandidateSelectionState,
    rank_and_select_candidates,
)
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionEvaluation,
    ConnectionInterfaceRole,
    ConnectionStatus,
    RuntimeVerificationStatus,
    TetherSide,
)
from tetherlens_ingest.recommendation import (
    CandidateAttachmentMode,
    CandidateConfiguration,
    CandidateEvaluation,
    LoadBearingComponent,
    PolicyApplicability,
    RecommendationState,
)
from tetherlens_ingest.recommendation_run import RecommendationRunResult
from tetherlens_ingest.recommendation_session import (
    RecommendationSessionResult,
    RecommendationSessionState,
    SessionConditionKind,
    SessionConditionOutcome,
    SessionConditionRef,
    SessionConditionResolution,
    resolve_recommendation_session,
)


def connection(
    *,
    endpoint_id: str,
    target_id: str,
    target_role: ConnectionInterfaceRole,
    side: TetherSide,
    runtime_pending: bool = False,
) -> ConnectionEvaluation:
    return ConnectionEvaluation(
        status=(
            ConnectionStatus.REQUIRES_VERIFICATION
            if runtime_pending
            else ConnectionStatus.COMPATIBLE
        ),
        basis=(
            CompatibilityBasis.RUNTIME_VERIFICATION
            if runtime_pending
            else CompatibilityBasis.VALIDATED_INTERFACE_CLASS
        ),
        endpoint_id=endpoint_id,
        target_interface_id=target_id,
        endpoint_tether_side=side,
        target_role=target_role,
        reason="test connection",
        verification_status=(
            RuntimeVerificationStatus.PENDING if runtime_pending else None
        ),
        verification_family=(
            "gated_connector_to_closed_interface.v1" if runtime_pending else None
        ),
    )


def generated_candidate(
    label: str,
    *,
    max_length_mm: float | None = 1200.0,
) -> GeneratedCandidate:
    selection = CandidatePathSelection(
        tool_ref="tool:1",
        tether_ref=f"tether:{label}",
        anchor_path_ref="anchor:1",
        tool_endpoint_id=f"endpoint:{label}:tool",
        tool_target_interface_id="tool:ring",
        anchor_endpoint_id=f"endpoint:{label}:anchor",
        anchor_target_interface_id="anchor:ring",
        components=[
            CandidateSelectedComponent(
                component_ref=f"component:{label}:tether",
                source_product_ref=f"tether:{label}",
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
                    component_id=f"component:{label}:tether",
                    rated_capacity_kg=5.0,
                )
            ],
            tether_max_length_mm=max_length_mm,
            attachment_mode=CandidateAttachmentMode.DIRECT,
            tool_side_connection=connection(
                endpoint_id=f"endpoint:{label}:tool",
                target_id="tool:ring",
                target_role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
                side=TetherSide.TOOL_SIDE,
            ),
            anchor_side_connection=connection(
                endpoint_id=f"endpoint:{label}:anchor",
                target_id="anchor:ring",
                target_role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
                side=TetherSide.ANCHOR_SIDE,
            ),
            policy_applicability=PolicyApplicability.NOT_APPLICABLE,
        ),
    )


def evaluation(
    candidate: GeneratedCandidate,
    *,
    pending_verification: str | None = None,
    pending_actions: list[str] | None = None,
    state: RecommendationState | None = None,
) -> CandidateEvaluation:
    pending_actions = list(pending_actions or [])
    has_conditions = pending_verification is not None or bool(pending_actions)
    if state is None:
        state = (
            RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
            if has_conditions
            else RecommendationState.RECOMMENDED
        )

    label = candidate.selection.tether_ref.removeprefix("tether:")
    tool_connection = connection(
        endpoint_id=f"endpoint:{label}:tool",
        target_id="tool:ring",
        target_role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
        side=TetherSide.TOOL_SIDE,
        runtime_pending=pending_verification is not None,
    )
    anchor_connection = connection(
        endpoint_id=f"endpoint:{label}:anchor",
        target_id="anchor:ring",
        target_role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        side=TetherSide.ANCHOR_SIDE,
    )
    return CandidateEvaluation(
        candidate_id=candidate.configuration.candidate_id,
        recommendation_state=state,
        checks=[],
        connections=[tool_connection, anchor_connection],
        pending_verification_connection_ids=(
            [pending_verification] if pending_verification is not None else []
        ),
        pending_action_constraint_ids=pending_actions,
    )


def recommendation_run(
    candidates: list[GeneratedCandidate],
    evaluations: list[CandidateEvaluation],
    *,
    ranking_context: CandidateRankingContext | None = None,
) -> RecommendationRunResult:
    selection = rank_and_select_candidates(
        candidates,
        evaluations,
        ranking_context=ranking_context,
    )
    return RecommendationRunResult(
        generated_candidates=candidates,
        evaluations=evaluations,
        ranking_context=ranking_context,
        selection=selection,
    )


def condition_resolution(
    candidate_id: str,
    kind: SessionConditionKind,
    condition_id: str,
    outcome: SessionConditionOutcome,
) -> SessionConditionResolution:
    return SessionConditionResolution(
        candidate_id=candidate_id,
        condition_kind=kind,
        condition_id=condition_id,
        outcome=outcome,
    )


def test_pending_condition_is_exposed_without_changing_original_candidate():
    candidate = generated_candidate("conditional")
    original_evaluation = evaluation(candidate, pending_actions=["action:bond-time"])
    run = recommendation_run([candidate], [original_evaluation])

    session = resolve_recommendation_session(run)

    assert session.state == RecommendationSessionState.ACTIVE
    assert session.active_candidate == run.selection.selected
    assert session.active_pending_conditions == [
        SessionConditionRef(
            candidate_id=candidate.configuration.candidate_id,
            condition_kind=SessionConditionKind.PRE_USE_ACTION,
            condition_id="action:bond-time",
        )
    ]
    assert session.ready_for_use is False
    assert session.active_candidate.evaluation == original_evaluation


def test_satisfied_condition_keeps_candidate_active_and_preserves_hard_evaluation():
    candidate = generated_candidate("conditional")
    original_evaluation = evaluation(candidate, pending_actions=["action:test"])
    run = recommendation_run([candidate], [original_evaluation])
    resolution = condition_resolution(
        candidate.configuration.candidate_id,
        SessionConditionKind.PRE_USE_ACTION,
        "action:test",
        SessionConditionOutcome.SATISFIED,
    )

    session = resolve_recommendation_session(run, [resolution])

    assert session.active_candidate == run.selection.selected
    assert session.active_pending_conditions == []
    assert session.active_satisfied_conditions == [resolution]
    assert session.ready_for_use is True
    assert (
        session.active_candidate.evaluation.recommendation_state
        == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    )
    assert session.active_candidate.evaluation.pending_action_constraint_ids == ["action:test"]


def test_partial_resolution_keeps_remaining_conditions_pending():
    candidate = generated_candidate("two-conditions")
    original_evaluation = evaluation(
        candidate,
        pending_verification="connection:tool",
        pending_actions=["action:test"],
    )
    run = recommendation_run([candidate], [original_evaluation])
    passed_verification = condition_resolution(
        candidate.configuration.candidate_id,
        SessionConditionKind.RUNTIME_VERIFICATION,
        "connection:tool",
        SessionConditionOutcome.SATISFIED,
    )

    session = resolve_recommendation_session(run, [passed_verification])

    assert session.state == RecommendationSessionState.ACTIVE
    assert session.active_satisfied_conditions == [passed_verification]
    assert session.active_pending_conditions == [
        SessionConditionRef(
            candidate_id=candidate.configuration.candidate_id,
            condition_kind=SessionConditionKind.PRE_USE_ACTION,
            condition_id="action:test",
        )
    ]
    assert session.ready_for_use is False


def test_failed_condition_rejects_only_current_candidate_and_advances_in_original_order():
    first = generated_candidate("a")
    second = generated_candidate("b")
    run = recommendation_run(
        [second, first],
        [
            evaluation(second, pending_actions=["action:check"]),
            evaluation(first, pending_actions=["action:check"]),
        ],
    )
    ranked = run.selection.ranked_viable_candidates
    original_selected = run.selection.selected
    failed = condition_resolution(
        ranked[0].candidate_id,
        SessionConditionKind.PRE_USE_ACTION,
        "action:check",
        SessionConditionOutcome.FAILED,
    )

    session = resolve_recommendation_session(run, [failed])

    assert session.rejected_candidates == [ranked[0]]
    assert session.active_candidate == ranked[1]
    assert run.selection.selected == original_selected == ranked[0]
    assert run.selection.state == CandidateSelectionState.SELECTED


def test_repeated_failures_exhaust_session_without_rewriting_global_run_outcome():
    candidates = [generated_candidate(label) for label in ["a", "b", "c"]]
    run = recommendation_run(
        candidates,
        [evaluation(candidate, pending_actions=["action:check"]) for candidate in candidates],
    )
    ranked = run.selection.ranked_viable_candidates
    resolutions = [
        condition_resolution(
            candidate.candidate_id,
            SessionConditionKind.PRE_USE_ACTION,
            "action:check",
            SessionConditionOutcome.FAILED,
        )
        for candidate in ranked
    ]

    session = resolve_recommendation_session(run, resolutions)

    assert session.state == RecommendationSessionState.EXHAUSTED
    assert session.active_candidate is None
    assert session.rejected_candidates == ranked
    assert session.ready_for_use is False
    assert run.selection.state == CandidateSelectionState.SELECTED
    assert run.selection.selected == ranked[0]


def test_resolution_input_order_is_canonicalized_by_original_ranking_and_condition_order():
    first = generated_candidate("a")
    second = generated_candidate("b")
    run = recommendation_run(
        [first, second],
        [
            evaluation(
                first,
                pending_verification="connection:tool",
                pending_actions=["action:test"],
            ),
            evaluation(second, pending_actions=["action:test"]),
        ],
    )
    ranked = run.selection.ranked_viable_candidates
    first_candidate = ranked[0]
    verification = condition_resolution(
        first_candidate.candidate_id,
        SessionConditionKind.RUNTIME_VERIFICATION,
        "connection:tool",
        SessionConditionOutcome.SATISFIED,
    )
    failed_action = condition_resolution(
        first_candidate.candidate_id,
        SessionConditionKind.PRE_USE_ACTION,
        "action:test",
        SessionConditionOutcome.FAILED,
    )

    forward = resolve_recommendation_session(run, [verification, failed_action])
    reversed_input = resolve_recommendation_session(run, [failed_action, verification])

    assert forward == reversed_input
    assert forward.resolutions == [verification, failed_action]
    assert forward.active_candidate == ranked[1]


def test_same_condition_identifier_on_two_candidates_remains_candidate_scoped():
    candidates = [generated_candidate("a"), generated_candidate("b")]
    run = recommendation_run(
        candidates,
        [evaluation(candidate, pending_actions=["shared-action"]) for candidate in candidates],
    )
    ranked = run.selection.ranked_viable_candidates
    failed_first = condition_resolution(
        ranked[0].candidate_id,
        SessionConditionKind.PRE_USE_ACTION,
        "shared-action",
        SessionConditionOutcome.FAILED,
    )

    session = resolve_recommendation_session(run, [failed_first])

    assert session.active_candidate == ranked[1]
    assert session.active_pending_conditions == [
        SessionConditionRef(
            candidate_id=ranked[1].candidate_id,
            condition_kind=SessionConditionKind.PRE_USE_ACTION,
            condition_id="shared-action",
        )
    ]


@pytest.mark.parametrize(
    "kind, condition_id",
    [
        (SessionConditionKind.RUNTIME_VERIFICATION, "action:test"),
        (SessionConditionKind.PRE_USE_ACTION, "unknown-action"),
    ],
)
def test_resolution_must_match_original_candidate_kind_and_identifier(kind, condition_id):
    candidate = generated_candidate("conditional")
    run = recommendation_run(
        [candidate],
        [evaluation(candidate, pending_actions=["action:test"])],
    )

    with pytest.raises(ValueError, match="originally pending condition"):
        resolve_recommendation_session(
            run,
            [
                condition_resolution(
                    candidate.configuration.candidate_id,
                    kind,
                    condition_id,
                    SessionConditionOutcome.SATISFIED,
                )
            ],
        )


def test_duplicate_terminal_resolution_for_same_condition_is_rejected():
    candidate = generated_candidate("conditional")
    run = recommendation_run(
        [candidate],
        [evaluation(candidate, pending_actions=["action:test"])],
    )
    passed = condition_resolution(
        candidate.configuration.candidate_id,
        SessionConditionKind.PRE_USE_ACTION,
        "action:test",
        SessionConditionOutcome.SATISFIED,
    )
    failed = passed.model_copy(update={"outcome": SessionConditionOutcome.FAILED})

    with pytest.raises(ValueError, match="only one terminal session resolution"):
        resolve_recommendation_session(run, [passed, failed])


def test_lower_ranked_candidate_cannot_be_resolved_before_current_candidate_fails():
    candidates = [generated_candidate("a"), generated_candidate("b")]
    run = recommendation_run(
        candidates,
        [evaluation(candidate, pending_actions=["action:test"]) for candidate in candidates],
    )
    ranked = run.selection.ranked_viable_candidates

    with pytest.raises(ValueError, match="cannot be resolved before"):
        resolve_recommendation_session(
            run,
            [
                condition_resolution(
                    ranked[1].candidate_id,
                    SessionConditionKind.PRE_USE_ACTION,
                    "action:test",
                    SessionConditionOutcome.SATISFIED,
                )
            ],
        )


def test_contextually_infeasible_and_hard_blocked_candidates_cannot_receive_session_resolution():
    selectable = generated_candidate("selectable", max_length_mm=1200.0)
    too_short = generated_candidate("too-short", max_length_mm=500.0)
    blocked = generated_candidate("blocked", max_length_mm=1200.0)
    run = recommendation_run(
        [selectable, too_short, blocked],
        [
            evaluation(selectable, pending_actions=["action:test"]),
            evaluation(too_short, pending_actions=["action:test"]),
            evaluation(blocked, pending_actions=["action:test"], state=None),
        ],
        ranking_context=CandidateRankingContext(required_reach_mm=1000.0),
    )

    assert len(run.selection.contextually_infeasible_candidates) == 1
    assert len(run.selection.blocked_candidates) == 1

    for candidate in [
        run.selection.contextually_infeasible_candidates[0],
        run.selection.blocked_candidates[0],
    ]:
        with pytest.raises(ValueError, match="ranked selectable candidates"):
            resolve_recommendation_session(
                run,
                [
                    condition_resolution(
                        candidate.candidate_id,
                        SessionConditionKind.PRE_USE_ACTION,
                        "action:test",
                        SessionConditionOutcome.FAILED,
                    )
                ],
            )


def test_session_resolution_requires_a_run_with_a_selected_candidate():
    blocked = generated_candidate("blocked")
    exhausted_run = recommendation_run(
        [blocked],
        [evaluation(blocked, state=None)],
    )
    assert exhausted_run.selection.state == CandidateSelectionState.NO_SUITABLE_RECOMMENDATION

    with pytest.raises(ValueError, match="requires a recommendation run with a selected candidate"):
        resolve_recommendation_session(exhausted_run)


def test_reach_unknown_remains_unknown_after_session_condition_is_satisfied():
    unknown = generated_candidate("unknown", max_length_mm=None)
    run = recommendation_run(
        [unknown],
        [evaluation(unknown, pending_actions=["action:test"])],
        ranking_context=CandidateRankingContext(required_reach_mm=1000.0),
    )
    passed = condition_resolution(
        unknown.configuration.candidate_id,
        SessionConditionKind.PRE_USE_ACTION,
        "action:test",
        SessionConditionOutcome.SATISFIED,
    )

    session = resolve_recommendation_session(run, [passed])

    assert session.ready_for_use is True
    assert session.active_candidate is not None
    assert session.active_candidate.generated_candidate.configuration.tether_max_length_mm is None
    assert session.recommendation_run.ranking_context == CandidateRankingContext(
        required_reach_mm=1000.0
    )


def test_directly_constructed_session_result_cannot_replace_deterministic_active_candidate():
    candidates = [generated_candidate("a"), generated_candidate("b")]
    run = recommendation_run(
        candidates,
        [evaluation(candidate, pending_actions=["action:test"]) for candidate in candidates],
    )
    session = resolve_recommendation_session(run)
    ranked = run.selection.ranked_viable_candidates

    with pytest.raises(ValueError, match="first unrejected candidate"):
        RecommendationSessionResult(
            recommendation_run=run,
            resolutions=session.resolutions,
            state=session.state,
            active_candidate=ranked[1],
            active_pending_conditions=session.active_pending_conditions,
            active_satisfied_conditions=session.active_satisfied_conditions,
            rejected_candidates=session.rejected_candidates,
        )
