from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString, Tag


_BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}
_BLOCK_MARKER = "\u241e"

_EPISTEMIC_DENIAL_PREFIX = re.compile(
    r"(?:"
    r"\b(?:do|does|did)\s+not\s+(?:assume|infer|conclude|interpret|treat|read|take)\b"
    r"|\b(?:cannot|can't)\s+(?:assume|infer|conclude|interpret|treat|read|take)\b"
    r"|\b(?:is|are|was|were)\s+not\s+(?:established|confirmed|stated|clear)\b"
    r")",
    re.I,
)
_PREFIX_NEGATION = re.compile(
    r"\b(?:"
    r"not|never|cannot|can't|"
    r"(?:do|does|did)\s+not|don't|doesn't|didn't|"
    r"(?:must|should|shall|may|can|could|would)\s+not|"
    r"mustn't|shouldn't|couldn't|wouldn't|"
    r"(?:is|are|was|were)\s+not|isn't|aren't|wasn't|weren't"
    r")\b[^.!?;\n]{0,100}$",
    re.I,
)
_TRAILING_NEGATION = re.compile(
    r"^(?:(?:is|are|was|were|be|being)\s+)?(?:not|never)\s+"
    r"(?:supported|required|recommended|suitable|compatible|permitted|allowed|intended)\b",
    re.I,
)
_NEGATIVE_MODAL = (
    r"(?:"
    r"(?:must|should|shall|may|can|could|would)\s+not|"
    r"cannot|can't|couldn't|wouldn't|shouldn't|mustn't|"
    r"(?:do|does|did)\s+not|don't|doesn't|didn't|"
    r"never"
    r")"
)
_RELATION_ACTION = (
    r"(?:use|used|using|attach|attached|attaching|connect|connected|connecting|"
    r"anchor|anchored|anchoring|tether|tethered|tethering|clip|clipped|clipping|hook|hooked)"
)
_NEGATIVE_RELATION = (
    r"(?:"
    r"(?:(?:is|are|was|were)\s+not|isn't|aren't|wasn't|weren't)\s+"
    r"(?:suitable|compatible)|"
    r"(?:is|are|was|were)\s+(?:unsuitable|incompatible)"
    r")"
)
_EXCLUSION = r"(?:but\s+not|not|never|except(?:ing)?|excluding?|other\s+than)"


def html_evidence_blocks(html: str) -> list[str]:
    """Return normalized prose blocks without joining separate HTML block elements."""

    soup = BeautifulSoup(html, "html.parser")
    rendered = _render_with_block_markers(soup)
    return [
        normalized
        for block in rendered.split(_BLOCK_MARKER)
        if (normalized := re.sub(r"\s+", " ", block).strip())
    ]


def html_evidence_clauses(html: str) -> list[str]:
    """Return sentence/clause evidence units without joining separate HTML blocks.

    Inline markup remains inside the same evidence unit, while semantic block elements
    are hard boundaries. This is intended for prose extractors that must not create one
    apparent manufacturer statement by joining text from adjacent paragraphs, list
    items, table cells, or headings.
    """

    clauses: list[str] = []
    for block in html_evidence_blocks(html):
        clauses.extend(
            part.strip()
            for part in re.split(r"(?<=[.!?;])\s+", block)
            if part.strip()
        )
    return clauses


def match_is_locally_contradicted(
    text: str,
    match: re.Match[str],
    *,
    subject_patterns: tuple[str, ...] = (),
    prefix_chars: int = 140,
    suffix_chars: int = 180,
) -> bool:
    """Return whether nearby grammar invalidates a positive-looking evidence match.

    The positive evidence pattern remains the caller's responsibility. This helper owns
    only manufacturer-neutral contradiction semantics around a match:

    - prefix/assertion negation in the current clause;
    - exclusions or negative relation assertions involving caller-supplied referents;
    - immediate trailing predicate negation;
    - same-sentence or immediately adjacent action prohibitions; and
    - nearby not-suitable / not-compatible / unsuitable / incompatible assertions
      about the same referent.

    The word "without" is deliberately not a generic negator: wording such as
    "without removing gloves" must not veto otherwise affirmative evidence. Likewise
    "not only" is additive rather than contradictory.

    The suffix scan is anchored to what immediately follows the match and never crosses
    a newline, which callers may use as a hard block boundary.
    """

    if match.start() < 0 or match.end() > len(text):
        raise ValueError("match must belong to text")

    prefix = _bounded_prefix(text, match.start(), prefix_chars)
    suffix = _bounded_suffix(text, match.end(), suffix_chars)
    matched_text = match.group(0)

    if _EPISTEMIC_DENIAL_PREFIX.search(prefix) is not None:
        return True

    predicate_prefix = _local_predicate_prefix(prefix)
    predicate_prefix = re.sub(r"\bnot\s+only\b", "", predicate_prefix, flags=re.I)
    if _PREFIX_NEGATION.search(predicate_prefix) is not None:
        return True

    if _TRAILING_NEGATION.search(suffix) is not None:
        return True

    if not subject_patterns:
        return False

    subject = "(?:" + "|".join(subject_patterns) + ")"
    if _subject_is_excluded_or_denied(matched_text, subject):
        return True
    if _negative_relation_assertion(matched_text, subject):
        return True
    if _post_match_action_prohibition(suffix, subject):
        return True
    if _post_match_relation_contradiction(suffix, subject):
        return True
    return False


