import math

import pytest
from pydantic import ValidationError

from tetherlens_ingest.compatibility import (
    AttachmentEligibility,
    CaptiveState,
    CandidateAssessment,
    ComparisonOperator,
    EligibilityPath,
    EligibilityStatus,
    FeatureKind,
    FeaturePredicate,
    ManufacturerAssessment,
    ManufacturerPosition,
    PolicyStatus,
    TechnicalStatus,
    ToolInterfaceFeature,
    evaluate_attachment_eligibility,
)


def captive_feature_rule() -> AttachmentEligibility:
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


def test_captive_handle_path_binds_kind_and_captive_state_to_same_feature():
    features = [
        ToolInterfaceFeature(
            feature_id="handle-1",
            feature_kind=FeatureKind.HANDLE,
            captive_state=CaptiveState.NON_CAPTIVE,
        ),
        ToolInterfaceFeature(
            feature_id="opening-1",
            feature_kind=FeatureKind.THROUGH_OPENING,
            captive_state=CaptiveState.CAPTIVE,
        ),
    ]

    result = evaluate_attachment_eligibility(captive_feature_rule(), features)

    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.eligible is True
    assert {(match.binding_name, match.feature_id) for match in result.matches} == {
        ("opening", "opening-1")
    }


def test_captive_handle_path_matches_one_feature_that_satisfies_both_predicates():
    features = [
        ToolInterfaceFeature(
            feature_id="handle-1",
            feature_kind=FeatureKind.HANDLE,
            captive_state=CaptiveState.CAPTIVE,
        )
    ]

    result = evaluate_attachment_eligibility(captive_feature_rule(), features)

    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.eligible is True
    assert [(match.binding_name, match.feature_id) for match in result.matches] == [
        ("handle", "handle-1")
    ]


def test_unknown_captive_state_makes_matching_geometry_unresolved():
    result = evaluate_attachment_eligibility(
        captive_feature_rule(),
        [ToolInterfaceFeature(feature_id="handle-1", feature_kind=FeatureKind.HANDLE)],
    )

    assert result.status == EligibilityStatus.UNRESOLVED
    assert result.eligible is False
    assert result.matches == []


def test_dimension_requirement_cannot_be_borrowed_from_another_feature():
    rule = AttachmentEligibility(
        paths=[
            EligibilityPath(
                requirements=[
                    FeaturePredicate(property_key="feature_kind", value="through_opening"),
                    FeaturePredicate(
                        property_key="dimension:hole_diameter",
                        operator=ComparisonOperator.GTE,
                        value=8.0,
                    ),
                ]
            )
        ]
    )
    features = [
        ToolInterfaceFeature(
            feature_id="small-opening",
            feature_kind=FeatureKind.THROUGH_OPENING,
            dimensions_mm={"hole_diameter": 5.0},
        ),
        ToolInterfaceFeature(
            feature_id="large-handle",
            feature_kind=FeatureKind.HANDLE,
            dimensions_mm={"hole_diameter": 12.0},
        ),
    ]

    result = evaluate_attachment_eligibility(rule, features)

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.eligible is False
    assert result.matches == []


def test_feature_local_prohibition_only_invalidates_the_bound_feature():
    rule = AttachmentEligibility(
        paths=[
            EligibilityPath(
                requirements=[
                    FeaturePredicate(property_key="feature_kind", value="surface"),
                    FeaturePredicate(property_key="attribute:surface_profile", value="flat"),
                ],
                prohibitions=[
                    FeaturePredicate(property_key="attribute:removable", value=True),
                ],
            )
        ]
    )
    features = [
        ToolInterfaceFeature(
            feature_id="battery-door",
            feature_kind=FeatureKind.SURFACE,
            attributes={"surface_profile": "flat", "removable": True},
        ),
        ToolInterfaceFeature(
            feature_id="fixed-housing",
            feature_kind=FeatureKind.SURFACE,
            attributes={"surface_profile": "flat", "removable": False},
        ),
    ]

    result = evaluate_attachment_eligibility(rule, features)

    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.eligible is True
    assert [match.feature_id for match in result.matches] == ["fixed-housing"]


