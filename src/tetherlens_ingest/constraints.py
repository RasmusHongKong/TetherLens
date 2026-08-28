from __future__ import annotations

import math
from collections import defaultdict
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .compatibility import FeatureKind, ToolInterfaceFeature
from .models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ConstraintOperator,
)


ConstraintValue = str | int | float | bool


class ProductConstraintDisposition(StrEnum):
    """How one resolved product constraint participates in recommendation reasoning."""

    HARD = "hard"
    PRE_USE_OBLIGATION = "pre_use_obligation"


class ProductConstraintStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    REQUIRES_ACTION = "requires_action"
    UNRESOLVED = "unresolved"


class ProductConstraintResolutionError(ValueError):
    """Accepted constraint claims are internally inconsistent or malformed."""


class ResolvedProductConstraint(BaseModel):
    """One normalized, reusable constraint resolved from accepted catalogue claims.

    The runtime model intentionally retains the source subject and source URLs while
    avoiding product/SKU-specific semantics. Multiple evidence-equivalent claims are
    coalesced into one runtime constraint with all supporting source URLs retained.
    """

    constraint_id: str = Field(min_length=1)
    subject_type: ClaimSubjectType
    subject_ref: str = Field(min_length=1)
    constraint_key: str = Field(min_length=1)
    operator: ConstraintOperator
    value: ConstraintValue
    unit: str | None = None
    disposition: ProductConstraintDisposition
    source_urls: list[str] = Field(default_factory=list)
    raw_values: list[str] = Field(default_factory=list)


class ProductConstraintContext(BaseModel):
    """Runtime facts needed by the currently supported product-constraint rules.

    Installation facts are deliberately bound to one ToolInterfaceFeature. Callers
    must evaluate another candidate installation location with another context rather
    than combining attributes from separate tool features.

    Current normalized feature attributes consumed by these rules are:

    - ``surface_profile`` -> e.g. ``flat``
    - ``surface_condition.<code>`` -> boolean, e.g. ``surface_condition.clean``
    - ``part_type`` -> e.g. ``removable_cover_or_door``
    """

    installation_feature: ToolInterfaceFeature | None = None
    tether_max_length_mm: float | None = None
    bond_elapsed_h: float | None = None
    pre_use_attachment_test_passed: bool | None = None

    @field_validator("tether_max_length_mm", mode="before")
    @classmethod
    def validate_tether_max_length(cls, value: Any) -> Any:
        return _finite_number_or_none(
            value,
            field_name="tether_max_length_mm",
            allow_zero=False,
        )

    @field_validator("bond_elapsed_h", mode="before")
    @classmethod
    def validate_bond_elapsed(cls, value: Any) -> Any:
        return _finite_number_or_none(
            value,
            field_name="bond_elapsed_h",
            allow_zero=True,
        )


class ProductConstraintEvaluation(BaseModel):
    constraint_id: str
    constraint_key: str
    status: ProductConstraintStatus
    reason: str
    subject_refs: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


# These semantics are intentionally narrow. Other declared constraints remain accepted
# catalogue facts until their technical/manufacturer/policy meaning is explicitly
# modeled rather than being forced through a generic boolean evaluator.
_SUPPORTED_CONSTRAINTS: dict[
    str,
    tuple[ConstraintOperator, ProductConstraintDisposition],
] = {
    "installation_surface_profile": (
        ConstraintOperator.REQUIRES,
        ProductConstraintDisposition.HARD,
    ),
    "required_surface_condition": (
        ConstraintOperator.REQUIRES,
        ProductConstraintDisposition.HARD,
    ),
    "prohibited_tool_part_type": (
        ConstraintOperator.PROHIBITS,
        ProductConstraintDisposition.HARD,
    ),
    "max_lanyard_length_mm": (
        ConstraintOperator.LTE,
        ProductConstraintDisposition.HARD,
    ),
    "minimum_bond_time_h": (
        ConstraintOperator.GTE,
        ProductConstraintDisposition.PRE_USE_OBLIGATION,
    ),
    "pre_use_attachment_test_required": (
        ConstraintOperator.REQUIRES,
        ProductConstraintDisposition.PRE_USE_OBLIGATION,
    ),
}


