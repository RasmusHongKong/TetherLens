from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from .candidate_selection import CandidateSelectionState, EvaluatedCandidate
from .recommendation_run import RecommendationRunResult


class SessionConditionKind(StrEnum):
    """Kind of pending condition carried by one hard-viable candidate."""

    RUNTIME_VERIFICATION = "runtime_verification"
    PRE_USE_ACTION = "pre_use_action"


class SessionConditionOutcome(StrEnum):
    """Terminal outcome of one pending condition for the current session/configuration."""

    SATISFIED = "satisfied"
    FAILED = "failed"


class RecommendationSessionState(StrEnum):
    """Whether a ranked selectable candidate remains usable in this session."""

    ACTIVE = "active"
    EXHAUSTED = "exhausted"


class SessionConditionRef(BaseModel):
    """Candidate-scoped identity of one pending runtime/pre-use condition."""

    candidate_id: str = Field(min_length=1)
    condition_kind: SessionConditionKind
    condition_id: str = Field(min_length=1)


class SessionConditionResolution(SessionConditionRef):
    """Terminal session-local resolution of one condition from the original evaluation."""

    outcome: SessionConditionOutcome


class RecommendationSessionResult(BaseModel):
    """Deterministic session overlay over one immutable recommendation run.

    The originating ``RecommendationRunResult`` remains the authority for candidate
    generation, hard evaluation, contextual feasibility and ranking. This model records
    only terminal outcomes of conditions that were already pending on ranked selectable
    candidates. A failed condition rejects that candidate for this session/configuration
    and fallback advances through the original ranked order without regenerating,
    re-evaluating or re-ranking the candidate set.
    """

    recommendation_run: RecommendationRunResult
    resolutions: list[SessionConditionResolution] = Field(default_factory=list)
    state: RecommendationSessionState
    active_candidate: EvaluatedCandidate | None = None
    active_pending_conditions: list[SessionConditionRef] = Field(default_factory=list)
    active_satisfied_conditions: list[SessionConditionResolution] = Field(default_factory=list)
    rejected_candidates: list[EvaluatedCandidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_session_projection(self) -> RecommendationSessionResult:
        expected = _resolve_session_projection(
            self.recommendation_run,
            self.resolutions,
        )
        if self.resolutions != expected.resolutions:
            raise ValueError(
                "session resolutions must be in deterministic ranked candidate/condition order"
            )
        if self.state != expected.state:
            raise ValueError("session state must match deterministic condition resolution")
        if self.active_candidate != expected.active_candidate:
            raise ValueError(
                "active candidate must be the first unrejected candidate in the original ranking"
            )
        if self.active_pending_conditions != expected.active_pending_conditions:
            raise ValueError(
                "active pending conditions must match unresolved conditions from the original evaluation"
            )
        if self.active_satisfied_conditions != expected.active_satisfied_conditions:
            raise ValueError(
                "active satisfied conditions must match terminal satisfied session resolutions"
            )
        if self.rejected_candidates != expected.rejected_candidates:
            raise ValueError(
                "rejected candidates must match failed session conditions in original ranked order"
            )
        return self


def resolve_recommendation_session(
    recommendation_run: RecommendationRunResult,
    resolutions: list[SessionConditionResolution] | None = None,
) -> RecommendationSessionResult:
    """Resolve session conditions and deterministically choose the current candidate.

    Only conditions explicitly listed as pending on the original ``CandidateEvaluation``
    may be resolved. Condition identity is candidate-scoped, so an observation for one
    physical candidate cannot leak into another candidate that happens to carry the same
    local connection or constraint identifier.

    Absence of a resolution means the condition remains pending. ``SATISFIED`` keeps the
    candidate usable; ``FAILED`` rejects only that candidate for the current
    session/configuration. Lower-ranked candidates are not resolved until every higher
    ranked candidate before them has failed, preserving the lazy field-verification
    workflow and the selector's original deterministic order.

    This generic overlay consumes terminal condition outcomes only. The applicable
    family-specific connection/product evaluator remains responsible for establishing
    that the underlying structured runtime observations or pre-use facts actually
    constitute a satisfied or failed condition.
    """

    supplied_resolutions = list(resolutions or [])
    projection = _resolve_session_projection(recommendation_run, supplied_resolutions)
    return RecommendationSessionResult(
        recommendation_run=recommendation_run,
        resolutions=projection.resolutions,
        state=projection.state,
        active_candidate=projection.active_candidate,
        active_pending_conditions=projection.active_pending_conditions,
        active_satisfied_conditions=projection.active_satisfied_conditions,
        rejected_candidates=projection.rejected_candidates,
    )


@dataclass(frozen=True)
class _SessionProjection:
    resolutions: list[SessionConditionResolution]
    state: RecommendationSessionState
    active_candidate: EvaluatedCandidate | None
    active_pending_conditions: list[SessionConditionRef]
    active_satisfied_conditions: list[SessionConditionResolution]
    rejected_candidates: list[EvaluatedCandidate]


def _resolve_session_projection(
    recommendation_run: RecommendationRunResult,
    resolutions: list[SessionConditionResolution],
) -> _SessionProjection:
    selection = recommendation_run.selection
    if selection.state != CandidateSelectionState.SELECTED:
        raise ValueError(
            "session condition resolution requires a recommendation run with a selected candidate"
        )

    ranked = selection.ranked_viable_candidates
    if not ranked or selection.selected != ranked[0]:
        raise ValueError(
            "session condition resolution requires the run's complete deterministic selectable ranking"
        )

    rank_by_candidate_id = {
        candidate.candidate_id: index for index, candidate in enumerate(ranked)
    }
    conditions_by_candidate_id = {
        candidate.candidate_id: _pending_condition_refs(candidate) for candidate in ranked
    }

    resolution_by_key: dict[
        tuple[str, SessionConditionKind, str],
        SessionConditionResolution,
    ] = {}
    for resolution in resolutions:
        if resolution.candidate_id not in rank_by_candidate_id:
            raise ValueError(
                "session conditions may target only ranked selectable candidates from the original run; "
                f"got candidate_id={resolution.candidate_id!r}"
            )

        candidate_conditions = conditions_by_candidate_id[resolution.candidate_id]
        condition_key = _condition_key(resolution)
        valid_keys = {_condition_key(condition) for condition in candidate_conditions}
        if condition_key not in valid_keys:
            raise ValueError(
                "session resolution must match an originally pending condition with the same "
                "candidate, kind and identifier; "
                f"got candidate_id={resolution.candidate_id!r}, "
                f"condition_kind={resolution.condition_kind.value!r}, "
                f"condition_id={resolution.condition_id!r}"
            )
        if condition_key in resolution_by_key:
            raise ValueError(
                "each candidate-scoped pending condition may have only one terminal session resolution; "
                f"got duplicate {condition_key!r}"
            )
        resolution_by_key[condition_key] = resolution

    rejected_candidates = [
        candidate
        for candidate in ranked
        if _has_failed_condition(
            conditions_by_candidate_id[candidate.candidate_id],
            resolution_by_key,
        )
    ]
    rejected_ids = {candidate.candidate_id for candidate in rejected_candidates}
    active_candidate = next(
        (candidate for candidate in ranked if candidate.candidate_id not in rejected_ids),
        None,
    )

    if active_candidate is not None:
        active_rank = rank_by_candidate_id[active_candidate.candidate_id]
        premature = sorted(
            {
                resolution.candidate_id
                for resolution in resolutions
                if rank_by_candidate_id[resolution.candidate_id] > active_rank
            }
        )
        if premature:
            raise ValueError(
                "lower-ranked candidate conditions cannot be resolved before all higher-ranked "
                f"candidates have failed; premature candidate ids={premature!r}"
            )

    canonical_resolutions = [
        resolution_by_key[key]
        for candidate in ranked
        for condition in conditions_by_candidate_id[candidate.candidate_id]
        if (key := _condition_key(condition)) in resolution_by_key
    ]

    if active_candidate is None:
        return _SessionProjection(
            resolutions=canonical_resolutions,
            state=RecommendationSessionState.EXHAUSTED,
            active_candidate=None,
            active_pending_conditions=[],
            active_satisfied_conditions=[],
            rejected_candidates=rejected_candidates,
        )

    active_conditions = conditions_by_candidate_id[active_candidate.candidate_id]
    active_pending_conditions = [
        condition
        for condition in active_conditions
        if _condition_key(condition) not in resolution_by_key
    ]
    active_satisfied_conditions = [
        resolution_by_key[key]
        for condition in active_conditions
        if (key := _condition_key(condition)) in resolution_by_key
        and resolution_by_key[key].outcome == SessionConditionOutcome.SATISFIED
    ]

    return _SessionProjection(
        resolutions=canonical_resolutions,
        state=RecommendationSessionState.ACTIVE,
        active_candidate=active_candidate,
        active_pending_conditions=active_pending_conditions,
        active_satisfied_conditions=active_satisfied_conditions,
        rejected_candidates=rejected_candidates,
    )


def _pending_condition_refs(candidate: EvaluatedCandidate) -> list[SessionConditionRef]:
    evaluation = candidate.evaluation
    refs = [
        SessionConditionRef(
            candidate_id=candidate.candidate_id,
            condition_kind=SessionConditionKind.RUNTIME_VERIFICATION,
            condition_id=condition_id,
        )
        for condition_id in evaluation.pending_verification_connection_ids
    ]
    refs.extend(
        SessionConditionRef(
            candidate_id=candidate.candidate_id,
            condition_kind=SessionConditionKind.PRE_USE_ACTION,
            condition_id=condition_id,
        )
        for condition_id in evaluation.pending_action_constraint_ids
    )

    keys = [_condition_key(ref) for ref in refs]
    if len(set(keys)) != len(keys):
        raise ValueError(
            "candidate evaluation pending condition identifiers must be unique within each "
            f"candidate/kind scope; candidate_id={candidate.candidate_id!r}"
        )
    return refs


def _has_failed_condition(
    conditions: list[SessionConditionRef],
    resolution_by_key: dict[
        tuple[str, SessionConditionKind, str],
        SessionConditionResolution,
    ],
) -> bool:
    return any(
        (resolution := resolution_by_key.get(_condition_key(condition))) is not None
        and resolution.outcome == SessionConditionOutcome.FAILED
        for condition in conditions
    )


def _condition_key(
    condition: SessionConditionRef,
) -> tuple[str, SessionConditionKind, str]:
    return (
        condition.candidate_id,
        condition.condition_kind,
        condition.condition_id,
    )
