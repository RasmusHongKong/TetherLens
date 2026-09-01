import itertools

import pytest

from tetherlens_ingest.candidate_generation import (
    CandidateComponentRole,
    CandidatePathSelection,
    CandidateSelectedComponent,
    GeneratedCandidate,
    _candidate_id,
)
from tetherlens_ingest.candidate_selection import (
    CandidateSelectionResult,
    CandidateSelectionState,
    EvaluatedCandidate,
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


def connection(
    *,
    endpoint_id: str,
    target_id: str,
    target_role: ConnectionInterfaceRole,
    side: TetherSide,
    basis: CompatibilityBasis = CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
    review_required: bool = False,
) -> ConnectionEvaluation:
    return ConnectionEvaluation(
        status=ConnectionStatus.COMPATIBLE,
        basis=basis,
        endpoint_id=endpoint_id,
        target_interface_id=target_id,
        endpoint_tether_side=side,
        target_role=target_role,
        reason="test compatible connection",
        verification_status=(
            RuntimeVerificationStatus.PASSED
            if basis == CompatibilityBasis.RUNTIME_VERIFICATION
            else None
        ),
        review_required=review_required,
    )


def generated_candidate(label: str) -> GeneratedCandidate:
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
            ),
            CandidateSelectedComponent(
                component_ref="component:anchor",
                source_product_ref="anchor:1",
                role=CandidateComponentRole.ANCHOR,
            ),
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
                ),
                LoadBearingComponent(
                    component_id="component:anchor",
                    rated_capacity_kg=5.0,
                ),
            ],
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
    state: RecommendationState | None = RecommendationState.RECOMMENDED,
    pending_verifications: int = 0,
    pending_actions: int = 0,
    tool_basis: CompatibilityBasis = CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
    anchor_basis: CompatibilityBasis = CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
    review_required: bool = False,
) -> CandidateEvaluation:
    label = candidate.selection.tether_ref.removeprefix("tether:")
    return CandidateEvaluation(
        candidate_id=candidate.configuration.candidate_id,
        recommendation_state=state,
        checks=[],
        connections=[
            connection(
                endpoint_id=f"endpoint:{label}:tool",
                target_id="tool:ring",
                target_role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
                side=TetherSide.TOOL_SIDE,
                basis=tool_basis,
                review_required=review_required,
            ),
            connection(
                endpoint_id=f"endpoint:{label}:anchor",
                target_id="anchor:ring",
                target_role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
                side=TetherSide.ANCHOR_SIDE,
                basis=anchor_basis,
            ),
        ],
        pending_verification_connection_ids=[
            f"verification:{index}" for index in range(pending_verifications)
        ],
        pending_action_constraint_ids=[
            f"action:{index}" for index in range(pending_actions)
        ],
        review_required=review_required,
    )


def test_blocked_candidate_is_never_ranked_or_selected():
    blocked = generated_candidate("blocked")
    viable = generated_candidate("viable")

    result = rank_and_select_candidates(
        [blocked, viable],
        [
            evaluation(blocked, state=None),
            evaluation(viable),
        ],
    )

    assert result.state == CandidateSelectionState.SELECTED
    assert result.selected is not None
    assert result.selected.candidate_id == viable.configuration.candidate_id
    assert [candidate.candidate_id for candidate in result.ranked_viable_candidates] == [
        viable.configuration.candidate_id
    ]
    assert [candidate.candidate_id for candidate in result.blocked_candidates] == [
        blocked.configuration.candidate_id
    ]


def test_fully_recommended_candidate_beats_conditional_candidate():
    full = generated_candidate("full")
    conditional = generated_candidate("conditional")

    result = rank_and_select_candidates(
        [conditional, full],
        [
            evaluation(
                conditional,
                state=RecommendationState.RECOMMENDED_WITH_CONSTRAINTS,
                pending_actions=1,
            ),
            evaluation(full),
        ],
    )

    assert result.selected is not None
    assert result.selected.candidate_id == full.configuration.candidate_id


def test_conditional_ranking_prefers_fewer_pending_conditions_then_fewer_verifications():
    one_action = generated_candidate("one-action")
    one_verification = generated_candidate("one-verification")
    two_actions = generated_candidate("two-actions")

    result = rank_and_select_candidates(
        [two_actions, one_verification, one_action],
        [
            evaluation(
                two_actions,
                state=RecommendationState.RECOMMENDED_WITH_CONSTRAINTS,
                pending_actions=2,
            ),
            evaluation(
                one_verification,
                state=RecommendationState.RECOMMENDED_WITH_CONSTRAINTS,
                pending_verifications=1,
                tool_basis=CompatibilityBasis.RUNTIME_VERIFICATION,
            ),
            evaluation(
                one_action,
                state=RecommendationState.RECOMMENDED_WITH_CONSTRAINTS,
                pending_actions=1,
            ),
        ],
    )

    assert [candidate.candidate_id for candidate in result.ranked_viable_candidates] == [
        one_action.configuration.candidate_id,
        one_verification.configuration.candidate_id,
        two_actions.configuration.candidate_id,
    ]


