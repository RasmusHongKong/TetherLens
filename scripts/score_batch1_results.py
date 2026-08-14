from __future__ import annotations

import json
from pathlib import Path

from tetherlens_ingest.benchmark import (
    load_golden,
    score_extraction_product,
    score_recommendation_data_product,
    summarize_acquisition,
    summarize_extraction_scores,
    summarize_recommendation_data_scores,
)

RESULT_PATH = Path("batch1-benchmark-results.json")


def main() -> None:
    payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    golden = load_golden()
    extraction_scores = []
    recommendation_scores = []

    for record in payload.get("results", []):
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
        record["extraction_quality"] = extraction
        record["recommendation_data"] = recommendation
        extraction_scores.append(extraction)
        recommendation_scores.append(recommendation)

    payload["benchmark_scores"] = {
        "acquisition_coverage": summarize_acquisition(payload.get("results", [])),
        "extraction_quality": summarize_extraction_scores(extraction_scores),
        "recommendation_data_coverage": summarize_recommendation_data_scores(recommendation_scores),
    }
    payload["golden_version"] = golden.get("version")
    payload.pop("quality_summary", None)
    RESULT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps({"type": "benchmark_scores", **payload["benchmark_scores"]}, indent=2))
    for record in payload.get("results", []):
        extraction = record.get("extraction_quality", {})
        recommendation = record.get("recommendation_data", {})
        if extraction.get("forbidden_hits") or extraction.get("missed_expected") or extraction.get("unexpected_extracted") or not recommendation.get("baseline_complete", True):
            print(json.dumps({
                "type": "benchmark_detail",
                "manufacturer": record["manufacturer"],
                "sku": record.get("sku"),
                "extraction_precision": extraction.get("precision"),
                "extraction_recall": extraction.get("recall"),
                "missed_expected": extraction.get("missed_expected", []),
                "forbidden_hits": extraction.get("forbidden_hits", []),
                "unexpected_extracted": extraction.get("unexpected_extracted", []),
                "baseline_complete": recommendation.get("baseline_complete"),
                "requirement_results": recommendation.get("requirement_results", []),
                "known_gaps": recommendation.get("known_gaps", []),
            }, indent=2))


if __name__ == "__main__":
    main()