def test_missing_prohibited_fact_makes_otherwise_matching_path_unresolved():
    rule = AttachmentEligibility(
        paths=[
            EligibilityPath(
                requirements=[
                    FeaturePredicate(property_key="feature_kind", value="surface"),
                    FeaturePredicate(property_key="attribute:surface_profile", value="flat"),
                ],
                prohibitions=[
                    FeaturePredicate(property_key="attribute:removable", value=True),
                ],
            )
        ]
    )

    result = evaluate_attachment_eligibility(
        rule,
        [
            ToolInterfaceFeature(
                feature_id="unknown-flat-surface",
                feature_kind=FeatureKind.SURFACE,
                attributes={"surface_profile": "flat"},
            )
        ],
    )

    assert result.status == EligibilityStatus.UNRESOLVED
    assert result.eligible is False
    assert result.matches == []


def test_known_prohibited_fact_makes_path_ineligible():
    rule = AttachmentEligibility(
        paths=[
            EligibilityPath(
                requirements=[FeaturePredicate(property_key="feature_kind", value="surface")],
                prohibitions=[FeaturePredicate(property_key="attribute:removable", value=True)],
            )
        ]
    )

    result = evaluate_attachment_eligibility(
        rule,
        [
            ToolInterfaceFeature(
                feature_id="battery-door",
                feature_kind=FeatureKind.SURFACE,
                attributes={"removable": True},
            )
        ],
    )

    assert result.status == EligibilityStatus.INELIGIBLE


def test_missing_dimension_produces_unresolved_numeric_requirement():
    rule = AttachmentEligibility(
        paths=[
            EligibilityPath(
                requirements=[
                    FeaturePredicate(
                        property_key="dimension:section_diameter",
                        operator=ComparisonOperator.LTE,
                        value=20.0,
                    )
                ]
            )
        ]
    )

    result = evaluate_attachment_eligibility(
        rule,
        [ToolInterfaceFeature(feature_id="handle-1", feature_kind=FeatureKind.HANDLE)],
    )

    assert result.status == EligibilityStatus.UNRESOLVED
    assert result.eligible is False


@pytest.mark.parametrize("invalid", [-1.0, 0.0, math.inf, -math.inf, math.nan])
def test_invalid_physical_dimensions_are_rejected(invalid: float):
    with pytest.raises(ValidationError):
        ToolInterfaceFeature(
            feature_id="bad-feature",
            feature_kind=FeatureKind.EXTERNAL_SECTION,
            dimensions_mm={"section_diameter": invalid},
        )


def test_manufacturer_assessments_preserve_multiple_issuers_without_aggregation():
    assessment = CandidateAssessment(
        technical_status=TechnicalStatus.COMPATIBLE,
        manufacturer_assessments=[
            ManufacturerAssessment(
                issuer_manufacturer="Hilti",
                scope="tool_manufacturer",
                position=ManufacturerPosition.CONTRARY_TO_MANUFACTURER_INSTRUCTION,
                claim_or_evidence_ref="claim:hilti-use-only",
            ),
            ManufacturerAssessment(
                issuer_manufacturer="Example Attachment Co",
                scope="attachment_manufacturer",
                position=ManufacturerPosition.EXPLICITLY_COMPATIBLE,
                claim_or_evidence_ref="claim:attachment-compatible",
            ),
        ],
        policy_status=PolicyStatus.PERMITTED,
    )

    assert assessment.technical_status == TechnicalStatus.COMPATIBLE
    assert len(assessment.manufacturer_assessments) == 2
    assert {
        (item.issuer_manufacturer, item.position)
        for item in assessment.manufacturer_assessments
    } == {
        ("Hilti", ManufacturerPosition.CONTRARY_TO_MANUFACTURER_INSTRUCTION),
        ("Example Attachment Co", ManufacturerPosition.EXPLICITLY_COMPATIBLE),
    }
    assert not hasattr(assessment, "manufacturer_status")
