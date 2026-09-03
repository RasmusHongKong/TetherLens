import pytest

from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
)
from tetherlens_ingest.candidate_selection import (
    CandidateRankingContext,
    CandidateSelectionState,
    ContextCheckStatus,
    ContextCheckType,
    rank_and_select_candidates,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.constraints import (
    ProductConstraintDisposition,
    ProductConstraintStatus,
    resolve_product_constraints,
)
from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ConstraintOperator,
)
from tetherlens_ingest.recommendation_run import run_recommendation


EXPOSURE = "salt_spray"
OTHER_EXPOSURE = "hydraulic_fluid"
SOURCE_URL = "https://example.test/manufacturer/tether"


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


def exposure_constraints(product_ref: str, exposure: str):
    return resolve_product_constraints(
        [
            CandidateClaim(
                subject_type=ClaimSubjectType.PRODUCT,
                subject_ref="self",
                property_key="prohibited_exposure",
                value=exposure,
                raw_value=f"Do not expose to {exposure}",
                source_url=SOURCE_URL,
                evidence_method="manufacturer_stated",
                extractor="test.environment.v1",
                claim_type=ClaimType.DECLARED_CONSTRAINT,
                constraint_operator=ConstraintOperator.PROHIBITS,
            )
        ],
        source_product_ref=product_ref,
    )


