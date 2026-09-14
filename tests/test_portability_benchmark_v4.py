from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


BENCHMARK_DIR = Path(__file__).resolve().parents[1] / "benchmarks"
V1_PATH = BENCHMARK_DIR / "cross_vendor_portability_v1.json"
V2_PATH = BENCHMARK_DIR / "cross_vendor_portability_v2.json"
V3_PATH = BENCHMARK_DIR / "cross_vendor_portability_v3.json"
V4_PATH = BENCHMARK_DIR / "cross_vendor_portability_v4.json"


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


def test_all_historical_portability_cohorts_keep_their_semantic_freezes() -> None:
    assert _counts(_load(V1_PATH)) == {"A": 0, "B": 5, "C": 3, "D": 0}
    assert _counts(_load(V2_PATH)) == {"A": 0, "B": 6, "C": 2, "D": 0}
    assert _counts(_load(V3_PATH)) == {"A": 0, "B": 5, "C": 3, "D": 0}

    assert _load(V1_PATH)["freeze_point"]["through_pr"] == 51
    assert _load(V2_PATH)["freeze_point"]["through_pr"] == 55
    assert _load(V3_PATH)["freeze_point"]["pending_pr"] == 58


def test_v4_is_identity_fresh_and_frozen_after_the_anchor_vertical_proof() -> None:
    benchmark = _load(V4_PATH)

    assert benchmark["benchmark"] == "cross_vendor_portability_v4"
    assert benchmark["freeze_point"] == {
        "branch": "vertical/anchor-attachment-portability-v4",
        "commit": "211a9bdfe9e818b7233f77183e2d4175d708aabf",
        "base_main_commit": "5e9e5f2923e3409957bdba146c280a9d932ea0e9",
        "through_pr": 60,
        "pending_pr": 61,
    }
    assert benchmark["classification"] == {
        "A": "facts_only",
        "B": "vendor_ingestion_only",
        "C": "new_reusable_primitive",
        "D": "sku_specific_exception",
    }

    products = benchmark["products"]
    assert len(products) == 8
    assert Counter(product["manufacturer"] for product in products) == {
        "FallTech": 2,
        "Ergodyne": 2,
        "Klein Tools": 2,
        "GRIPPS": 1,
        "Milwaukee": 1,
    }
    assert Counter(product["product_type"] for product in products) == {
        "AnchorAttachment": 4,
        "ToolAttachment": 3,
        "Tether": 1,
    }

    historical = set().union(
        _identities(V1_PATH),
        _identities(V2_PATH),
        _identities(V3_PATH),
    )
    assert historical.isdisjoint(_identities(V4_PATH))

    vertical_proof_products = {
        ("Milwaukee", "48-22-8855"),
        ("FallTech", "5424A10"),
        ("Ergodyne", "19171"),
    }
    assert vertical_proof_products.isdisjoint(_identities(V4_PATH))


def test_v4_finds_two_recurring_anchor_c_seams_and_d_remains_zero() -> None:
    benchmark = _load(V4_PATH)
    products = benchmark["products"]

    assert benchmark["result"] == {"A": 0, "B": 4, "C": 4, "D": 0}
    assert _counts(benchmark) == {"A": 0, "B": 4, "C": 4, "D": 0}
    assert not [product for product in products if product["classification"] == "D"]

    b_products = [product for product in products if product["classification"] == "B"]
    c_products = [product for product in products if product["classification"] == "C"]

    assert len(b_products) == 4
    assert all(product["required_core_changes"] == [] for product in b_products)
    assert {product["product_type"] for product in b_products} == {
        "ToolAttachment",
        "Tether",
    }

    assert len(c_products) == 4
    assert all(product["product_type"] == "AnchorAttachment" for product in c_products)
    assert all(product["required_core_changes"] for product in c_products)

    wrist = {
        (product["manufacturer"], product["sku"])
        for product in c_products
        if "worker_worn_anchor" in product["archetypes"]
    }
    bucket_lip = {
        (product["manufacturer"], product["sku"])
        for product in c_products
        if "bucket_lip_anchor" in product["archetypes"]
    }
    assert wrist == {("FallTech", "5331A1"), ("GRIPPS", "H01086")}
    assert bucket_lip == {("Ergodyne", "19178"), ("Klein Tools", "5144LG3")}

    assert "Do not shift the development centre" in benchmark["decision"]
    assert "worker-worn wrist anchors" in benchmark["decision"]
    assert "bucket-lip/edge" in benchmark["decision"]


def test_v4_records_complete_evidence_led_audit_rationale() -> None:
    for product in _load(V4_PATH)["products"]:
        assert product["source_url"].startswith("https://")
        assert product["archetypes"]
        assert product["observed_public_facts"]
        assert product["core_fit"]
        assert product["portability_gap"].strip()

    gripps = next(
        product
        for product in _load(V4_PATH)["products"]
        if product["manufacturer"] == "GRIPPS"
    )
    assert any(
        "not a numeric fit envelope" in note
        for note in gripps["evidence_notes"]
    )
