from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .candidate_generation import (
    AnchorPathOption,
    CandidatePathSelection,
    CandidatePolicyContext,
    ConnectionEvaluationContext,
    ProductConstraintRuntimeState,
    ResolvedToolCandidate,
    TetherOption,
    ToolAttachmentAssemblyOption,
)
from .candidate_selection import (
    CandidateContextEvaluation,
    CandidateRankingContext,
    CandidateSelectionState,
)
from .recommendation import CandidateCheck, CandidateEvaluation
from .recommendation_run import RecommendationRunResult, run_recommendation


class FieldToolResolutionSource(StrEnum):
    CATALOGUE = "catalogue"
    SESSION_LOCAL_GENERIC = "session_local_generic"


class FieldToolResolutionState(StrEnum):
    RESOLVED = "resolved"
    NEEDS_INPUT = "needs_input"
    NOT_READY = "not_ready"


class FieldInputRequirementKind(StrEnum):
    TOOL_IDENTIFICATION = "tool_identification"
    TOOL_CONFIRMATION = "tool_confirmation"
    OPERATIONAL_PROFILE_SELECTION = "operational_profile_selection"


class FieldReadinessIssueCode(StrEnum):
    TOOL_NOT_CATALOGUED = "tool_not_catalogued"
    NO_OPERATIONAL_PROFILE = "no_operational_profile"
    OPERATIONAL_MASS_NOT_ESTABLISHED = "operational_mass_not_established"


class FieldRecommendationState(StrEnum):
    NEEDS_INPUT = "needs_input"
    NOT_READY = "not_ready"
    SELECTED = "selected"
    NO_GENERATED_CANDIDATES = "no_generated_candidates"
    NO_SUITABLE_RECOMMENDATION = "no_suitable_recommendation"


class OperationalToolProfile(BaseModel):
    """One exact operational configuration exposed to the demand-side workflow.

    The contained ``ResolvedToolCandidate`` is already normalized for recommendation
    generation. ``configuration_product_refs`` retains supporting configuration identity
    such as an installed Battery without making that Battery a tethering component.
    """

    profile_ref: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    tool: ResolvedToolCandidate
    configuration_product_refs: list[str] = Field(default_factory=list)

    @field_validator("configuration_product_refs")
    @classmethod
    def validate_configuration_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("configuration product refs must be non-empty")
        if len(set(values)) != len(values):
            raise ValueError("configuration product refs must be unique within one profile")
        return values


class FieldToolCatalogueEntry(BaseModel):
    """Demand-side view of one exact/sufficiently-specific catalogued Tool."""

    tool_ref: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    operational_profiles: list[OperationalToolProfile] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_profiles(self) -> FieldToolCatalogueEntry:
        profile_refs = [profile.profile_ref for profile in self.operational_profiles]
        if len(set(profile_refs)) != len(profile_refs):
            raise ValueError(
                f"operational profile refs must be unique for tool {self.tool_ref!r}"
            )
        mismatches = [
            profile.profile_ref
            for profile in self.operational_profiles
            if profile.tool.tool_ref != self.tool_ref
        ]
        if mismatches:
            raise ValueError(
                "operational profiles must retain their owning tool_ref; "
                f"tool {self.tool_ref!r}, mismatched profiles={mismatches!r}"
            )
        return self


class FieldRecommendationCatalogue(BaseModel):
    """Normalized catalogue slice available to one field recommendation workflow.

    This model does not perform ingestion, evidence acceptance, or catalogue querying.
    Callers supply the complete set of normalized tethering alternatives and anchor paths
    that are actually available to this recommendation run.
    """

    tools: list[FieldToolCatalogueEntry] = Field(default_factory=list)
    tethers: list[TetherOption] = Field(default_factory=list)
    anchor_paths: list[AnchorPathOption] = Field(default_factory=list)
    tool_attachment_assemblies: list[ToolAttachmentAssemblyOption] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_tool_identity(self) -> FieldRecommendationCatalogue:
        tool_refs = [tool.tool_ref for tool in self.tools]
        if len(set(tool_refs)) != len(tool_refs):
            raise ValueError("field recommendation catalogue tool refs must be unique")
        return self


