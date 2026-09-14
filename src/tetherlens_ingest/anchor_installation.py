from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .compatibility import ComparisonOperator, EligibilityStatus, ScalarValue


class PrimaryAnchorFeatureKind(StrEnum):
    """Small evidence-led vocabulary for concrete primary-anchor features."""

    BELT = "belt"
    BEAM = "beam"
    RAIL = "rail"


class AnchorInstallationMethod(StrEnum):
    """Primary mechanism retaining an AnchorAttachment on its selected anchor feature."""

    WRAP = "wrap"
    CINCH = "cinch"
    THREAD_OVER = "thread_over"


class PrimaryAnchorFeature(BaseModel):
    """One concrete feature on a resolved primary anchor.

    This is deliberately separate from ``ToolInterfaceFeature``. Anchor installation
    evidence currently needs only an evidence-led structural kind plus optional local
    dimensions/attributes. Facts from separate feature instances must never be stitched
    together to satisfy one installation path.
    """

    feature_id: str = Field(min_length=1)
    feature_kind: PrimaryAnchorFeatureKind
    location_description: str | None = None
    dimensions_mm: dict[str, float] = Field(default_factory=dict)
    attributes: dict[str, ScalarValue] = Field(default_factory=dict)

    @field_validator("dimensions_mm", mode="before")
    @classmethod
    def validate_dimensions_mm(cls, dimensions: Any) -> Any:
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


class ResolvedPrimaryAnchor(BaseModel):
    """Resolved runtime anchor identity plus concrete installation features."""

    primary_anchor_ref: str = Field(min_length=1)
    features: list[PrimaryAnchorFeature] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_feature_identity(self) -> ResolvedPrimaryAnchor:
        ids = [feature.feature_id for feature in self.features]
        duplicates = sorted({feature_id for feature_id in ids if ids.count(feature_id) > 1})
        if duplicates:
            raise ValueError(
                "primary-anchor feature ids must be unique within one resolved anchor: "
                f"{duplicates!r}"
            )
        return self


class AnchorFeaturePredicate(BaseModel):
    """One predicate evaluated against one bound PrimaryAnchorFeature."""

    property_key: str
    operator: ComparisonOperator = ComparisonOperator.EQ
    value: ScalarValue

    @model_validator(mode="after")
    def validate_predicate(self) -> AnchorFeaturePredicate:
        allowed = {"feature_kind", "location_description"}
        is_dimension = self.property_key.startswith("dimension:") and len(
            self.property_key
        ) > len("dimension:")
        is_attribute = self.property_key.startswith("attribute:") and len(
            self.property_key
        ) > len("attribute:")
        if self.property_key not in allowed and not is_dimension and not is_attribute:
            raise ValueError(
                f"unsupported primary-anchor feature property_key: {self.property_key}"
            )
        if self.property_key == "feature_kind":
            valid_feature_kinds = {kind.value for kind in PrimaryAnchorFeatureKind}
            if not isinstance(self.value, str) or self.value not in valid_feature_kinds:
                raise ValueError(
                    "feature_kind predicate value must be a valid primary-anchor feature kind"
                )
        if is_dimension or self.operator in _ORDERED_OPERATORS:
            _coerce_finite_number(
                self.value,
                error_message="ordered predicate value must be a finite non-boolean number",
            )
        return self


