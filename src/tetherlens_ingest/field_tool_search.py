from __future__ import annotations

import re
import unicodedata

from .field_recommendation import FieldRecommendationCatalogue


# Python's Unicode-aware ``\w`` includes letters/digits plus underscore. Excluding
# underscore keeps punctuation/separators as boundaries while retaining non-ASCII
# alphanumeric identity text.
_SEARCH_TOKEN = re.compile(r"[^\W_]+")


def candidate_tool_refs_from_text_search(
    query: str,
    catalogue: FieldRecommendationCatalogue,
    *,
    max_candidates: int = 5,
) -> list[str]:
    """Return a bounded advisory shortlist from deterministic catalogue text search.

    Search is deliberately lexical rather than fuzzy or semantic. Case and punctuation
    are normalized into Unicode alphanumeric tokens, and every query token must be
    present in the Tool's ``tool_ref`` or ``display_name``. Matching preserves catalogue
    order and never resolves or confirms a Tool; callers must pass the returned refs
    through the existing explicit-confirmation field boundary.
    """

    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int):
        raise ValueError("max_candidates must be a positive integer")
    if max_candidates <= 0:
        raise ValueError("max_candidates must be a positive integer")

    query_tokens = _tokens(query)
    if not query_tokens:
        return []

    candidate_refs: list[str] = []
    for tool in catalogue.tools:
        searchable_tokens = set(_tokens(tool.tool_ref))
        searchable_tokens.update(_tokens(tool.display_name))
        if all(token in searchable_tokens for token in query_tokens):
            candidate_refs.append(tool.tool_ref)
            if len(candidate_refs) >= max_candidates:
                break

    return candidate_refs


def _tokens(value: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return tuple(_SEARCH_TOKEN.findall(normalized))
