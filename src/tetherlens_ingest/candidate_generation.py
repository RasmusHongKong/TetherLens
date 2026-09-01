from __future__ import annotations

import json
import math
from collections import defaultdict
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .compatibility import (
    AttachmentEligibility,
    EligibilityEvaluation,
    EligibilityMatch,
    EligibilityStatus,
    PolicyStatus,
    ToolInterfaceFeature,
    evaluate_attachment_eligibility,
)
from .connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionManufacturerAssessment,
    ConnectionRuleResult,
    ConnectorSpec,
    GatedConnectorClosedInterfaceVerification,
    TetherSide,
    evaluate_endpoint_engagement,
)
from .constraints import (
    ProductConstraintContext,
    ProductConstraintEvaluation,
    ResolvedProductConstraint,
    evaluate_product_constraints,
)
from .recommendation import (
    CandidateAttachmentMode,
    CandidateConfiguration,
    LoadBearingComponent,
    PolicyApplicability,
)


class CandidateComponentRole(StrEnum):
    TOOL_ATTACHMENT = "tool_attachment"
    TETHER = "tether"
    ANCHOR = "anchor"


class CandidateComponentOption(BaseModel):
    """One physical component instance available to a generated candidate path.

    ``component_ref`` identifies the runtime component instance used by capacity checks.
    ``source_product_ref`` identifies the catalogue product whose normalized constraints
    belong to that component. They are intentionally separate so a future assembly may
    contain multiple instances of one catalogue product without losing instance identity.
    """

    component_ref: str = Field(min_length=1)
    source_product_ref: str = Field(min_length=1)
    rated_capacity_kg: float | None = None
    load_bearing: bool = True
    product_constraints: list[ResolvedProductConstraint] = Field(default_factory=list)

    @field_validator("rated_capacity_kg", mode="before")
    @classmethod
    def validate_capacity(cls, value: Any) -> Any:
        return _positive_finite_or_none(value, field_name="rated_capacity_kg")

    @model_validator(mode="after")
    def validate_constraint_ownership(self) -> CandidateComponentOption:
        mismatches = sorted(
            {
                constraint.source_product_ref
                for constraint in self.product_constraints
                if constraint.source_product_ref != self.source_product_ref
            }
        )
        if mismatches:
            raise ValueError(
                "component product constraints must retain the component source product "
                f"identity; expected {self.source_product_ref!r}, got {mismatches!r}"
            )
        _require_unique_local_ids(
            [constraint.constraint_id for constraint in self.product_constraints],
            scope=f"component {self.component_ref!r}",
            label="product constraint ids",
        )
        return self


class ResolvedToolCandidate(BaseModel):
    """Resolved tool facts needed by candidate construction, not raw catalogue claims."""

    tool_ref: str = Field(min_length=1)
    object_mass_kg: float | None = None
    features: list[ToolInterfaceFeature] = Field(default_factory=list)
    direct_interfaces: list[ConnectionInterface] = Field(default_factory=list)

    @field_validator("object_mass_kg", mode="before")
    @classmethod
    def validate_mass(cls, value: Any) -> Any:
        return _positive_finite_or_none(value, field_name="object_mass_kg")

    @model_validator(mode="after")
    def validate_tool_identity_and_direct_interfaces(self) -> ResolvedToolCandidate:
        _require_unique_local_ids(
            [feature.feature_id for feature in self.features],
            scope=f"resolved tool {self.tool_ref!r}",
            label="feature ids",
        )
        invalid = [
            interface.interface_id
            for interface in self.direct_interfaces
            if interface.role != ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE
        ]
        if invalid:
            raise ValueError(
                "resolved tool direct interfaces must use role "
                f"tool_direct_tether_interface: {invalid!r}"
            )
        _require_unique_local_ids(
            [interface.interface_id for interface in self.direct_interfaces],
            scope=f"resolved tool {self.tool_ref!r}",
            label="direct interface ids",
        )
        return self