class AnchorEligibilityPath(BaseModel):
    """AND predicates evaluated against one primary-anchor feature instance."""

    binding_name: str = Field(default="primary_anchor_feature", min_length=1)
    requirements: list[AnchorFeaturePredicate] = Field(default_factory=list)
    prohibitions: list[AnchorFeaturePredicate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_non_empty_predicates(self) -> AnchorEligibilityPath:
        if not self.requirements and not self.prohibitions:
            raise ValueError(
                "anchor eligibility paths require at least one requirement or prohibition"
            )
        return self


class AnchorAttachmentInstallationRule(BaseModel):
    """Evidence-backed installation scope for one AnchorAttachment product.

    The rule is manufacturer-neutral: product identity scopes the source constraints,
    while executable paths describe only the normalized primary-anchor feature facts
    actually established by accepted evidence.
    """

    rule_id: str = Field(min_length=1)
    source_product_ref: str = Field(min_length=1)
    installation_method: AnchorInstallationMethod
    paths: list[AnchorEligibilityPath] = Field(min_length=1)
    source_urls: list[str] = Field(min_length=1)

    @field_validator("source_urls", mode="before")
    @classmethod
    def validate_source_urls(cls, source_urls: Any) -> Any:
        return _normalize_source_urls(source_urls)


class AnchorEligibilityMatch(BaseModel):
    path_index: int = Field(ge=0)
    binding_name: str = Field(min_length=1)
    feature_id: str = Field(min_length=1)


class AnchorInstallationEligibilityEvaluation(BaseModel):
    """Eligibility result plus the exact rule/anchor provenance evaluated."""

    status: EligibilityStatus
    matches: list[AnchorEligibilityMatch] = Field(default_factory=list)
    rule_id: str = Field(min_length=1)
    source_product_ref: str = Field(min_length=1)
    primary_anchor_ref: str = Field(min_length=1)
    installation_method: AnchorInstallationMethod
    source_urls: list[str] = Field(min_length=1)

    @field_validator("source_urls", mode="before")
    @classmethod
    def validate_source_urls(cls, source_urls: Any) -> Any:
        return _normalize_source_urls(source_urls)

    @property
    def eligible(self) -> bool:
        return self.status == EligibilityStatus.ELIGIBLE


class AnchorEligibilityProof(BaseModel):
    path_index: int = Field(ge=0)
    binding_name: str = Field(min_length=1)


class AnchorInstallationBinding(BaseModel):
    """One concrete AnchorAttachment installation bound to one primary-anchor feature."""

    primary_anchor_ref: str = Field(min_length=1)
    installation_feature_id: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    source_product_ref: str = Field(min_length=1)
    installation_method: AnchorInstallationMethod
    eligibility_proofs: list[AnchorEligibilityProof] = Field(min_length=1)
    source_urls: list[str] = Field(min_length=1)

    @field_validator("source_urls", mode="before")
    @classmethod
    def validate_source_urls(cls, source_urls: Any) -> Any:
        return _normalize_source_urls(source_urls)


def evaluate_anchor_installation_eligibility(
    rule: AnchorAttachmentInstallationRule,
    anchor: ResolvedPrimaryAnchor,
) -> AnchorInstallationEligibilityEvaluation:
    """Evaluate one AnchorAttachment rule against concrete primary-anchor features."""

    matches: list[AnchorEligibilityMatch] = []
    saw_unresolved = False

    for path_index, path in enumerate(rule.paths):
        for feature in anchor.features:
            path_result = _evaluate_path(path, feature)
            if path_result == _PredicateResult.MATCH:
                matches.append(
                    AnchorEligibilityMatch(
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

    return AnchorInstallationEligibilityEvaluation(
        status=status,
        matches=matches,
        rule_id=rule.rule_id,
        source_product_ref=rule.source_product_ref,
        primary_anchor_ref=anchor.primary_anchor_ref,
        installation_method=rule.installation_method,
        source_urls=list(rule.source_urls),
    )


def resolve_anchor_installation_bindings(
    rule: AnchorAttachmentInstallationRule,
    anchor: ResolvedPrimaryAnchor,
) -> list[AnchorInstallationBinding]:
    """Return one deterministic binding per eligible primary-anchor feature.

    Multiple eligibility paths proving the same concrete feature are retained as audit
    proofs on one physical binding rather than creating duplicate installation options.
    """

    evaluation = evaluate_anchor_installation_eligibility(rule, anchor)
    if not evaluation.eligible:
        return []

    grouped: dict[str, list[AnchorEligibilityMatch]] = {}
    for match in evaluation.matches:
        grouped.setdefault(match.feature_id, []).append(match)

    bindings: list[AnchorInstallationBinding] = []
    for feature_id in sorted(grouped):
        matches = sorted(
            grouped[feature_id],
            key=lambda match: (match.path_index, match.binding_name),
        )
        bindings.append(
            AnchorInstallationBinding(
                primary_anchor_ref=anchor.primary_anchor_ref,
                installation_feature_id=feature_id,
                rule_id=rule.rule_id,
                source_product_ref=rule.source_product_ref,
                installation_method=rule.installation_method,
                eligibility_proofs=[
                    AnchorEligibilityProof(
                        path_index=match.path_index,
                        binding_name=match.binding_name,
                    )
                    for match in matches
                ],
                source_urls=list(rule.source_urls),
            )
        )
    return bindings


def bound_anchor_installation_evaluation(
    binding: AnchorInstallationBinding,
) -> AnchorInstallationEligibilityEvaluation:
    """Project a resolved binding into the exact eligibility result retained downstream."""

    return AnchorInstallationEligibilityEvaluation(
        status=EligibilityStatus.ELIGIBLE,
        matches=[
            AnchorEligibilityMatch(
                path_index=proof.path_index,
                binding_name=proof.binding_name,
                feature_id=binding.installation_feature_id,
            )
            for proof in binding.eligibility_proofs
        ],
        rule_id=binding.rule_id,
        source_product_ref=binding.source_product_ref,
        primary_anchor_ref=binding.primary_anchor_ref,
        installation_method=binding.installation_method,
        source_urls=list(binding.source_urls),
    )


def _evaluate_path(
    path: AnchorEligibilityPath,
    feature: PrimaryAnchorFeature,
) -> _PredicateResult:
    requirement_results = [
        _predicate_result(feature, predicate) for predicate in path.requirements
    ]
    if _PredicateResult.MISMATCH in requirement_results:
        return _PredicateResult.MISMATCH

    prohibition_results = [
        _predicate_result(feature, predicate) for predicate in path.prohibitions
    ]
    if _PredicateResult.MATCH in prohibition_results:
        return _PredicateResult.MISMATCH

    if (
        _PredicateResult.UNRESOLVED in requirement_results
        or _PredicateResult.UNRESOLVED in prohibition_results
    ):
        return _PredicateResult.UNRESOLVED
    return _PredicateResult.MATCH


def _predicate_result(
    feature: PrimaryAnchorFeature,
    predicate: AnchorFeaturePredicate,
) -> _PredicateResult:
    actual = _feature_value(feature, predicate.property_key)
    if actual is _MISSING:
        return _PredicateResult.UNRESOLVED
    return _compare(actual, predicate.operator, predicate.value)


def _feature_value(feature: PrimaryAnchorFeature, property_key: str) -> Any:
    if property_key == "feature_kind":
        return feature.feature_kind.value
    if property_key == "location_description":
        return (
            feature.location_description
            if feature.location_description is not None
            else _MISSING
        )
    if property_key.startswith("dimension:"):
        return feature.dimensions_mm.get(
            property_key.removeprefix("dimension:"),
            _MISSING,
        )
    if property_key.startswith("attribute:"):
        return feature.attributes.get(
            property_key.removeprefix("attribute:"),
            _MISSING,
        )
    return _MISSING


def _compare(
    actual: Any,
    operator: ComparisonOperator,
    expected: ScalarValue,
) -> _PredicateResult:
    if _is_nonfinite_number(actual) or _is_nonfinite_number(expected):
        return _PredicateResult.UNRESOLVED
    if operator == ComparisonOperator.EQ:
        matched = _scalar_values_equal(actual, expected)
        return _PredicateResult.MATCH if matched else _PredicateResult.MISMATCH
    if operator == ComparisonOperator.NEQ:
        matched = not _scalar_values_equal(actual, expected)
        return _PredicateResult.MATCH if matched else _PredicateResult.MISMATCH
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


def _scalar_values_equal(actual: Any, expected: ScalarValue) -> bool:
    if isinstance(actual, bool) != isinstance(expected, bool):
        return False
    return actual == expected


def _normalize_source_urls(source_urls: Any) -> Any:
    if not isinstance(source_urls, list):
        return source_urls
    normalized: list[str] = []
    for source_url in source_urls:
        if not isinstance(source_url, str):
            raise ValueError("anchor installation source URLs must be nonblank strings")
        stripped = source_url.strip()
        if not stripped:
            raise ValueError("anchor installation source URLs must be nonblank strings")
        normalized.append(stripped)
    return normalized


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
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and not _is_nonfinite_number(value)
    )


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