def tether_option(
    label: str,
    *,
    prohibited_exposure: str | None = None,
    max_length_mm: float = 1200.0,
) -> TetherOption:
    tether_ref = f"product:tether-{label}"
    tool_spec_ref = f"{tether_ref}:connector:tool"
    anchor_spec_ref = f"{tether_ref}:connector:anchor"
    constraints = (
        exposure_constraints(tether_ref, prohibited_exposure)
        if prohibited_exposure is not None
        else []
    )
    return TetherOption(
        tether_ref=tether_ref,
        component=CandidateComponentOption(
            component_ref=f"component:tether-{label}",
            source_product_ref=tether_ref,
            rated_capacity_kg=5.0,
            product_constraints=constraints,
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
        min_length_mm=400.0,
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


def test_prohibited_exposure_resolves_as_contextual_and_does_not_change_hard_viability():
    result = run_recommendation(
        tool(),
        [tether_option("environment", prohibited_exposure=EXPOSURE)],
        [anchor_path()],
    )

    assert result.selection.state == CandidateSelectionState.SELECTED
    assert len(result.evaluations) == 1
    evaluation = result.evaluations[0]
    assert evaluation.recommendation_state is not None
    assert all("prohibited_exposure" not in check.check_id for check in evaluation.checks)

    deferred = result.generated_candidates[0].configuration.product_constraint_evaluations
    assert len(deferred) == 1
    assert deferred[0].status == ProductConstraintStatus.DEFERRED_CONTEXT
    assert deferred[0].component_ref == "component:tether-environment"
    assert deferred[0].resolved_constraint is not None
    assert deferred[0].resolved_constraint.disposition == ProductConstraintDisposition.CONTEXTUAL
    assert deferred[0].resolved_constraint.value == EXPOSURE
    assert deferred[0].source_urls == [SOURCE_URL]


def test_matching_environmental_prohibition_excludes_only_affected_candidate_with_provenance():
    prohibited = tether_option("a-prohibited", prohibited_exposure=EXPOSURE)
    unknown = tether_option("z-unknown")

    baseline = run_recommendation(
        tool(),
        [unknown, prohibited],
        [anchor_path()],
    )
    assert baseline.selection.selected is not None
    assert baseline.selection.selected.generated_candidate.selection.tether_ref == (
        "product:tether-a-prohibited"
    )

    contextual = run_recommendation(
        tool(),
        [unknown, prohibited],
        [anchor_path()],
        ranking_context=CandidateRankingContext(environmental_exposures=[EXPOSURE]),
    )

    assert all(evaluation.recommendation_state is not None for evaluation in contextual.evaluations)
    assert contextual.selection.selected is not None
    assert contextual.selection.selected.generated_candidate.selection.tether_ref == (
        "product:tether-z-unknown"
    )
    assert [
        candidate.generated_candidate.selection.tether_ref
        for candidate in contextual.selection.contextually_infeasible_candidates
    ] == ["product:tether-a-prohibited"]

    by_tether = {
        candidate.generated_candidate.selection.tether_ref: candidate.candidate_id
        for candidate in [
            *contextual.selection.ranked_viable_candidates,
            *contextual.selection.contextually_infeasible_candidates,
        ]
    }
    context_by_id = {
        evaluation.candidate_id: evaluation
        for evaluation in contextual.selection.context_evaluations
    }

    prohibited_check = context_by_id[by_tether["product:tether-a-prohibited"]].checks[0]
    assert prohibited_check.check_type == ContextCheckType.PROHIBITED_EXPOSURE
    assert prohibited_check.status == ContextCheckStatus.INFEASIBLE
    assert "component:tether-a-prohibited" in prohibited_check.subject_refs
    assert "product:tether-a-prohibited" in prohibited_check.subject_refs
    assert SOURCE_URL in prohibited_check.source_urls

    unknown_check = context_by_id[by_tether["product:tether-z-unknown"]].checks[0]
    assert unknown_check.status == ContextCheckStatus.UNKNOWN
    assert "suitability is not established" in unknown_check.reason
    assert unknown_check.source_urls == []


def test_unrelated_exposure_is_neutral_and_does_not_turn_absence_into_suitability():
    result = run_recommendation(
        tool(),
        [tether_option("a-prohibited", prohibited_exposure=EXPOSURE)],
        [anchor_path()],
        ranking_context=CandidateRankingContext(
            environmental_exposures=[OTHER_EXPOSURE]
        ),
    )

    assert result.selection.state == CandidateSelectionState.SELECTED
    assert result.selection.contextually_infeasible_candidates == []
    assert len(result.selection.context_evaluations) == 1
    check = result.selection.context_evaluations[0].checks[0]
    assert check.status == ContextCheckStatus.UNKNOWN
    assert "suitability is not established" in check.reason


def test_environmental_only_exhaustion_requires_every_viable_candidate_to_be_proven_infeasible():
    result = run_recommendation(
        tool(),
        [
            tether_option("first", prohibited_exposure=EXPOSURE),
            tether_option("second", prohibited_exposure=EXPOSURE),
        ],
        [anchor_path()],
        ranking_context=CandidateRankingContext(environmental_exposures=[EXPOSURE]),
    )

    assert result.selection.state == CandidateSelectionState.NO_SUITABLE_RECOMMENDATION
    assert result.selection.ranked_viable_candidates == []
    assert len(result.selection.contextually_infeasible_candidates) == 2
    assert result.selection.blocked_candidates == []
    assert all(evaluation.recommendation_state is not None for evaluation in result.evaluations)


def test_unknown_environmental_candidate_prevents_false_exhaustion():
    result = run_recommendation(
        tool(),
        [
            tether_option("a-prohibited", prohibited_exposure=EXPOSURE),
            tether_option("z-unknown"),
        ],
        [anchor_path()],
        ranking_context=CandidateRankingContext(environmental_exposures=[EXPOSURE]),
    )

    assert result.selection.state == CandidateSelectionState.SELECTED
    assert result.selection.selected is not None
    assert result.selection.selected.generated_candidate.selection.tether_ref == (
        "product:tether-z-unknown"
    )


def test_environmental_context_combines_with_required_reach_without_mutating_hard_evaluations():
    short_unknown = tether_option("a-short", max_length_mm=800.0)
    long_prohibited = tether_option(
        "z-long-prohibited",
        prohibited_exposure=EXPOSURE,
        max_length_mm=1200.0,
    )

    result = run_recommendation(
        tool(),
        [short_unknown, long_prohibited],
        [anchor_path()],
        ranking_context=CandidateRankingContext(
            required_reach_mm=1000.0,
            environmental_exposures=[EXPOSURE],
        ),
    )

    assert result.selection.state == CandidateSelectionState.NO_SUITABLE_RECOMMENDATION
    assert len(result.selection.contextually_infeasible_candidates) == 2
    assert all(evaluation.recommendation_state is not None for evaluation in result.evaluations)
    checks_by_candidate = {
        evaluation.candidate_id: evaluation.checks
        for evaluation in result.selection.context_evaluations
    }
    assert {check.check_type for checks in checks_by_candidate.values() for check in checks} == {
        ContextCheckType.REQUIRED_REACH,
        ContextCheckType.PROHIBITED_EXPOSURE,
    }


def test_contextual_constraint_identity_mismatch_fails_closed():
    run = run_recommendation(
        tool(),
        [tether_option("malformed", prohibited_exposure=EXPOSURE)],
        [anchor_path()],
    )
    generated = run.generated_candidates[0]
    malformed_constraint = generated.configuration.product_constraint_evaluations[0].model_copy(
        update={"component_ref": "component:not-selected"}
    )
    malformed_configuration = generated.configuration.model_copy(
        update={"product_constraint_evaluations": [malformed_constraint]}
    )
    malformed_generated = generated.model_copy(update={"configuration": malformed_configuration})

    with pytest.raises(ValueError, match="component outside the candidate selection"):
        rank_and_select_candidates(
            [malformed_generated],
            run.evaluations,
            ranking_context=CandidateRankingContext(environmental_exposures=[EXPOSURE]),
        )


def test_environmental_exposure_codes_are_explicit_and_deterministic():
    context = CandidateRankingContext(
        environmental_exposures=["salt_spray", "hydraulic_fluid"]
    )
    assert context.environmental_exposures == ["hydraulic_fluid", "salt_spray"]

    with pytest.raises(ValueError, match="duplicate exposure"):
        CandidateRankingContext(environmental_exposures=[EXPOSURE, EXPOSURE])
    with pytest.raises(ValueError, match="non-empty exposure"):
        CandidateRankingContext(environmental_exposures=["   "])
