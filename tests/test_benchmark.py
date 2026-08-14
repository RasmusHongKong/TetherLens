from tetherlens_ingest.benchmark import score_product, summarize_scores


def test_golden_scoring_counts_forbidden_claim_as_false_positive():
    golden = {
        "products": {
            "Example:X1": {
                "scored_property_keys": ["rated_capacity_kg", "connector.opening_action_count"],
                "expected": [
                    {"subject_type": "product", "subject_ref": "self", "property_key": "rated_capacity_kg", "value": 5.0}
                ],
                "forbidden": [
                    {"property_key": "connector.opening_action_count"}
                ],
            }
        }
    }
    claims = [
        {"subject_type": "product", "subject_ref": "self", "property_key": "rated_capacity_kg", "value": 5.0},
        {"subject_type": "connector_spec", "subject_ref": "x", "property_key": "connector.opening_action_count", "value": 3},
    ]
    score = score_product("Example", "X1", claims, golden)
    assert score["true_positive_count"] == 1
    assert score["false_positive_count"] == 1
    assert len(score["forbidden_hits"]) == 1
    assert score["precision"] == 0.5
    assert score["recall"] == 1.0


def test_golden_scoring_respects_subject_identity():
    golden = {
        "products": {
            "Example:X2": {
                "scored_property_keys": ["rated_capacity_kg"],
                "expected": [
                    {"subject_type": "physical_interface", "subject_ref": "anchor", "property_key": "rated_capacity_kg", "value": 5.0}
                ],
                "forbidden": [],
            }
        }
    }
    claims = [
        {"subject_type": "product", "subject_ref": "self", "property_key": "rated_capacity_kg", "value": 5.0}
    ]
    score = score_product("Example", "X2", claims, golden)
    assert score["true_positive_count"] == 0
    assert score["false_positive_count"] == 1
    assert score["false_negative_count"] == 1


def test_summary_uses_micro_counts():
    summary = summarize_scores([
        {"scored": True, "true_positive_count": 3, "false_positive_count": 1, "false_negative_count": 1, "forbidden_hits": []},
        {"scored": True, "true_positive_count": 1, "false_positive_count": 0, "false_negative_count": 1, "forbidden_hits": [{"x": 1}]},
    ])
    assert summary["true_positive_count"] == 4
    assert summary["false_positive_count"] == 1
    assert summary["false_negative_count"] == 2
    assert summary["micro_precision"] == 0.8
    assert summary["micro_recall"] == 4 / 6
    assert summary["forbidden_hit_count"] == 1
