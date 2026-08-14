from __future__ import annotations

import json
from pathlib import Path

from tetherlens_ingest.benchmark import load_golden, score_product, summarize_scores

RESULT_PATH = Path("batch1-benchmark-results.json")


def main() -> None:
    payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    golden = load_golden()
    product_scores = []

    for record in payload.get("results", []):
        score = score_product(
            record["manufacturer"],
            record.get("sku"),
            record.get("claims", []),
            golden,
        )
        record["quality_score"] = score
        product_scores.append(score)

    payload["quality_summary"] = summarize_scores(product_scores)
    payload["golden_version"] = golden.get("version")
    RESULT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps({"type": "quality_summary", **payload["quality_summary"]}, indent=2))
    for record in payload.get("results", []):
        score = record.get("quality_score", {})
        if score.get("forbidden_hits") or score.get("missed_expected"):
            print(json.dumps({
                "type": "quality_detail",
                "manufacturer": record["manufacturer"],
                "sku": record.get("sku"),
                "precision": score.get("precision"),
                "recall": score.get("recall"),
                "missed_expected": score.get("missed_expected", []),
                "forbidden_hits": score.get("forbidden_hits", []),
                "unmatched_extracted": score.get("unmatched_extracted", []),
            }, indent=2))


if __name__ == "__main__":
    main()
