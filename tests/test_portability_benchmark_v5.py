from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


BENCHMARK_DIR = Path(__file__).resolve().parents[1] / "benchmarks"
V1_PATH = BENCHMARK_DIR / "cross_vendor_portability_v1.json"
V2_PATH = BENCHMARK_DIR / "cross_vendor_portability_v2.json"
V3_PATH = BENCHMARK_DIR / "cross_vendor_portability_v3.json"
V4_PATH = BENCHMARK_DIR / "cross_vendor_portability_v4.json"
V5_PATH = BENCHMARK_DIR / "cross_vendor_portability_v5.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _counts(benchmark: dict) -> dict[str, int]:
    counts = Counter(product["classification"] for product in benchmark["products"])
    return {grade: counts[grade] for grade in ("A", "B", "C", "D")}


def _identities(path: Path) -> set[tuple[str, str]]:
    return {
        (product["manufacturer"], product["sku"])
        for product in _load(path)["products"]
    }


def test_all_historical_portability_cohorts_remain_frozen() -> None:
    assert _counts(_load(V1_PATH)) == {"A": 0, "B": 5, "C": 3, "D": 0}
    assert _counts(_load(V2_PATH)) == {"A": 0, "B": 6, "C": 2, "D": 0}
    assert _counts(_load(V3_PATH)) == {"A": 0, "B": 5, "C": 3, "D": 0}
    assert _counts(_load(V4_PATH)) == {"A": 0, "B": 4, "C": 4, "D": 0}


def test_v5_was_frozen_against_merged_post_pr62_main_before_classification() -> None:
    benchmark = _load(V5_PATH)

    assert benchmark["benchmark"] == "cross_vendor_portability_v5"
    assert benchmark["freeze_point"] == {
        "branch": "main",
        "commit": "87f3c277f108e38dc3ec7d070e38c94868d355a6",
        "through_pr": 62,
    }
    assert benchmark["sample_status"] == "classified_after_freeze_commit"
    assert benchmark["sample_freeze_commit"] == "e7c03c942b3fb2456033f7d5d3e15ee3cfee09d7"
    assert len(benchmark["products"]) == 8
    assert Counter(product["product_type"] for product in benchmark["products"]) == {
        "ToolAttachment": 4,
        "Tether": 4,
    }
    assert Counter(product["manufacturer"] for product in benchmark["products"]) == {
        "GRIPPS": 2,
        "FallTech": 1,
        "Ergodyne": 1,
        "Safewaze": 1,
        "Milwaukee": 1,
        "3M": 1,
        "Guardian": 1,
    }


def test_v5_is_disjoint_from_every_historical_cohort_and_recent_vertical_proof() -> None:
    historical = set().union(
        _identities(V1_PATH),
        _identities(V2_PATH),
        _identities(V3_PATH),
        _identities(V4_PATH),
    )
    assert historical.isdisjoint(_identities(V5_PATH))

    recent_vertical_proof_products = {
        ("GRIPPS", "H01150"),
        ("3M", "1500028"),
        ("Milwaukee", "48-22-8855"),
        ("FallTech", "5424A10"),
        ("Ergodyne", "19171"),
        ("FallTech", "5331A1"),
        ("GRIPPS", "H01086"),
        ("Ergodyne", "19178"),
        ("Klein Tools", "5144LG3"),
    }
    assert recent_vertical_proof_products.isdisjoint(_identities(V5_PATH))


def test_v5_is_ab_majority_but_repeats_one_narrow_dimensional_c_seam() -> None:
    benchmark = _load(V5_PATH)
    products = benchmark["products"]

    assert benchmark["result"] == {"A": 0, "B": 6, "C": 2, "D": 0}
    assert _counts(benchmark) == {"A": 0, "B": 6, "C": 2, "D": 0}
    assert not [product for product in products if product["classification"] == "D"]

    b_products = [product for product in products if product["classification"] == "B"]
    c_products = [product for product in products if product["classification"] == "C"]

    assert len(b_products) == 6
    assert all(product["required_core_changes"] == [] for product in b_products)

    assert {
        (product["manufacturer"], product["sku"])
        for product in c_products
    } == {
        ("FallTech", "5401A1"),
        ("Ergodyne", "19747"),
    }
    assert all(product["required_core_changes"] for product in c_products)
    assert all(
        "dimension" in product["portability_gap"].casefold()
        for product in c_products
    )

    assert "Do not shift the development centre fully" in benchmark["decision"]
    assert "feature-bound dimensional eligibility" in benchmark["decision"]


def test_v5_records_evidence_led_audit_rationale() -> None:
    for product in _load(V5_PATH)["products"]:
        assert product["source_url"].startswith("https://")
        assert product["archetypes"]
        assert product["observed_public_facts"]
        assert product["core_fit"]
        assert product["portability_gap"].strip()
