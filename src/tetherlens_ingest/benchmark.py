from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_GOLDEN_PATH = Path("benchmarks/batch1_golden.json")
DEFAULT_GOLDEN_OVERLAY_PATH = Path("benchmarks/batch1_source_graph_overrides.json")


def load_golden(
    path: Path = DEFAULT_GOLDEN_PATH,
    overlay_path: Path = DEFAULT_GOLDEN_OVERLAY_PATH,
) -> dict[str, Any]:
    golden = json.loads(path.read_text(encoding="utf-8"))
    if overlay_path.exists():
        overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
        golden["products"].update(overlay.get("products", {}))
        golden["version"] = overlay.get("version", golden.get("version"))
        golden["overlay_description"] = overlay.get("description")
    return golden


def summarize_acquisition(records: list[dict[str, Any]]) -> dict[str, Any]:
    attempted = len(records)
    acquired = sum(bool(record.get("acquisition_succeeded")) for record in records)
    artifacts = sum(int(record.get("artifact_count", 0)) for record in records)
    observations = Counter(
        observation.get("code")
        for record in records
        for observation in record.get("acquisition_observations", [])
        if observation.get("code")
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("manufacturer"))].append(record)

    by_manufacturer = {}
    for manufacturer, manufacturer_records in sorted(grouped.items()):
        manufacturer_acquired = sum(bool(record.get("acquisition_succeeded")) for record in manufacturer_records)
        by_manufacturer[manufacturer] = {
            "attempted": len(manufacturer_records),
            "acquired": manufacturer_acquired,
            "failed": len(manufacturer_records) - manufacturer_acquired,
            "acquisition_rate": manufacturer_acquired / len(manufacturer_records) if manufacturer_records else None,
            "artifact_count": sum(int(record.get("artifact_count", 0)) for record in manufacturer_records),
        }

    return {
        "attempted": attempted,
        "acquired": acquired,
        "failed": attempted - acquired,
        "acquisition_rate": acquired / attempted if attempted else None,
        "artifact_count": artifacts,
        "acquisition_observation_codes": dict(sorted(observations.items())),
        "by_manufacturer": by_manufacturer,
    }


def score_acquisition_product(
    manufacturer: str,
    sku: str | None,
    observations: list[dict[str, Any]],
    golden: dict[str, Any],
) -> dict[str, Any]:
    key = f"{manufacturer}:{sku}"
    spec = golden.get("products", {}).get(key)
    acquisition_spec = spec.get("acquisition_expectations") if spec else None
    if not acquisition_spec:
        return {"scored": False, "reason": "NO_ACQUISITION_EXPECTATION"}

    required = list(acquisition_spec.get("required_observations", []))
    forbidden = list(acquisition_spec.get("forbidden_observations", []))
    missing_required = [
        target
        for target in required
        if not any(_matches_observation(target, observation) for observation in observations)
    ]
    forbidden_hits = [
        {"forbidden": target, "observation": observation}
        for target in forbidden
        for observation in observations
        if _matches_observation(target, observation)
    ]
    return {
        "scored": True,
        "passed": not missing_required and not forbidden_hits,
        "required_count": len(required),
        "required_matched_count": len(required) - len(missing_required),
        "missing_required": missing_required,
        "forbidden_hits": forbidden_hits,
    }


def summarize_acquisition_scores(product_scores: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [score for score in product_scores if score.get("scored")]
    passed = sum(bool(score.get("passed")) for score in scored)
    return {
        "products_scored": len(scored),
        "products_passed": passed,
        "products_failed": len(scored) - passed,
        "missing_required_count": sum(len(score.get("missing_required", [])) for score in scored),
        "forbidden_hit_count": sum(len(score.get("forbidden_hits", [])) for score in scored),
    }


def score_extraction_product(
    manufacturer: str,
    sku: str | None,
    claims: list[dict[str, Any]],
    golden: dict[str, Any],
) -> dict[str, Any]:
    key = f"{manufacturer}:{sku}"
    spec = golden.get("products", {}).get(key)
    if not spec:
        return {"scored": False, "reason": "NO_GOLDEN_EXPECTATION"}

    expected = list(spec.get("expected_claims", spec.get("expected", [])))
    forbidden = list(spec.get("forbidden_claims", spec.get("forbidden", [])))
    ignored = list(spec.get("ignored_claims", []))

    extracted = [
        claim
        for claim in claims
        if not any(_matches(pattern, claim, require_value=False) for pattern in ignored)
    ]

    used_indices: set[int] = set()
    matched_expected: list[dict[str, Any]] = []
    missed_expected: list[dict[str, Any]] = []

    for target in expected:
        match_index = next(
            (
                index
                for index, claim in enumerate(extracted)
                if index not in used_indices and _matches(target, claim)
            ),
            None,
        )
        if match_index is None:
            missed_expected.append(target)
        else:
            used_indices.add(match_index)
            matched_expected.append(target)

    unmatched_extracted = [
        claim for index, claim in enumerate(extracted) if index not in used_indices
    ]
    forbidden_hits = [
        {"forbidden": pattern, "claim": claim}
        for pattern in forbidden
        for claim in extracted
        if _matches(pattern, claim)
    ]

    tp = len(matched_expected)
    fp = len(unmatched_extracted)
    fn = len(missed_expected)

    return {
        "scored": True,
        "expected_count": len(expected),
        "extracted_count": len(extracted),
        "ignored_extracted_count": len(claims) - len(extracted),
        "true_positive_count": tp,
        "false_positive_count": fp,
        "false_negative_count": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "matched_expected": matched_expected,
        "missed_expected": missed_expected,
        "forbidden_hits": forbidden_hits,
        "unexpected_extracted": unmatched_extracted,
    }


def summarize_extraction_scores(product_scores: list[dict[str, Any]]) -> dict[str, Any]:
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
        "unexpected_extracted_count": sum(len(score.get("unexpected_extracted", [])) for score in scored),
    }


