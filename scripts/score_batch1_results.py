from __future__ import annotations

import json
from pathlib import Path

from tetherlens_ingest.benchmark import (
    load_golden,
    score_acquisition_product,
    score_extraction_product,
    score_recommendation_data_product,
    summarize_acquisition,
    summarize_acquisition_scores,
    summarize_extraction_scores,
    summarize_recommendation_data_scores,
)

RESULT_PATH = Path("batch1-benchmark-results.json")


def main() -> None:
    payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    golden = load_golden()
    acquisition_scores = []
    extraction_scores = []
    recommendation_scores = []

    for record in payload.get("results", []):
        acquisition = score_acquisition_product(
            record["manufacturer"],
            record.get("sku"),
            record.get("acquisition_observations", []),
            golden,
        )
        extraction = score_extraction_product(
            record["manufacturer"],
            record.get("sku"),
            record.get("claims", []),
            golden,
        )
        recommendation = score_recommendation_data_product(
            record["manufacturer"],
            record.get("sku"),
            record.get("claims", []),
            golden,
        )
        record["acquisition_quality"] = acquisition
        record["extraction_quality"] = extraction
        record["recommendation_data"] = recommendation
        acquisition_scores.append(acquisition)
        extraction_scores.append(extraction)
        recommendation_scores.append(recommendation)

    acquisition_quality_summary = summarize_acquisition_scores(acquisition_scores)
    extraction_summary = summarize_extraction_scores(extraction_scores)
    payload["benchmark_scores"] = {
        "acquisition_coverage": summarize_acquisition(payload.get("results", [])),
        "acquisition_quality": acquisition_quality_summary,
        "extraction_quality": extraction_summary,
        "recommendation_data_coverage": summarize_recommendation_data_scores(recommendation_scores),
    }
    payload["golden_version"] = golden.get("version")
    payload.pop("quality_summary", None)
    RESULT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps({"type": "benchmark_scores", **payload["benchmark_scores"]}, indent=2))
    for record in payload.get("results", []):
        acquisition = record.get("acquisition_quality", {})
        extraction = record.get("extraction_quality", {})
        recommendation = record.get("recommendation_data", {})
        if (
            acquisition.get("scored") and not acquisition.get("passed", True)
            or extraction.get("forbidden_hits")
            or extraction.get("missed_expected")
            or extraction.get("unexpected_extracted")
            or not recommendation.get("baseline_complete", True)
        ):
            print(json.dumps({
                "type": "benchmark_detail",
                "manufacturer": record["manufacturer"],
                "sku": record.get("sku"),
                "acquisition_passed": acquisition.get("passed") if acquisition.get("scored") else None,
                "missing_required_observations": acquisition.get("missing_required", []),
                "forbidden_observation_hits": acquisition.get("forbidden_hits", []),
                "extraction_precision": extraction.get("precision"),
                "extraction_recall": extraction.get("recall"),
                "missed_expected": extraction.get("missed_expected", []),
                "forbidden_hits": extraction.get("forbidden_hits", []),
                "unexpected_extracted": extraction.get("unexpected_extracted", []),
                "baseline_complete": recommendation.get("baseline_complete"),
                "requirement_results": recommendation.get("requirement_results", []),
                "known_gaps": recommendation.get("known_gaps", []),
            }, indent=2))

    # Recommendation-data gaps are legitimate benchmark findings and do not fail CI.
    # Acquisition and extraction regressions do: the golden contract is the ingestion safety gate.
    if (
        acquisition_quality_summary.get("products_failed", 0)
        or extraction_summary.get("false_positive_count", 0)
        or extraction_summary.get("false_negative_count", 0)
        or extraction_summary.get("forbidden_hit_count", 0)
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
