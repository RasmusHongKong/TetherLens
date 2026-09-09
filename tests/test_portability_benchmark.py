from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


BENCHMARK_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "cross_vendor_portability_v1.json"


def _load() -> dict:
    return json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))


def test_cross_vendor_portability_cohort_is_frozen_and_diverse() -> None:
    benchmark = _load()

    assert benchmark["benchmark"] == "cross_vendor_portability_v1"
    assert benchmark["freeze_point"] == {
        "branch": "main",
        "commit": "7e9785456e3f52511f017fdc0a3f19afc1c652c7",
        "through_pr": 51,
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
        "GRIPPS": 2,
        "FallTech": 2,
        "Ty-Flot": 2,
        "Dropsafe": 2,
    }
    assert all(product["manufacturer"] != "NLG" for product in products)
    assert {product["product_type"] for product in products} == {"Tether", "ToolAttachment"}


def test_initial_portability_assessment_separates_ingestion_from_core_change() -> None:
    products = _load()["products"]

    assert Counter(product["classification"] for product in products) == {"B": 7, "C": 1}
    assert not [product for product in products if product["classification"] == "D"]

    for product in products:
        assert product["source_url"].startswith("https://")
        assert product["archetypes"]
        assert product["observed_public_facts"]
        assert product["core_fit"]
        assert product["portability_gap"].strip()

        if product["classification"] in {"A", "B"}:
            assert product["required_core_changes"] == []
        else:
            assert product["required_core_changes"]


def test_portability_cohort_contains_both_reuse_and_stressor_archetypes() -> None:
    archetypes = {
        archetype
        for product in _load()["products"]
        for archetype in product["archetypes"]
    }

    assert {
        "dual_carabiner",
        "directional_endpoints",
        "carabiner_loop_tether",
        "cinch_loop",
        "tool_attachment",
        "d_ring",
        "coil_tether",
        "cold_shrink",
        "triple_action",
        "auto_locking",
    } <= archetypes
