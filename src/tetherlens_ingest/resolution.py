from __future__ import annotations

from collections import defaultdict

from .compatibility import (
    AttachmentEligibility,
    CaptiveState,
    EligibilityPath,
    FeatureKind,
    FeaturePredicate,
    FeatureRole,
    ToolInterfaceFeature,
)
from .models import CandidateClaim, ClaimSubjectType
from .normalize import length_to_mm


FEATURE_KIND_KEY = "feature.kind"
FEATURE_ROLE_KEY = "feature.role"
FEATURE_CAPTIVE_STATE_KEY = "feature.captive_state"
FEATURE_LOCATION_KEY = "feature.location_description"
FEATURE_DIMENSION_PREFIX = "feature.dimension."
FEATURE_ATTRIBUTE_PREFIX = "feature.attribute."
ATTACHMENT_SELECTION_CLASS_KEY = "attachment_selection_class"


class ClaimResolutionError(ValueError):
    """Accepted claims are internally inconsistent or unsupported for resolution."""


def resolve_tool_interface_features(claims: list[CandidateClaim]) -> list[ToolInterfaceFeature]:
    """Resolve accepted feature-scoped claims into runtime tool features.

    This function deliberately does not decide which candidate claims are accepted.
    Callers must pass only reconciled/accepted claims. Feature identity is carried by
    ``subject_ref`` so facts from separate physical features cannot be combined.
    """

    grouped: dict[str, list[CandidateClaim]] = defaultdict(list)
    for claim in claims:
        if claim.subject_type != ClaimSubjectType.PHYSICAL_INTERFACE:
            continue
        if not _is_feature_claim(claim.property_key):
            continue
        grouped[claim.subject_ref].append(claim)

    features: list[ToolInterfaceFeature] = []
    for feature_id, feature_claims in grouped.items():
        kind_claim = _single_claim(feature_claims, FEATURE_KIND_KEY)
        if kind_claim is None:
            # A physical-interface subject is not a ToolInterfaceFeature until its
            # normalized geometry has been established.
            continue

        role_claim = _single_claim(feature_claims, FEATURE_ROLE_KEY)
        captive_claim = _single_claim(feature_claims, FEATURE_CAPTIVE_STATE_KEY)
        location_claim = _single_claim(feature_claims, FEATURE_LOCATION_KEY)

        dimensions_mm: dict[str, float] = {}
        attributes: dict[str, str | int | float | bool] = {}
        for claim in feature_claims:
            if claim.property_key.startswith(FEATURE_DIMENSION_PREFIX):
                code = claim.property_key.removeprefix(FEATURE_DIMENSION_PREFIX)
                if not code:
                    continue
                dimensions_mm[code] = _dimension_to_mm(claim)
            elif claim.property_key.startswith(FEATURE_ATTRIBUTE_PREFIX):
                code = claim.property_key.removeprefix(FEATURE_ATTRIBUTE_PREFIX)
                if not code:
                    continue
                _set_unique(attributes, code, claim.value, feature_id)

        features.append(
            ToolInterfaceFeature(
                feature_id=feature_id,
                feature_kind=FeatureKind(str(kind_claim.value)),
                feature_role=(
                    FeatureRole(str(role_claim.value))
                    if role_claim is not None
                    else FeatureRole.UNKNOWN
                ),
                captive_state=(
                    CaptiveState(str(captive_claim.value))
                    if captive_claim is not None
                    else CaptiveState.UNKNOWN
                ),
                location_description=(
                    str(location_claim.value) if location_claim is not None else None
                ),
                dimensions_mm=dimensions_mm,
                attributes=attributes,
            )
        )

    return features


def resolve_attachment_eligibility(claims: list[CandidateClaim]) -> AttachmentEligibility | None:
    """Compile accepted attachment semantics into reusable feature eligibility.

    The first supported selection class is intentionally geometry-led and reusable:
    a captive-feature attachment can install on one captive handle OR one captive
    through-opening. No tool or attachment SKU participates in this compilation.
    """

    selection = _single_claim(claims, ATTACHMENT_SELECTION_CLASS_KEY)
    if selection is None:
        return None

    if selection.value == "captive_feature_attachment":
        return AttachmentEligibility(
            paths=[
                EligibilityPath(
                    binding_name="handle",
                    requirements=[
                        FeaturePredicate(property_key="feature_kind", value="handle"),
                        FeaturePredicate(property_key="captive_state", value="captive"),
                    ],
                ),
                EligibilityPath(
                    binding_name="opening",
                    requirements=[
                        FeaturePredicate(property_key="feature_kind", value="through_opening"),
                        FeaturePredicate(property_key="captive_state", value="captive"),
                    ],
                ),
            ]
        )

    raise ClaimResolutionError(
        f"unsupported attachment selection class: {selection.value!r}"
    )


def _is_feature_claim(property_key: str) -> bool:
    return property_key in {
        FEATURE_KIND_KEY,
        FEATURE_ROLE_KEY,
        FEATURE_CAPTIVE_STATE_KEY,
        FEATURE_LOCATION_KEY,
    } or property_key.startswith((FEATURE_DIMENSION_PREFIX, FEATURE_ATTRIBUTE_PREFIX))


def _single_claim(
    claims: list[CandidateClaim],
    property_key: str,
) -> CandidateClaim | None:
    matches = [claim for claim in claims if claim.property_key == property_key]
    if not matches:
        return None

    normalized_values = {(str(claim.value), claim.unit or "") for claim in matches}
    if len(normalized_values) > 1:
        subjects = sorted({claim.subject_ref for claim in matches})
        raise ClaimResolutionError(
            f"conflicting accepted claims for {property_key!r} on {subjects}: "
            f"{sorted(normalized_values)!r}"
        )
    return matches[0]


def _dimension_to_mm(claim: CandidateClaim) -> float:
    if isinstance(claim.value, bool) or not isinstance(claim.value, (int, float)):
        raise ClaimResolutionError(
            f"feature dimension {claim.property_key!r} must be numeric"
        )
    if claim.unit is None:
        raise ClaimResolutionError(
            f"feature dimension {claim.property_key!r} requires a unit"
        )
    try:
        return float(length_to_mm(float(claim.value), claim.unit))
    except ValueError as exc:
        raise ClaimResolutionError(str(exc)) from exc


def _set_unique(
    target: dict[str, str | int | float | bool],
    key: str,
    value: str | int | float | bool,
    feature_id: str,
) -> None:
    if key in target and target[key] != value:
        raise ClaimResolutionError(
            f"conflicting accepted feature attribute {key!r} on {feature_id!r}"
        )
    target[key] = value
