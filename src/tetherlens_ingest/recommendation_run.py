from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, Field, model_validator

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
from .compatibility import ToolInterfaceFeature
from .connection import ConnectionInterface
from .recommendation import CandidateEvaluation, evaluate_candidate_configuration


class CandidateToolBinding(BaseModel):
    """Generation-time Tool-side facts independently bound to one candidate.

    A direct candidate retains the exact normalized Tool interface it targeted. A
    ToolAttachment candidate instead retains the exact Tool feature whose facts made the
    selected eligibility binding possible. These snapshots are deliberately independent
    of ``RecommendationRunResult.tool`` so reconstruction cannot replace the retained Tool
    and make an old generated path appear valid merely by recomputing a run-level digest.
    """

    candidate_id: str = Field(min_length=1)
    direct_interface: ConnectionInterface | None = None
    installation_feature: ToolInterfaceFeature | None = None

    @model_validator(mode="after")
    def validate_one_binding_kind(self) -> CandidateToolBinding:
        if (self.direct_interface is None) == (self.installation_feature is None):
            raise ValueError(
                "candidate Tool binding must retain exactly one direct interface or "
                "ToolAttachment installation feature"
            )
        return self


class RecommendationRunResult(BaseModel):
    """Complete auditable result of one recommendation run.

    Runs produced by ``run_recommendation`` retain the exact normalized Tool input, a
    canonical fingerprint of that generation input, and independent per-candidate
    generation-time Tool bindings, in addition to every generated candidate, every
    corresponding hard evaluation, the explicit ranking context, and the deterministic
    selection result. ``tool`` remains optional only for older/manual focused fixtures
    that construct a run directly rather than through the orchestration boundary.
    """

    tool: ResolvedToolCandidate | None = None
    tool_fingerprint: str | None = None
    generation_tool_bindings: list[CandidateToolBinding] = Field(default_factory=list)
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

        binding_ids = [binding.candidate_id for binding in self.generation_tool_bindings]
        if len(set(binding_ids)) != len(binding_ids):
            raise ValueError(
                "recommendation run generation Tool bindings must be unique per candidate"
            )

        if self.tool is None:
            if self.tool_fingerprint is not None:
                raise ValueError(
                    "recommendation run Tool fingerprint requires a retained normalized Tool"
                )
            if self.generation_tool_bindings:
                raise ValueError(
                    "recommendation run generation Tool bindings require a retained normalized Tool"
                )
        else:
            if self.tool_fingerprint is None:
                raise ValueError(
                    "recommendation run retaining a Tool must retain its generation fingerprint"
                )
            expected_fingerprint = resolved_tool_fingerprint(self.tool)
            if self.tool_fingerprint != expected_fingerprint:
                raise ValueError(
                    "recommendation run retained Tool must match the exact normalized Tool "
                    "generation fingerprint"
                )

            if set(binding_ids) != set(generated_ids):
                missing = sorted(set(generated_ids) - set(binding_ids))
                unexpected = sorted(set(binding_ids) - set(generated_ids))
                raise ValueError(
                    "recommendation run requires exact generation Tool binding coverage for its "
                    f"generated set; missing bindings={missing!r}, unexpected bindings={unexpected!r}"
                )

            bindings_by_candidate = {
                binding.candidate_id: binding for binding in self.generation_tool_bindings
            }
            direct_interfaces_by_id = {
                interface.interface_id: interface for interface in self.tool.direct_interfaces
            }
            features_by_id = {feature.feature_id: feature for feature in self.tool.features}

            for candidate in self.generated_candidates:
                candidate_id = candidate.configuration.candidate_id
                selection = candidate.selection
                binding = bindings_by_candidate[candidate_id]
                if selection.tool_ref != self.tool.tool_ref:
                    raise ValueError(
                        "recommendation run generated candidates must retain the run Tool identity; "
                        f"candidate {candidate_id!r} has {selection.tool_ref!r}, "
                        f"run Tool is {self.tool.tool_ref!r}"
                    )
                if candidate.configuration.object_mass_kg != self.tool.object_mass_kg:
                    raise ValueError(
                        "recommendation run generated candidates must retain the run Tool operational "
                        f"mass; candidate {candidate_id!r} has "
                        f"{candidate.configuration.object_mass_kg!r}, run Tool has "
                        f"{self.tool.object_mass_kg!r}"
                    )

                if selection.attachment_assembly_ref is None:
                    retained_interface = direct_interfaces_by_id.get(
                        selection.tool_target_interface_id
                    )
                    if retained_interface is None:
                        raise ValueError(
                            "recommendation run direct candidate target must belong to the exact "
                            f"retained run Tool; candidate {candidate_id!r} targets "
                            f"{selection.tool_target_interface_id!r}"
                        )
                    if binding.direct_interface is None:
                        raise ValueError(
                            "recommendation run direct candidate must retain its generation-time "
                            f"Tool interface binding; candidate {candidate_id!r}"
                        )
                    if binding.direct_interface != retained_interface:
                        raise ValueError(
                            "recommendation run generation-time direct interface binding must match "
                            f"the exact retained run Tool; candidate {candidate_id!r}"
                        )
                else:
                    feature_id = selection.installation_feature_id
                    retained_feature = features_by_id.get(feature_id)
                    if retained_feature is None:
                        raise ValueError(
                            "recommendation run ToolAttachment candidate installation feature must "
                            "belong to the exact retained run Tool; "
                            f"candidate {candidate_id!r} binds {feature_id!r}"
                        )
                    if binding.installation_feature is None:
                        raise ValueError(
                            "recommendation run ToolAttachment candidate must retain its "
                            f"generation-time installation feature binding; candidate {candidate_id!r}"
                        )
                    if binding.installation_feature != retained_feature:
                        raise ValueError(
                            "recommendation run generation-time ToolAttachment feature binding must "
                            f"match the exact retained run Tool; candidate {candidate_id!r}"
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

        expected_selection = rank_and_select_candidates(
            self.generated_candidates,
            self.evaluations,
            ranking_context=self.ranking_context,
        )
        if self.selection != expected_selection:
            raise ValueError(
                "recommendation run selection must match deterministic selection for the "
                "retained generated candidates, evaluations, and ranking context"
            )

        return self


def resolved_tool_fingerprint(tool: ResolvedToolCandidate) -> str:
    """Return a canonical digest of every normalized Tool fact used by generation.

    Feature and direct-interface lists are canonicalized by their local identifiers so
    semantically irrelevant list ordering does not change the digest. All facts inside
    those objects, and any future top-level ``ResolvedToolCandidate`` fields, remain part
    of the fingerprint through the complete model dump.
    """

    payload = tool.model_dump(mode="json")
    payload["features"] = sorted(
        payload.get("features", []),
        key=lambda item: item["feature_id"],
    )
    payload["direct_interfaces"] = sorted(
        payload.get("direct_interfaces", []),
        key=lambda item: item["interface_id"],
    )
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _generation_tool_bindings(
    tool: ResolvedToolCandidate,
    generated_candidates: list[GeneratedCandidate],
) -> list[CandidateToolBinding]:
    """Snapshot the exact Tool-side object each generated candidate bound to."""

    direct_interfaces_by_id = {
        interface.interface_id: interface for interface in tool.direct_interfaces
    }
    features_by_id = {feature.feature_id: feature for feature in tool.features}
    bindings: list[CandidateToolBinding] = []

    for candidate in generated_candidates:
        candidate_id = candidate.configuration.candidate_id
        selection = candidate.selection
        if selection.attachment_assembly_ref is None:
            interface = direct_interfaces_by_id.get(selection.tool_target_interface_id)
            if interface is None:
                raise ValueError(
                    "generated direct candidate target is absent from its generation Tool; "
                    f"candidate {candidate_id!r} targets {selection.tool_target_interface_id!r}"
                )
            bindings.append(
                CandidateToolBinding(
                    candidate_id=candidate_id,
                    direct_interface=interface.model_copy(deep=True),
                )
            )
            continue

        feature_id = selection.installation_feature_id
        feature = features_by_id.get(feature_id)
        if feature is None:
            raise ValueError(
                "generated ToolAttachment candidate feature is absent from its generation Tool; "
                f"candidate {candidate_id!r} binds {feature_id!r}"
            )
        bindings.append(
            CandidateToolBinding(
                candidate_id=candidate_id,
                installation_feature=feature.model_copy(deep=True),
            )
        )

    return bindings


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
    retained_tool = tool.model_copy(deep=True)

    return RecommendationRunResult(
        tool=retained_tool,
        tool_fingerprint=resolved_tool_fingerprint(retained_tool),
        generation_tool_bindings=_generation_tool_bindings(tool, generated_candidates),
        generated_candidates=generated_candidates,
        evaluations=evaluations,
        ranking_context=ranking_context,
        selection=selection,
    )
