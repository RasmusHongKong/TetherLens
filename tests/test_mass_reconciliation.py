from __future__ import annotations

import pytest

from tetherlens_ingest.models import CandidateClaim
from tetherlens_ingest.reconciliation import (
    mass_claim_rounding_interval_kg,
    mass_claims_semantically_agree,
)


def _claim(value_kg: float, raw_value: str | None) -> CandidateClaim:
    return CandidateClaim(
        property_key="rated_capacity_kg",
        value=value_kg,
        unit="kg",
        raw_value=raw_value,
        source_url="https://example.test/evidence",
        extractor="test.v0",
    )


def test_rounded_metric_and_customary_mass_declarations_semantically_agree() -> None:
    customary = _claim(4.535924, "up to 10 lb")
    metric = _claim(4.53, "maximum load 4.53 kg")

    assert mass_claims_semantically_agree([customary, metric]) is True


def test_materially_different_mass_declarations_do_not_semantically_agree() -> None:
    ten_pounds = _claim(4.535924, "up to 10 lb")
    five_kg = _claim(5.0, "maximum load 5.0 kg")

    assert mass_claims_semantically_agree([ten_pounds, five_kg]) is False


def test_gripps_style_rounded_dual_unit_values_can_correspond() -> None:
    metric = _claim(36.3, "load rating 36.3 kg")
    customary = _claim(36.28739, "load rating 80 lb")

    assert mass_claims_semantically_agree([metric, customary]) is True


def test_gripps_known_material_capacity_difference_remains_a_conflict() -> None:
    lower = _claim(36.3, "load rating 36.3 kg")
    higher = _claim(36.9, "load rating 36.9 kg")

    assert mass_claims_semantically_agree([lower, higher]) is False


def test_source_precision_controls_mass_rounding_interval() -> None:
    claim = _claim(4.53, "maximum load 4.53 kg")

    low, high = mass_claim_rounding_interval_kg(claim)

    assert low == pytest.approx(4.525)
    assert high == pytest.approx(4.535)


def test_missing_raw_mass_declaration_fails_closed_to_exact_normalized_value() -> None:
    exact = _claim(4.535924, None)
    rounded = _claim(4.53, "maximum load 4.53 kg")

    assert mass_claim_rounding_interval_kg(exact) == (4.535924, 4.535924)
    assert mass_claims_semantically_agree([exact, rounded]) is False
