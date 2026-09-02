import pytest

import tetherlens_ingest.recommendation_run as recommendation_run_module
from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
)
from tetherlens_ingest.candidate_selection import (
    CandidateRankingContext,
    CandidateSelectionState,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.recommendation import RecommendationState
from tetherlens_ingest.recommendation_run import RecommendationRunResult, run_recommendation


def direct_ring() -> ConnectionInterface:
    return ConnectionInterface(
        interface_id="tool:ring",
        role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
        interface_type="ring",
    )


def container_ring() -> ConnectionInterface:
    return ConnectionInterface(
        interface_id="container:ring",
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="ring",
    )


def tether_option(label: str, *, capacity_kg: float) -> TetherOption:
    tether_ref = f"product:tether-{label}"
    tool_spec_ref = f"{tether_ref}:connector:tool"
    anchor_spec_ref = f"{tether_ref}:connector:anchor"
    return TetherOption(
        tether_ref=tether_ref,
        component=CandidateComponentOption(
            component_ref=f"component:tether-{label}",
            source_product_ref=tether_ref,
            rated_capacity_kg=capacity_kg,
        ),
        endpoints=[
            ConnectionInterface(
                interface_id=f"endpoint:{label}:tool",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.TOOL_SIDE,
                connector_spec_ref=tool_spec_ref,
            ),
            ConnectionInterface(
                interface_id=f"endpoint:{label}:anchor",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.ANCHOR_SIDE,
                connector_spec_ref=anchor_spec_ref,
            ),
        ],
        connector_specs={
            tool_spec_ref: ConnectorSpec(
                connector_spec_id=tool_spec_ref,
                opening_action_count=2,
            ),
            anchor_spec_ref: ConnectorSpec(
                connector_spec_id=anchor_spec_ref,
                opening_action_count=2,
            ),
        },
        max_length_mm=1200.0,
    )


def anchor_path() -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="anchor:path-1",
        components=[
            CandidateComponentOption(
                component_ref="component:anchor-1",
                source_product_ref="product:anchor-1",
                rated_capacity_kg=5.0,
            )
        ],
        target_interfaces=[container_ring()],
    )


def tool() -> ResolvedToolCandidate:
    return ResolvedToolCandidate(
        tool_ref="tool:1",
        object_mass_kg=2.0,
        direct_interfaces=[direct_ring()],
    )


def test_run_recommendation_retains_complete_set_and_selects_real_viable_candidate():
    result = run_recommendation(
        tool(),
        [
            tether_option("blocked", capacity_kg=1.0),
            tether_option("viable", capacity_kg=5.0),
        ],
        [anchor_path()],
    )

    assert len(result.generated_candidates) == 2
    assert len(result.evaluations) == 2
    assert {
        candidate.configuration.candidate_id for candidate in result.generated_candidates
    } == {evaluation.candidate_id for evaluation in result.evaluations}

    assert result.selection.state == CandidateSelectionState.SELECTED
    assert result.selection.selected is not None
    assert result.selection.selected.generated_candidate.selection.tether_ref == "product:tether-viable"
    assert (
        result.selection.selected.evaluation.recommendation_state
        == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    )
    assert len(result.selection.ranked_viable_candidates) == 1
    assert len(result.selection.blocked_candidates) == 1


def test_recommendation_run_result_rejects_incomplete_evaluation_coverage():
    result = run_recommendation(
        tool(),
        [tether_option("viable", capacity_kg=5.0)],
        [anchor_path()],
    )

    with pytest.raises(ValueError, match="exact evaluation coverage"):
        RecommendationRunResult(
            generated_candidates=result.generated_candidates,
            evaluations=[],
            selection=result.selection,
        )


def test_recommendation_run_result_rejects_selection_inconsistent_with_required_reach():
    result = run_recommendation(
        tool(),
        [tether_option("viable", capacity_kg=5.0)],
        [anchor_path()],
    )

    with pytest.raises(ValueError, match="must match deterministic selection"):
        RecommendationRunResult(
            generated_candidates=result.generated_candidates,
            evaluations=result.evaluations,
            ranking_context=CandidateRankingContext(required_reach_mm=1300.0),
            selection=result.selection,
        )


def test_recommendation_run_result_rejects_contextual_exclusion_without_reach_requirement():
    contextual = run_recommendation(
        tool(),
        [tether_option("viable", capacity_kg=5.0)],
        [anchor_path()],
        ranking_context=CandidateRankingContext(required_reach_mm=1300.0),
    )

    with pytest.raises(ValueError, match="must match deterministic selection"):
        RecommendationRunResult(
            generated_candidates=contextual.generated_candidates,
            evaluations=contextual.evaluations,
            selection=contextual.selection,
        )


def test_run_recommendation_can_conclude_global_exhaustion_only_after_complete_evaluation():
    result = run_recommendation(
        tool(),
        [
            tether_option("blocked-a", capacity_kg=1.0),
            tether_option("blocked-b", capacity_kg=1.5),
        ],
        [anchor_path()],
    )

    assert len(result.generated_candidates) == 2
    assert len(result.evaluations) == 2
    assert all(evaluation.recommendation_state is None for evaluation in result.evaluations)
    assert result.selection.state == CandidateSelectionState.NO_SUITABLE_RECOMMENDATION
    assert result.selection.ranked_viable_candidates == []
    assert len(result.selection.blocked_candidates) == 2


def test_run_recommendation_preserves_empty_generation_as_distinct_outcome():
    result = run_recommendation(tool(), [], [anchor_path()])

    assert result.generated_candidates == []
    assert result.evaluations == []
    assert result.selection.state == CandidateSelectionState.NO_GENERATED_CANDIDATES
    assert result.selection.selected is None


def test_run_recommendation_evaluates_every_generated_candidate_exactly_once(monkeypatch):
    evaluated_ids: list[str] = []
    original_evaluator = recommendation_run_module.evaluate_candidate_configuration

    def tracking_evaluator(candidate):
        evaluated_ids.append(candidate.candidate_id)
        return original_evaluator(candidate)

    monkeypatch.setattr(
        recommendation_run_module,
        "evaluate_candidate_configuration",
        tracking_evaluator,
    )

    result = recommendation_run_module.run_recommendation(
        tool(),
        [
            tether_option("first", capacity_kg=5.0),
            tether_option("second", capacity_kg=5.0),
        ],
        [anchor_path()],
    )

    generated_ids = [
        candidate.configuration.candidate_id for candidate in result.generated_candidates
    ]
    assert evaluated_ids == generated_ids
    assert len(evaluated_ids) == len(set(evaluated_ids)) == 2


def test_run_recommendation_does_not_convert_stage_failure_into_exhaustion(monkeypatch):
    def failing_evaluator(candidate):
        raise RuntimeError(f"evaluation failed for {candidate.candidate_id}")

    monkeypatch.setattr(
        recommendation_run_module,
        "evaluate_candidate_configuration",
        failing_evaluator,
    )

    with pytest.raises(RuntimeError, match="evaluation failed"):
        recommendation_run_module.run_recommendation(
            tool(),
            [tether_option("viable", capacity_kg=5.0)],
            [anchor_path()],
        )
