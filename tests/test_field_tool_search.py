import pytest

from tetherlens_ingest.field_recommendation import (
    FieldRecommendationCatalogue,
    FieldToolCatalogueEntry,
)
from tetherlens_ingest.field_tool_search import candidate_tool_refs_from_text_search


def _tool(tool_ref: str, display_name: str) -> FieldToolCatalogueEntry:
    return FieldToolCatalogueEntry(
        tool_ref=tool_ref,
        display_name=display_name,
    )


def test_exact_sku_text_search_returns_only_catalogued_tool_ref() -> None:
    catalogue = FieldRecommendationCatalogue(
        tools=[
            _tool(
                "Milwaukee:48-22-7215",
                "Milwaukee 48-22-7215 14L Aluminum Pipe Wrench",
            ),
            _tool(
                "Milwaukee:48-22-7214",
                'Milwaukee 48-22-7214 14" Aluminum Pipe Wrench',
            ),
        ]
    )

    assert candidate_tool_refs_from_text_search("48-22-7215", catalogue) == [
        "Milwaukee:48-22-7215"
    ]
    assert candidate_tool_refs_from_text_search("milwaukee 48 22 7215", catalogue) == [
        "Milwaukee:48-22-7215"
    ]


def test_text_search_can_return_bounded_shortlist_without_confidence_ranking() -> None:
    catalogue = FieldRecommendationCatalogue(
        tools=[
            _tool(
                "Milwaukee:48-22-7215",
                "Milwaukee 48-22-7215 14L Aluminum Pipe Wrench",
            ),
            _tool(
                "Milwaukee:48-22-7214",
                'Milwaukee 48-22-7214 14" Aluminum Pipe Wrench',
            ),
            _tool("Hilti:2293133", "Hilti 2293133 Rotary Hammer"),
        ]
    )

    assert candidate_tool_refs_from_text_search("milwaukee pipe wrench", catalogue) == [
        "Milwaukee:48-22-7215",
        "Milwaukee:48-22-7214",
    ]
    assert candidate_tool_refs_from_text_search(
        "milwaukee pipe wrench",
        catalogue,
        max_candidates=1,
    ) == ["Milwaukee:48-22-7215"]


def test_text_search_does_not_prefix_or_fuzzy_match_identifiers() -> None:
    catalogue = FieldRecommendationCatalogue(
        tools=[
            _tool(
                "Milwaukee:48-22-7215",
                "Milwaukee 48-22-7215 14L Aluminum Pipe Wrench",
            )
        ]
    )

    assert candidate_tool_refs_from_text_search("48-22-721", catalogue) == []
    assert candidate_tool_refs_from_text_search("Milwaukie 48-22-7215", catalogue) == []
    assert candidate_tool_refs_from_text_search("---", catalogue) == []


def test_text_search_preserves_unicode_identity_tokens() -> None:
    catalogue = FieldRecommendationCatalogue(
        tools=[
            _tool("Müller:M100", "Müller M100 Wrench"),
            _tool("Möller:M200", "Möller M200 Wrench"),
            _tool("牧田:TD001", "牧田 TD001 充电冲击起子"),
            _tool("Unicode:H100", "हिंदी H100 Drill"),
            _tool("Unicode:H200", "हिदी H200 Drill"),
        ]
    )

    assert candidate_tool_refs_from_text_search("Müller", catalogue) == ["Müller:M100"]
    assert candidate_tool_refs_from_text_search("Möller", catalogue) == ["Möller:M200"]
    assert candidate_tool_refs_from_text_search("牧田 TD001", catalogue) == ["牧田:TD001"]

    # Unicode normalization keeps canonically equivalent user input searchable without
    # stripping the distinguishing accented letter.
    assert candidate_tool_refs_from_text_search("Mu\u0308ller M100", catalogue) == [
        "Müller:M100"
    ]

    # Combining vowel signs and diacritics remain part of the identity token rather
    # than collapsing distinct Devanagari strings to the same letter-only tokens.
    assert candidate_tool_refs_from_text_search(
        "हिंदी",
        catalogue,
        max_candidates=1,
    ) == ["Unicode:H100"]
    assert candidate_tool_refs_from_text_search(
        "हिदी",
        catalogue,
        max_candidates=1,
    ) == ["Unicode:H200"]


def test_text_search_rejects_non_positive_candidate_limit() -> None:
    catalogue = FieldRecommendationCatalogue()

    with pytest.raises(ValueError, match="positive integer"):
        candidate_tool_refs_from_text_search("Milwaukee", catalogue, max_candidates=0)
    with pytest.raises(ValueError, match="positive integer"):
        candidate_tool_refs_from_text_search("Milwaukee", catalogue, max_candidates=True)