def resolve_product_constraints(claims: list[CandidateClaim]) -> list[ResolvedProductConstraint]:
    """Resolve supported accepted claims into normalized runtime constraints.

    Callers must pass only accepted/reconciled claims. Unsupported declared constraints
    are deliberately ignored here rather than assigned accidental technical semantics.

    ``max_lanyard_length_mm`` predates structured ``claim_type`` / ``operator`` metadata
    in the NLG adapter. It is accepted as a transitional normalized product limit and
    receives its established ``actual tether max length <= declared max`` semantics.
    All other supported keys require ``claim_type = declared_constraint``.
    """

    grouped: dict[
        tuple[ClaimSubjectType, str, str, ConstraintOperator, str, str],
        list[CandidateClaim],
    ] = defaultdict(list)

    for claim in claims:
        semantic = _SUPPORTED_CONSTRAINTS.get(claim.property_key)
        if semantic is None:
            continue

        expected_operator, _ = semantic
        if claim.property_key == "max_lanyard_length_mm":
            operator = claim.constraint_operator or expected_operator
        else:
            if claim.claim_type != ClaimType.DECLARED_CONSTRAINT:
                continue
            if claim.constraint_operator is None:
                raise ProductConstraintResolutionError(
                    f"declared constraint {claim.property_key!r} is missing its operator"
                )
            operator = claim.constraint_operator

        if operator != expected_operator:
            raise ProductConstraintResolutionError(
                f"unsupported operator {operator.value!r} for {claim.property_key!r}; "
                f"expected {expected_operator.value!r}"
            )

        _validate_constraint_value(claim.property_key, claim.value, claim.unit)
        grouped[
            (
                claim.subject_type,
                claim.subject_ref,
                claim.property_key,
                operator,
                _stable_value_key(claim.value),
                claim.unit or "",
            )
        ].append(claim)

    resolved: list[ResolvedProductConstraint] = []
    for index, (group_key, grouped_claims) in enumerate(
        sorted(grouped.items(), key=lambda item: tuple(str(part) for part in item[0])),
        start=1,
    ):
        subject_type, subject_ref, property_key, operator, _, unit = group_key
        _, disposition = _SUPPORTED_CONSTRAINTS[property_key]
        exemplar = grouped_claims[0]
        resolved.append(
            ResolvedProductConstraint(
                constraint_id=f"{subject_ref}:{property_key}:{index}",
                subject_type=subject_type,
                subject_ref=subject_ref,
                constraint_key=property_key,
                operator=operator,
                value=exemplar.value,
                unit=unit or None,
                disposition=disposition,
                source_urls=_dedupe_strings(claim.source_url for claim in grouped_claims),
                raw_values=_dedupe_strings(
                    claim.raw_value for claim in grouped_claims if claim.raw_value
                ),
            )
        )

    return resolved


def evaluate_product_constraints(
    constraints: list[ResolvedProductConstraint],
    context: ProductConstraintContext,
) -> list[ProductConstraintEvaluation]:
    """Evaluate normalized product constraints against one candidate installation.

    Hard installation constraints fail or remain unresolved when the required runtime
    fact is absent. Pre-use obligations become ``requires_action`` while their required
    action is pending, allowing the candidate to remain conditionally recommendable.
    """

    return [_evaluate_constraint(constraint, context) for constraint in constraints]


