from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


ScalarValue = str | int | float | bool


class FeatureKind(StrEnum):
    THROUGH_OPENING = "through_opening"
    RING = "ring"
    HANDLE = "handle"
    NARROWED_SECTION = "narrowed_section"
    EXTERNAL_SECTION = "external_section"
    SURFACE = "surface"
    OTHER = "other"


class FeatureRole(StrEnum):
    TETHER_INTERFACE = "tether_interface"
    ACCESSORY_MOUNT = "accessory_mount"
    GRIP = "grip"
    WORKING_PART = "working_part"
    OTHER = "other"
    UNKNOWN = "unknown"


class CaptiveState(StrEnum):
    CAPTIVE = "captive"
    NON_CAPTIVE = "non_captive"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class ComparisonOperator(StrEnum):
    EQ = "eq"
    NEQ = "neq"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"


class ManufacturerPosition(StrEnum):
    EXPLICITLY_REQUIRED = "explicitly_required"
    EXPLICITLY_ENDORSED = "explicitly_endorsed"
    EXPLICITLY_COMPATIBLE = "explicitly_compatible"
    CONTRARY_TO_MANUFACTURER_INSTRUCTION = "contrary_to_manufacturer_instruction"
    EXPLICITLY_PROHIBITED = "explicitly_prohibited"
    NO_STATEMENT = "no_statement"


