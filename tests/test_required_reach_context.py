import itertools
import math

import pytest

from tetherlens_ingest.candidate_generation import (
    CandidateComponentRole,
    CandidatePathSelection,
    CandidateRankingFacts,
    CandidateSelectedComponent,
    GeneratedCandidate,
    _candidate_id,
)
from tetherlens_ingest.candidate_selection import (
    CandidateRankingContext,
    CandidateSelectionState,
    SnagRiskLevel,
    rank_and_select_candidates,
)
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionEvaluation,
    ConnectionInterfaceRole,
    ConnectionStatus,
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
) -> ConnectionEvaluation:
    return ConnectionEvaluation(
        status=ConnectionStatus.COMPATIBLE,
        basis=CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
        endpoint_id=endpoint_id,
        target_interface_id=target_id,
        endpoint_tether_side=side,
        target_role=target_role,
        reason="test compatible connection",
    )


def generated_candidate(
    label: str,
    *,
    min_length_mm: float | None = None,
    max_length_mm: float | None = None,
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
        ranking_facts=CandidateRankingFacts(
            tether_min_length_mm=min_length_mm,
        ),
    )


def evaluation(
    candidate: GeneratedCandidate,
    *,
    state: RecommendationState | None = RecommendationState.RECOMMENDED,
    pending_actions: int = 0,
) -> CandidateEvaluation:
    return CandidateEvaluation(
        candidate_id=candidate.configuration.candidate_id,
        recommendation_state=state,
        checks=[],
        connections=list(candidate.configuration.connections),
        pending_action_constraint_ids=[
            f"action:{index}" for index in range(pending_actions)
        ],
    )


@pytest.mark.parametrize(
    "invalid",
    [0, -1, math.inf, -math.inf, math.nan, True, "1200"],
)
def test_required_reach_must_be_a_finite_positive_number(invalid):
    with pytest.raises(ValueError, match="required_reach_mm"):
        CandidateRankingContext(required_reach_mm=invalid)


def test_known_short_candidate_is_contextually_infeasible_not_hard_blocked():
    short = generated_candidate("short", max_length_mm=900.0)
    adequate = generated_candidate("adequate", max_length_mm=1200.0)

    result = rank_and_select_candidates(
        [short, adequate],
        [evaluation(short), evaluation(adequate)],
        ranking_context=CandidateRankingContext(required_reach_mm=1000.0),
    )

    assert result.state == CandidateSelectionState.SELECTED
    assert result.selected is not None
    assert result.selected.candidate_id == adequate.configuration.candidate_id
    assert [candidate.candidate_id for candidate in result.contextually_infeasible_candidates] == [
        short.configuration.candidate_id
    ]
    assert result.contextually_infeasible_candidates[0].viable
    assert result.blocked_candidates == []


def test_exact_required_reach_threshold_is_feasible_and_excess_reach_is_not_rewarded():
    exact = generated_candidate("exact", max_length_mm=1000.0)
    excess = generated_candidate("excess", max_length_mm=2000.0)
    expected = sorted(
        [exact.configuration.candidate_id, excess.configuration.candidate_id]
    )

    result = rank_and_select_candidates(
        [excess, exact],
        [evaluation(exact), evaluation(excess)],
        ranking_context=CandidateRankingContext(required_reach_mm=1000.0),
    )

    assert [candidate.candidate_id for candidate in result.ranked_viable_candidates] == expected
    assert result.contextually_infeasible_candidates == []


def test_known_adequate_reach_ranks_ahead_of_unknown_reach_even_with_lower_baseline_quality():
    adequate_conditional = generated_candidate("adequate", max_length_mm=1200.0)
    unknown_full = generated_candidate("unknown")

    result = rank_and_select_candidates(
        [unknown_full, adequate_conditional],
        [
            evaluation(unknown_full),
            evaluation(
                adequate_conditional,
                state=RecommendationState.RECOMMENDED_WITH_CONSTRAINTS,
                pending_actions=1,
            ),
        ],
        ranking_context=CandidateRankingContext(required_reach_mm=1000.0),
    )

    assert result.selected is not None
    assert result.selected.candidate_id == adequate_conditional.configuration.candidate_id
    assert [candidate.candidate_id for candidate in result.ranked_viable_candidates] == [
        adequate_conditional.configuration.candidate_id,
        unknown_full.configuration.candidate_id,
    ]


