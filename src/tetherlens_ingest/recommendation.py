from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .compatibility import EligibilityEvaluation, EligibilityStatus, PolicyStatus
from .connection import ConnectionEvaluation, ConnectionStatus


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
    CONNECTION_COMPATIBILITY = "connection_compatibility"
    POLICY = "policy"


class CandidateCheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    REQUIRES_VERIFICATION = "requires_verification"
    UNRESOLVED = "unresolved"


class LoadBearingComponent(BaseModel):
    """One load-bearing component participating in the candidate path."""

    component_id: str = Field(min_length=1)
    rated_capacity_kg: float | None = None

    @field_validator("rated_capacity_kg", mode="before")
    @classmethod
    def validate_capacity(cls, value: Any) -> Any:
        return _positive_finite_or_none(value, field_name="rated_capacity_kg")


class LanyardLengthConstraint(BaseModel):
    """One accepted maximum-lanyard-length constraint applied to the candidate."""

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
    first slice. A full tethering path must contain at least the tool-side and
    anchor/container-side connection evaluations.
    """

    candidate_id: str = Field(min_length=1)
    object_mass_kg: float | None = None
    load_bearing_components: list[LoadBearingComponent] = Field(min_length=1)
    tether_max_length_mm: float | None = None
    lanyard_length_constraints: list[LanyardLengthConstraint] = Field(default_factory=list)
    attachment_eligibility: EligibilityEvaluation | None = None
    connections: list[ConnectionEvaluation] = Field(min_length=2)
    policy_status: PolicyStatus | None = None

    @field_validator("object_mass_kg", mode="before")
    @classmethod
    def validate_object_mass(cls, value: Any) -> Any:
        return _positive_finite_or_none(value, field_name="object_mass_kg")

    @field_validator("tether_max_length_mm", mode="before")
    @classmethod
    def validate_tether_max_length(cls, value: Any) -> Any:
        return _positive_finite_or_none(value, field_name="tether_max_length_mm")


class CandidateCheck(BaseModel):
    check_id: str
    check_type: CandidateCheckType
    status: CandidateCheckStatus
    reason: str
    subject_refs: list[str] = Field(default_factory=list)


class CandidateEvaluation(BaseModel):
    """Auditable hard-constraint result for one candidate configuration."""

    candidate_id: str
    recommendation_state: RecommendationState | None
    checks: list[CandidateCheck]
    connections: list[ConnectionEvaluation]
    pending_verification_connection_ids: list[str] = Field(default_factory=list)
    review_required: bool = False

    @property
    def recommended(self) -> bool:
        return self.recommendation_state is not None

    @property
    def blocked(self) -> bool:
        return self.recommendation_state is None


def evaluate_candidate_configuration(candidate: CandidateConfiguration) -> CandidateEvaluation:
    """Compose existing primitive evaluations into one candidate recommendation state.

    This function does not create compatibility, infer missing catalogue facts, rank
    candidates or decide that no alternative exists. Any failed or unresolved hard
    check blocks this candidate. ``requires_verification`` remains usable and produces
    ``recommended_with_constraints`` when every other hard check passes.
    """

    checks: list[CandidateCheck] = []

    if candidate.attachment_eligibility is not None:
        eligibility = candidate.attachment_eligibility
        if eligibility.status == EligibilityStatus.ELIGIBLE:
            status = CandidateCheckStatus.PASSED
            reason = "tool attachment eligibility is established for at least one bound tool feature"
            refs = [match.feature_id for match in eligibility.matches]
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

    if candidate.policy_status is not None:
        if candidate.policy_status == PolicyStatus.PERMITTED:
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
    requires_verification = any(
        check.status == CandidateCheckStatus.REQUIRES_VERIFICATION for check in checks
    )

    if blocked:
        recommendation_state = None
    elif requires_verification:
        recommendation_state = RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    else:
        recommendation_state = RecommendationState.RECOMMENDED

    return CandidateEvaluation(
        candidate_id=candidate.candidate_id,
        recommendation_state=recommendation_state,
        checks=checks,
        connections=list(candidate.connections),
        pending_verification_connection_ids=[
            _connection_id(connection)
            for connection in candidate.connections
            if connection.status == ConnectionStatus.REQUIRES_VERIFICATION
        ],
        review_required=any(connection.review_required for connection in candidate.connections),
    )


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
