from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .compatibility import EligibilityEvaluation, EligibilityStatus, PolicyStatus
from .connection import (
    ConnectionEvaluation,
    ConnectionInterfaceRole,
    ConnectionStatus,
    TetherSide,
)
from .constraints import ProductConstraintEvaluation, ProductConstraintStatus


class RecommendationState(StrEnum):
    """Recommendation state for one already-generated candidate configuration.

    ``None`` on ``CandidateEvaluation.recommendation_state`` means this candidate is
    blocked. It deliberately does not mean that the whole search has exhausted all
    alternatives and therefore must not be widened into ``no suitable recommendation``.
    """

    RECOMMENDED = "recommended"
    RECOMMENDED_WITH_CONSTRAINTS = "recommended_with_constraints"


class CandidateCheckType(StrEnum):
    ATTACHMENT_ELIGIBILITY = "attachment_eligibility"
    LOAD_CAPACITY = "load_capacity"
    LANYARD_LENGTH = "lanyard_length"
    PRODUCT_CONSTRAINT = "product_constraint"
    CONNECTION_COMPATIBILITY = "connection_compatibility"
    POLICY = "policy"


class CandidateCheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    REQUIRES_VERIFICATION = "requires_verification"
    REQUIRES_ACTION = "requires_action"
    UNRESOLVED = "unresolved"


class CandidateAttachmentMode(StrEnum):
    """Whether the candidate path reaches the tether directly or through a ToolAttachment."""

    DIRECT = "direct"
    TOOL_ATTACHMENT = "tool_attachment"


class PolicyApplicability(StrEnum):
    """Whether a site/configuration policy evaluation is required for this candidate."""

    NOT_APPLICABLE = "not_applicable"
    APPLICABLE = "applicable"


class LoadBearingComponent(BaseModel):
    """One load-bearing component participating in the candidate path."""

    component_id: str = Field(min_length=1)
    rated_capacity_kg: float | None = None

    @field_validator("rated_capacity_kg", mode="before")
    @classmethod
    def validate_capacity(cls, value: Any) -> Any:
        return _positive_finite_or_none(value, field_name="rated_capacity_kg")


class LanyardLengthConstraint(BaseModel):
    """Legacy runtime maximum-lanyard-length input retained during normalization migration.

    New catalogue-to-runtime paths should prefer ``ProductConstraintEvaluation`` from
    ``constraints.resolve_product_constraints`` / ``evaluate_product_constraints``.
    This shape remains supported so PR #31 callers do not break during the migration.
    """

    constraint_id: str = Field(min_length=1)
    max_lanyard_length_mm: float | None = None

    @field_validator("max_lanyard_length_mm", mode="before")
    @classmethod
    def validate_max_length(cls, value: Any) -> Any:
        return _positive_finite_or_none(value, field_name="max_lanyard_length_mm")


class CandidateConfiguration(BaseModel):
    """Small runtime composition of already-resolved recommendation primitives.

    The object intentionally consumes normalized results rather than Claims or product
    identities. Candidate generation, ranking and evidence acceptance stay outside this
    layer.

    Product installation/use constraints enter only as resolved evaluations. Hard and
    pre-use obligations are composed here; explicitly contextual constraints remain
    retained on the configuration but are deferred to downstream context evaluation.
    This keeps raw claim keys and manufacturer-specific extraction details out of
    recommendation composition without turning absent work context into a hard failure.
    """

    candidate_id: str = Field(min_length=1)
    object_mass_kg: float | None = None
    load_bearing_components: list[LoadBearingComponent] = Field(min_length=1)
    tether_max_length_mm: float | None = None
    lanyard_length_constraints: list[LanyardLengthConstraint] = Field(default_factory=list)
    product_constraint_evaluations: list[ProductConstraintEvaluation] = Field(default_factory=list)
    attachment_mode: CandidateAttachmentMode
    attachment_eligibility: EligibilityEvaluation | None = None
    tool_side_connection: ConnectionEvaluation
    anchor_side_connection: ConnectionEvaluation
    policy_applicability: PolicyApplicability
    policy_status: PolicyStatus | None = None

    @field_validator("object_mass_kg", mode="before")
    @classmethod
    def validate_object_mass(cls, value: Any) -> Any:
        return _positive_finite_or_none(value, field_name="object_mass_kg")

    @field_validator("tether_max_length_mm", mode="before")
    @classmethod
    def validate_tether_max_length(cls, value: Any) -> Any:
        return _positive_finite_or_none(value, field_name="tether_max_length_mm")

    @model_validator(mode="after")
    def validate_path_semantics(self) -> CandidateConfiguration:
        expected_tool_target_role = (
            ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE
            if self.attachment_mode == CandidateAttachmentMode.DIRECT
            else ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
        )
        if self.tool_side_connection.target_role != expected_tool_target_role:
            raise ValueError(
                "tool-side connection target role must match the candidate attachment mode"
            )
        if self.tool_side_connection.endpoint_tether_side not in {
            TetherSide.TOOL_SIDE,
            TetherSide.EITHER,
        }:
            raise ValueError("tool-side connection must use a tool-capable tether endpoint")
        if self.anchor_side_connection.target_role not in _ANCHOR_SIDE_TARGET_ROLES:
            raise ValueError(
                "anchor-side connection must target an anchor/container tether interface"
            )
        if self.anchor_side_connection.endpoint_tether_side not in {
            TetherSide.ANCHOR_SIDE,
            TetherSide.EITHER,
        }:
            raise ValueError("anchor-side connection must use an anchor-capable tether endpoint")
        if (
            self.attachment_mode == CandidateAttachmentMode.DIRECT
            and self.attachment_eligibility is not None
        ):
            raise ValueError("direct candidates must not supply ToolAttachment eligibility")
        if (
            self.policy_applicability == PolicyApplicability.NOT_APPLICABLE
            and self.policy_status is not None
        ):
            raise ValueError(
                "policy-not-applicable candidates must not supply a policy evaluation"
            )
        return self

    @property
    def connections(self) -> list[ConnectionEvaluation]:
        """Return required path connections in deterministic tool-to-anchor order."""

        return [self.tool_side_connection, self.anchor_side_connection]


