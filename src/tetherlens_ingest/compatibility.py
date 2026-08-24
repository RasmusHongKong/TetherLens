from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


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
    UNRESOLVED = "unresolved"


class PolicyStatus(StrEnum):
    PERMITTED = "permitted"
    PROHIBITED = "prohibited"
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
    def validate_property_key(self) -> "FeaturePredicate":
        allowed = {
            "feature_kind",
            "feature_role",
            "captive_state",
            "location_description",
        }
        if self.property_key in allowed:
            return self
        if self.property_key.startswith("dimension:") and len(self.property_key) > len("dimension:"):
            return self
        if self.property_key.startswith("attribute:") and len(self.property_key) > len("attribute:"):
            return self
        raise ValueError(f"unsupported feature-local property_key: {self.property_key}")


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
    eligible: bool
    matches: list[EligibilityMatch] = Field(default_factory=list)


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

    for path_index, path in enumerate(eligibility.paths):
        for feature in features:
            if not all(_predicate_matches(feature, predicate) for predicate in path.requirements):
                continue
            if any(_predicate_matches(feature, predicate) for predicate in path.prohibitions):
                continue
            matches.append(
                EligibilityMatch(
                    path_index=path_index,
                    binding_name=path.binding_name,
                    feature_id=feature.feature_id,
                )
            )

    return EligibilityEvaluation(eligible=bool(matches), matches=matches)


def _predicate_matches(feature: ToolInterfaceFeature, predicate: FeaturePredicate) -> bool:
    actual = _feature_value(feature, predicate.property_key)
    if actual is _MISSING:
        return False
    return _compare(actual, predicate.operator, predicate.value)


def _feature_value(feature: ToolInterfaceFeature, property_key: str) -> Any:
    if property_key == "feature_kind":
        return feature.feature_kind.value
    if property_key == "feature_role":
        return feature.feature_role.value
    if property_key == "captive_state":
        return feature.captive_state.value
    if property_key == "location_description":
        return feature.location_description if feature.location_description is not None else _MISSING
    if property_key.startswith("dimension:"):
        return feature.dimensions_mm.get(property_key.removeprefix("dimension:"), _MISSING)
    if property_key.startswith("attribute:"):
        return feature.attributes.get(property_key.removeprefix("attribute:"), _MISSING)
    return _MISSING


def _compare(actual: Any, operator: ComparisonOperator, expected: ScalarValue) -> bool:
    if operator == ComparisonOperator.EQ:
        return actual == expected
    if operator == ComparisonOperator.NEQ:
        return actual != expected

    if not isinstance(actual, (int, float)) or isinstance(actual, bool):
        return False
    if not isinstance(expected, (int, float)) or isinstance(expected, bool):
        return False

    if operator == ComparisonOperator.LT:
        return actual < expected
    if operator == ComparisonOperator.LTE:
        return actual <= expected
    if operator == ComparisonOperator.GT:
        return actual > expected
    if operator == ComparisonOperator.GTE:
        return actual >= expected
    return False


_MISSING = object()
