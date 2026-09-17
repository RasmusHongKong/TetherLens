from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, Field, model_validator

from .candidate_generation import (
    AnchorPathOption,
    CandidateComponentRole,
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
from .compatibility import (
    AttachmentEligibility,
    EligibilityPath,
    FeaturePredicate,
    ToolInterfaceFeature,
)
from .connection import ConnectionInterface
from .recommendation import (
    CandidateEvaluation,
    PolicyApplicability,
    evaluate_candidate_configuration,
)
from .tool_attachment_installation import (
    EvidenceBoundToolAttachmentAssemblyOption,
    ToolAttachmentInstallationBinding,
)


class CandidateToolBinding(BaseModel):
    """Generation-time Tool-side facts independently bound to one candidate.

    A direct candidate retains the exact normalized Tool interface it targeted. A
    ToolAttachment candidate retains the exact Tool feature selected during generation.
    When that path exists because of product-scoped manufacturer installation evidence,
    the accepted ``ToolAttachmentInstallationBinding`` is retained separately from the
    feature snapshot rather than being rewritten as a reusable geometry rule.
    """

    candidate_id: str = Field(min_length=1)
    direct_interface: ConnectionInterface | None = None
    installation_feature: ToolInterfaceFeature | None = None
    attachment_installation_binding: ToolAttachmentInstallationBinding | None = None

    @model_validator(mode="after")
    def validate_binding_shape(self) -> CandidateToolBinding:
        if self.direct_interface is not None:
            if (
                self.installation_feature is not None
                or self.attachment_installation_binding is not None
            ):
                raise ValueError(
                    "direct candidate Tool bindings must not retain ToolAttachment installation data"
                )
            return self

        if self.installation_feature is None:
            raise ValueError(
                "candidate Tool binding must retain a direct interface or ToolAttachment feature"
            )
        evidence_binding = self.attachment_installation_binding
        if (
            evidence_binding is not None
            and evidence_binding.installation_feature_id != self.installation_feature.feature_id
        ):
            raise ValueError(
                "evidence-bound ToolAttachment provenance must match the retained installation feature"
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
                    if binding.attachment_installation_binding is not None:
                        raise ValueError(
                            "direct candidate must not retain ToolAttachment installation evidence"
                        )
                    continue

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

                evidence_binding = binding.attachment_installation_binding
                if evidence_binding is not None:
                    if evidence_binding.tool_ref != self.tool.tool_ref:
                        raise ValueError(
                            "ToolAttachment installation evidence must retain the exact run Tool identity"
                        )
                    if evidence_binding.installation_feature_id != feature_id:
                        raise ValueError(
                            "ToolAttachment installation evidence must retain the selected feature identity"
                        )
                    attachment_products = {
                        component.source_product_ref
                        for component in selection.components
                        if component.role == CandidateComponentRole.TOOL_ATTACHMENT
                    }
                    if evidence_binding.source_product_ref not in attachment_products:
                        raise ValueError(
                            "ToolAttachment installation evidence must belong to a selected attachment product"
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
    *,
    evidence_bindings_by_candidate: dict[str, ToolAttachmentInstallationBinding] | None = None,
) -> list[CandidateToolBinding]:
    """Snapshot exact Tool-side objects and any evidence-bound installation provenance."""

    direct_interfaces_by_id = {
        interface.interface_id: interface for interface in tool.direct_interfaces
    }
    features_by_id = {feature.feature_id: feature for feature in tool.features}
    evidence_bindings = evidence_bindings_by_candidate or {}
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
        evidence_binding = evidence_bindings.get(candidate_id)
        bindings.append(
            CandidateToolBinding(
                candidate_id=candidate_id,
                installation_feature=feature.model_copy(deep=True),
                attachment_installation_binding=(
                    evidence_binding.model_copy(deep=True)
                    if evidence_binding is not None
                    else None
                ),
            )
        )

    unexpected = sorted(set(evidence_bindings) - {binding.candidate_id for binding in bindings})
    if unexpected:
        raise ValueError(
            "ToolAttachment installation evidence refers to candidates outside the generated set: "
            f"{unexpected!r}"
        )
    return bindings


def run_recommendation(
    tool: ResolvedToolCandidate,
    tethers: list[TetherOption],
    anchor_paths: list[AnchorPathOption],
    *,
    tool_attachment_assemblies: list[ToolAttachmentAssemblyOption] | None = None,
    evidence_bound_tool_attachment_assemblies: list[
        EvidenceBoundToolAttachmentAssemblyOption
    ]
    | None = None,
    product_runtime_state: list[ProductConstraintRuntimeState] | None = None,
    connection_contexts: list[ConnectionEvaluationContext] | None = None,
    policy_contexts: list[CandidatePolicyContext] | None = None,
    ranking_context: CandidateRankingContext | None = None,
) -> RecommendationRunResult:
    """Run complete generation -> evaluation -> deterministic contextual selection.

    Reusable technical ToolAttachment eligibility is passed to the existing generator
    unchanged. When accepted first-party evidence establishes an exact Tool/product/
    feature installation without enough geometry for a reusable rule, this boundary
    invokes the same generator on a one-feature Tool projection and retains the original
    evidence binding separately in ``CandidateToolBinding``. That execution projection
    is local to this run; it is never persisted or reused as technical compatibility.

    When no evidence-bound assemblies are supplied, generation is exactly the historical
    single generator invocation. Exceptions from any stage deliberately propagate: an
    orchestration/invariant failure is not equivalent to successful global exhaustion.
    """

    evidence_assemblies = list(evidence_bound_tool_attachment_assemblies or [])
    if not evidence_assemblies:
        generated_candidates = generate_candidate_configurations(
            tool,
            tethers,
            anchor_paths,
            tool_attachment_assemblies=tool_attachment_assemblies,
            product_runtime_state=product_runtime_state,
            connection_contexts=connection_contexts,
            policy_contexts=policy_contexts,
        )
        evidence_bindings_by_candidate: dict[
            str, ToolAttachmentInstallationBinding
        ] = {}
    else:
        generated_candidates, evidence_bindings_by_candidate = (
            _generate_with_evidence_bound_installations(
                tool,
                tethers,
                anchor_paths,
                tool_attachment_assemblies=tool_attachment_assemblies,
                evidence_bound_tool_attachment_assemblies=evidence_assemblies,
                product_runtime_state=product_runtime_state,
                connection_contexts=connection_contexts,
                policy_contexts=policy_contexts,
            )
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
        generation_tool_bindings=_generation_tool_bindings(
            tool,
            generated_candidates,
            evidence_bindings_by_candidate=evidence_bindings_by_candidate,
        ),
        generated_candidates=generated_candidates,
        evaluations=evaluations,
        ranking_context=ranking_context,
        selection=selection,
    )


def _generate_with_evidence_bound_installations(
    tool: ResolvedToolCandidate,
    tethers: list[TetherOption],
    anchor_paths: list[AnchorPathOption],
    *,
    tool_attachment_assemblies: list[ToolAttachmentAssemblyOption] | None,
    evidence_bound_tool_attachment_assemblies: list[
        EvidenceBoundToolAttachmentAssemblyOption
    ],
    product_runtime_state: list[ProductConstraintRuntimeState] | None,
    connection_contexts: list[ConnectionEvaluationContext] | None,
    policy_contexts: list[CandidatePolicyContext] | None,
) -> tuple[list[GeneratedCandidate], dict[str, ToolAttachmentInstallationBinding]]:
    generic_assemblies = list(tool_attachment_assemblies or [])
    generic_refs = {assembly.assembly_ref for assembly in generic_assemblies}
    evidence_ref_list = [
        assembly.assembly_ref for assembly in evidence_bound_tool_attachment_assemblies
    ]
    evidence_refs = set(evidence_ref_list)
    if len(evidence_refs) != len(evidence_ref_list):
        duplicates = sorted(
            ref for ref in evidence_refs if evidence_ref_list.count(ref) > 1
        )
        raise ValueError(
            "evidence-bound ToolAttachment assembly refs must be unique: "
            f"{duplicates!r}"
        )
    overlap = sorted(generic_refs & evidence_refs)
    if overlap:
        raise ValueError(
            "ToolAttachment assembly refs must be unique across technical and evidence-bound routes: "
            f"{overlap!r}"
        )

    generic_policy_contexts = _generic_policy_contexts(
        generic_refs,
        policy_contexts,
    )
    generated = generate_candidate_configurations(
        tool,
        tethers,
        anchor_paths,
        tool_attachment_assemblies=generic_assemblies,
        product_runtime_state=product_runtime_state,
        connection_contexts=connection_contexts,
        policy_contexts=generic_policy_contexts,
    )
    candidate_ids = {candidate.configuration.candidate_id for candidate in generated}
    evidence_by_candidate: dict[str, ToolAttachmentInstallationBinding] = {}
    features_by_id = {feature.feature_id: feature for feature in tool.features}

    for assembly in sorted(
        evidence_bound_tool_attachment_assemblies,
        key=lambda item: item.assembly_ref,
    ):
        for binding in sorted(
            assembly.installation_bindings,
            key=lambda item: item.binding_id,
        ):
            if binding.tool_ref != tool.tool_ref:
                continue
            feature = features_by_id.get(binding.installation_feature_id)
            if feature is None:
                # Accepted evidence cannot become executable until the feature itself is
                # normalized on the selected Tool. Do not fabricate the missing feature.
                continue

            projected_assembly = ToolAttachmentAssemblyOption(
                assembly_ref=assembly.assembly_ref,
                components=[component.model_copy(deep=True) for component in assembly.components],
                eligibility=AttachmentEligibility(
                    paths=[
                        EligibilityPath(
                            binding_name="manufacturer_declared_installation",
                            requirements=[
                                FeaturePredicate(
                                    property_key="feature_kind",
                                    value=feature.feature_kind.value,
                                )
                            ],
                        )
                    ]
                ),
                provided_interfaces=[
                    interface.model_copy(deep=True)
                    for interface in assembly.provided_interfaces
                ],
                installation_method=(
                    assembly.installation_method.model_copy(deep=True)
                    if assembly.installation_method is not None
                    else None
                ),
            )
            projected_tool = tool.model_copy(
                deep=True,
                update={
                    "features": [feature.model_copy(deep=True)],
                    "direct_interfaces": [],
                },
            )
            binding_policy_contexts = _binding_policy_contexts(
                assembly.assembly_ref,
                binding.installation_feature_id,
                policy_contexts,
            )
            bound_candidates = generate_candidate_configurations(
                projected_tool,
                tethers,
                anchor_paths,
                tool_attachment_assemblies=[projected_assembly],
                product_runtime_state=product_runtime_state,
                connection_contexts=connection_contexts,
                policy_contexts=binding_policy_contexts,
            )

            for candidate in bound_candidates:
                candidate_id = candidate.configuration.candidate_id
                if candidate_id in candidate_ids:
                    continue
                generated.append(candidate)
                candidate_ids.add(candidate_id)
                evidence_by_candidate[candidate_id] = binding

    if policy_contexts is not None:
        _validate_policy_context_coverage(policy_contexts, generated)
    else:
        _validate_combined_legacy_anchor_policy(generated, anchor_paths)

    return generated, evidence_by_candidate


def _generic_policy_contexts(
    generic_assembly_refs: set[str],
    policy_contexts: list[CandidatePolicyContext] | None,
) -> list[CandidatePolicyContext] | None:
    if policy_contexts is None:
        return None
    return [
        context
        for context in policy_contexts
        if context.attachment_assembly_ref is None
        or context.attachment_assembly_ref in generic_assembly_refs
    ]


def _binding_policy_contexts(
    assembly_ref: str,
    feature_id: str,
    policy_contexts: list[CandidatePolicyContext] | None,
) -> list[CandidatePolicyContext] | None:
    if policy_contexts is None:
        return None
    return [
        context
        for context in policy_contexts
        if context.attachment_assembly_ref == assembly_ref
        and context.installation_feature_id == feature_id
    ]


def _policy_context_key(context: CandidatePolicyContext) -> tuple[str | None, ...]:
    return (
        context.tool_ref,
        context.tether_ref,
        context.anchor_path_ref,
        context.attachment_assembly_ref,
        context.installation_feature_id,
        context.primary_anchor_ref,
        context.anchor_installation_feature_id,
        context.anchor_installation_rule_id,
        context.tool_endpoint_id,
        context.tool_target_interface_id,
        context.anchor_endpoint_id,
        context.anchor_target_interface_id,
    )


def _selection_policy_key(candidate: GeneratedCandidate) -> tuple[str | None, ...]:
    selection = candidate.selection
    anchor_binding = selection.anchor_installation_binding
    return (
        selection.tool_ref,
        selection.tether_ref,
        selection.anchor_path_ref,
        selection.attachment_assembly_ref,
        selection.installation_feature_id,
        anchor_binding.primary_anchor_ref if anchor_binding is not None else None,
        anchor_binding.installation_feature_id if anchor_binding is not None else None,
        anchor_binding.rule_id if anchor_binding is not None else None,
        selection.tool_endpoint_id,
        selection.tool_target_interface_id,
        selection.anchor_endpoint_id,
        selection.anchor_target_interface_id,
    )


def _validate_policy_context_coverage(
    policy_contexts: list[CandidatePolicyContext],
    generated_candidates: list[GeneratedCandidate],
) -> None:
    expected = {_policy_context_key(context) for context in policy_contexts}
    actual = {_selection_policy_key(candidate) for candidate in generated_candidates}
    unused = expected - actual
    if unused:
        raise ValueError(
            "candidate policy contexts must match generated candidates; unused contexts: "
            f"{sorted(repr(key) for key in unused)!r}"
        )


def _validate_combined_legacy_anchor_policy(
    generated_candidates: list[GeneratedCandidate],
    anchor_paths: list[AnchorPathOption],
) -> None:
    applicable_anchor_refs = {
        anchor.anchor_path_ref
        for anchor in anchor_paths
        if anchor.policy_applicability == PolicyApplicability.APPLICABLE
    }
    for anchor_ref in applicable_anchor_refs:
        count = sum(
            candidate.selection.anchor_path_ref == anchor_ref
            for candidate in generated_candidates
        )
        if count > 1:
            raise ValueError(
                "anchor-scoped applicable policy cannot be broadcast across multiple generated "
                "candidates; supply CandidatePolicyContext values for the complete candidate selections"
            )
