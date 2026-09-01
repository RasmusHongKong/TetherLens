from __future__ import annotations

from pydantic import BaseModel

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
from .candidate_selection import CandidateSelectionResult, rank_and_select_candidates
from .recommendation import CandidateEvaluation, evaluate_candidate_configuration


class RecommendationRunResult(BaseModel):
    """Complete auditable result of one recommendation run.

    The result retains every generated candidate, every corresponding hard evaluation,
    and the deterministic selection result. It intentionally does not flatten candidate
    provenance or add user-facing explanation/session state.
    """

    generated_candidates: list[GeneratedCandidate]
    evaluations: list[CandidateEvaluation]
    selection: CandidateSelectionResult


def run_recommendation(
    tool: ResolvedToolCandidate,
    tethers: list[TetherOption],
    anchor_paths: list[AnchorPathOption],
    *,
    tool_attachment_assemblies: list[ToolAttachmentAssemblyOption] | None = None,
    product_runtime_state: list[ProductConstraintRuntimeState] | None = None,
    connection_contexts: list[ConnectionEvaluationContext] | None = None,
    policy_contexts: list[CandidatePolicyContext] | None = None,
) -> RecommendationRunResult:
    """Run complete generation -> evaluation -> deterministic selection.

    This boundary owns the generator invocation and evaluates exactly the complete list
    returned by it before selection. The existing generator, evaluator and selector remain
    the sole authorities for candidate construction, hard viability and ranking/global
    exhaustion respectively.

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
    selection = rank_and_select_candidates(generated_candidates, evaluations)

    return RecommendationRunResult(
        generated_candidates=generated_candidates,
        evaluations=evaluations,
        selection=selection,
    )