class CandidateCheck(BaseModel):
    check_id: str
    check_type: CandidateCheckType
    status: CandidateCheckStatus
    reason: str
    subject_refs: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class CandidateEvaluation(BaseModel):
    """Auditable hard-constraint result for one candidate configuration."""

    candidate_id: str
    recommendation_state: RecommendationState | None
    checks: list[CandidateCheck]
    connections: list[ConnectionEvaluation]
    pending_verification_connection_ids: list[str] = Field(default_factory=list)
    pending_action_constraint_ids: list[str] = Field(default_factory=list)
    review_required: bool = False

    @property
    def recommended(self) -> bool:
        return self.recommendation_state is not None

    @property
    def blocked(self) -> bool:
        return self.recommendation_state is None

    @property
    def has_constraints(self) -> bool:
        return self.recommendation_state == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS

    @property
    def requires_verification(self) -> bool:
        """Whether a selected candidate has pending physical connection verification."""

        return bool(self.pending_verification_connection_ids)

    @property
    def requires_action(self) -> bool:
        """Whether a selected candidate has pending non-connection pre-use actions."""

        return bool(self.pending_action_constraint_ids)


def evaluate_candidate_configuration(candidate: CandidateConfiguration) -> CandidateEvaluation:
    """Compose existing primitive evaluations into one candidate recommendation state.

    This function does not create compatibility, infer missing catalogue facts, rank
    candidates or decide that no alternative exists. Any failed or unresolved hard
    check blocks this candidate. Pending connection verification or another validated
    pre-use action remains usable and produces ``recommended_with_constraints`` when
    every other hard check passes. Product constraints explicitly marked as deferred
    context are retained on the original configuration but do not become hard checks.

    Feature-scoped product constraints must all refer to one installation feature that
    also appears in the ToolAttachment eligibility matches. This keeps the same-feature
    invariant intact across the boundary between eligibility and product constraints.
    """

    checks: list[CandidateCheck] = []

    if candidate.attachment_mode == CandidateAttachmentMode.TOOL_ATTACHMENT:
        eligibility = candidate.attachment_eligibility
        if eligibility is None:
            status = CandidateCheckStatus.UNRESOLVED
            reason = "ToolAttachment eligibility is required but no evaluation is available"
            refs = []
        elif eligibility.status == EligibilityStatus.ELIGIBLE and eligibility.matches:
            status = CandidateCheckStatus.PASSED
            reason = "tool attachment eligibility is established for at least one bound tool feature"
            refs = [match.feature_id for match in eligibility.matches]
        elif eligibility.status == EligibilityStatus.ELIGIBLE:
            status = CandidateCheckStatus.UNRESOLVED
            reason = "tool attachment eligibility is marked eligible but has no bound feature match"
            refs = []
        elif eligibility.status == EligibilityStatus.INELIGIBLE:
            status = CandidateCheckStatus.FAILED
            reason = "tool attachment is ineligible for the resolved tool features"
            refs = []
        else:
            status = CandidateCheckStatus.UNRESOLVED
            reason = "tool attachment eligibility cannot be resolved from the available feature facts"
            refs = []
        checks.append(
            CandidateCheck(
                check_id="attachment_eligibility",
                check_type=CandidateCheckType.ATTACHMENT_ELIGIBILITY,
                status=status,
                reason=reason,
                subject_refs=refs,
            )
        )

    for component in candidate.load_bearing_components:
        if candidate.object_mass_kg is None:
            status = CandidateCheckStatus.UNRESOLVED
            reason = "object operational mass is not established for the load-capacity check"
        elif component.rated_capacity_kg is None:
            status = CandidateCheckStatus.UNRESOLVED
            reason = "component rated capacity is not established"
        elif component.rated_capacity_kg < candidate.object_mass_kg:
            status = CandidateCheckStatus.FAILED
            reason = (
                f"component rated capacity {component.rated_capacity_kg:g} kg is below "
                f"the {candidate.object_mass_kg:g} kg object mass"
            )
        else:
            status = CandidateCheckStatus.PASSED
            reason = (
                f"component rated capacity {component.rated_capacity_kg:g} kg meets or exceeds "
                f"the {candidate.object_mass_kg:g} kg object mass"
            )
        checks.append(
            CandidateCheck(
                check_id=f"load_capacity:{component.component_id}",
                check_type=CandidateCheckType.LOAD_CAPACITY,
                status=status,
                reason=reason,
                subject_refs=[component.component_id],
            )
        )

    # Legacy direct runtime inputs remain supported while catalogue callers migrate to
    # normalized ProductConstraintEvaluation for this same semantic limit.
    for constraint in candidate.lanyard_length_constraints:
        if candidate.tether_max_length_mm is None:
            status = CandidateCheckStatus.UNRESOLVED
            reason = "tether maximum length is not established for the applicable length constraint"
        elif constraint.max_lanyard_length_mm is None:
            status = CandidateCheckStatus.UNRESOLVED
            reason = "applicable maximum-lanyard-length limit is not established"
        elif candidate.tether_max_length_mm > constraint.max_lanyard_length_mm:
            status = CandidateCheckStatus.FAILED
            reason = (
                f"tether maximum length {candidate.tether_max_length_mm:g} mm exceeds "
                f"the {constraint.max_lanyard_length_mm:g} mm limit"
            )
        else:
            status = CandidateCheckStatus.PASSED
            reason = (
                f"tether maximum length {candidate.tether_max_length_mm:g} mm is within "
                f"the {constraint.max_lanyard_length_mm:g} mm limit"
            )
        checks.append(
            CandidateCheck(
                check_id=f"lanyard_length:{constraint.constraint_id}",
                check_type=CandidateCheckType.LANYARD_LENGTH,
                status=status,
                reason=reason,
                subject_refs=[constraint.constraint_id],
            )
        )

    feature_binding_problem = _feature_constraint_binding_problem(candidate)
    for constraint in candidate.product_constraint_evaluations:
        if constraint.status == ProductConstraintStatus.DEFERRED_CONTEXT:
            continue
        if constraint.installation_feature_id is not None and feature_binding_problem is not None:
            status = CandidateCheckStatus.UNRESOLVED
            reason = feature_binding_problem
        elif constraint.status == ProductConstraintStatus.PASSED:
            status = CandidateCheckStatus.PASSED
            reason = constraint.reason
        elif constraint.status == ProductConstraintStatus.FAILED:
            status = CandidateCheckStatus.FAILED
            reason = constraint.reason
        elif constraint.status == ProductConstraintStatus.REQUIRES_ACTION:
            status = CandidateCheckStatus.REQUIRES_ACTION
            reason = constraint.reason
        else:
            status = CandidateCheckStatus.UNRESOLVED
            reason = constraint.reason

        subject_refs = list(constraint.subject_refs)
        if constraint.component_ref is not None and constraint.component_ref not in subject_refs:
            subject_refs.insert(0, constraint.component_ref)
        checks.append(
            CandidateCheck(
                check_id=f"product_constraint:{_product_constraint_evaluation_id(constraint)}",
                check_type=CandidateCheckType.PRODUCT_CONSTRAINT,
                status=status,
                reason=reason,
                subject_refs=subject_refs,
                source_urls=list(constraint.source_urls),
            )
        )

    for connection in candidate.connections:
        if connection.status == ConnectionStatus.COMPATIBLE:
            status = CandidateCheckStatus.PASSED
        elif connection.status == ConnectionStatus.INCOMPATIBLE:
            status = CandidateCheckStatus.FAILED
        elif connection.status == ConnectionStatus.REQUIRES_VERIFICATION:
            status = CandidateCheckStatus.REQUIRES_VERIFICATION
        else:
            status = CandidateCheckStatus.UNRESOLVED

        checks.append(
            CandidateCheck(
                check_id=_connection_id(connection),
                check_type=CandidateCheckType.CONNECTION_COMPATIBILITY,
                status=status,
                reason=connection.reason,
                subject_refs=[connection.endpoint_id, connection.target_interface_id],
            )
        )

    if candidate.policy_applicability == PolicyApplicability.APPLICABLE:
        if candidate.policy_status is None:
            status = CandidateCheckStatus.UNRESOLVED
            reason = "policy applies but no policy evaluation is available"
        elif candidate.policy_status == PolicyStatus.PERMITTED:
            status = CandidateCheckStatus.PASSED
            reason = "candidate is permitted by the supplied policy evaluation"
        elif candidate.policy_status == PolicyStatus.PROHIBITED:
            status = CandidateCheckStatus.FAILED
            reason = "candidate is prohibited by the supplied policy evaluation"
        else:
            status = CandidateCheckStatus.UNRESOLVED
            reason = "applicable policy cannot be resolved for this candidate"
        checks.append(
            CandidateCheck(
                check_id="policy",
                check_type=CandidateCheckType.POLICY,
                status=status,
                reason=reason,
            )
        )

    blocked = any(
        check.status in {CandidateCheckStatus.FAILED, CandidateCheckStatus.UNRESOLVED}
        for check in checks
    )
    condition_pending = any(
        check.status
        in {
            CandidateCheckStatus.REQUIRES_VERIFICATION,
            CandidateCheckStatus.REQUIRES_ACTION,
        }
        for check in checks
    )

    if blocked:
        recommendation_state = None
    elif condition_pending:
        recommendation_state = RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    else:
        recommendation_state = RecommendationState.RECOMMENDED

    pending_verification_connection_ids: list[str] = []
    pending_action_constraint_ids: list[str] = []
    if recommendation_state == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS:
        pending_verification_connection_ids = [
            _connection_id(connection)
            for connection in candidate.connections
            if connection.status == ConnectionStatus.REQUIRES_VERIFICATION
        ]
        pending_action_constraint_ids = [
            _product_constraint_evaluation_id(constraint)
            for constraint in candidate.product_constraint_evaluations
            if constraint.status == ProductConstraintStatus.REQUIRES_ACTION
            and (
                constraint.installation_feature_id is None
                or feature_binding_problem is None
            )
        ]

    return CandidateEvaluation(
        candidate_id=candidate.candidate_id,
        recommendation_state=recommendation_state,
        checks=checks,
        connections=list(candidate.connections),
        pending_verification_connection_ids=pending_verification_connection_ids,
        pending_action_constraint_ids=pending_action_constraint_ids,
        review_required=any(connection.review_required for connection in candidate.connections),
    )


