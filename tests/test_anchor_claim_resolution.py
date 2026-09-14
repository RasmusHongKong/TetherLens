import pytest

from tetherlens_ingest.anchor_claim_resolution import (
    AnchorClaimResolutionError,
    resolve_anchor_attachment_installation_rule,
)
from tetherlens_ingest.compatibility import ComparisonOperator
from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ConstraintOperator,
)


SOURCE = "https://manufacturer.example/anchor"


def _claim(
    property_key: str,
    value,
    *,
    subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT,
    subject_ref: str = "self",
    operator: ConstraintOperator | None = None,
) -> CandidateClaim:
    return CandidateClaim(
        subject_type=subject_type,
        subject_ref=subject_ref,
        property_key=property_key,
        value=value,
        source_url=SOURCE,
        extractor="test",
        constraint_operator=operator,
    )


def test_anchor_rule_compiler_fails_closed_on_conflicting_feature_kind_within_one_path():
    claims = [
        _claim("anchor_installation.method", "wrap"),
        _claim(
            "anchor_installation.feature_kind",
            "beam",
            subject_type=ClaimSubjectType.ANCHOR_INSTALLATION_PATH,
            subject_ref="same-path",
        ),
        _claim(
            "anchor_installation.feature_kind",
            "rail",
            subject_type=ClaimSubjectType.ANCHOR_INSTALLATION_PATH,
            subject_ref="same-path",
        ),
    ]

    with pytest.raises(AnchorClaimResolutionError, match="conflicting accepted anchor claims"):
        resolve_anchor_attachment_installation_rule(
            claims,
            source_product_ref="manufacturer:anchor",
        )


def test_anchor_rule_compiler_keeps_different_feature_kinds_as_explicit_or_paths():
    claims = [
        _claim("anchor_installation.method", "wrap"),
        _claim(
            "anchor_installation.feature_kind",
            "beam",
            subject_type=ClaimSubjectType.ANCHOR_INSTALLATION_PATH,
            subject_ref="beam",
        ),
        _claim(
            "anchor_installation.feature_kind",
            "rail",
            subject_type=ClaimSubjectType.ANCHOR_INSTALLATION_PATH,
            subject_ref="rail",
        ),
    ]

    rule = resolve_anchor_attachment_installation_rule(
        claims,
        source_product_ref="manufacturer:anchor",
    )

    assert rule is not None
    assert [path.binding_name for path in rule.paths] == ["beam", "rail"]


def test_anchor_rule_compiler_maps_requires_to_equality_requirement():
    claims = [
        _claim("anchor_installation.method", "thread_over"),
        _claim(
            "anchor_installation.feature_kind",
            "belt",
            subject_type=ClaimSubjectType.ANCHOR_INSTALLATION_PATH,
            subject_ref="belt",
        ),
        _claim(
            "anchor_installation.attribute.open_for_threading",
            True,
            subject_type=ClaimSubjectType.ANCHOR_INSTALLATION_PATH,
            subject_ref="belt",
            operator=ConstraintOperator.REQUIRES,
        ),
    ]

    rule = resolve_anchor_attachment_installation_rule(
        claims,
        source_product_ref="manufacturer:anchor",
    )

    assert rule is not None
    assert rule.paths[0].prohibitions == []
    requirement = next(
        predicate
        for predicate in rule.paths[0].requirements
        if predicate.property_key == "attribute:open_for_threading"
    )
    assert requirement.operator == ComparisonOperator.EQ
    assert requirement.value is True