class ToolAttachmentAssemblyOption(BaseModel):
    """One installable ToolAttachment assembly.

    An assembly may contain one or many component instances. Candidate construction is
    therefore based on an assembly relationship plus component facts, not on an
    assumption that one ToolAttachment SKU always equals one complete physical path.
    """

    assembly_ref: str = Field(min_length=1)
    components: list[CandidateComponentOption] = Field(min_length=1)
    eligibility: AttachmentEligibility
    provided_interfaces: list[ConnectionInterface] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_provided_interfaces(self) -> ToolAttachmentAssemblyOption:
        invalid = [
            interface.interface_id
            for interface in self.provided_interfaces
            if interface.role != ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
        ]
        if invalid:
            raise ValueError(
                "ToolAttachment-provided interfaces must use role "
                f"tool_attachment_tether_side: {invalid!r}"
            )
        _require_unique_local_ids(
            [interface.interface_id for interface in self.provided_interfaces],
            scope=f"assembly {self.assembly_ref!r}",
            label="provided interface ids",
        )
        _require_unique_component_refs(self.components, scope=f"assembly {self.assembly_ref!r}")
        if not any(component.load_bearing for component in self.components):
            raise ValueError(
                "ToolAttachment assemblies must contain at least one load-bearing component"
            )
        return self


class TetherOption(BaseModel):
    tether_ref: str = Field(min_length=1)
    component: CandidateComponentOption
    endpoints: list[ConnectionInterface] = Field(min_length=2)
    connector_specs: dict[str, ConnectorSpec] = Field(default_factory=dict)
    max_length_mm: float | None = None

    @field_validator("max_length_mm", mode="before")
    @classmethod
    def validate_max_length(cls, value: Any) -> Any:
        return _positive_finite_or_none(value, field_name="max_length_mm")

    @model_validator(mode="after")
    def validate_tether(self) -> TetherOption:
        if not self.component.load_bearing:
            raise ValueError("the tether component must participate in the load-bearing path")
        invalid = [
            endpoint.interface_id
            for endpoint in self.endpoints
            if endpoint.role != ConnectionInterfaceRole.TETHER_CONNECTION
        ]
        if invalid:
            raise ValueError(f"tether endpoints must use role tether_connection: {invalid!r}")
        if len({endpoint.interface_id for endpoint in self.endpoints}) != len(self.endpoints):
            raise ValueError("tether endpoint ids must be unique within one tether option")
        mismatched_connector_specs = sorted(
            key
            for key, connector_spec in self.connector_specs.items()
            if key != connector_spec.connector_spec_id
        )
        if mismatched_connector_specs:
            raise ValueError(
                "connector spec map keys must match the contained connector_spec_id: "
                f"{mismatched_connector_specs!r}"
            )
        return self


class AnchorPathOption(BaseModel):
    """One anchor/container-side path exposed to tether endpoint generation.

    Legacy anchor-scoped policy remains supported only when it maps to exactly one
    generated candidate. Configuration-specific policy must use CandidatePolicyContext
    so one tether/attachment selection cannot inherit another selection's result.
    """

    anchor_path_ref: str = Field(min_length=1)
    components: list[CandidateComponentOption] = Field(default_factory=list)
    target_interfaces: list[ConnectionInterface] = Field(min_length=1)
    policy_applicability: PolicyApplicability = PolicyApplicability.NOT_APPLICABLE
    policy_status: PolicyStatus | None = None

    @model_validator(mode="after")
    def validate_targets_and_policy(self) -> AnchorPathOption:
        allowed_roles = {
            ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
            ConnectionInterfaceRole.CONTAINER_CONNECTION,
        }
        invalid = [
            interface.interface_id
            for interface in self.target_interfaces
            if interface.role not in allowed_roles
        ]
        if invalid:
            raise ValueError(
                "anchor path targets must be anchor-attachment or container tether interfaces: "
                f"{invalid!r}"
            )
        _require_unique_local_ids(
            [interface.interface_id for interface in self.target_interfaces],
            scope=f"anchor path {self.anchor_path_ref!r}",
            label="target interface ids",
        )
        _require_unique_component_refs(self.components, scope=f"anchor path {self.anchor_path_ref!r}")
        if (
            self.policy_applicability == PolicyApplicability.NOT_APPLICABLE
            and self.policy_status is not None
        ):
            raise ValueError(
                "policy-not-applicable anchor paths must not supply a policy evaluation"
            )
        return self