class FieldToolObservation(BaseModel):
    """Structured output of recognition/search plus explicit worker confirmation.

    Candidate refs are advisory recognition/search output. They never become a resolved
    Tool until ``confirmed_tool_ref`` is supplied. A session-local generic profile is an
    explicit fallback when the worker/tool cannot be resolved to a catalogue record.
    """

    candidate_tool_refs: list[str] = Field(default_factory=list)
    confirmed_tool_ref: str | None = Field(default=None, min_length=1)
    selected_operational_profile_ref: str | None = Field(default=None, min_length=1)
    generic_profile: OperationalToolProfile | None = None

    @field_validator("candidate_tool_refs")
    @classmethod
    def validate_candidate_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("candidate tool refs must be non-empty")
        if len(set(values)) != len(values):
            raise ValueError("candidate tool refs must be unique")
        return values

    @model_validator(mode="after")
    def validate_resolution_modes(self) -> FieldToolObservation:
        if self.generic_profile is not None and self.confirmed_tool_ref is not None:
            raise ValueError(
                "catalogue confirmation and session-local generic fallback are mutually exclusive"
            )
        if (
            self.generic_profile is not None
            and self.selected_operational_profile_ref is not None
        ):
            raise ValueError(
                "a session-local generic profile cannot also select a catalogue operational profile"
            )
        return self


class FieldInputOption(BaseModel):
    ref: str = Field(min_length=1)
    label: str = Field(min_length=1)


class FieldInputRequirement(BaseModel):
    kind: FieldInputRequirementKind
    options: list[FieldInputOption] = Field(default_factory=list)


class FieldReadinessIssue(BaseModel):
    code: FieldReadinessIssueCode
    subject_ref: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class ResolvedFieldTool(BaseModel):
    source: FieldToolResolutionSource
    tool_display_name: str = Field(min_length=1)
    operational_profile: OperationalToolProfile


