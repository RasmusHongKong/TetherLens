from __future__ import annotations

import json
from pathlib import Path

RESULT_PATH = Path("nlg-unseen-results.json")
GOLDEN_PATH = Path("benchmarks/nlg_unseen_golden.json")


def _claim_key(claim: dict) -> tuple[str, str, str, str]:
    return (
        str(claim.get("subject_type", "product")),
        str(claim.get("subject_ref", "self")),
        str(claim.get("property_key")),
        json.dumps(claim.get("value"), sort_keys=True),
    )


def main() -> None:
    payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    total_expected = 0
    total_matched = 0
    products_passed = 0
    product_scores: list[dict] = []

    for record in payload.get("results", []):
        sku = str(record.get("sku"))
        expected = golden.get("products", {}).get(sku, {}).get("expected_claims", [])
        actual = record.get("claims", [])
        expected_keys = {_claim_key(claim) for claim in expected}
        actual_keys = {_claim_key(claim) for claim in actual}
        missing = [claim for claim in expected if _claim_key(claim) not in actual_keys]
        additional = [claim for claim in actual if _claim_key(claim) not in expected_keys]
        matched = len(expected) - len(missing)
        passed = not missing

        score = {
            "sku": sku,
            "expected_count": len(expected),
            "matched_count": matched,
            "recall": matched / len(expected) if expected else 1.0,
            "passed": passed,
            "missing_expected": missing,
            "additional_extracted": additional,
        }
        record["unseen_golden_score"] = score
        product_scores.append(score)
        total_expected += len(expected)
        total_matched += matched
        products_passed += int(passed)

    summary = {
        "golden_version": golden.get("version"),
        "products_scored": len(product_scores),
        "products_passed": products_passed,
        "expected_claims": total_expected,
        "matched_expected_claims": total_matched,
        "recall": total_matched / total_expected if total_expected else 1.0,
    }
    payload["unseen_golden_summary"] = summary
    RESULT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps({"type": "nlg_unseen_golden_summary", **summary}, indent=2))
    for score in product_scores:
        if score["missing_expected"] or score["additional_extracted"]:
            print(json.dumps({"type": "nlg_unseen_golden_detail", **score}, indent=2))

    if products_passed != len(product_scores):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