class ProductConstraintRuntimeState(BaseModel):
    """Session facts scoped to one physical component installation.

    ToolAttachment installation facts such as elapsed bond time and a pre-use attachment
    test belong to the selected tool feature as well as the component instance. A
    ``None`` feature binding is reserved for components evaluated without a selected
    tool installation feature, such as tether or anchor-side components.
    """

    component_ref: str = Field(min_length=1)
    installation_feature_id: str | None = Field(default=None, min_length=1)
    bond_elapsed_h: float | None = None
    pre_use_attachment_test_passed: bool | None = None

    @field_validator("bond_elapsed_h", mode="before")
    @classmethod
    def validate_bond_elapsed(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("bond_elapsed_h must be a finite non-negative number when provided")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric < 0:
            raise ValueError("bond_elapsed_h must be a finite non-negative number when provided")
        return numeric


class ConnectionEvaluationContext(BaseModel):
    """Optional connection reasoning scoped to both owning candidate options.

    Interface identifiers are local to their source products and may repeat across
    options. ``tether_ref`` and ``target_owner_ref`` therefore participate in the key
    so evidence for one product pair cannot leak into another pair that happens to use
    the same local endpoint/interface ids.
    """

    tether_ref: str = Field(min_length=1)
    target_owner_ref: str = Field(min_length=1)
    endpoint_id: str = Field(min_length=1)
    target_interface_id: str = Field(min_length=1)
    manufacturer_assessments: list[ConnectionManufacturerAssessment] = Field(default_factory=list)
    derived_results: list[ConnectionRuleResult] = Field(default_factory=list)
    verification_observations: GatedConnectorClosedInterfaceVerification | None = None


class CandidatePolicyContext(BaseModel):
    """Policy result bound to one complete physical candidate selection."""

    tool_ref: str = Field(min_length=1)
    tether_ref: str = Field(min_length=1)
    anchor_path_ref: str = Field(min_length=1)
    attachment_assembly_ref: str | None = Field(default=None, min_length=1)
    installation_feature_id: str | None = Field(default=None, min_length=1)
    tool_endpoint_id: str = Field(min_length=1)
    tool_target_interface_id: str = Field(min_length=1)
    anchor_endpoint_id: str = Field(min_length=1)
    anchor_target_interface_id: str = Field(min_length=1)
    policy_applicability: PolicyApplicability
    policy_status: PolicyStatus | None = None

    @model_validator(mode="after")
    def validate_policy(self) -> CandidatePolicyContext:
        if (
            self.policy_applicability == PolicyApplicability.NOT_APPLICABLE
            and self.policy_status is not None
        ):
            raise ValueError(
                "policy-not-applicable candidate contexts must not supply a policy evaluation"
            )
        return self


class CandidateSelectedComponent(BaseModel):
    component_ref: str = Field(min_length=1)
    source_product_ref: str = Field(min_length=1)
    role: CandidateComponentRole


class EligibilityProof(BaseModel):
    """One eligibility path that proves the selected physical feature is installable."""

    path_index: int = Field(ge=0)
    binding_name: str


class CandidatePathSelection(BaseModel):
    """Explicit identity and binding metadata for one generated candidate path."""

    tool_ref: str = Field(min_length=1)
    tether_ref: str = Field(min_length=1)
    anchor_path_ref: str = Field(min_length=1)
    attachment_assembly_ref: str | None = None
    installation_feature_id: str | None = None
    eligibility_proofs: list[EligibilityProof] = Field(default_factory=list)
    tool_endpoint_id: str = Field(min_length=1)
    tool_target_interface_id: str = Field(min_length=1)
    anchor_endpoint_id: str = Field(min_length=1)
    anchor_target_interface_id: str = Field(min_length=1)
    components: list[CandidateSelectedComponent] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_attachment_binding(self) -> CandidatePathSelection:
        if self.attachment_assembly_ref is None:
            if self.installation_feature_id is not None or self.eligibility_proofs:
                raise ValueError(
                    "direct candidate selections must not supply ToolAttachment feature binding"
                )
            return self

        if self.installation_feature_id is None or not self.eligibility_proofs:
            raise ValueError(
                "ToolAttachment candidate selection requires an installation feature and "
                "at least one eligibility proof"
            )
        return self


class GeneratedCandidate(BaseModel):
    """A generated path plus the existing evaluator-ready configuration."""

    selection: CandidatePathSelection
    configuration: CandidateConfiguration

    @model_validator(mode="after")
    def validate_selection_matches_configuration(self) -> GeneratedCandidate:
        selection = self.selection
        configuration = self.configuration
        has_attachment = selection.attachment_assembly_ref is not None
        expected_mode = (
            CandidateAttachmentMode.TOOL_ATTACHMENT
            if has_attachment
            else CandidateAttachmentMode.DIRECT
        )
        if configuration.attachment_mode != expected_mode:
            raise ValueError("generated selection attachment mode does not match configuration")
        if configuration.tool_side_connection.endpoint_id != selection.tool_endpoint_id:
            raise ValueError("generated selection tool endpoint does not match configuration")
        if (
            configuration.tool_side_connection.target_interface_id
            != selection.tool_target_interface_id
        ):
            raise ValueError("generated selection tool target does not match configuration")
        if configuration.anchor_side_connection.endpoint_id != selection.anchor_endpoint_id:
            raise ValueError("generated selection anchor endpoint does not match configuration")
        if (
            configuration.anchor_side_connection.target_interface_id
            != selection.anchor_target_interface_id
        ):
            raise ValueError("generated selection anchor target does not match configuration")
        if has_attachment:
            eligibility = configuration.attachment_eligibility
            if eligibility is None or eligibility.status != EligibilityStatus.ELIGIBLE:
                raise ValueError("generated ToolAttachment candidate must retain eligible binding")
            expected_feature = selection.installation_feature_id
            if not eligibility.matches or {
                match.feature_id for match in eligibility.matches
            } != {expected_feature}:
                raise ValueError(
                    "generated ToolAttachment candidate eligibility must bind only the selected feature"
                )
            expected_proofs = {
                (proof.path_index, proof.binding_name) for proof in selection.eligibility_proofs
            }
            actual_proofs = {
                (match.path_index, match.binding_name) for match in eligibility.matches
            }
            if actual_proofs != expected_proofs:
                raise ValueError(
                    "generated ToolAttachment candidate eligibility proofs do not match selection"
                )
        return self


def generate_candidate_configurations(
    tool: ResolvedToolCandidate,
    tethers: list[TetherOption],
    anchor_paths: list[AnchorPathOption],
    *,
    tool_attachment_assemblies: list[ToolAttachmentAssemblyOption] | None = None,
    product_runtime_state: list[ProductConstraintRuntimeState] | None = None,
    connection_contexts: list[ConnectionEvaluationContext] | None = None,
    policy_contexts: list[CandidatePolicyContext] | None = None,
) -> list[GeneratedCandidate]:
    """Generate explicit direct and ToolAttachment candidate paths.

    The generator consumes normalized runtime primitives only. It does not accept raw
    claims, rank candidates, infer policy, or conclude that an empty result means
    ``no suitable recommendation``.

    Structurally admissible endpoint assignments are generated even when connection
    evaluation is later ``incompatible`` or ``unresolved``; the existing candidate
    evaluator remains responsible for hard-constraint viability. ToolAttachment paths
    are generated only for explicit eligible feature matches because a generated path
    must bind installation constraints to one concrete tool feature.

    Multiple eligibility paths proving the same concrete feature are retained as audit
    proofs on one physical candidate rather than multiplying candidate identities.

    When ``policy_contexts`` is supplied, every generated candidate must have exactly one
    complete-selection policy context, including explicit ``not_applicable`` results.
    Legacy anchor-scoped applicable policy is accepted only when the anchor produces one
    candidate, preventing a policy result from being broadcast across product choices.
    """

    attachment_assemblies = list(tool_attachment_assemblies or [])
    runtime_state = _product_runtime_state_map(product_runtime_state or [])
    connection_context_map = _connection_context_map(connection_contexts or [])
    policy_context_map = (
        _candidate_policy_context_map(policy_contexts)
        if policy_contexts is not None
        else None
    )
    used_policy_context_keys: set[tuple[str | None, ...]] = set()
    legacy_policy_anchor_refs: set[str] = set()
    feature_by_id = {feature.feature_id: feature for feature in tool.features}

    _require_unique_option_refs(
        [tether.tether_ref for tether in tethers],
        label="tether_ref",
    )
    _require_unique_option_refs(
        [assembly.assembly_ref for assembly in attachment_assemblies],
        label="assembly_ref",
    )
    _require_unique_option_refs(
        [anchor_path.anchor_path_ref for anchor_path in anchor_paths],
        label="anchor_path_ref",
    )
    _require_unique_option_refs(
        [
            tool.tool_ref,
            *[assembly.assembly_ref for assembly in attachment_assemblies],
            *[anchor_path.anchor_path_ref for anchor_path in anchor_paths],
        ],
        label="connection target owner ref",
    )

    tool_targets: list[_ToolTarget] = [
        _ToolTarget(
            attachment_mode=CandidateAttachmentMode.DIRECT,
            owner_ref=tool.tool_ref,
            target_interface=interface,
        )
        for interface in tool.direct_interfaces
    ]

    for assembly in attachment_assemblies:
        eligibility = evaluate_attachment_eligibility(assembly.eligibility, tool.features)
        if eligibility.status != EligibilityStatus.ELIGIBLE:
            continue
        matches_by_feature = _eligibility_matches_by_feature(eligibility.matches)
        for feature_id, matches in matches_by_feature.items():
            feature = feature_by_id.get(feature_id)
            if feature is None:
                continue
            bound_eligibility = EligibilityEvaluation(
                status=EligibilityStatus.ELIGIBLE,
                matches=matches,
            )
            for interface in assembly.provided_interfaces:
                tool_targets.append(
                    _ToolTarget(
                        attachment_mode=CandidateAttachmentMode.TOOL_ATTACHMENT,
                        owner_ref=assembly.assembly_ref,
                        target_interface=interface,
                        assembly=assembly,
                        installation_feature=feature,
                        eligibility=bound_eligibility,
                        eligibility_matches=matches,
                    )
                )

    generated: list[GeneratedCandidate] = []
    for tether in tethers:
        endpoint_assignments = _endpoint_assignments(tether.endpoints)
        for tool_target in tool_targets:
            attachment_components = (
                list(tool_target.assembly.components)
                if tool_target.assembly is not None
                else []
            )
            attachment_constraint_evaluations = _evaluate_component_constraints(
                attachment_components,
                tether_max_length_mm=tether.max_length_mm,
                installation_feature=tool_target.installation_feature,
                runtime_state=runtime_state,
            )
            tether_constraint_evaluations = _evaluate_component_constraints(
                [tether.component],
                tether_max_length_mm=tether.max_length_mm,
                installation_feature=None,
                runtime_state=runtime_state,
            )

            for tool_endpoint, anchor_endpoint in endpoint_assignments:
                tool_connection = _evaluate_connection(
                    tool_endpoint,
                    tool_target.target_interface,
                    tether_ref=tether.tether_ref,
                    target_owner_ref=tool_target.owner_ref,
                    connector_specs=tether.connector_specs,
                    context_map=connection_context_map,
                )

                for anchor_path in anchor_paths:
                    _require_unique_component_refs(
                        [*attachment_components, tether.component, *anchor_path.components],
                        scope="generated candidate path",
                    )
                    anchor_constraint_evaluations = _evaluate_component_constraints(
                        anchor_path.components,
                        tether_max_length_mm=tether.max_length_mm,
                        installation_feature=None,
                        runtime_state=runtime_state,
                    )
                    constraint_evaluations = [
                        *attachment_constraint_evaluations,
                        *tether_constraint_evaluations,
                        *anchor_constraint_evaluations,
                    ]

                    for anchor_target in anchor_path.target_interfaces:
                        anchor_connection = _evaluate_connection(
                            anchor_endpoint,
                            anchor_target,
                            tether_ref=tether.tether_ref,
                            target_owner_ref=anchor_path.anchor_path_ref,
                            connector_specs=tether.connector_specs,
                            context_map=connection_context_map,
                        )
                        selected_components = _selected_components(
                            attachment_components,
                            tether.component,
                            anchor_path.components,
                        )
                        selection = CandidatePathSelection(
                            tool_ref=tool.tool_ref,
                            tether_ref=tether.tether_ref,
                            anchor_path_ref=anchor_path.anchor_path_ref,
                            attachment_assembly_ref=(
                                tool_target.assembly.assembly_ref
                                if tool_target.assembly is not None
                                else None
                            ),
                            installation_feature_id=(
                                tool_target.installation_feature.feature_id
                                if tool_target.installation_feature is not None
                                else None
                            ),
                            eligibility_proofs=[
                                EligibilityProof(
                                    path_index=match.path_index,
                                    binding_name=match.binding_name,
                                )
                                for match in tool_target.eligibility_matches
                            ],
                            tool_endpoint_id=tool_endpoint.interface_id,
                            tool_target_interface_id=tool_target.target_interface.interface_id,
                            anchor_endpoint_id=anchor_endpoint.interface_id,
                            anchor_target_interface_id=anchor_target.interface_id,
                            components=selected_components,
                        )
                        if policy_context_map is None:
                            if anchor_path.policy_applicability == PolicyApplicability.APPLICABLE:
                                if anchor_path.anchor_path_ref in legacy_policy_anchor_refs:
                                    raise ValueError(
                                        "anchor-scoped applicable policy cannot be broadcast across "
                                        "multiple generated candidates; supply CandidatePolicyContext "
                                        "values for the complete candidate selections"
                                    )
                                legacy_policy_anchor_refs.add(anchor_path.anchor_path_ref)
                            policy_applicability = anchor_path.policy_applicability
                            policy_status = anchor_path.policy_status
                        else:
                            policy_key = _candidate_policy_key(selection)
                            policy_context = policy_context_map.get(policy_key)
                            if policy_context is None:
                                raise ValueError(
                                    "candidate policy contexts must cover every generated candidate; "
                                    f"missing context for {policy_key!r}"
                                )
                            used_policy_context_keys.add(policy_key)
                            policy_applicability = policy_context.policy_applicability
                            policy_status = policy_context.policy_status

                        candidate_id = _candidate_id(selection)
                        configuration = CandidateConfiguration(
                            candidate_id=candidate_id,
                            object_mass_kg=tool.object_mass_kg,
                            load_bearing_components=_load_bearing_components(
                                attachment_components,
                                tether.component,
                                anchor_path.components,
                            ),
                            tether_max_length_mm=tether.max_length_mm,
                            product_constraint_evaluations=constraint_evaluations,
                            attachment_mode=tool_target.attachment_mode,
                            attachment_eligibility=tool_target.eligibility,
                            tool_side_connection=tool_connection,
                            anchor_side_connection=anchor_connection,
                            policy_applicability=policy_applicability,
                            policy_status=policy_status,
                        )
                        generated.append(
                            GeneratedCandidate(
                                selection=selection,
                                configuration=configuration,
                            )
                        )

    if policy_context_map is not None:
        unused_policy_contexts = set(policy_context_map) - used_policy_context_keys
        if unused_policy_contexts:
            raise ValueError(
                "candidate policy contexts must match generated candidates; unused contexts: "
                f"{sorted(repr(key) for key in unused_policy_contexts)!r}"
            )

    return generated


class _ToolTarget(BaseModel):
    attachment_mode: CandidateAttachmentMode
    owner_ref: str = Field(min_length=1)
    target_interface: ConnectionInterface
    assembly: ToolAttachmentAssemblyOption | None = None
    installation_feature: ToolInterfaceFeature | None = None
    eligibility: EligibilityEvaluation | None = None
    eligibility_matches: list[EligibilityMatch] = Field(default_factory=list)


def _eligibility_matches_by_feature(
    matches: list[EligibilityMatch],
) -> dict[str, list[EligibilityMatch]]:
    grouped: dict[str, list[EligibilityMatch]] = defaultdict(list)
    for match in matches:
        grouped[match.feature_id].append(match)
    return dict(grouped)


def _endpoint_assignments(
    endpoints: list[ConnectionInterface],
) -> list[tuple[ConnectionInterface, ConnectionInterface]]:
    tool_capable = [
        endpoint
        for endpoint in endpoints
        if endpoint.tether_side in {TetherSide.TOOL_SIDE, TetherSide.EITHER}
    ]
    anchor_capable = [
        endpoint
        for endpoint in endpoints
        if endpoint.tether_side in {TetherSide.ANCHOR_SIDE, TetherSide.EITHER}
    ]
    return [
        (tool_endpoint, anchor_endpoint)
        for tool_endpoint in tool_capable
        for anchor_endpoint in anchor_capable
        if tool_endpoint.interface_id != anchor_endpoint.interface_id
    ]


def _evaluate_component_constraints(
    components: list[CandidateComponentOption],
    *,
    tether_max_length_mm: float | None,
    installation_feature: ToolInterfaceFeature | None,
    runtime_state: dict[
        tuple[str, str | None],
        ProductConstraintRuntimeState,
    ],
) -> list[ProductConstraintEvaluation]:
    evaluations: list[ProductConstraintEvaluation] = []
    installation_feature_id = (
        installation_feature.feature_id if installation_feature is not None else None
    )
    for component in components:
        state = runtime_state.get((component.component_ref, installation_feature_id))
        context = ProductConstraintContext(
            installation_feature=installation_feature,
            tether_max_length_mm=tether_max_length_mm,
            bond_elapsed_h=state.bond_elapsed_h if state is not None else None,
            pre_use_attachment_test_passed=(
                state.pre_use_attachment_test_passed if state is not None else None
            ),
        )
        component_evaluations = evaluate_product_constraints(
            component.product_constraints,
            context,
        )
        evaluations.extend(
            evaluation.model_copy(update={"component_ref": component.component_ref})
            for evaluation in component_evaluations
        )
    return evaluations


def _product_runtime_state_map(
    states: list[ProductConstraintRuntimeState],
) -> dict[tuple[str, str | None], ProductConstraintRuntimeState]:
    mapped: dict[tuple[str, str | None], ProductConstraintRuntimeState] = {}
    for state in states:
        key = (state.component_ref, state.installation_feature_id)
        if key in mapped:
            raise ValueError(
                "product runtime state must be unique per component installation: "
                f"{key!r}"
            )
        mapped[key] = state
    return mapped


def _evaluate_connection(
    endpoint: ConnectionInterface,
    target: ConnectionInterface,
    *,
    tether_ref: str,
    target_owner_ref: str,
    connector_specs: dict[str, ConnectorSpec],
    context_map: dict[tuple[str, str, str, str], ConnectionEvaluationContext],
):
    context = context_map.get(
        (
            tether_ref,
            target_owner_ref,
            endpoint.interface_id,
            target.interface_id,
        )
    )
    return evaluate_endpoint_engagement(
        endpoint,
        target,
        connector_specs=connector_specs,
        manufacturer_assessments=(context.manufacturer_assessments if context else None),
        derived_results=(context.derived_results if context else None),
        verification_observations=(context.verification_observations if context else None),
    )


def _connection_context_map(
    contexts: list[ConnectionEvaluationContext],
) -> dict[tuple[str, str, str, str], ConnectionEvaluationContext]:
    mapped: dict[tuple[str, str, str, str], ConnectionEvaluationContext] = {}
    for context in contexts:
        key = (
            context.tether_ref,
            context.target_owner_ref,
            context.endpoint_id,
            context.target_interface_id,
        )
        if key in mapped:
            raise ValueError(
                "connection evaluation context must be unique per owning option pair and "
                f"endpoint/target pair: {key!r}"
            )
        mapped[key] = context
    return mapped


def _candidate_policy_context_map(
    contexts: list[CandidatePolicyContext],
) -> dict[tuple[str | None, ...], CandidatePolicyContext]:
    mapped: dict[tuple[str | None, ...], CandidatePolicyContext] = {}
    for context in contexts:
        key = _candidate_policy_context_key(context)
        if key in mapped:
            raise ValueError(
                "candidate policy context must be unique per complete candidate selection: "
                f"{key!r}"
            )
        mapped[key] = context
    return mapped


def _candidate_policy_context_key(
    context: CandidatePolicyContext,
) -> tuple[str | None, ...]:
    return (
        context.tool_ref,
        context.tether_ref,
        context.anchor_path_ref,
        context.attachment_assembly_ref,
        context.installation_feature_id,
        context.tool_endpoint_id,
        context.tool_target_interface_id,
        context.anchor_endpoint_id,
        context.anchor_target_interface_id,
    )


def _candidate_policy_key(selection: CandidatePathSelection) -> tuple[str | None, ...]:
    return (
        selection.tool_ref,
        selection.tether_ref,
        selection.anchor_path_ref,
        selection.attachment_assembly_ref,
        selection.installation_feature_id,
        selection.tool_endpoint_id,
        selection.tool_target_interface_id,
        selection.anchor_endpoint_id,
        selection.anchor_target_interface_id,
    )


def _selected_components(
    attachment_components: list[CandidateComponentOption],
    tether_component: CandidateComponentOption,
    anchor_components: list[CandidateComponentOption],
) -> list[CandidateSelectedComponent]:
    return [
        *[
            CandidateSelectedComponent(
                component_ref=component.component_ref,
                source_product_ref=component.source_product_ref,
                role=CandidateComponentRole.TOOL_ATTACHMENT,
            )
            for component in attachment_components
        ],
        CandidateSelectedComponent(
            component_ref=tether_component.component_ref,
            source_product_ref=tether_component.source_product_ref,
            role=CandidateComponentRole.TETHER,
        ),
        *[
            CandidateSelectedComponent(
                component_ref=component.component_ref,
                source_product_ref=component.source_product_ref,
                role=CandidateComponentRole.ANCHOR,
            )
            for component in anchor_components
        ],
    ]


def _load_bearing_components(
    attachment_components: list[CandidateComponentOption],
    tether_component: CandidateComponentOption,
    anchor_components: list[CandidateComponentOption],
) -> list[LoadBearingComponent]:
    components = [*attachment_components, tether_component, *anchor_components]
    return [
        LoadBearingComponent(
            component_id=component.component_ref,
            rated_capacity_kg=component.rated_capacity_kg,
        )
        for component in components
        if component.load_bearing
    ]


def _candidate_id(selection: CandidatePathSelection) -> str:
    identity = {
        "tool_ref": selection.tool_ref,
        "attachment_assembly_ref": selection.attachment_assembly_ref,
        "installation_feature_id": selection.installation_feature_id,
        "tether_ref": selection.tether_ref,
        "tool_endpoint_id": selection.tool_endpoint_id,
        "tool_target_interface_id": selection.tool_target_interface_id,
        "anchor_path_ref": selection.anchor_path_ref,
        "anchor_endpoint_id": selection.anchor_endpoint_id,
        "anchor_target_interface_id": selection.anchor_target_interface_id,
        "component_refs": [
            component.component_ref for component in selection.components
        ],
    }
    return "candidate:" + json.dumps(
        identity,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _require_unique_component_refs(
    components: list[CandidateComponentOption],
    *,
    scope: str,
) -> None:
    refs = [component.component_ref for component in components]
    duplicates = sorted({ref for ref in refs if refs.count(ref) > 1})
    if duplicates:
        raise ValueError(f"component refs must be unique within {scope}: {duplicates!r}")


def _require_unique_local_ids(ids: list[str], *, scope: str, label: str) -> None:
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        raise ValueError(f"{label} must be unique within {scope}: {duplicates!r}")


def _require_unique_option_refs(refs: list[str], *, label: str) -> None:
    duplicates = sorted({ref for ref in refs if refs.count(ref) > 1})
    if duplicates:
        raise ValueError(f"{label} values must be unique within one generation call: {duplicates!r}")


def _positive_finite_or_none(value: Any, *, field_name: str) -> Any:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a finite positive number when provided")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{field_name} must be a finite positive number when provided")
    return numeric