class FieldToolResolution(BaseModel):
    state: FieldToolResolutionState
    resolved: ResolvedFieldTool | None = None
    requirements: list[FieldInputRequirement] = Field(default_factory=list)
    issues: list[FieldReadinessIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_state(self) -> FieldToolResolution:
        if self.state == FieldToolResolutionState.RESOLVED:
            if self.resolved is None or self.requirements or self.issues:
                raise ValueError(
                    "resolved field tool state requires only one resolved tool/profile"
                )
            return self

        if self.resolved is not None:
            raise ValueError("non-resolved field tool states must not carry a resolved tool")

        if self.state == FieldToolResolutionState.NEEDS_INPUT:
            if not self.requirements or self.issues:
                raise ValueError(
                    "needs-input field tool state requires input requirements and no readiness issues"
                )
            return self

        if not self.issues or self.requirements:
            raise ValueError(
                "not-ready field tool state requires readiness issues and no input requirements"
            )
        return self


class FieldRecommendationSummary(BaseModel):
    """Field-facing structured projection of the exact selected candidate.

    Safety-relevant installation/connection facts remain on the exact retained path
    selection and evaluation. Pending checks are copied as complete ``CandidateCheck``
    objects; no outcome or instruction is reconstructed by parsing reason text.
    """

    operational_profile_ref: str = Field(min_length=1)
    operational_profile_label: str = Field(min_length=1)
    operational_mass_kg: float
    configuration_product_refs: list[str] = Field(default_factory=list)
    path_selection: CandidatePathSelection
    evaluation: CandidateEvaluation
    context_evaluation: CandidateContextEvaluation | None = None
    pending_verification_checks: list[CandidateCheck] = Field(default_factory=list)
    pending_action_checks: list[CandidateCheck] = Field(default_factory=list)

    @field_validator("operational_mass_kg", mode="before")
    @classmethod
    def validate_operational_mass(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("operational_mass_kg must be a finite positive number")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric <= 0:
            raise ValueError("operational_mass_kg must be a finite positive number")
        return numeric


class FieldRecommendationResult(BaseModel):
    state: FieldRecommendationState
    tool_resolution: FieldToolResolution
    recommendation_run: RecommendationRunResult | None = None
    recommendation: FieldRecommendationSummary | None = None

    @model_validator(mode="after")
    def validate_state(self) -> FieldRecommendationResult:
        if self.state == FieldRecommendationState.NEEDS_INPUT:
            if (
                self.tool_resolution.state != FieldToolResolutionState.NEEDS_INPUT
                or self.recommendation_run is not None
                or self.recommendation is not None
            ):
                raise ValueError(
                    "needs-input field result must retain only a needs-input tool resolution"
                )
            return self

        if self.state == FieldRecommendationState.NOT_READY:
            if (
                self.tool_resolution.state != FieldToolResolutionState.NOT_READY
                or self.recommendation_run is not None
                or self.recommendation is not None
            ):
                raise ValueError(
                    "not-ready field result must retain only a not-ready tool resolution"
                )
            return self

        if self.tool_resolution.state != FieldToolResolutionState.RESOLVED:
            raise ValueError("recommendation-run field states require a resolved tool")

        run = self.recommendation_run
        if run is None:
            raise ValueError("recommendation-run field states require a retained recommendation run")
        resolved = self.tool_resolution.resolved
        if resolved is None:  # pragma: no cover - protected by state validation above.
            raise ValueError("recommendation-run field states require a resolved tool")
        if run.tool != resolved.operational_profile.tool:
            raise ValueError(
                "retained recommendation run Tool must match the resolved operational profile Tool"
            )

        expected_state = {
            CandidateSelectionState.SELECTED: FieldRecommendationState.SELECTED,
            CandidateSelectionState.NO_GENERATED_CANDIDATES: (
                FieldRecommendationState.NO_GENERATED_CANDIDATES
            ),
            CandidateSelectionState.NO_SUITABLE_RECOMMENDATION: (
                FieldRecommendationState.NO_SUITABLE_RECOMMENDATION
            ),
        }[run.selection.state]
        if self.state != expected_state:
            raise ValueError(
                "field recommendation state must match the retained recommendation run selection"
            )

        if self.state != FieldRecommendationState.SELECTED:
            if self.recommendation is not None:
                raise ValueError("non-selected recommendation-run states must not carry a summary")
            return self

        selected = run.selection.selected
        summary = self.recommendation
        if selected is None or summary is None:
            raise ValueError("selected field recommendation requires a selected summary")
        expected_summary = _build_field_recommendation_summary(
            resolved.operational_profile,
            run,
        )
        if summary != expected_summary:
            raise ValueError(
                "field recommendation summary must match the deterministic projection "
                "of the retained selected candidate and operational profile"
            )
        return self


def resolve_field_tool(
    observation: FieldToolObservation,
    catalogue_tools: list[FieldToolCatalogueEntry],
) -> FieldToolResolution:
    """Resolve recognition/confirmation input to one exact operational tool profile.

    This function does not recognize images, infer identity, invent Battery selection,
    or accept raw physical facts. It only coordinates explicit confirmation against
    normalized catalogue entries or an explicitly supplied session-local generic profile.
    """

    tools_by_ref = {tool.tool_ref: tool for tool in catalogue_tools}
    if len(tools_by_ref) != len(catalogue_tools):
        raise ValueError("catalogue tool refs must be unique")

    if observation.generic_profile is not None:
        return _resolved_profile_or_not_ready(
            observation.generic_profile,
            source=FieldToolResolutionSource.SESSION_LOCAL_GENERIC,
            tool_display_name=observation.generic_profile.display_name,
        )

    if observation.confirmed_tool_ref is None:
        unknown_candidates = [
            tool_ref
            for tool_ref in observation.candidate_tool_refs
            if tool_ref not in tools_by_ref
        ]
        if unknown_candidates:
            return FieldToolResolution(
                state=FieldToolResolutionState.NOT_READY,
                issues=[
                    FieldReadinessIssue(
                        code=FieldReadinessIssueCode.TOOL_NOT_CATALOGUED,
                        subject_ref=tool_ref,
                        detail=(
                            "recognition/search returned a Tool that is not present in the "
                            "normalized field catalogue"
                        ),
                    )
                    for tool_ref in unknown_candidates
                ],
            )

        if observation.candidate_tool_refs:
            return FieldToolResolution(
                state=FieldToolResolutionState.NEEDS_INPUT,
                requirements=[
                    FieldInputRequirement(
                        kind=FieldInputRequirementKind.TOOL_CONFIRMATION,
                        options=[
                            FieldInputOption(
                                ref=tool_ref,
                                label=tools_by_ref[tool_ref].display_name,
                            )
                            for tool_ref in observation.candidate_tool_refs
                        ],
                    )
                ],
            )

        return FieldToolResolution(
            state=FieldToolResolutionState.NEEDS_INPUT,
            requirements=[
                FieldInputRequirement(
                    kind=FieldInputRequirementKind.TOOL_IDENTIFICATION,
                )
            ],
        )

    entry = tools_by_ref.get(observation.confirmed_tool_ref)
    if entry is None:
        return FieldToolResolution(
            state=FieldToolResolutionState.NOT_READY,
            issues=[
                FieldReadinessIssue(
                    code=FieldReadinessIssueCode.TOOL_NOT_CATALOGUED,
                    subject_ref=observation.confirmed_tool_ref,
                    detail="the confirmed Tool is not present in the normalized field catalogue",
                )
            ],
        )

    profiles = entry.operational_profiles
    if not profiles:
        return FieldToolResolution(
            state=FieldToolResolutionState.NOT_READY,
            issues=[
                FieldReadinessIssue(
                    code=FieldReadinessIssueCode.NO_OPERATIONAL_PROFILE,
                    subject_ref=entry.tool_ref,
                    detail=(
                        "the confirmed Tool has no resolved operational profile available "
                        "for load reasoning"
                    ),
                )
            ],
        )

    selected_ref = observation.selected_operational_profile_ref
    if selected_ref is None and len(profiles) > 1:
        return _profile_selection_required(profiles)
    if selected_ref is None:
        profile = profiles[0]
    else:
        profile = next(
            (profile for profile in profiles if profile.profile_ref == selected_ref),
            None,
        )
        if profile is None:
            return _profile_selection_required(profiles)

    return _resolved_profile_or_not_ready(
        profile,
        source=FieldToolResolutionSource.CATALOGUE,
        tool_display_name=entry.display_name,
    )


def run_field_recommendation(
    observation: FieldToolObservation,
    catalogue: FieldRecommendationCatalogue,
    *,
    product_runtime_state: list[ProductConstraintRuntimeState] | None = None,
    connection_contexts: list[ConnectionEvaluationContext] | None = None,
    policy_contexts: list[CandidatePolicyContext] | None = None,
    ranking_context: CandidateRankingContext | None = None,
) -> FieldRecommendationResult:
    """Drive one field workflow into the existing complete recommendation pipeline.

    Tool/profile resolution is the only new decision layer here. Once it succeeds, the
    function passes the normalized Tool and the catalogue's complete supplied alternatives
    to ``run_recommendation`` unchanged. Generation, hard evaluation, contextual
    feasibility/ranking and global exhaustion therefore remain owned by their existing
    layers.
    """

    tool_resolution = resolve_field_tool(observation, catalogue.tools)
    if tool_resolution.state == FieldToolResolutionState.NEEDS_INPUT:
        return FieldRecommendationResult(
            state=FieldRecommendationState.NEEDS_INPUT,
            tool_resolution=tool_resolution,
        )
    if tool_resolution.state == FieldToolResolutionState.NOT_READY:
        return FieldRecommendationResult(
            state=FieldRecommendationState.NOT_READY,
            tool_resolution=tool_resolution,
        )

    resolved = tool_resolution.resolved
    if resolved is None:  # pragma: no cover - protected by FieldToolResolution validation.
        raise ValueError("resolved field tool state is missing its resolved profile")

    recommendation_run = run_recommendation(
        resolved.operational_profile.tool,
        catalogue.tethers,
        catalogue.anchor_paths,
        tool_attachment_assemblies=catalogue.tool_attachment_assemblies,
        product_runtime_state=product_runtime_state,
        connection_contexts=connection_contexts,
        policy_contexts=policy_contexts,
        ranking_context=ranking_context,
    )

    if recommendation_run.selection.state == CandidateSelectionState.SELECTED:
        return FieldRecommendationResult(
            state=FieldRecommendationState.SELECTED,
            tool_resolution=tool_resolution,
            recommendation_run=recommendation_run,
            recommendation=_build_field_recommendation_summary(
                resolved.operational_profile,
                recommendation_run,
            ),
        )

    state = (
        FieldRecommendationState.NO_GENERATED_CANDIDATES
        if recommendation_run.selection.state
        == CandidateSelectionState.NO_GENERATED_CANDIDATES
        else FieldRecommendationState.NO_SUITABLE_RECOMMENDATION
    )
    return FieldRecommendationResult(
        state=state,
        tool_resolution=tool_resolution,
        recommendation_run=recommendation_run,
    )


def _profile_selection_required(
    profiles: list[OperationalToolProfile],
) -> FieldToolResolution:
    return FieldToolResolution(
        state=FieldToolResolutionState.NEEDS_INPUT,
        requirements=[
            FieldInputRequirement(
                kind=FieldInputRequirementKind.OPERATIONAL_PROFILE_SELECTION,
                options=[
                    FieldInputOption(ref=profile.profile_ref, label=profile.display_name)
                    for profile in profiles
                ],
            )
        ],
    )


def _resolved_profile_or_not_ready(
    profile: OperationalToolProfile,
    *,
    source: FieldToolResolutionSource,
    tool_display_name: str,
) -> FieldToolResolution:
    if profile.tool.object_mass_kg is None:
        return FieldToolResolution(
            state=FieldToolResolutionState.NOT_READY,
            issues=[
                FieldReadinessIssue(
                    code=FieldReadinessIssueCode.OPERATIONAL_MASS_NOT_ESTABLISHED,
                    subject_ref=profile.profile_ref,
                    detail=(
                        "the selected operational profile does not establish object mass "
                        "for load reasoning"
                    ),
                )
            ],
        )

    return FieldToolResolution(
        state=FieldToolResolutionState.RESOLVED,
        resolved=ResolvedFieldTool(
            source=source,
            tool_display_name=tool_display_name,
            operational_profile=profile,
        ),
    )


def _build_field_recommendation_summary(
    profile: OperationalToolProfile,
    recommendation_run: RecommendationRunResult,
) -> FieldRecommendationSummary:
    selected = recommendation_run.selection.selected
    if selected is None:
        raise ValueError("cannot build a field summary without a selected candidate")

    evaluation = selected.evaluation
    verification_ids = set(evaluation.pending_verification_connection_ids)
    action_check_ids = {
        f"product_constraint:{constraint_id}"
        for constraint_id in evaluation.pending_action_constraint_ids
    }
    pending_verification_checks = [
        check for check in evaluation.checks if check.check_id in verification_ids
    ]
    pending_action_checks = [
        check for check in evaluation.checks if check.check_id in action_check_ids
    ]

    if len(pending_verification_checks) != len(verification_ids):
        raise ValueError(
            "selected candidate pending verification ids must map to retained hard checks"
        )
    if len(pending_action_checks) != len(action_check_ids):
        raise ValueError(
            "selected candidate pending action ids must map to retained hard checks"
        )

    context_evaluation = next(
        (
            context
            for context in recommendation_run.selection.context_evaluations
            if context.candidate_id == selected.candidate_id
        ),
        None,
    )

    mass = profile.tool.object_mass_kg
    if mass is None:  # pragma: no cover - protected by resolution.
        raise ValueError("selected operational profile is missing operational mass")

    return FieldRecommendationSummary(
        operational_profile_ref=profile.profile_ref,
        operational_profile_label=profile.display_name,
        operational_mass_kg=mass,
        configuration_product_refs=profile.configuration_product_refs,
        path_selection=selected.generated_candidate.selection,
        evaluation=evaluation,
        context_evaluation=context_evaluation,
        pending_verification_checks=pending_verification_checks,
        pending_action_checks=pending_action_checks,
    )