def _evaluate_constraint(
    constraint: ResolvedProductConstraint,
    context: ProductConstraintContext,
) -> ProductConstraintEvaluation:
    key = constraint.constraint_key

    if key == "installation_surface_profile":
        feature = context.installation_feature
        if feature is None:
            return _result(
                constraint,
                ProductConstraintStatus.UNRESOLVED,
                "installation surface is required but no bound tool feature is available",
            )
        actual = feature.attributes.get("surface_profile")
        if actual is None:
            return _result(
                constraint,
                ProductConstraintStatus.UNRESOLVED,
                "surface profile is not established for the bound installation feature",
                feature.feature_id,
            )
        if actual == constraint.value:
            return _result(
                constraint,
                ProductConstraintStatus.PASSED,
                f"bound installation feature has required surface profile {constraint.value!r}",
                feature.feature_id,
            )
        return _result(
            constraint,
            ProductConstraintStatus.FAILED,
            f"bound installation feature surface profile {actual!r} does not satisfy "
            f"required profile {constraint.value!r}",
            feature.feature_id,
        )

    if key == "required_surface_condition":
        feature = context.installation_feature
        if feature is None:
            return _result(
                constraint,
                ProductConstraintStatus.UNRESOLVED,
                "installation surface condition is required but no bound tool feature is available",
            )
        attribute_key = f"surface_condition.{constraint.value}"
        actual = feature.attributes.get(attribute_key)
        if actual is None:
            return _result(
                constraint,
                ProductConstraintStatus.UNRESOLVED,
                f"required surface condition {constraint.value!r} is not established "
                "for the bound installation feature",
                feature.feature_id,
            )
        if actual is True:
            return _result(
                constraint,
                ProductConstraintStatus.PASSED,
                f"bound installation feature satisfies surface condition {constraint.value!r}",
                feature.feature_id,
            )
        if actual is False:
            return _result(
                constraint,
                ProductConstraintStatus.FAILED,
                f"bound installation feature does not satisfy surface condition {constraint.value!r}",
                feature.feature_id,
            )
        return _result(
            constraint,
            ProductConstraintStatus.UNRESOLVED,
            f"surface condition {constraint.value!r} must resolve to a boolean runtime fact",
            feature.feature_id,
        )

    if key == "prohibited_tool_part_type":
        feature = context.installation_feature
        if feature is None:
            return _result(
                constraint,
                ProductConstraintStatus.UNRESOLVED,
                "prohibited installation location cannot be checked without a bound tool feature",
            )
        actual = feature.attributes.get("part_type")
        if actual is None:
            return _result(
                constraint,
                ProductConstraintStatus.UNRESOLVED,
                "tool part type is not established for the bound installation feature",
                feature.feature_id,
            )
        if actual == constraint.value:
            return _result(
                constraint,
                ProductConstraintStatus.FAILED,
                f"bound installation feature is prohibited part type {constraint.value!r}",
                feature.feature_id,
            )
        return _result(
            constraint,
            ProductConstraintStatus.PASSED,
            f"bound installation feature part type {actual!r} is not the prohibited "
            f"type {constraint.value!r}",
            feature.feature_id,
        )

    if key == "max_lanyard_length_mm":
        actual = context.tether_max_length_mm
        if actual is None:
            return _result(
                constraint,
                ProductConstraintStatus.UNRESOLVED,
                "tether maximum length is not established for the applicable product limit",
            )
        limit = float(constraint.value)
        if actual <= limit:
            return _result(
                constraint,
                ProductConstraintStatus.PASSED,
                f"tether maximum length {actual:g} mm is within the {limit:g} mm product limit",
            )
        return _result(
            constraint,
            ProductConstraintStatus.FAILED,
            f"tether maximum length {actual:g} mm exceeds the {limit:g} mm product limit",
        )

    if key == "minimum_bond_time_h":
        required = float(constraint.value)
        actual = context.bond_elapsed_h
        if actual is None:
            return _result(
                constraint,
                ProductConstraintStatus.REQUIRES_ACTION,
                f"allow at least {required:g} hours of bond time before use",
            )
        if actual >= required:
            return _result(
                constraint,
                ProductConstraintStatus.PASSED,
                f"elapsed bond time {actual:g} h meets the required {required:g} h minimum",
            )
        return _result(
            constraint,
            ProductConstraintStatus.REQUIRES_ACTION,
            f"bond time is {actual:g} h; wait until at least {required:g} h has elapsed before use",
        )

    if key == "pre_use_attachment_test_required":
        if constraint.value is not True:
            return _result(
                constraint,
                ProductConstraintStatus.UNRESOLVED,
                "pre-use attachment-test constraint has unsupported non-true value",
            )
        passed = context.pre_use_attachment_test_passed
        if passed is None:
            return _result(
                constraint,
                ProductConstraintStatus.REQUIRES_ACTION,
                "perform the manufacturer-required attachment test before use",
            )
        if passed:
            return _result(
                constraint,
                ProductConstraintStatus.PASSED,
                "manufacturer-required pre-use attachment test has passed",
            )
        return _result(
            constraint,
            ProductConstraintStatus.FAILED,
            "manufacturer-required pre-use attachment test failed",
        )

    # Resolution currently emits only supported keys, so reaching this branch means
    # a malformed runtime object was supplied directly rather than resolved normally.
    return _result(
        constraint,
        ProductConstraintStatus.UNRESOLVED,
        f"no runtime evaluator is registered for product constraint {key!r}",
    )


def _result(
    constraint: ResolvedProductConstraint,
    status: ProductConstraintStatus,
    reason: str,
    *subject_refs: str,
) -> ProductConstraintEvaluation:
    return ProductConstraintEvaluation(
        constraint_id=constraint.constraint_id,
        constraint_key=constraint.constraint_key,
        status=status,
        reason=reason,
        subject_refs=list(subject_refs),
        source_urls=list(constraint.source_urls),
    )


def _validate_constraint_value(
    property_key: str,
    value: ConstraintValue,
    unit: str | None,
) -> None:
    if property_key in {"max_lanyard_length_mm", "minimum_bond_time_h"}:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ProductConstraintResolutionError(
                f"numeric constraint {property_key!r} requires a finite positive number"
            )
        numeric = float(value)
        if not math.isfinite(numeric) or numeric <= 0:
            raise ProductConstraintResolutionError(
                f"numeric constraint {property_key!r} requires a finite positive number"
            )
        expected_unit = "mm" if property_key == "max_lanyard_length_mm" else "h"
        if unit not in {None, expected_unit}:
            raise ProductConstraintResolutionError(
                f"constraint {property_key!r} requires unit {expected_unit!r} when a unit is provided"
            )
    elif property_key == "pre_use_attachment_test_required" and not isinstance(value, bool):
        raise ProductConstraintResolutionError(
            "pre_use_attachment_test_required must be boolean"
        )
    elif property_key in {
        "installation_surface_profile",
        "required_surface_condition",
        "prohibited_tool_part_type",
    } and (not isinstance(value, str) or not value.strip()):
        raise ProductConstraintResolutionError(
            f"constraint {property_key!r} requires a non-empty string value"
        )


def _stable_value_key(value: ConstraintValue) -> str:
    return f"{type(value).__name__}:{value!r}"


def _dedupe_strings(values) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values))


def _finite_number_or_none(
    value: Any,
    *,
    field_name: str,
    allow_zero: bool,
) -> Any:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a finite number when provided")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0 or (numeric == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{field_name} must be a finite {qualifier} number when provided")
    return numeric
