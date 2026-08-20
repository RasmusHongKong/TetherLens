from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tetherlens_ingest.benchmark import (
    score_extraction_product,
    score_recommendation_data_product,
    summarize_extraction_scores,
    summarize_recommendation_data_scores,
)

DEFAULT_RESULT_PATH = Path("benchmarks/batch2_nlg_blind_run130.json")
DEFAULT_GOLDEN_PATH = Path("benchmarks/batch2_nlg_golden.json")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score Batch 2 NLG results against the post-blind golden contract."
    )
    parser.add_argument(
        "result_path",
        nargs="?",
        type=Path,
        default=DEFAULT_RESULT_PATH,
        help="Result JSON to score. Defaults to the immutable blind run 130 snapshot.",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=DEFAULT_GOLDEN_PATH,
        help="Golden contract path.",
    )
    parser.add_argument(
        "--write-scored",
        type=Path,
        help="Optional path for a copy of the result payload with per-product scores attached.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = json.loads(args.result_path.read_text(encoding="utf-8"))
    golden = json.loads(args.golden.read_text(encoding="utf-8"))

    extraction_scores = []
    recommendation_scores = []
    missing_requirement_categories: Counter[str] = Counter()

    for record in payload.get("results", []):
        manufacturer = record.get("manufacturer", "NLG")
        extraction = score_extraction_product(
            manufacturer,
            record.get("sku"),
            record.get("claims", []),
            golden,
        )
        recommendation = score_recommendation_data_product(
            manufacturer,
            record.get("sku"),
            record.get("claims", []),
            golden,
        )
        record["extraction_quality"] = extraction
        record["recommendation_data"] = recommendation
        extraction_scores.append(extraction)
        recommendation_scores.append(recommendation)
        for requirement in recommendation.get("requirement_results", []):
            if not requirement.get("present"):
                missing_requirement_categories[requirement.get("gap_if_missing", "unknown")] += 1

    extraction_summary = summarize_extraction_scores(extraction_scores)
    recommendation_summary = summarize_recommendation_data_scores(recommendation_scores)
    summary = {
        "result_path": str(args.result_path),
        "golden_version": golden.get("version"),
        "blind_reference": golden.get("blind_reference"),
        "extraction_quality": extraction_summary,
        "recommendation_data_coverage": recommendation_summary,
        "missing_requirement_categories": dict(sorted(missing_requirement_categories.items())),
    }

    print(json.dumps({"type": "batch2_nlg_score", **summary}, indent=2))
    for record in payload.get("results", []):
        extraction = record.get("extraction_quality", {})
        recommendation = record.get("recommendation_data", {})
        if extraction.get("missed_expected") or extraction.get("unexpected_extracted") or not recommendation.get("baseline_complete", True):
            print(json.dumps({
                "type": "batch2_nlg_detail",
                "sku": record.get("sku"),
                "title": record.get("catalogue_title"),
                "extraction_precision": extraction.get("precision"),
                "extraction_recall": extraction.get("recall"),
                "missed_expected": extraction.get("missed_expected", []),
                "unexpected_extracted": extraction.get("unexpected_extracted", []),
                "baseline_complete": recommendation.get("baseline_complete"),
                "missing_requirements": [
                    requirement
                    for requirement in recommendation.get("requirement_results", [])
                    if not requirement.get("present")
                ],
                "known_gaps": recommendation.get("known_gaps", []),
            }, indent=2))

    if args.write_scored:
        payload["post_blind_scores"] = summary
        args.write_scored.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # The immutable blind snapshot is an evaluation baseline, not a regression gate.
    # Its known false negatives and recommendation gaps are the findings we want to preserve.
    # Future fixed-output runs can be compared with this score before promoting a new gate.


if __name__ == "__main__":
    main()