def _feature_constraint_binding_problem(candidate: CandidateConfiguration) -> str | None:
    feature_ids = {
        constraint.installation_feature_id
        for constraint in candidate.product_constraint_evaluations
        if constraint.installation_feature_id is not None
        and constraint.status != ProductConstraintStatus.DEFERRED_CONTEXT
    }
    if not feature_ids:
        return None
    if len(feature_ids) > 1:
        return (
            "feature-scoped product constraints refer to multiple installation features; "
            "one candidate path must bind them to the same eligible feature"
        )
    if candidate.attachment_mode != CandidateAttachmentMode.TOOL_ATTACHMENT:
        return "feature-scoped product constraints require a ToolAttachment installation path"

    eligibility = candidate.attachment_eligibility
    if (
        eligibility is None
        or eligibility.status != EligibilityStatus.ELIGIBLE
        or not eligibility.matches
    ):
        return (
            "feature-scoped product constraints cannot be bound because ToolAttachment "
            "eligibility is not established"
        )

    feature_id = next(iter(feature_ids))
    eligible_feature_ids = {match.feature_id for match in eligibility.matches}
    if feature_id not in eligible_feature_ids:
        return (
            f"product constraints were evaluated against installation feature {feature_id!r}, "
            "which is not an eligible ToolAttachment feature for this candidate"
        )
    return None


def _product_constraint_evaluation_id(constraint: ProductConstraintEvaluation) -> str:
    if constraint.component_ref is None:
        return constraint.constraint_id
    return f"component={constraint.component_ref}|constraint={constraint.constraint_id}"


def _connection_id(connection: ConnectionEvaluation) -> str:
    return f"connection:{connection.endpoint_id}->{connection.target_interface_id}"


def _positive_finite_or_none(value: Any, *, field_name: str) -> Any:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a finite positive number when provided")
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field_name} must be a finite positive number when provided") from exc
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{field_name} must be a finite positive number when provided")
    return numeric


_ANCHOR_SIDE_TARGET_ROLES = {
    ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
    ConnectionInterfaceRole.CONTAINER_CONNECTION,
}
