from __future__ import annotations

import pytest

from tetherlens_ingest.models import CandidateClaim, ClaimSubjectType
from tetherlens_ingest.resolution import ClaimResolutionError, resolve_attachment_eligibility


SOURCE_URL = "https://example.test/attachment"


def _claim(
    property_key: str,
    value,
    *,
    subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT,
    subject_ref: str = "self",
    unit: str | None = None,
    source_url: str = SOURCE_URL,
) -> CandidateClaim:
    return CandidateClaim(
        subject_type=subject_type,
        subject_ref=subject_ref,
        property_key=property_key,
        value=value,
        unit=unit,
        source_url=source_url,
        extractor="test.v0",
    )


def test_external_section_attachment_rejects_missing_diameter_fit_envelope() -> None:
    claims = [
        _claim("attachment_selection_class", "external_section_attachment"),
    ]

    with pytest.raises(ClaimResolutionError, match="requires an accepted min/max diameter-fit envelope"):
        resolve_attachment_eligibility(claims)


@pytest.mark.parametrize(
    "property_key,value",
    [
        ("interface.dimension.min_diameter", 1.65),
        ("interface.dimension.max_diameter", 3.5),
    ],
)
def test_external_section_attachment_rejects_partial_diameter_fit_envelope(
    property_key: str,
    value: float,
) -> None:
    claims = [
        _claim("attachment_selection_class", "external_section_attachment"),
        _claim(
            property_key,
            value,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="tool_side_fit",
            unit="in",
        ),
    ]

    with pytest.raises(ClaimResolutionError, match="requires both min_diameter and max_diameter"):
        resolve_attachment_eligibility(claims)


def test_external_section_attachment_accepts_equivalent_diameter_evidence_after_unit_normalization() -> None:
    claims = [
        _claim("attachment_selection_class", "external_section_attachment"),
        _claim(
            "interface.dimension.min_diameter",
            1.0,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="tool_side_fit",
            unit="in",
            source_url="https://example.test/imperial",
        ),
        _claim(
            "interface.dimension.min_diameter",
            25.4,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="tool_side_fit",
            unit="mm",
            source_url="https://example.test/metric",
        ),
        _claim(
            "interface.dimension.max_diameter",
            3.5,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="tool_side_fit",
            unit="in",
            source_url="https://example.test/imperial",
        ),
        _claim(
            "interface.dimension.max_diameter",
            88.9,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="tool_side_fit",
            unit="mm",
            source_url="https://example.test/metric",
        ),
    ]

    eligibility = resolve_attachment_eligibility(claims)

    assert eligibility is not None
    requirements = eligibility.paths[0].requirements
    assert requirements[1].value == pytest.approx(25.4)
    assert requirements[2].value == pytest.approx(88.9)


def test_external_section_attachment_rejects_materially_conflicting_diameter_evidence_after_unit_normalization() -> None:
    claims = [
        _claim("attachment_selection_class", "external_section_attachment"),
        _claim(
            "interface.dimension.min_diameter",
            1.0,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="tool_side_fit",
            unit="in",
            source_url="https://example.test/imperial",
        ),
        _claim(
            "interface.dimension.min_diameter",
            30.0,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="tool_side_fit",
            unit="mm",
            source_url="https://example.test/metric",
        ),
        _claim(
            "interface.dimension.max_diameter",
            3.5,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="tool_side_fit",
            unit="in",
        ),
    ]

    with pytest.raises(ClaimResolutionError, match="conflicting accepted claims"):
        resolve_attachment_eligibility(claims)
