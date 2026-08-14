from __future__ import annotations

import re
from dataclasses import dataclass

LB_TO_KG = 0.45359237


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str


def mass_to_kg(value: float, unit: str) -> float:
    u = unit.strip().lower().replace("lbs", "lb")
    if u in {"kg", "kilogram", "kilograms"}:
        return round(value, 6)
    if u in {"lb", "pound", "pounds"}:
        return round(value * LB_TO_KG, 6)
    if u in {"g", "gram", "grams"}:
        return round(value / 1000, 6)
    raise ValueError(f"unsupported mass unit: {unit}")


def length_to_mm(value: float, unit: str) -> float:
    u = unit.strip().lower()
    if u == "mm":
        return value
    if u == "cm":
        return value * 10
    if u in {"m", "meter", "metre"}:
        return value * 1000
    if u in {"in", "inch", "inches", '"'}:
        return value * 25.4
    raise ValueError(f"unsupported length unit: {unit}")


def parse_mass(text: str) -> Quantity | None:
    m = re.search(r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>kg|kgs?|lb|lbs?|g)\b", text, re.I)
    if not m:
        return None
    return Quantity(mass_to_kg(float(m.group("value")), m.group("unit")), "kg")


def parse_length_range_mm(text: str) -> tuple[float, float] | None:
    m = re.search(
        r"(?P<a>\d+(?:\.\d+)?)\s*(?P<ua>mm|cm|m|in(?:ches)?|\")?\s*(?:to|[-–])\s*"
        r"(?P<b>\d+(?:\.\d+)?)\s*(?P<ub>mm|cm|m|in(?:ches)?|\")",
        text,
        re.I,
    )
    if not m:
        return None
    ua = m.group("ua") or m.group("ub")
    return (
        round(length_to_mm(float(m.group("a")), ua), 3),
        round(length_to_mm(float(m.group("b")), m.group("ub")), 3),
    )


def opening_action_count(text: str) -> int | None:
    lower = text.lower()
    patterns = {
        3: ("three-stage", "triple action", "triple-action", "three action"),
        2: ("two-stage", "dual action", "dual-action", "double action", "double-action"),
        1: ("single action", "single-action", "one-stage"),
    }
    for count, terms in patterns.items():
        if any(term in lower for term in terms):
            return count
    return None