def _bounded_prefix(text: str, match_start: int, limit: int) -> str:
    boundary = max(
        text.rfind(".", 0, match_start),
        text.rfind("!", 0, match_start),
        text.rfind("?", 0, match_start),
        text.rfind(";", 0, match_start),
        text.rfind("\n", 0, match_start),
    )
    return re.sub(r"\s+", " ", text[boundary + 1 : match_start][-limit:]).strip()


def _bounded_suffix(text: str, match_end: int, limit: int) -> str:
    suffix = text[match_end : match_end + limit]
    newline = suffix.find("\n")
    if newline >= 0:
        suffix = suffix[:newline]
    return re.sub(r"\s+", " ", suffix).strip()


def _local_predicate_prefix(prefix: str) -> str:
    """Return the coordinated predicate segment nearest the positive match."""

    parts = re.split(
        r"\b(?:and|but|yet|however|although|though)\b",
        prefix,
        flags=re.I,
    )
    return parts[-1].strip(" ,:")


def _subject_is_excluded_or_denied(text: str, subject: str) -> bool:
    before = re.compile(
        rf"\b{_EXCLUSION}\b[^.!?;]{{0,60}}{subject}",
        re.I,
    )
    after = re.compile(
        rf"{subject}[^.!?;]{{0,60}}"
        rf"(?:\b(?:not|never|except(?:ed)?|excluded)\b|{_NEGATIVE_RELATION})",
        re.I,
    )
    return before.search(text) is not None or after.search(text) is not None


def _negative_relation_assertion(text: str, subject: str) -> bool:
    return re.search(
        rf"{subject}[^.!?;]{{0,60}}{_NEGATIVE_RELATION}",
        text,
        re.I,
    ) is not None


def _post_match_action_prohibition(suffix: str, subject: str) -> bool:
    if not suffix:
        return False
    lead = (
        r"^\s*(?:[,;.!?]\s*)?"
        r"(?:(?:but|and|however|yet|although|though)\b[,:]?\s*)?"
    )
    prohibition = re.compile(
        rf"{lead}{_NEGATIVE_MODAL}\b[^.!?;]{{0,100}}"
        rf"{_RELATION_ACTION}\w*\b[^.!?;]{{0,100}}{subject}",
        re.I,
    )
    reverse_target = re.compile(
        rf"{lead}{_NEGATIVE_MODAL}\b[^.!?;]{{0,100}}{subject}"
        rf"[^.!?;]{{0,100}}{_RELATION_ACTION}\w*\b",
        re.I,
    )
    return prohibition.search(suffix) is not None or reverse_target.search(suffix) is not None


def _post_match_relation_contradiction(suffix: str, subject: str) -> bool:
    if not suffix:
        return False
    lead = (
        r"^\s*(?:[,;.!?]\s*)?"
        r"(?:(?:but|and|however|yet|although|though)\b[,:]?\s*)?"
    )
    return re.search(
        rf"{lead}{subject}[^.!?;]{{0,60}}{_NEGATIVE_RELATION}",
        suffix,
        re.I,
    ) is not None


def _render_with_block_markers(node: Tag | NavigableString) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    parts = [_render_with_block_markers(child) for child in node.children]
    text = " ".join(part for part in parts if part)
    if getattr(node, "name", None) in _BLOCK_TAGS:
        return f"{_BLOCK_MARKER}{text}{_BLOCK_MARKER}"
    return text