def test_all_unknown_reach_preserves_existing_snag_context_fallback():
    long_retracted = generated_candidate("a-long", min_length_mm=900.0)
    short_retracted = generated_candidate("z-short", min_length_mm=300.0)

    result = rank_and_select_candidates(
        [long_retracted, short_retracted],
        [evaluation(short_retracted), evaluation(long_retracted)],
        ranking_context=CandidateRankingContext(
            required_reach_mm=1000.0,
            snag_risk=SnagRiskLevel.ELEVATED,
        ),
    )

    assert result.selected is not None
    assert result.selected.candidate_id == short_retracted.configuration.candidate_id
    assert result.contextually_infeasible_candidates == []


def test_unknown_reach_remains_selectable_fallback_when_known_candidate_is_too_short():
    short = generated_candidate("short", max_length_mm=900.0)
    unknown = generated_candidate("unknown")

    result = rank_and_select_candidates(
        [short, unknown],
        [evaluation(short), evaluation(unknown)],
        ranking_context=CandidateRankingContext(required_reach_mm=1000.0),
    )

    assert result.state == CandidateSelectionState.SELECTED
    assert result.selected is not None
    assert result.selected.candidate_id == unknown.configuration.candidate_id
    assert [candidate.candidate_id for candidate in result.contextually_infeasible_candidates] == [
        short.configuration.candidate_id
    ]


def test_complete_known_reach_exhaustion_can_produce_no_suitable_recommendation():
    first = generated_candidate("first", max_length_mm=800.0)
    second = generated_candidate("second", max_length_mm=900.0)

    result = rank_and_select_candidates(
        [first, second],
        [evaluation(first), evaluation(second)],
        ranking_context=CandidateRankingContext(required_reach_mm=1000.0),
    )

    assert result.state == CandidateSelectionState.NO_SUITABLE_RECOMMENDATION
    assert result.selected is None
    assert result.ranked_viable_candidates == []
    assert {candidate.candidate_id for candidate in result.contextually_infeasible_candidates} == {
        first.configuration.candidate_id,
        second.configuration.candidate_id,
    }
    assert result.blocked_candidates == []


def test_hard_blocking_and_contextual_reach_exclusion_remain_separate():
    blocked_short = generated_candidate("blocked-short", max_length_mm=500.0)
    viable_short = generated_candidate("viable-short", max_length_mm=900.0)

    result = rank_and_select_candidates(
        [blocked_short, viable_short],
        [evaluation(blocked_short, state=None), evaluation(viable_short)],
        ranking_context=CandidateRankingContext(required_reach_mm=1000.0),
    )

    assert result.state == CandidateSelectionState.NO_SUITABLE_RECOMMENDATION
    assert [candidate.candidate_id for candidate in result.blocked_candidates] == [
        blocked_short.configuration.candidate_id
    ]
    assert [candidate.candidate_id for candidate in result.contextually_infeasible_candidates] == [
        viable_short.configuration.candidate_id
    ]


def test_required_reach_selection_is_input_order_independent():
    adequate = generated_candidate("adequate", max_length_mm=1200.0)
    unknown = generated_candidate("unknown")
    short = generated_candidate("short", max_length_mm=900.0)
    expected_contextual = [short.configuration.candidate_id]

    for generated_order in itertools.permutations([adequate, unknown, short]):
        evaluations = [evaluation(candidate) for candidate in reversed(generated_order)]
        result = rank_and_select_candidates(
            list(generated_order),
            evaluations,
            ranking_context=CandidateRankingContext(required_reach_mm=1000.0),
        )
        assert result.selected is not None
        assert result.selected.candidate_id == adequate.configuration.candidate_id
        assert [
            candidate.candidate_id for candidate in result.ranked_viable_candidates
        ] == [
            adequate.configuration.candidate_id,
            unknown.configuration.candidate_id,
        ]
        assert [
            candidate.candidate_id for candidate in result.contextually_infeasible_candidates
        ] == expected_contextual
