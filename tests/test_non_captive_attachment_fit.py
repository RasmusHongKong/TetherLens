import pytest

from tetherlens_ingest.compatibility import (
    CaptiveState,
    EligibilityStatus,
    FeatureKind,
    ToolInterfaceFeature,
    evaluate_attachment_eligibility,
)
from tetherlens_ingest.constraints import (
    ProductConstraintContext,
    ProductConstraintDisposition,
    ProductConstraintStatus,
    evaluate_product_constraints,
    resolve_product_constraints,
)
from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimType,
    ConstraintOperator,
)
from tetherlens_ingest.resolution import resolve_attachment_eligibility


_SOURCE = "https://manufacturer.example/install"


def claim(
    key: str,
    value,
    *,
    claim_type: ClaimType | None = None,
    operator: ConstraintOperator | None = None,
) -> CandidateClaim:
    return CandidateClaim(
        property_key=key,
        value=value,
        raw_value=f"{key}={value}",
        source_url=_SOURCE,
        extractor="test.non_captive_fit.v1",
        claim_type=claim_type,
        constraint_operator=operator,
    )


def test_handle_selection_class_accepts_handle_without_requiring_captive_state() -> None:
    eligibility = resolve_attachment_eligibility(
        [claim("attachment_selection_class", "handle_attachment")]
    )
    assert eligibility is not None

    result = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="handle:non-captive",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.NON_CAPTIVE,
            ),
            ToolInterfaceFeature(
                feature_id="handle:captive",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.CAPTIVE,
            ),
            ToolInterfaceFeature(
                feature_id="handle:unknown",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.UNKNOWN,
            ),
            ToolInterfaceFeature(
                feature_id="section:non-captive",
                feature_kind=FeatureKind.EXTERNAL_SECTION,
                captive_state=CaptiveState.NON_CAPTIVE,
            ),
        ],
    )

    assert result.status == EligibilityStatus.ELIGIBLE
    assert [(match.binding_name, match.feature_id) for match in result.matches] == [
        ("handle", "handle:non-captive"),
        ("handle", "handle:captive"),
        ("handle", "handle:unknown"),
    ]


def test_handle_selection_class_does_not_widen_to_external_section() -> None:
    eligibility = resolve_attachment_eligibility(
        [claim("attachment_selection_class", "handle_attachment")]
    )
    assert eligibility is not None

    result = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="section:non-captive",
                feature_kind=FeatureKind.EXTERNAL_SECTION,
                captive_state=CaptiveState.NON_CAPTIVE,
            )
        ],
    )

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.matches == []


def test_handle_selection_class_contains_no_inferred_state_or_fit_requirement() -> None:
    eligibility = resolve_attachment_eligibility(
        [claim("attachment_selection_class", "handle_attachment")]
    )
    assert eligibility is not None

    requirement_keys = [
        predicate.property_key
        for predicate in eligibility.paths[0].requirements
    ]
    assert requirement_keys == ["feature_kind"]
    assert "captive_state" not in requirement_keys
    assert not any(key.startswith("dimension:") for key in requirement_keys)


def test_secure_attachment_fit_resolves_as_distinct_pre_use_obligation() -> None:
    constraints = resolve_product_constraints(
        [
            claim(
                "secure_attachment_fit_required",
                True,
                claim_type=ClaimType.DECLARED_CONSTRAINT,
                operator=ConstraintOperator.REQUIRES,
            )
        ],
        source_product_ref="attachment:generic",
    )

    assert len(constraints) == 1
    constraint = constraints[0]
    assert constraint.constraint_key == "secure_attachment_fit_required"
    assert constraint.disposition == ProductConstraintDisposition.PRE_USE_OBLIGATION

    pending = evaluate_product_constraints([constraint], ProductConstraintContext())[0]
    passed = evaluate_product_constraints(
        [constraint],
        ProductConstraintContext(secure_attachment_fit_confirmed=True),
    )[0]
    failed = evaluate_product_constraints(
        [constraint],
        ProductConstraintContext(secure_attachment_fit_confirmed=False),
    )[0]

    assert pending.status == ProductConstraintStatus.REQUIRES_ACTION
    assert passed.status == ProductConstraintStatus.PASSED
    assert failed.status == ProductConstraintStatus.FAILED


def test_secure_fit_confirmation_does_not_satisfy_separate_attachment_test() -> None:
    constraints = resolve_product_constraints(
        [
            claim(
                "secure_attachment_fit_required",
                True,
                claim_type=ClaimType.DECLARED_CONSTRAINT,
                operator=ConstraintOperator.REQUIRES,
            ),
            claim(
                "pre_use_attachment_test_required",
                True,
                claim_type=ClaimType.DECLARED_CONSTRAINT,
                operator=ConstraintOperator.REQUIRES,
            ),
        ],
        source_product_ref="attachment:generic",
    )

    by_key = {
        evaluation.constraint_key: evaluation
        for evaluation in evaluate_product_constraints(
            constraints,
            ProductConstraintContext(secure_attachment_fit_confirmed=True),
        )
    }

    assert by_key["secure_attachment_fit_required"].status == ProductConstraintStatus.PASSED
    assert (
        by_key["pre_use_attachment_test_required"].status
        == ProductConstraintStatus.REQUIRES_ACTION
    )


@pytest.mark.parametrize("invalid", ["true", 1, 0])
def test_secure_attachment_fit_constraint_requires_boolean_source_value(invalid) -> None:
    with pytest.raises(ValueError, match="secure_attachment_fit_required must be boolean"):
        resolve_product_constraints(
            [
                claim(
                    "secure_attachment_fit_required",
                    invalid,
                    claim_type=ClaimType.DECLARED_CONSTRAINT,
                    operator=ConstraintOperator.REQUIRES,
                )
            ],
            source_product_ref="attachment:generic",
        )