class TechnicalStatus(StrEnum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    REQUIRES_VERIFICATION = "requires_verification"
    UNRESOLVED = "unresolved"


class PolicyStatus(StrEnum):
    PERMITTED = "permitted"
    PROHIBITED = "prohibited"
    UNRESOLVED = "unresolved"


class EligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNRESOLVED = "unresolved"


class ToolInterfaceFeature(BaseModel):
    """One concrete physical feature on a resolved tool.

    Each eligibility path is evaluated against one instance of this model. Facts
    from separate features must never be combined implicitly.
    """

    feature_id: str
    feature_kind: FeatureKind
    feature_role: FeatureRole = FeatureRole.UNKNOWN
    captive_state: CaptiveState = CaptiveState.UNKNOWN
    location_description: str | None = None
    dimensions_mm: dict[str, float] = Field(default_factory=dict)
    attributes: dict[str, ScalarValue] = Field(default_factory=dict)

    @field_validator("dimensions_mm", mode="before")
    @classmethod
    def validate_dimensions_mm(cls, dimensions: Any) -> Any:
        """Reject malformed physical measurements at the model boundary."""
        if not isinstance(dimensions, dict):
            return dimensions
        for key, value in dimensions.items():
            numeric = _coerce_finite_number(
                value,
                error_message=f"dimension {key!r} must be a finite positive number",
            )
            if numeric <= 0:
                raise ValueError(f"dimension {key!r} must be a finite positive number")
        return dimensions


class FeaturePredicate(BaseModel):
    """One predicate scoped to a single bound ToolInterfaceFeature.

    `property_key` is intentionally limited to feature-local fields. Dimension and
    additional normalized attributes use explicit prefixes rather than arbitrary
    object traversal:

    - `feature_kind`
    - `feature_role`
    - `captive_state`
    - `location_description`
    - `dimension:<dimension_type_code>`
    - `attribute:<attribute_code>`
    """

    property_key: str
    operator: ComparisonOperator = ComparisonOperator.EQ
    value: ScalarValue

    @model_validator(mode="after")
    def validate_predicate(self) -> "FeaturePredicate":
        allowed = {
            "feature_kind",
            "feature_role",
            "captive_state",
            "location_description",
        }
        is_dimension = self.property_key.startswith("dimension:") and len(self.property_key) > len("dimension:")
        is_attribute = self.property_key.startswith("attribute:") and len(self.property_key) > len("attribute:")

        if self.property_key not in allowed and not is_dimension and not is_attribute:
            raise ValueError(f"unsupported feature-local property_key: {self.property_key}")

        if is_dimension or self.operator in _ORDERED_OPERATORS:
            _coerce_finite_number(
                self.value,
                error_message="ordered predicate value must be a finite non-boolean number",
            )

        return self


class EligibilityPath(BaseModel):
    """AND predicates evaluated against one bound feature instance."""

    binding_name: str = "feature"
    requirements: list[FeaturePredicate] = Field(default_factory=list)
    prohibitions: list[FeaturePredicate] = Field(default_factory=list)


class AttachmentEligibility(BaseModel):
    """Bounded OR-of-AND feature eligibility.

    Any path may satisfy eligibility. Every requirement and prohibition inside a
    path is evaluated against the same ToolInterfaceFeature instance.
    """

    paths: list[EligibilityPath]

    @model_validator(mode="after")
    def require_paths(self) -> "AttachmentEligibility":
        if not self.paths:
            raise ValueError("attachment eligibility requires at least one path")
        return self


class EligibilityMatch(BaseModel):
    path_index: int
    binding_name: str
    feature_id: str


class EligibilityEvaluation(BaseModel):
    status: EligibilityStatus
    matches: list[EligibilityMatch] = Field(default_factory=list)

    @property
    def eligible(self) -> bool:
        return self.status == EligibilityStatus.ELIGIBLE


class ManufacturerAssessment(BaseModel):
    """One issuer-scoped manufacturer statement about a candidate configuration."""

    issuer_manufacturer: str
    scope: str
    position: ManufacturerPosition
    claim_or_evidence_ref: str | None = None


class CandidateAssessment(BaseModel):
    """Compatibility result dimensions kept deliberately independent."""

    technical_status: TechnicalStatus
    manufacturer_assessments: list[ManufacturerAssessment] = Field(default_factory=list)
    policy_status: PolicyStatus = PolicyStatus.UNRESOLVED


def evaluate_attachment_eligibility(
    eligibility: AttachmentEligibility,
    features: list[ToolInterfaceFeature],
) -> EligibilityEvaluation:
    matches: list[EligibilityMatch] = []
    saw_unresolved = False

    for path_index, path in enumerate(eligibility.paths):
        for feature in features:
            path_result = _evaluate_path(path, feature)
            if path_result == _PredicateResult.MATCH:
                matches.append(
                    EligibilityMatch(
                        path_index=path_index,
                        binding_name=path.binding_name,
                        feature_id=feature.feature_id,
                    )
                )
            elif path_result == _PredicateResult.UNRESOLVED:
                saw_unresolved = True

    if matches:
        status = EligibilityStatus.ELIGIBLE
    elif saw_unresolved:
        status = EligibilityStatus.UNRESOLVED
    else:
        status = EligibilityStatus.INELIGIBLE

    return EligibilityEvaluation(status=status, matches=matches)


def _evaluate_path(path: EligibilityPath, feature: ToolInterfaceFeature) -> "_PredicateResult":
    requirement_results = [_predicate_result(feature, predicate) for predicate in path.requirements]

    if _PredicateResult.MISMATCH in requirement_results:
        return _PredicateResult.MISMATCH

    prohibition_results = [_predicate_result(feature, predicate) for predicate in path.prohibitions]

    if _PredicateResult.MATCH in prohibition_results:
        return _PredicateResult.MISMATCH

    if (
        _PredicateResult.UNRESOLVED in requirement_results
        or _PredicateResult.UNRESOLVED in prohibition_results
    ):
        return _PredicateResult.UNRESOLVED

    return _PredicateResult.MATCH


def _predicate_result(feature: ToolInterfaceFeature, predicate: FeaturePredicate) -> "_PredicateResult":
    actual = _feature_value(feature, predicate.property_key)
    if actual is _MISSING:
        return _PredicateResult.UNRESOLVED
    return _compare(actual, predicate.operator, predicate.value)


def _feature_value(feature: ToolInterfaceFeature, property_key: str) -> Any:
    if property_key == "feature_kind":
        return feature.feature_kind.value
    if property_key == "feature_role":
        return _MISSING if feature.feature_role == FeatureRole.UNKNOWN else feature.feature_role.value
    if property_key == "captive_state":
        return _MISSING if feature.captive_state == CaptiveState.UNKNOWN else feature.captive_state.value
    if property_key == "location_description":
        return feature.location_description if feature.location_description is not None else _MISSING
    if property_key.startswith("dimension:"):
        return feature.dimensions_mm.get(property_key.removeprefix("dimension:"), _MISSING)
    if property_key.startswith("attribute:"):
        return feature.attributes.get(property_key.removeprefix("attribute:"), _MISSING)
    return _MISSING


def _compare(actual: Any, operator: ComparisonOperator, expected: ScalarValue) -> "_PredicateResult":
    if _is_nonfinite_number(actual) or _is_nonfinite_number(expected):
        return _PredicateResult.UNRESOLVED

    if operator == ComparisonOperator.EQ:
        return _PredicateResult.MATCH if actual == expected else _PredicateResult.MISMATCH
    if operator == ComparisonOperator.NEQ:
        return _PredicateResult.MATCH if actual != expected else _PredicateResult.MISMATCH

    if not _is_orderable_number(actual) or not _is_orderable_number(expected):
        return _PredicateResult.UNRESOLVED

    if operator == ComparisonOperator.LT:
        matched = actual < expected
    elif operator == ComparisonOperator.LTE:
        matched = actual <= expected
    elif operator == ComparisonOperator.GT:
        matched = actual > expected
    elif operator == ComparisonOperator.GTE:
        matched = actual >= expected
    else:
        return _PredicateResult.UNRESOLVED

    return _PredicateResult.MATCH if matched else _PredicateResult.MISMATCH


def _coerce_finite_number(value: Any, *, error_message: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(error_message)
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(error_message) from exc
    if not math.isfinite(numeric):
        raise ValueError(error_message)
    return numeric


def _is_orderable_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and not _is_nonfinite_number(value)


def _is_nonfinite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return not math.isfinite(float(value))
    except OverflowError:
        return True


class _PredicateResult(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNRESOLVED = "unresolved"


_ORDERED_OPERATORS = {
    ComparisonOperator.LT,
    ComparisonOperator.LTE,
    ComparisonOperator.GT,
    ComparisonOperator.GTE,
}

_MISSING = object()
