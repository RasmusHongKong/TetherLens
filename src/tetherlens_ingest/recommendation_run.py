from __future__ import annotations

from pydantic import BaseModel, model_validator

from .candidate_generation import (
    AnchorPathOption,
    CandidatePolicyContext,
    ConnectionEvaluationContext,
    GeneratedCandidate,
    ProductConstraintRuntimeState,
    ResolvedToolCandidate,
    TetherOption,
    ToolAttachmentAssemblyOption,
    generate_candidate_configurations,
)
from .candidate_selection import (
    CandidateRankingContext,
    CandidateSelectionResult,
    rank_and_select_candidates,
)
from .recommendation import CandidateEvaluation, evaluate_candidate_configuration


class RecommendationRunResult(BaseModel):
    """Complete auditable result of one recommendation run.

    The result retains every generated candidate, every corresponding hard evaluation,
    the explicit ranking context, and the deterministic selection result. It intentionally
    does not flatten candidate provenance or add user-facing explanation/session state.
    """

    generated_candidates: list[GeneratedCandidate]
    evaluations: list[CandidateEvaluation]
    ranking_context: CandidateRankingContext | None = None
    selection: CandidateSelectionResult

    @model_validator(mode="after")
    def validate_complete_run(self) -> RecommendationRunResult:
        generated_ids = [
            candidate.configuration.candidate_id for candidate in self.generated_candidates
        ]
        evaluation_ids = [evaluation.candidate_id for evaluation in self.evaluations]

        if len(set(generated_ids)) != len(generated_ids):
            raise ValueError("recommendation run generated candidate ids must be unique")
        if len(set(evaluation_ids)) != len(evaluation_ids):
            raise ValueError("recommendation run evaluation candidate ids must be unique")
        if set(generated_ids) != set(evaluation_ids):
            missing = sorted(set(generated_ids) - set(evaluation_ids))
            unexpected = sorted(set(evaluation_ids) - set(generated_ids))
            raise ValueError(
                "recommendation run requires exact evaluation coverage for its generated set; "
                f"missing evaluations={missing!r}, unexpected evaluations={unexpected!r}"
            )

        selected_candidates = [
            *self.selection.ranked_viable_candidates,
            *self.selection.contextually_infeasible_candidates,
            *self.selection.blocked_candidates,
        ]
        selected_ids = [candidate.candidate_id for candidate in selected_candidates]
        if set(selected_ids) != set(generated_ids):
            missing = sorted(set(generated_ids) - set(selected_ids))
            unexpected = sorted(set(selected_ids) - set(generated_ids))
            raise ValueError(
                "recommendation run selection must cover the exact generated set; "
                f"missing candidates={missing!r}, unexpected candidates={unexpected!r}"
            )

        generated_by_id = {
            candidate.configuration.candidate_id: candidate
            for candidate in self.generated_candidates
        }
        evaluations_by_id = {
            evaluation.candidate_id: evaluation for evaluation in self.evaluations
        }
        for selected_candidate in selected_candidates:
            candidate_id = selected_candidate.candidate_id
            if selected_candidate.generated_candidate != generated_by_id[candidate_id]:
                raise ValueError(
                    "recommendation run selection must retain the generated candidate for "
                    f"{candidate_id!r}"
                )
            if selected_candidate.evaluation != evaluations_by_id[candidate_id]:
                raise ValueError(
                    "recommendation run selection must retain the corresponding evaluation for "
                    f"{candidate_id!r}"
                )

        return self


def run_recommendation(
    tool: ResolvedToolCandidate,
    tethers: list[TetherOption],
    anchor_paths: list[AnchorPathOption],
    *,
    tool_attachment_assemblies: list[ToolAttachmentAssemblyOption] | None = None,
    product_runtime_state: list[ProductConstraintRuntimeState] | None = None,
    connection_contexts: list[ConnectionEvaluationContext] | None = None,
    policy_contexts: list[CandidatePolicyContext] | None = None,
    ranking_context: CandidateRankingContext | None = None,
) -> RecommendationRunResult:
    """Run complete generation -> evaluation -> deterministic contextual selection.

    This boundary owns the generator invocation and evaluates exactly the complete list
    returned by it before selection. The existing generator, evaluator and selector remain
    the sole authorities for candidate construction, hard viability and contextual
    selection/global exhaustion respectively. Ranking context may reorder hard-viable
    candidates and may exclude a candidate only when an explicit contextual feasibility
    rule establishes that the candidate cannot satisfy the stated task requirement.

    Exceptions from any stage deliberately propagate. An orchestration/invariant failure
    is not equivalent to a successful run whose complete candidate set is exhausted.
    """

    generated_candidates = generate_candidate_configurations(
        tool,
        tethers,
        anchor_paths,
        tool_attachment_assemblies=tool_attachment_assemblies,
        product_runtime_state=product_runtime_state,
        connection_contexts=connection_contexts,
        policy_contexts=policy_contexts,
    )
    evaluations = [
        evaluate_candidate_configuration(candidate.configuration)
        for candidate in generated_candidates
    ]
    selection = rank_and_select_candidates(
        generated_candidates,
        evaluations,
        ranking_context=ranking_context,
    )

    return RecommendationRunResult(
        generated_candidates=generated_candidates,
        evaluations=evaluations,
        ranking_context=ranking_context,
        selection=selection,
    )
