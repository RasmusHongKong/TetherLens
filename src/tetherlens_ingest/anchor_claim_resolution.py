from __future__ import annotations

from collections import defaultdict

from .anchor_installation import (
    AnchorAttachmentInstallationRule,
    AnchorEligibilityPath,
    AnchorFeaturePredicate,
    AnchorInstallationMethod,
)
from .compatibility import ComparisonOperator
from .models import CandidateClaim, ClaimSubjectType, ConstraintOperator
from .normalize import length_to_mm


ANCHOR_INSTALLATION_METHOD_KEY = "anchor_installation.method"
ANCHOR_PATH_FEATURE_KIND_KEY = "anchor_installation.feature_kind"
ANCHOR_PATH_LOCATION_KEY = "anchor_installation.location_description"
ANCHOR_PATH_DIMENSION_PREFIX = "anchor_installation.dimension."
ANCHOR_PATH_ATTRIBUTE_PREFIX = "anchor_installation.attribute."


class AnchorClaimResolutionError(ValueError):
    """Accepted anchor-installation claims are incomplete or internally inconsistent."""


def resolve_anchor_attachment_installation_rule(
    claims: list[CandidateClaim],
    *,
    source_product_ref: str,
    rule_id: str | None = None,
) -> AnchorAttachmentInstallationRule | None:
    """Compile accepted ingestion claims into one PR #60 installation rule.

    Adapters emit normalized rule-level installation method evidence plus one or more
    feature-local path subjects. Each path remains an AND-set on one concrete primary
    anchor feature; separate subjects are OR alternatives. This compiler is deliberately
    manufacturer-neutral and never branches on manufacturer or SKU.
    """

    method_claims = [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.PRODUCT
        and claim.property_key == ANCHOR_INSTALLATION_METHOD_KEY
    ]
    if not method_claims:
        return None

    method_value = _single_scalar(method_claims, ANCHOR_INSTALLATION_METHOD_KEY)
    try:
        installation_method = AnchorInstallationMethod(str(method_value))
    except ValueError as exc:
        raise AnchorClaimResolutionError(
            f"unsupported anchor installation method: {method_value!r}"
        ) from exc

    grouped: dict[str, list[CandidateClaim]] = defaultdict(list)
    for claim in claims:
        if claim.subject_type != ClaimSubjectType.ANCHOR_INSTALLATION_PATH:
            continue
        if _is_anchor_path_claim(claim.property_key):
            grouped[claim.subject_ref].append(claim)

    if not grouped:
        raise AnchorClaimResolutionError(
            "anchor installation method requires at least one accepted feature-local path"
        )

    paths: list[AnchorEligibilityPath] = []
    path_source_urls: list[str] = []
    for subject_ref in sorted(grouped):
        path_claims = grouped[subject_ref]
        kind_claims = [
            claim
            for claim in path_claims
            if claim.property_key == ANCHOR_PATH_FEATURE_KIND_KEY
        ]
        if not kind_claims:
            raise AnchorClaimResolutionError(
                f"anchor installation path {subject_ref!r} requires an explicit feature kind"
            )
        _single_scalar(
            kind_claims,
            f"{ANCHOR_PATH_FEATURE_KIND_KEY} on path {subject_ref!r}",
        )

        requirements: list[AnchorFeaturePredicate] = []
        prohibitions: list[AnchorFeaturePredicate] = []
        for claim in path_claims:
            predicate, prohibited = _predicate_from_claim(claim)
            if predicate is None:
                continue
            target = prohibitions if prohibited else requirements
            if predicate not in target:
                target.append(predicate)
            path_source_urls.append(claim.source_url)

        paths.append(
            AnchorEligibilityPath(
                binding_name=subject_ref,
                requirements=requirements,
                prohibitions=prohibitions,
            )
        )

    source_urls = sorted(
        {
            *(claim.source_url.strip() for claim in method_claims if claim.source_url.strip()),
            *(url.strip() for url in path_source_urls if url.strip()),
        }
    )
    if not source_urls:
        raise AnchorClaimResolutionError(
            "anchor installation rule requires nonblank source provenance"
        )

    return AnchorAttachmentInstallationRule(
        rule_id=rule_id or f"anchor-installation:{source_product_ref}",
        source_product_ref=source_product_ref,
        installation_method=installation_method,
        paths=paths,
        source_urls=source_urls,
    )


def _predicate_from_claim(
    claim: CandidateClaim,
) -> tuple[AnchorFeaturePredicate | None, bool]:
    property_key: str
    value = claim.value

    if claim.property_key == ANCHOR_PATH_FEATURE_KIND_KEY:
        property_key = "feature_kind"
    elif claim.property_key == ANCHOR_PATH_LOCATION_KEY:
        property_key = "location_description"
    elif claim.property_key.startswith(ANCHOR_PATH_DIMENSION_PREFIX):
        code = claim.property_key.removeprefix(ANCHOR_PATH_DIMENSION_PREFIX)
        if not code:
            return None, False
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AnchorClaimResolutionError(
                f"anchor dimension {claim.property_key!r} must be numeric"
            )
        if not claim.unit:
            raise AnchorClaimResolutionError(
                f"anchor dimension {claim.property_key!r} requires a unit"
            )
        try:
            value = float(length_to_mm(float(value), claim.unit))
        except ValueError as exc:
            raise AnchorClaimResolutionError(str(exc)) from exc
        property_key = f"dimension:{code}"
    elif claim.property_key.startswith(ANCHOR_PATH_ATTRIBUTE_PREFIX):
        code = claim.property_key.removeprefix(ANCHOR_PATH_ATTRIBUTE_PREFIX)
        if not code:
            return None, False
        property_key = f"attribute:{code}"
    else:
        return None, False

    operator = claim.constraint_operator or ConstraintOperator.EQ
    prohibited = operator == ConstraintOperator.PROHIBITS
    if operator in {ConstraintOperator.PROHIBITS, ConstraintOperator.REQUIRES}:
        comparison = ComparisonOperator.EQ
    else:
        try:
            comparison = ComparisonOperator(operator.value)
        except ValueError as exc:
            raise AnchorClaimResolutionError(
                f"unsupported anchor predicate operator {operator.value!r} on {claim.property_key!r}"
            ) from exc

    return (
        AnchorFeaturePredicate(
            property_key=property_key,
            operator=comparison,
            value=value,
        ),
        prohibited,
    )


def _single_scalar(
    claims: list[CandidateClaim],
    property_key: str,
):
    values = {claim.value for claim in claims}
    if len(values) != 1:
        raise AnchorClaimResolutionError(
            f"conflicting accepted anchor claims for {property_key!r}: {sorted(map(str, values))!r}"
        )
    return next(iter(values))


def _is_anchor_path_claim(property_key: str) -> bool:
    return property_key in {
        ANCHOR_PATH_FEATURE_KIND_KEY,
        ANCHOR_PATH_LOCATION_KEY,
    } or property_key.startswith(
        (ANCHOR_PATH_DIMENSION_PREFIX, ANCHOR_PATH_ATTRIBUTE_PREFIX)
    )
