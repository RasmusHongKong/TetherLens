from __future__ import annotations

import pytest

from tetherlens_ingest.compatibility import (
    CaptiveState,
    EligibilityStatus,
    FeatureKind,
    ToolInterfaceFeature,
    evaluate_attachment_eligibility,
)
from tetherlens_ingest.models import CandidateClaim
from tetherlens_ingest.resolution import ClaimResolutionError, resolve_attachment_eligibility


def selection_claim(value: str, *, source_url: str = "https://manufacturer.test/product") -> CandidateClaim:
    return CandidateClaim(
        property_key="attachment_selection_class",
        value=value,
        source_url=source_url,
        extractor="test",
    )


def captive_features() -> list[ToolInterfaceFeature]:
    return [
        ToolInterfaceFeature(
            feature_id="handle-1",
            feature_kind=FeatureKind.HANDLE,
            captive_state=CaptiveState.CAPTIVE,
        ),
        ToolInterfaceFeature(
            feature_id="opening-1",
            feature_kind=FeatureKind.THROUGH_OPENING,
            captive_state=CaptiveState.CAPTIVE,
        ),
    ]


@pytest.mark.parametrize(
    ("selection_class", "expected_binding", "expected_feature_id"),
    [
        ("captive_handle_attachment", "handle", "handle-1"),
        ("captive_through_opening_attachment", "opening", "opening-1"),
    ],
)
def test_single_feature_captive_classes_do_not_widen_to_the_other_feature_kind(
    selection_class: str,
    expected_binding: str,
    expected_feature_id: str,
) -> None:
    eligibility = resolve_attachment_eligibility([selection_claim(selection_class)])

    assert eligibility is not None
    assert len(eligibility.paths) == 1

    result = evaluate_attachment_eligibility(eligibility, captive_features())

    assert result.status == EligibilityStatus.ELIGIBLE
    assert [(match.binding_name, match.feature_id) for match in result.matches] == [
        (expected_binding, expected_feature_id)
    ]


@pytest.mark.parametrize(
    ("selection_class", "wrong_feature_kind"),
    [
        ("captive_handle_attachment", FeatureKind.THROUGH_OPENING),
        ("captive_through_opening_attachment", FeatureKind.HANDLE),
    ],
)
def test_single_feature_captive_classes_reject_the_other_captive_feature_kind(
    selection_class: str,
    wrong_feature_kind: FeatureKind,
) -> None:
    eligibility = resolve_attachment_eligibility([selection_claim(selection_class)])
    assert eligibility is not None

    result = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="wrong-kind",
                feature_kind=wrong_feature_kind,
                captive_state=CaptiveState.CAPTIVE,
            )
        ],
    )

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.matches == []


@pytest.mark.parametrize(
    ("selection_class", "feature_kind"),
    [
        ("captive_handle_attachment", FeatureKind.HANDLE),
        ("captive_through_opening_attachment", FeatureKind.THROUGH_OPENING),
    ],
)
def test_single_feature_captive_classes_remain_unresolved_when_captive_state_is_unknown(
    selection_class: str,
    feature_kind: FeatureKind,
) -> None:
    eligibility = resolve_attachment_eligibility([selection_claim(selection_class)])
    assert eligibility is not None

    result = evaluate_attachment_eligibility(
        eligibility,
        [ToolInterfaceFeature(feature_id="candidate", feature_kind=feature_kind)],
    )

    assert result.status == EligibilityStatus.UNRESOLVED
    assert result.matches == []


def test_existing_combined_captive_class_preserves_handle_or_through_opening_semantics() -> None:
    eligibility = resolve_attachment_eligibility(
        [selection_claim("captive_feature_attachment")]
    )

    assert eligibility is not None
    assert [path.binding_name for path in eligibility.paths] == ["handle", "opening"]

    result = evaluate_attachment_eligibility(eligibility, captive_features())

    assert result.status == EligibilityStatus.ELIGIBLE
    assert [
        (match.path_index, match.binding_name, match.feature_id)
        for match in result.matches
    ] == [
        (0, "handle", "handle-1"),
        (1, "opening", "opening-1"),
    ]


def test_duplicate_same_selection_class_does_not_duplicate_runtime_paths() -> None:
    eligibility = resolve_attachment_eligibility(
        [
            selection_claim(
                "captive_handle_attachment",
                source_url="https://manufacturer.test/product",
            ),
            selection_claim(
                "captive_handle_attachment",
                source_url="https://manufacturer.test/instructions",
            ),
        ]
    )

    assert eligibility is not None
    assert len(eligibility.paths) == 1
    assert eligibility.paths[0].binding_name == "handle"


def test_conflicting_accepted_selection_classes_fail_closed_instead_of_being_unioned() -> None:
    with pytest.raises(ClaimResolutionError, match="conflicting accepted claims"):
        resolve_attachment_eligibility(
            [
                selection_claim("captive_handle_attachment"),
                selection_claim("captive_through_opening_attachment"),
            ]
        )


def test_unsupported_selection_class_still_fails_closed() -> None:
    with pytest.raises(ClaimResolutionError, match="unsupported attachment selection class"):
        resolve_attachment_eligibility([selection_claim("invented_attachment_class")])
