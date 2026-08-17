from tetherlens_ingest.benchmark import (
    score_acquisition_product,
    score_extraction_product,
    score_recommendation_data_product,
    summarize_acquisition,
    summarize_acquisition_scores,
    summarize_extraction_scores,
    summarize_recommendation_data_scores,
)


def test_acquisition_scoring_requires_discovery_and_forbids_seed_fallback():
    golden = {
        "products": {
            "Example:X0": {
                "acquisition_expectations": {
                    "required_observations": [
                        {"code": "RELATED_SOURCES_DISCOVERED", "value": 2}
                    ],
                    "forbidden_observations": [
                        {"code": "RELATED_SOURCES_SEEDED"}
                    ],
                }
            }
        }
    }
    passing = score_acquisition_product(
        "Example",
        "X0",
        [{"code": "RELATED_SOURCES_DISCOVERED", "value": 2}],
        golden,
    )
    assert passing["passed"] is True
    assert passing["missing_required"] == []
    assert passing["forbidden_hits"] == []

    failing = score_acquisition_product(
        "Example",
        "X0",
        [{"code": "RELATED_SOURCES_SEEDED", "value": 2}],
        golden,
    )
    assert failing["passed"] is False
    assert failing["missing_required"] == [{"code": "RELATED_SOURCES_DISCOVERED", "value": 2}]
    assert len(failing["forbidden_hits"]) == 1


def test_extraction_scoring_counts_forbidden_claim_as_false_positive():
    golden = {
        "products": {
            "Example:X1": {
                "expected_claims": [
                    {"subject_type": "product", "subject_ref": "self", "property_key": "rated_capacity_kg", "value": 5.0}
                ],
                "forbidden_claims": [
                    {"property_key": "connector.opening_action_count"}
                ],
                "ignored_claims": [],
            }
        }
    }
    claims = [
        {"subject_type": "product", "subject_ref": "self", "property_key": "rated_capacity_kg", "value": 5.0},
        {"subject_type": "connector_spec", "subject_ref": "x", "property_key": "connector.opening_action_count", "value": 3},
    ]
    score = score_extraction_product("Example", "X1", claims, golden)
    assert score["true_positive_count"] == 1
    assert score["false_positive_count"] == 1
    assert len(score["forbidden_hits"]) == 1
    assert score["precision"] == 0.5
    assert score["recall"] == 1.0


def test_extraction_scoring_is_strict_for_unexpected_property_keys():
    golden = {
        "products": {
            "Example:X2": {
                "expected_claims": [
                    {"subject_type": "product", "subject_ref": "self", "property_key": "rated_capacity_kg", "value": 5.0}
                ],
                "forbidden_claims": [],
                "ignored_claims": [],
            }
        }
    }
    claims = [
        {"subject_type": "product", "subject_ref": "self", "property_key": "rated_capacity_kg", "value": 5.0},
        {"subject_type": "product", "subject_ref": "self", "property_key": "invented_field", "value": "bad"},
    ]
    score = score_extraction_product("Example", "X2", claims, golden)
    assert score["true_positive_count"] == 1
    assert score["false_positive_count"] == 1
    assert score["unexpected_extracted"][0]["property_key"] == "invented_field"
    assert score["precision"] == 0.5


def test_extraction_scoring_respects_subject_identity():
    golden = {
        "products": {
            "Example:X3": {
                "expected_claims": [
                    {"subject_type": "physical_interface", "subject_ref": "anchor", "property_key": "rated_capacity_kg", "value": 5.0}
                ],
                "forbidden_claims": [],
                "ignored_claims": [],
            }
        }
    }
    claims = [
        {"subject_type": "product", "subject_ref": "self", "property_key": "rated_capacity_kg", "value": 5.0}
    ]
    score = score_extraction_product("Example", "X3", claims, golden)
    assert score["true_positive_count"] == 0
    assert score["false_positive_count"] == 1
    assert score["false_negative_count"] == 1


def test_recommendation_data_is_independent_from_extraction_quality():
    golden = {
        "products": {
            "Example:X4": {
                "expected_claims": [
                    {"subject_type": "product", "subject_ref": "self", "property_key": "tool_body_mass_kg", "value": 1.3}
                ],
                "forbidden_claims": [],
                "ignored_claims": [],
                "recommendation_data": {
                    "baseline_requirements": [
                        {
                            "name": "operational_mass",
                            "any_of": [{"subject_type": "product", "subject_ref": "self", "property_key": "operational_mass_kg"}],
                            "gap_if_missing": "document_join",
                        }
                    ],
                    "known_gaps": [{"category": "document_join", "field": "battery"}],
                },
            }
        }
    }
    claims = [
        {"subject_type": "product", "subject_ref": "self", "property_key": "tool_body_mass_kg", "value": 1.3}
    ]
    extraction = score_extraction_product("Example", "X4", claims, golden)
    coverage = score_recommendation_data_product("Example", "X4", claims, golden)
    assert extraction["precision"] == 1.0
    assert extraction["recall"] == 1.0
    assert coverage["baseline_complete"] is False
    assert coverage["requirement_results"][0]["gap_if_missing"] == "document_join"


def test_summary_helpers_use_separate_dimensions():
    acquisition = summarize_acquisition([
        {"manufacturer": "A", "acquisition_succeeded": True, "artifact_count": 1, "acquisition_observations": []},
        {"manufacturer": "A", "acquisition_succeeded": False, "artifact_count": 0, "acquisition_observations": []},
    ])
    assert acquisition["acquisition_rate"] == 0.5

    acquisition_quality = summarize_acquisition_scores([
        {"scored": True, "passed": True, "missing_required": [], "forbidden_hits": []},
        {"scored": True, "passed": False, "missing_required": [{"code": "X"}], "forbidden_hits": [{"code": "Y"}]},
    ])
    assert acquisition_quality["products_passed"] == 1
    assert acquisition_quality["products_failed"] == 1
    assert acquisition_quality["missing_required_count"] == 1
    assert acquisition_quality["forbidden_hit_count"] == 1

    extraction = summarize_extraction_scores([
        {"scored": True, "true_positive_count": 3, "false_positive_count": 1, "false_negative_count": 1, "forbidden_hits": [], "unexpected_extracted": [{}]},
        {"scored": True, "true_positive_count": 1, "false_positive_count": 0, "false_negative_count": 1, "forbidden_hits": [{"x": 1}], "unexpected_extracted": []},
    ])
    assert extraction["micro_precision"] == 0.8
    assert extraction["micro_recall"] == 4 / 6

    recommendation = summarize_recommendation_data_scores([
        {"scored": True, "baseline_complete": True, "requirements_total": 1, "requirements_present": 1, "requirement_results": [{"present": True}], "known_gaps": []},
        {"scored": True, "baseline_complete": False, "requirements_total": 1, "requirements_present": 0, "requirement_results": [{"present": False, "gap_if_missing": "source_blocked"}], "known_gaps": [{"category": "source_blocked"}]},
    ])
    assert recommendation["baseline_product_coverage"] == 0.5
    assert recommendation["requirement_coverage"] == 0.5
    assert recommendation["missing_requirement_categories"] == {"source_blocked": 1}
