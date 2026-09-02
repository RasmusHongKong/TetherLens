from __future__ import annotations

import math
from enum import StrEnum
from itertools import groupby
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .candidate_generation import GeneratedCandidate
from .connection import CompatibilityBasis
from .recommendation import CandidateEvaluation, RecommendationState


class SnagRiskLevel(StrEnum):
    STANDARD = "standard"
    ELEVATED = "elevated"


class CandidateRankingContext(BaseModel):
    """Explicit work context that may affect already-hard-viable candidates."""

    snag_risk: SnagRiskLevel | None = None
    required_reach_mm: float | None = None

    @field_validator("required_reach_mm", mode="before")
    @classmethod
    def validate_required_reach(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("required_reach_mm must be a finite positive number when provided")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric <= 0:
            raise ValueError("required_reach_mm must be a finite positive number when provided")
        return numeric


class CandidateSelectionState(StrEnum):
    SELECTED = "selected"
    NO_SUITABLE_RECOMMENDATION = "no_suitable_recommendation"
    NO_GENERATED_CANDIDATES = "no_generated_candidates"


class EvaluatedCandidate(BaseModel):
    """One generated physical path paired with its hard-constraint evaluation.

    Ranking never reconstructs candidate identity from product references or from the
    canonical candidate id. The original generated selection is retained so component,
    installation-feature and endpoint provenance remain attached to every ranked result.
    """

    generated_candidate: GeneratedCandidate
    evaluation: CandidateEvaluation

    @model_validator(mode="after")
    def validate_identity(self) -> EvaluatedCandidate:
        generated_id = self.generated_candidate.configuration.candidate_id
        if self.evaluation.candidate_id != generated_id:
            raise ValueError(
                "generated candidate and evaluation must have the same candidate_id; "
                f"got {generated_id!r} and {self.evaluation.candidate_id!r}"
            )
        return self

    @property
    def candidate_id(self) -> str:
        return self.evaluation.candidate_id

    @property
    def viable(self) -> bool:
        """Hard viability is owned exclusively by the existing candidate evaluator."""

        return self.evaluation.recommendation_state is not None


class CandidateSelectionResult(BaseModel):
    """Deterministic global selection result over one complete generated candidate set."""

    state: CandidateSelectionState
    selected: EvaluatedCandidate | None = None
    ranked_viable_candidates: list[EvaluatedCandidate] = Field(default_factory=list)
    contextually_infeasible_candidates: list[EvaluatedCandidate] = Field(default_factory=list)
    blocked_candidates: list[EvaluatedCandidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_state(self) -> CandidateSelectionResult:
        ranked_ids = [candidate.candidate_id for candidate in self.ranked_viable_candidates]
        contextual_ids = [
            candidate.candidate_id for candidate in self.contextually_infeasible_candidates
        ]
        blocked_ids = [candidate.candidate_id for candidate in self.blocked_candidates]

        if len(set(ranked_ids)) != len(ranked_ids):
            raise ValueError("ranked viable candidate ids must be unique")
        if len(set(contextual_ids)) != len(contextual_ids):
            raise ValueError("contextually infeasible candidate ids must be unique")
        if len(set(blocked_ids)) != len(blocked_ids):
            raise ValueError("blocked candidate ids must be unique")

        overlap = sorted(
            (set(ranked_ids) & set(contextual_ids))
            | (set(ranked_ids) & set(blocked_ids))
            | (set(contextual_ids) & set(blocked_ids))
        )
        if overlap:
            raise ValueError(
                "candidate cannot appear in more than one selection partition: "
                f"{overlap!r}"
            )

        incorrectly_ranked = [
            candidate.candidate_id
            for candidate in self.ranked_viable_candidates
            if not candidate.viable
        ]
        if incorrectly_ranked:
            raise ValueError(
                "ranked viable candidates must have a non-null recommendation state: "
                f"{incorrectly_ranked!r}"
            )
        incorrectly_contextual = [
            candidate.candidate_id
            for candidate in self.contextually_infeasible_candidates
            if not candidate.viable
        ]
        if incorrectly_contextual:
            raise ValueError(
                "contextually infeasible candidates must remain hard-viable: "
                f"{incorrectly_contextual!r}"
            )
        incorrectly_blocked = [
            candidate.candidate_id
            for candidate in self.blocked_candidates
            if candidate.viable
        ]
        if incorrectly_blocked:
            raise ValueError(
                "blocked candidates must have a null recommendation state: "
                f"{incorrectly_blocked!r}"
            )

        if self.state == CandidateSelectionState.SELECTED:
            if self.selected is None or not self.ranked_viable_candidates:
                raise ValueError("selected state requires a selected viable candidate")
            if not self.selected.viable:
                raise ValueError("selected candidate must be viable")
            if self.selected != self.ranked_viable_candidates[0]:
                raise ValueError(
                    "selected candidate must equal the complete first ranked viable candidate"
                )
            return self

        if self.selected is not None:
            raise ValueError("non-selected states must not carry a selected candidate")

        if self.state == CandidateSelectionState.NO_SUITABLE_RECOMMENDATION:
            if self.ranked_viable_candidates:
                raise ValueError("no-suitable state cannot contain selectable viable candidates")
            if not self.contextually_infeasible_candidates and not self.blocked_candidates:
                raise ValueError(
                    "no-suitable state requires at least one generated candidate that was evaluated"
                )
            return self

        if (
            self.ranked_viable_candidates
            or self.contextually_infeasible_candidates
            or self.blocked_candidates
        ):
            raise ValueError("no-generated-candidates state must not contain candidates")
        return self


def rank_and_select_candidates(
    generated_candidates: list[GeneratedCandidate],
    evaluations: list[CandidateEvaluation],
    *,
    ranking_context: CandidateRankingContext | None = None,
) -> CandidateSelectionResult:
    """Select the highest-ranked candidate that is hard-viable and contextually usable.

    The function requires exact one-to-one evaluation coverage for the generated set.
    Ranking cannot rescue a blocked candidate: hard viability remains exactly the
    evaluator's ``recommendation_state is not None`` decision.

    An explicit ``required_reach_mm`` is a contextual feasibility requirement rather
    than a hard evaluator check. A hard-viable candidate whose established maximum
    working length is below the requirement is retained separately as contextually
    infeasible. Missing maximum length is not treated as failure: known-adequate
    candidates rank ahead of reach-unknown fallbacks, while an all-unknown set preserves
    the existing deterministic baseline/context ordering.

    Baseline quality remains deliberately lexicographic rather than weighted:

    1. fully recommended before recommended-with-constraints;
    2. fewer pending verification/pre-use conditions;
    3. for equal pending burden, fewer pending physical verifications;
    4. stronger connection evidence (established catalogue basis before runtime
       verification, and runtime verification before no basis); and
    5. no internal review signal before review-required.

    Elevated snag risk still acts only inside complete baseline-quality ties within the
    same reach-knowledge tier. It prefers lower minimum/retracted tether length when
    every candidate in that tied group has the fact. Maximum/extended length is never
    used as a snag proxy, and excess reach above the stated minimum is not rewarded.
    Canonical candidate id remains the deterministic final fallback.
    """

    generated_by_id = _unique_generated_by_id(generated_candidates)
    evaluations_by_id = _unique_evaluations_by_id(evaluations)

    generated_ids = set(generated_by_id)
    evaluation_ids = set(evaluations_by_id)
    if generated_ids != evaluation_ids:
        missing = sorted(generated_ids - evaluation_ids)
        unexpected = sorted(evaluation_ids - generated_ids)
        raise ValueError(
            "candidate selection requires exact evaluation coverage for the generated set; "
            f"missing evaluations={missing!r}, unexpected evaluations={unexpected!r}"
        )

    if not generated_candidates:
        return CandidateSelectionResult(
            state=CandidateSelectionState.NO_GENERATED_CANDIDATES,
        )

    paired = [
        EvaluatedCandidate(
            generated_candidate=generated,
            evaluation=evaluations_by_id[generated.configuration.candidate_id],
        )
        for generated in generated_candidates
    ]

    hard_viable = [candidate for candidate in paired if candidate.viable]
    contextually_infeasible = _contextually_infeasible_candidates(
        hard_viable,
        ranking_context=ranking_context,
    )
    contextually_infeasible_ids = {
        candidate.candidate_id for candidate in contextually_infeasible
    }
    selectable = [
        candidate
        for candidate in hard_viable
        if candidate.candidate_id not in contextually_infeasible_ids
    ]
    viable = _rank_viable_candidates(
        selectable,
        ranking_context=ranking_context,
    )
    blocked = sorted(
        (candidate for candidate in paired if not candidate.viable),
        key=lambda candidate: candidate.candidate_id,
    )

    if viable:
        return CandidateSelectionResult(
            state=CandidateSelectionState.SELECTED,
            selected=viable[0],
            ranked_viable_candidates=viable,
            contextually_infeasible_candidates=contextually_infeasible,
            blocked_candidates=blocked,
        )

    return CandidateSelectionResult(
        state=CandidateSelectionState.NO_SUITABLE_RECOMMENDATION,
        contextually_infeasible_candidates=contextually_infeasible,
        blocked_candidates=blocked,
    )


def _contextually_infeasible_candidates(
    candidates: list[EvaluatedCandidate],
    *,
    ranking_context: CandidateRankingContext | None,
) -> list[EvaluatedCandidate]:
    if ranking_context is None or ranking_context.required_reach_mm is None:
        return []

    required_reach_mm = ranking_context.required_reach_mm
    return sorted(
        (
            candidate
            for candidate in candidates
            if candidate.generated_candidate.configuration.tether_max_length_mm is not None
            and candidate.generated_candidate.configuration.tether_max_length_mm
            < required_reach_mm
        ),
        key=lambda candidate: candidate.candidate_id,
    )


def _rank_viable_candidates(
    candidates: list[EvaluatedCandidate],
    *,
    ranking_context: CandidateRankingContext | None,
) -> list[EvaluatedCandidate]:
    if ranking_context is None or ranking_context.required_reach_mm is None:
        return _rank_baseline_and_snag(
            candidates,
            ranking_context=ranking_context,
        )

    reach_established = [
        candidate
        for candidate in candidates
        if candidate.generated_candidate.configuration.tether_max_length_mm is not None
    ]
    reach_unknown = [
        candidate
        for candidate in candidates
        if candidate.generated_candidate.configuration.tether_max_length_mm is None
    ]
    return [
        *_rank_baseline_and_snag(
            reach_established,
            ranking_context=ranking_context,
        ),
        *_rank_baseline_and_snag(
            reach_unknown,
            ranking_context=ranking_context,
        ),
    ]


def _rank_baseline_and_snag(
    candidates: list[EvaluatedCandidate],
    *,
    ranking_context: CandidateRankingContext | None,
) -> list[EvaluatedCandidate]:
    baseline_ranked = sorted(candidates, key=_ranking_key)
    if (
        ranking_context is None
        or ranking_context.snag_risk != SnagRiskLevel.ELEVATED
    ):
        return baseline_ranked

    ranked: list[EvaluatedCandidate] = []
    for _, grouped_candidates in groupby(
        baseline_ranked,
        key=_baseline_quality_key,
    ):
        group = list(grouped_candidates)
        minimum_lengths = [
            candidate.generated_candidate.ranking_facts.tether_min_length_mm
            for candidate in group
        ]
        if all(length is not None for length in minimum_lengths):
            group = sorted(
                group,
                key=lambda candidate: (
                    candidate.generated_candidate.ranking_facts.tether_min_length_mm,
                    candidate.candidate_id,
                ),
            )
        ranked.extend(group)
    return ranked


def _baseline_quality_key(
    candidate: EvaluatedCandidate,
) -> tuple[int, int, int, int, int, int]:
    evaluation = candidate.evaluation
    state_tier = (
        0
        if evaluation.recommendation_state == RecommendationState.RECOMMENDED
        else 1
    )
    pending_verification_count = len(evaluation.pending_verification_connection_ids)
    pending_action_count = len(evaluation.pending_action_constraint_ids)
    total_pending_conditions = pending_verification_count + pending_action_count

    no_basis_count = sum(
        connection.basis == CompatibilityBasis.NONE for connection in evaluation.connections
    )
    runtime_basis_count = sum(
        connection.basis == CompatibilityBasis.RUNTIME_VERIFICATION
        for connection in evaluation.connections
    )

    return (
        state_tier,
        total_pending_conditions,
        pending_verification_count,
        no_basis_count,
        runtime_basis_count,
        1 if evaluation.review_required else 0,
    )


def _ranking_key(candidate: EvaluatedCandidate) -> tuple[int, int, int, int, int, int, str]:
    return (*_baseline_quality_key(candidate), candidate.candidate_id)


def _unique_generated_by_id(
    candidates: list[GeneratedCandidate],
) -> dict[str, GeneratedCandidate]:
    mapped: dict[str, GeneratedCandidate] = {}
    for candidate in candidates:
        candidate_id = candidate.configuration.candidate_id
        if candidate_id in mapped:
            raise ValueError(f"generated candidate ids must be unique: {candidate_id!r}")
        mapped[candidate_id] = candidate
    return mapped


def _unique_evaluations_by_id(
    evaluations: list[CandidateEvaluation],
) -> dict[str, CandidateEvaluation]:
    mapped: dict[str, CandidateEvaluation] = {}
    for evaluation in evaluations:
        if evaluation.candidate_id in mapped:
            raise ValueError(
                f"candidate evaluation ids must be unique: {evaluation.candidate_id!r}"
            )
        mapped[evaluation.candidate_id] = evaluation
    return mapped
