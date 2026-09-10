from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


BENCHMARK_DIR = Path(__file__).resolve().parents[1] / "benchmarks"
V1_PATH = BENCHMARK_DIR / "cross_vendor_portability_v1.json"
V2_PATH = BENCHMARK_DIR / "cross_vendor_portability_v2.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_post_pr55_portability_cohort_is_frozen_and_unseen() -> None:
    benchmark = _load(V2_PATH)

    assert benchmark["benchmark"] == "cross_vendor_portability_v2"
    assert benchmark["freeze_point"] == {
        "branch": "main",
        "commit": "29c01939c8e8774dcc553527255fc4281708480c",
        "through_pr": 55,
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
        "GRIPPS": 2,
        "Ergodyne": 2,
        "3M": 2,
    }
    assert {product["product_type"] for product in products} == {"Tether", "ToolAttachment"}

    v1_products = {
        (product["manufacturer"], product["sku"])
        for product in _load(V1_PATH)["products"]
    }
    v2_products = {
        (product["manufacturer"], product["sku"])
        for product in products
    }
    assert v1_products.isdisjoint(v2_products)

    # V1 identity disjointness is not sufficient for a genuinely fresh audit. The
    # pre-PR #55 architecture explicitly used an Ergodyne web ToolAttachment retained
    # with required tape/wrap as a design input. Exclude that already-modelled family,
    # not just one exact SKU, so it cannot inflate the post-#55 reuse result.
    assert not [
        product
        for product in products
        if product["manufacturer"] == "Ergodyne"
        and product["product_type"] == "ToolAttachment"
        and {"wrap", "required_pairing", "multi_component_assembly"}.issubset(
            set(product["archetypes"])
        )
    ]


def test_post_pr55_portability_is_predominantly_existing_core_reuse() -> None:
    benchmark = _load(V2_PATH)
    products = benchmark["products"]
    counts = Counter(product["classification"] for product in products)

    assert counts == {"B": 6, "C": 2}
    assert benchmark["result"] == {"A": 0, "B": 6, "C": 2, "D": 0}
    assert sum(counts[classification] for classification in {"A", "B"}) > len(products) / 2
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


def test_remaining_c_gap_recurs_across_independent_manufacturers() -> None:
    c_products = [
        product
        for product in _load(V2_PATH)["products"]
        if product["classification"] == "C"
    ]

    assert {(product["manufacturer"], product["sku"]) for product in c_products} == {
        ("GRIPPS", "H01150"),
        ("3M", "1500028"),
    }
    assert len({product["manufacturer"] for product in c_products}) == 2
    assert all(
        any("non_captive" in archetype for archetype in product["archetypes"])
        for product in c_products
    )
    assert all(
        "fit" in " ".join(product["required_core_changes"]).lower()
        for product in c_products
    )


def test_required_pairing_reuses_existing_core_without_becoming_a_c_gap() -> None:
    paired_products = [
        product
        for product in _load(V2_PATH)["products"]
        if "required_pairing" in product["archetypes"]
    ]

    assert {(product["manufacturer"], product["sku"]) for product in paired_products} == {
        ("3M", "1500007"),
    }
    assert all(product["classification"] == "B" for product in paired_products)
    assert all("multi_component_assembly" in product["archetypes"] for product in paired_products)


def test_replacement_ergodyne_case_is_a_genuinely_different_tether_family() -> None:
    product = next(
        product
        for product in _load(V2_PATH)["products"]
        if product["manufacturer"] == "Ergodyne" and product["sku"] == "19301"
    )

    assert product["model"] == "Squids 3001"
    assert product["product_type"] == "Tether"
    assert product["classification"] == "B"
    assert {"retractable_tether", "directional_endpoints", "cinch_loop"}.issubset(
        set(product["archetypes"])
    )
    assert "wrap" not in product["archetypes"]
    assert "required_pairing" not in product["archetypes"]