def score_recommendation_data_product(
    manufacturer: str,
    sku: str | None,
    claims: list[dict[str, Any]],
    golden: dict[str, Any],
) -> dict[str, Any]:
    key = f"{manufacturer}:{sku}"
    spec = golden.get("products", {}).get(key)
    recommendation_spec = spec.get("recommendation_data") if spec else None
    if not recommendation_spec:
        return {"scored": False, "reason": "NO_RECOMMENDATION_DATA_EXPECTATION"}

    requirement_results = []
    for requirement in recommendation_spec.get("baseline_requirements", []):
        alternatives = list(requirement.get("any_of", []))
        matched_claim = next(
            (
                claim
                for claim in claims
                if any(_matches(pattern, claim) for pattern in alternatives)
            ),
            None,
        )
        requirement_results.append({
            "name": requirement.get("name"),
            "present": matched_claim is not None,
            "matched_claim": matched_claim,
            "gap_if_missing": requirement.get("gap_if_missing", "unknown"),
            "detail": requirement.get("detail"),
        })

    missing = [result for result in requirement_results if not result["present"]]
    return {
        "scored": True,
        "baseline_complete": not missing,
        "requirements_total": len(requirement_results),
        "requirements_present": len(requirement_results) - len(missing),
        "requirements_missing": len(missing),
        "requirement_results": requirement_results,
        "known_gaps": list(recommendation_spec.get("known_gaps", [])),
    }


def summarize_recommendation_data_scores(product_scores: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [score for score in product_scores if score.get("scored")]
    complete = sum(bool(score.get("baseline_complete")) for score in scored)
    requirements_total = sum(int(score.get("requirements_total", 0)) for score in scored)
    requirements_present = sum(int(score.get("requirements_present", 0)) for score in scored)

    missing_categories = Counter(
        result.get("gap_if_missing", "unknown")
        for score in scored
        for result in score.get("requirement_results", [])
        if not result.get("present")
    )
    known_gap_categories = Counter(
        gap.get("category", "unknown")
        for score in scored
        for gap in score.get("known_gaps", [])
    )

    return {
        "products_scored": len(scored),
        "baseline_products_complete": complete,
        "baseline_product_coverage": complete / len(scored) if scored else None,
        "requirements_total": requirements_total,
        "requirements_present": requirements_present,
        "requirements_missing": requirements_total - requirements_present,
        "requirement_coverage": requirements_present / requirements_total if requirements_total else None,
        "missing_requirement_categories": dict(sorted(missing_categories.items())),
        "products_with_known_gaps": sum(bool(score.get("known_gaps")) for score in scored),
        "known_gap_count": sum(len(score.get("known_gaps", [])) for score in scored),
        "known_gap_categories": dict(sorted(known_gap_categories.items())),
    }


score_product = score_extraction_product
summarize_scores = summarize_extraction_scores


def _matches(target: dict[str, Any], claim: dict[str, Any], require_value: bool = True) -> bool:
    for field in ("subject_type", "subject_ref", "property_key"):
        if field in target and target[field] != claim.get(field):
            return False
    if require_value and "value" in target and not _value_equal(target["value"], claim.get("value")):
        return False
    return True


def _matches_observation(target: dict[str, Any], observation: dict[str, Any]) -> bool:
    for field, expected in target.items():
        actual = observation.get(field)
        if field == "value":
            if not _value_equal(expected, actual):
                return False
        elif expected != actual:
            return False
    return True


def _value_equal(expected: Any, actual: Any) -> bool:
    if (
        isinstance(expected, (int, float))
        and not isinstance(expected, bool)
        and isinstance(actual, (int, float))
        and not isinstance(actual, bool)
    ):
        return abs(float(expected) - float(actual)) <= 1e-6
    return expected == actual
