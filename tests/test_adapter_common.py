import re

from tetherlens_ingest.adapters.common import bounded_record_for_identifier


SKU_MARKER = re.compile(r"\b\d{2}-\d{2}-\d{4}\b")


def test_bounded_record_keeps_repeated_selected_identifier_until_different_record() -> None:
    text = "\n".join(
        [
            "48-22-7215 metadata title",
            "overview",
            "48-22-7215 product heading",
            "Tether-ready lanyard hole",
            "48-22-7216 related product",
            "Tether-ready handle loop",
        ]
    )

    record = bounded_record_for_identifier(text, "48-22-7215", SKU_MARKER)

    assert record is not None
    assert record.count("48-22-7215") == 2
    assert "Tether-ready lanyard hole" in record
    assert "48-22-7216" not in record
    assert "Tether-ready handle loop" not in record


def test_bounded_record_fails_closed_when_identifier_is_not_a_record_marker() -> None:
    text = "48-22-7214 first record\n48-22-7216 second record"

    assert bounded_record_for_identifier(text, "48-22-7215", SKU_MARKER) is None
