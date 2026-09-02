import pytest

from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
    generate_candidate_configurations,
)
from tetherlens_ingest.candidate_selection import (
    CandidateRankingContext,
    CandidateSelectionState,
    SnagRiskLevel,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.recommendation_run import run_recommendation


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


def tether_option(
    label: str,
    *,
    min_length_mm: float | None,
    max_length_mm: float = 1200.0,
) -> TetherOption:
    tether_ref = f"product:tether-{label}"
    tool_spec_ref = f"{tether_ref}:connector:tool"
    anchor_spec_ref = f"{tether_ref}:connector:anchor"
    return TetherOption(
        tether_ref=tether_ref,
        component=CandidateComponentOption(
            component_ref=f"component:tether-{label}",
            source_product_ref=tether_ref,
            rated_capacity_kg=5.0,
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
        min_length_mm=min_length_mm,
        max_length_mm=max_length_mm,
    )


def tool() -> ResolvedToolCandidate:
    return ResolvedToolCandidate(
        tool_ref="tool:1",
        object_mass_kg=2.0,
        direct_interfaces=[direct_ring()],
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


def test_tether_option_rejects_minimum_length_greater_than_maximum_length():
    with pytest.raises(ValueError, match="min_length_mm must be <= max_length_mm"):
        tether_option("invalid", min_length_mm=1300.0, max_length_mm=1200.0)


def test_generation_carries_minimum_length_as_ranking_only_fact():
    generated = generate_candidate_configurations(
        tool(),
        [tether_option("fact", min_length_mm=450.0, max_length_mm=1200.0)],
        [anchor_path()],
    )

    assert len(generated) == 1
    candidate = generated[0]
    assert candidate.ranking_facts.tether_min_length_mm == 450.0
    assert candidate.configuration.tether_max_length_mm == 1200.0
    assert candidate.selection.tether_ref == "product:tether-fact"


def test_run_context_can_change_only_the_order_of_viable_baseline_ties():
    long = tether_option("a-long", min_length_mm=900.0)
    short = tether_option("z-short", min_length_mm=300.0)

    baseline = run_recommendation(
        tool(),
        [short, long],
        [anchor_path()],
    )
    assert baseline.ranking_context is None
    assert baseline.selection.selected is not None
    assert baseline.selection.selected.generated_candidate.selection.tether_ref == (
        "product:tether-a-long"
    )

    context = CandidateRankingContext(snag_risk=SnagRiskLevel.ELEVATED)
    contextual = run_recommendation(
        tool(),
        [short, long],
        [anchor_path()],
        ranking_context=context,
    )

    assert contextual.ranking_context == context
    assert contextual.selection.selected is not None
    assert contextual.selection.selected.generated_candidate.selection.tether_ref == (
        "product:tether-z-short"
    )
    assert [
        candidate.generated_candidate.selection.tether_ref
        for candidate in contextual.selection.ranked_viable_candidates
    ] == [
        "product:tether-z-short",
        "product:tether-a-long",
    ]


def test_run_required_reach_excludes_known_short_candidate_without_changing_hard_evaluation():
    short = tether_option("a-short", min_length_mm=300.0, max_length_mm=900.0)
    adequate = tether_option("z-adequate", min_length_mm=500.0, max_length_mm=1200.0)
    context = CandidateRankingContext(required_reach_mm=1000.0)

    result = run_recommendation(
        tool(),
        [short, adequate],
        [anchor_path()],
        ranking_context=context,
    )

    assert result.ranking_context == context
    assert len(result.generated_candidates) == 2
    assert len(result.evaluations) == 2
    assert all(evaluation.recommendation_state is not None for evaluation in result.evaluations)
    assert result.selection.selected is not None
    assert result.selection.selected.generated_candidate.selection.tether_ref == (
        "product:tether-z-adequate"
    )
    assert [
        candidate.generated_candidate.selection.tether_ref
        for candidate in result.selection.contextually_infeasible_candidates
    ] == ["product:tether-a-short"]
    assert result.selection.blocked_candidates == []


def test_run_can_conclude_no_suitable_when_every_hard_viable_candidate_is_known_too_short():
    first = tether_option("first", min_length_mm=300.0, max_length_mm=800.0)
    second = tether_option("second", min_length_mm=400.0, max_length_mm=900.0)

    result = run_recommendation(
        tool(),
        [first, second],
        [anchor_path()],
        ranking_context=CandidateRankingContext(required_reach_mm=1000.0),
    )

    assert result.selection.state == CandidateSelectionState.NO_SUITABLE_RECOMMENDATION
    assert result.selection.selected is None
    assert result.selection.ranked_viable_candidates == []
    assert len(result.selection.contextually_infeasible_candidates) == 2
    assert result.selection.blocked_candidates == []
