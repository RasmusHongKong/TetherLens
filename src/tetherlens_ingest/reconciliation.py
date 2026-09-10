from __future__ import annotations

import re
from collections.abc import Iterable

from .models import CandidateClaim
from .normalize import mass_to_kg


_MASS_DECLARATION = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>kg|kgs?|kilograms?|lb|lbs?|pounds?|g|grams?)\b",
    re.I,
)


def mass_claim_rounding_interval_kg(claim: CandidateClaim) -> tuple[float, float]:
    """Return the kilogram interval implied by one rounded source declaration.

    Ingested mass values are normalized to kilograms, but manufacturer declarations
    often publish equivalent metric/customary values at different decimal precision.
    The source's displayed precision therefore determines the rounding interval used
    for semantic reconciliation. If the raw declaration is unavailable, fail closed by
    treating the normalized value as exact rather than inventing tolerance.
    """

    if isinstance(claim.value, bool) or not isinstance(claim.value, (int, float)):
        raise ValueError("mass claim value must be numeric")

    fallback = float(claim.value)
    match = _MASS_DECLARATION.search(claim.raw_value or "")
    if match is None:
        return fallback, fallback

    value_text = match.group("value")
    value = float(value_text)
    decimal_places = len(value_text.partition(".")[2]) if "." in value_text else 0
    half_step = 0.5 * (10 ** -decimal_places)
    low = max(0.0, value - half_step)
    high = value + half_step
    unit = match.group("unit")
    return mass_to_kg(low, unit), mass_to_kg(high, unit)


def mass_claims_semantically_agree(claims: Iterable[CandidateClaim]) -> bool:
    """Return True when all supplied mass declarations share a plausible value.

    This helper deliberately does not choose which evidence should be compared. Evidence
    priority, product identity and property-specific safety policy remain caller concerns;
    this function only supplies the reusable unit/rounding equivalence calculation.
    """

    claim_list = list(claims)
    if len(claim_list) <= 1:
        return True

    intervals = [mass_claim_rounding_interval_kg(claim) for claim in claim_list]
    return max(low for low, _ in intervals) <= min(high for _, high in intervals)
