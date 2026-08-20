from tetherlens_ingest.benchmark import score_extraction_product


def test_forbidden_claim_with_value_only_rejects_that_value():
    golden = {
        "products": {
            "Example:X1B": {
                "expected_claims": [
                    {
                        "subject_type": "tether_connection_point",
                        "subject_ref": "connection_point_2",
                        "property_key": "connection_point.interface_type",
                        "value": "loop",
                    }
                ],
                "forbidden_claims": [
                    {
                        "subject_type": "tether_connection_point",
                        "subject_ref": "connection_point_2",
                        "property_key": "connection_point.interface_type",
                        "value": "carabiner",
                    }
                ],
                "ignored_claims": [],
            }
        }
    }

    passing = score_extraction_product(
        "Example",
        "X1B",
        [{
            "subject_type": "tether_connection_point",
            "subject_ref": "connection_point_2",
            "property_key": "connection_point.interface_type",
            "value": "loop",
        }],
        golden,
    )
    assert passing["forbidden_hits"] == []
    assert passing["precision"] == 1.0
    assert passing["recall"] == 1.0

    failing = score_extraction_product(
        "Example",
        "X1B",
        [
            {
                "subject_type": "tether_connection_point",
                "subject_ref": "connection_point_2",
                "property_key": "connection_point.interface_type",
                "value": "loop",
            },
            {
                "subject_type": "tether_connection_point",
                "subject_ref": "connection_point_2",
                "property_key": "connection_point.interface_type",
                "value": "carabiner",
            },
        ],
        golden,
    )
    assert len(failing["forbidden_hits"]) == 1
    assert failing["forbidden_hits"][0]["claim"]["value"] == "carabiner"


def test_forbidden_claim_without_value_remains_property_wildcard():
    golden = {
        "products": {
            "Example:X1C": {
                "expected_claims": [],
                "forbidden_claims": [
                    {
                        "subject_type": "tether_connection_point",
                        "subject_ref": "connection_point_2",
                        "property_key": "connection_point.interface_type",
                    }
                ],
                "ignored_claims": [],
            }
        }
    }

    score = score_extraction_product(
        "Example",
        "X1C",
        [{
            "subject_type": "tether_connection_point",
            "subject_ref": "connection_point_2",
            "property_key": "connection_point.interface_type",
            "value": "loop",
        }],
        golden,
    )
    assert len(score["forbidden_hits"]) == 1
