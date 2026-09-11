from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


BENCHMARK_DIR = Path(__file__).resolve().parents[1] / "benchmarks"
V1_PATH = BENCHMARK_DIR / "cross_vendor_portability_v1.json"
V2_PATH = BENCHMARK_DIR / "cross_vendor_portability_v2.json"
V3_PATH = BENCHMARK_DIR / "cross_vendor_portability_v3.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _counts(benchmark: dict) -> dict[str, int]:
    counts = Counter(product["classification"] for product in benchmark["products"])
    return {grade: counts[grade] for grade in ("A", "B", "C", "D")}


def test_historical_portability_cohorts_remain_frozen() -> None:
    v1 = _load(V1_PATH)
    v2 = _load(V2_PATH)

    assert v1["freeze_point"] == {
        "branch": "main",
        "commit": "7e9785456e3f52511f017fdc0a3f19afc1c652c7",
        "through_pr": 51,
    }
    assert _counts(v1) == {"A": 0, "B": 5, "C": 3, "D": 0}

    assert v2["freeze_point"] == {
        "branch": "main",
        "commit": "29c01939c8e8774dcc553527255fc4281708480c",
        "through_pr": 55,
    }
    assert v2["result"] == {"A": 0, "B": 6, "C": 2, "D": 0}
    assert _counts(v2) == {"A": 0, "B": 6, "C": 2, "D": 0}


def test_v3_is_frozen_at_the_post_quickspin_vertical_state_and_is_identity_fresh() -> None:
    benchmark = _load(V3_PATH)

    assert benchmark["benchmark"] == "cross_vendor_portability_v3"
    assert benchmark["freeze_point"] == {
        "branch": "vertical/quickspin-snaplock-portability-v3",
        "commit": "b99897a79b65cce47a499d0110345340613dc2a2",
        "base_main_commit": "94722224944d8d2c8afc38fc2d069c12f608a9ad",
        "through_pr": 57,
        "pending_pr": 58,
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
        "Safewaze": 2,
        "Milwaukee": 2,
        "FallTech": 2,
        "Guardian": 1,
        "Ergodyne": 1,
    }
    assert {product["product_type"] for product in products} == {
        "Tether",
        "AnchorAttachment",
    }

    historical_products = {
        (product["manufacturer"], product["sku"])
        for path in (V1_PATH, V2_PATH)
        for product in _load(path)["products"]
    }
    v3_products = {
        (product["manufacturer"], product["sku"])
        for product in products
    }
    assert historical_products.isdisjoint(v3_products)


def test_v3_tethers_are_throughput_but_anchor_installation_is_recurring_c_pressure() -> None:
    benchmark = _load(V3_PATH)
    products = benchmark["products"]

    assert benchmark["result"] == {"A": 0, "B": 5, "C": 3, "D": 0}
    assert _counts(benchmark) == {"A": 0, "B": 5, "C": 3, "D": 0}
    assert not [product for product in products if product["classification"] == "D"]

    b_products = [product for product in products if product["classification"] == "B"]
    c_products = [product for product in products if product["classification"] == "C"]

    assert len(b_products) == 5
    assert all(product["product_type"] == "Tether" for product in b_products)
    assert all(product["required_core_changes"] == [] for product in b_products)

    assert len(c_products) == 3
    assert all(product["product_type"] == "AnchorAttachment" for product in c_products)
    assert {product["manufacturer"] for product in c_products} == {
        "Milwaukee",
        "FallTech",
        "Ergodyne",
    }
    assert all(product["required_core_changes"] for product in c_products)
    assert all(
        "installation" in " ".join(product["required_core_changes"]).lower()
        and "anchor" in " ".join(product["required_core_changes"]).lower()
        for product in c_products
    )

    assert "Do not declare semantic saturation yet" in benchmark["decision"]


def test_v3_records_complete_audit_rationale_for_every_product() -> None:
    for product in _load(V3_PATH)["products"]:
        assert product["source_url"].startswith("https://")
        assert product["archetypes"]
        assert product["observed_public_facts"]
        assert product["core_fit"]
        assert product["portability_gap"].strip()
