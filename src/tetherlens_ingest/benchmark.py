from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_GOLDEN_PATH = Path("benchmarks/batch1_golden.json")


def load_golden(path: Path = DEFAULT_GOLDEN_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def score_product(manufacturer: str, sku: str | None, claims: list[dict[str, Any]], golden: dict[str, Any]) -> dict[str, Any]:
    key = f"{manufacturer}:{sku}"
    spec = golden.get("products", {}).get(key)
    if not spec:
        return {"scored": False, "reason": "NO_GOLDEN_EXPECTATION"}

    scored_keys = set(spec.get("scored_property_keys", []))
    extracted = [claim for claim in claims if claim.get("property_key") in scored_keys]
    expected = list(spec.get("expected", []))
    forbidden = list(spec.get("forbidden", []))

    matched_expected: list[dict[str, Any]] = []
    missed_expected: list[dict[str, Any]] = []
    for target in expected:
        match = next((claim for claim in extracted if _matches(target, claim)), None)
        if match:
            matched_expected.append(target)
        else:
            missed_expected.append(target)

    forbidden_hits = [
        {"forbidden": target, "claim": claim}
        for target in forbidden
        for claim in extracted
        if _matches(target, claim, require_value=False)
    ]

    expected_matches = [claim for claim in extracted if any(_matches(target, claim) for target in expected)]
    unmatched_extracted = [
        claim
        for claim in extracted
        if not any(_matches(target, claim) for target in expected)
        and not any(_matches(target, claim, require_value=False) for target in forbidden)
    ]

    tp = len(expected_matches)
    fp = len(extracted) - tp
    fn = len(missed_expected)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None

    return {
        "scored": True,
        "expected_count": len(expected),
        "scored_extracted_count": len(extracted),
        "true_positive_count": tp,
        "false_positive_count": fp,
        "false_negative_count": fn,
        "precision": precision,
        "recall": recall,
        "matched_expected": matched_expected,
        "missed_expected": missed_expected,
        "forbidden_hits": forbidden_hits,
        "unmatched_extracted": unmatched_extracted,
    }


def summarize_scores(product_scores: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [score for score in product_scores if score.get("scored")]
    tp = sum(int(score.get("true_positive_count", 0)) for score in scored)
    fp = sum(int(score.get("false_positive_count", 0)) for score in scored)
    fn = sum(int(score.get("false_negative_count", 0)) for score in scored)
    return {
        "products_scored": len(scored),
        "true_positive_count": tp,
        "false_positive_count": fp,
        "false_negative_count": fn,
        "micro_precision": tp / (tp + fp) if tp + fp else None,
        "micro_recall": tp / (tp + fn) if tp + fn else None,
        "forbidden_hit_count": sum(len(score.get("forbidden_hits", [])) for score in scored),
    }


def _matches(target: dict[str, Any], claim: dict[str, Any], require_value: bool = True) -> bool:
    for field in ("subject_type", "subject_ref", "property_key"):
        if field in target and target[field] != claim.get(field):
            return False
    if require_value and "value" in target and not _value_equal(target["value"], claim.get("value")):
        return False
    return True


def _value_equal(expected: Any, actual: Any) -> bool:
    if isinstance(expected, (int, float)) and not isinstance(expected, bool) and isinstance(actual, (int, float)) and not isinstance(actual, bool):
        return abs(float(expected) - float(actual)) <= 1e-6
    return expected == actual