def test_established_connection_evidence_beats_runtime_evidence_when_other_factors_tie():
    established = generated_candidate("established")
    runtime = generated_candidate("runtime")

    result = rank_and_select_candidates(
        [runtime, established],
        [
            evaluation(runtime, tool_basis=CompatibilityBasis.RUNTIME_VERIFICATION),
            evaluation(established),
        ],
    )

    assert result.selected is not None
    assert result.selected.candidate_id == established.configuration.candidate_id


def test_review_signal_is_only_a_late_ranking_preference():
    clean = generated_candidate("clean")
    review = generated_candidate("review")

    result = rank_and_select_candidates(
        [review, clean],
        [
            evaluation(review, review_required=True),
            evaluation(clean),
        ],
    )

    assert result.selected is not None
    assert result.selected.candidate_id == clean.configuration.candidate_id
    assert review.configuration.candidate_id in {
        candidate.candidate_id for candidate in result.ranked_viable_candidates
    }


def test_total_tie_uses_canonical_candidate_id_and_is_input_order_independent():
    first = generated_candidate("first")
    second = generated_candidate("second")
    expected = sorted(
        [first.configuration.candidate_id, second.configuration.candidate_id]
    )

    for generated_order in itertools.permutations([first, second]):
        evaluations = [evaluation(candidate) for candidate in reversed(generated_order)]
        result = rank_and_select_candidates(list(generated_order), evaluations)
        assert [candidate.candidate_id for candidate in result.ranked_viable_candidates] == expected
        assert result.selected is not None
        assert result.selected.candidate_id == expected[0]


def test_ranked_candidate_retains_original_selection_and_component_provenance():
    candidate = generated_candidate("provenance")

    result = rank_and_select_candidates([candidate], [evaluation(candidate)])

    assert result.selected is not None
    selected = result.selected.generated_candidate.selection
    assert selected.tether_ref == "tether:provenance"
    assert [component.component_ref for component in selected.components] == [
        "component:provenance:tether",
        "component:anchor",
    ]
    assert [component.source_product_ref for component in selected.components] == [
        "tether:provenance",
        "anchor:1",
    ]


def test_exact_evaluation_coverage_is_required_before_selection_or_exhaustion():
    first = generated_candidate("first")
    second = generated_candidate("second")
    unexpected = generated_candidate("unexpected")

    with pytest.raises(ValueError, match="exact evaluation coverage"):
        rank_and_select_candidates(
            [first, second],
            [evaluation(first), evaluation(unexpected)],
        )


def test_duplicate_generated_or_evaluation_ids_are_rejected():
    candidate = generated_candidate("duplicate")

    with pytest.raises(ValueError, match="generated candidate ids must be unique"):
        rank_and_select_candidates(
            [candidate, candidate],
            [evaluation(candidate)],
        )

    with pytest.raises(ValueError, match="candidate evaluation ids must be unique"):
        rank_and_select_candidates(
            [candidate],
            [evaluation(candidate), evaluation(candidate)],
        )


def test_no_suitable_recommendation_requires_nonempty_fully_evaluated_exhaustion():
    first = generated_candidate("first")
    second = generated_candidate("second")

    exhausted = rank_and_select_candidates(
        [first, second],
        [evaluation(first, state=None), evaluation(second, state=None)],
    )
    empty = rank_and_select_candidates([], [])

    assert exhausted.state == CandidateSelectionState.NO_SUITABLE_RECOMMENDATION
    assert exhausted.selected is None
    assert exhausted.ranked_viable_candidates == []
    assert len(exhausted.blocked_candidates) == 2

    assert empty.state == CandidateSelectionState.NO_GENERATED_CANDIDATES
    assert empty.selected is None
    assert empty.ranked_viable_candidates == []
    assert empty.blocked_candidates == []


def test_evaluated_candidate_rejects_identity_mismatch():
    first = generated_candidate("first")
    second = generated_candidate("second")

    with pytest.raises(ValueError, match="same candidate_id"):
        EvaluatedCandidate(
            generated_candidate=first,
            evaluation=evaluation(second),
        )


def test_selection_result_rejects_blocked_selected_object_with_winner_id():
    candidate = generated_candidate("winner")
    ranked = EvaluatedCandidate(
        generated_candidate=candidate,
        evaluation=evaluation(candidate),
    )
    blocked_selected = EvaluatedCandidate(
        generated_candidate=candidate,
        evaluation=evaluation(candidate, state=None),
    )

    with pytest.raises(ValueError, match="selected candidate must be viable"):
        CandidateSelectionResult(
            state=CandidateSelectionState.SELECTED,
            selected=blocked_selected,
            ranked_viable_candidates=[ranked],
        )


def test_selection_result_requires_complete_selected_object_to_match_ranked_winner():
    candidate = generated_candidate("winner")
    ranked = EvaluatedCandidate(
        generated_candidate=candidate,
        evaluation=evaluation(candidate),
    )
    different_selected = EvaluatedCandidate(
        generated_candidate=candidate,
        evaluation=evaluation(candidate, review_required=True),
    )

    with pytest.raises(ValueError, match="complete first ranked viable candidate"):
        CandidateSelectionResult(
            state=CandidateSelectionState.SELECTED,
            selected=different_selected,
            ranked_viable_candidates=[ranked],
        )
