import re

import pytest

from tetherlens_ingest.adapters.evidence_context import (
    evidence_sentence_for_match,
    html_evidence_blocks,
    html_evidence_clauses,
    match_is_interrogative,
    match_is_locally_contradicted,
)


_GRIPPS_RELATION = re.compile(
    r"\bsuitable\s+for\s+use\s+with\s+our\b[^.;!?]{0,120}\bH01067\b"
    r"[^.;!?]{0,80}\bwrist\s+tethers?\b",
    re.I,
)
_GRIPPS_SUBJECTS = (
    r"\bH01067\b",
    r"\b(?:this|the)\s+tether\b",
    r"\b(?:it|them)\b",
    r"\bthis\s+anchor\b",
    r"\b(?:that|this)\s+way\b",
)
_QUICK_CLIP_RELATION = re.compile(
    r"\bQuick\s*Clip\s+can\s+be\s+attached\s+to\s+a\s+D[\s-]?Ring\b",
    re.I,
)
_QUICK_CLIP_SUBJECTS = (
    r"\b(?:the\s+)?Quick\s*Clip\b",
    r"\b(?:the\s+)?D[\s-]?Ring\b",
    r"\b(?:it|(?:the|this)\s+attachment)\b",
    r"\b(?:that|this)\s+way\b",
)


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("Suitable for use with our H01067 wrist tethers.", False),
        ("Not suitable for use with our H01067 wrist tethers.", True),
        ("No product is suitable for use with our H01067 wrist tethers.", True),
        (
            "No special tools are required, this product is suitable for use with our "
            "H01067 wrist tethers.",
            False,
        ),
        ("Not only suitable for use with our H01067 wrist tethers.", False),
        (
            "This anchor does not contain metal and Suitable for use with our "
            "H01067 wrist tethers.",
            False,
        ),
        (
            "Suitable for use with our H01060 wrist tethers, not H01067 wrist tethers.",
            True,
        ),
        (
            "Suitable for use with our H01060 wrist tethers, except H01067 wrist tethers.",
            True,
        ),
        (
            "Suitable for use with our H01060 wrist tethers, but H01067 is not "
            "suitable for wrist tethers.",
            True,
        ),
        (
            "Suitable for use with our H01067 wrist tethers, but must not be "
            "connected that way.",
            True,
        ),
        (
            "Suitable for use with our H01067 wrist tethers, but must not be used.",
            True,
        ),
        (
            "Suitable for use with our H01067 wrist tethers, but this tether must not "
            "be used that way.",
            True,
        ),
        (
            "Suitable for use with our H01067 wrist tethers. "
            "Do not connect this tether to the anchor.",
            True,
        ),
        (
            "Suitable for use with our H01067 wrist tethers. "
            "However, do not connect it this way.",
            True,
        ),
        (
            "Suitable for use with our H01067 wrist tethers. "
            "H01067 is not compatible with this anchor.",
            True,
        ),
        (
            "Suitable for use with our H01067 wrist tethers. "
            "H01067 isn't suitable for this anchor.",
            True,
        ),
        (
            "Suitable for use with our H01067 wrist tethers. "
            "H01067 is incompatible with this anchor.",
            True,
        ),
        (
            "Suitable for use with our H01067 wrist tethers. "
            "H01067 is unsuitable for this anchor.",
            True,
        ),
        (
            "Suitable for use with our H01067 wrist tethers.\n"
            "Do not connect this tether to the anchor.",
            False,
        ),
    ),
)
def test_local_contradiction_matrix_for_product_pairing(text: str, expected: bool) -> None:
    match = _GRIPPS_RELATION.search(text)
    assert match is not None
    assert (
        match_is_locally_contradicted(
            text,
            match,
            subject_patterns=_GRIPPS_SUBJECTS,
        )
        is expected
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("The Quick Clip can be attached to a D Ring.", False),
        (
            "No special tools are required, the Quick Clip can be attached to a D Ring.",
            False,
        ),
        (
            "The Quick Clip can be attached to a D Ring without removing gloves.",
            False,
        ),
        (
            "Do not assume the Quick Clip can be attached to a D Ring.",
            True,
        ),
        (
            "It is not established that the Quick Clip can be attached to a D Ring.",
            True,
        ),
        (
            "The Quick Clip can be attached to a D Ring, but must not be used that way.",
            True,
        ),
        (
            "The Quick Clip can be attached to a D Ring, but must not be used.",
            True,
        ),
        (
            "The Quick Clip can be attached to a D Ring, but it must not be used that way.",
            True,
        ),
        (
            "The Quick Clip can be attached to a D Ring. "
            "However, do not connect it this way.",
            True,
        ),
        (
            "The Quick Clip can be attached to a D Ring. "
            "The Quick Clip is incompatible with the D Ring.",
            True,
        ),
    ),
)
def test_local_contradiction_matrix_for_interface_relation(text: str, expected: bool) -> None:
    match = _QUICK_CLIP_RELATION.search(text)
    assert match is not None
    assert (
        match_is_locally_contradicted(
            text,
            match,
            subject_patterns=_QUICK_CLIP_SUBJECTS,
        )
        is expected
    )


def test_trailing_predicate_negation_is_shared_even_without_subject_patterns() -> None:
    text = "Use on curved surfaces is not supported."
    match = re.search(r"\buse\s+on\s+curved\s+surfaces\b", text, re.I)
    assert match is not None
    assert match_is_locally_contradicted(text, match)


def test_html_evidence_rendering_preserves_inline_text_and_hard_block_boundaries() -> None:
    html = (
        "<p>The Quick <strong>Clip</strong> can be attached to a D Ring.</p>"
        "<p>Do not connect it this way.</p>"
    )

    blocks = html_evidence_blocks(html)
    clauses = html_evidence_clauses(html)

    assert "The Quick Clip can be attached to a D Ring." in blocks
    assert "Do not connect it this way." in blocks
    assert not any(
        "D Ring. Do not connect" in block
        for block in blocks
    )
    assert "The Quick Clip can be attached to a D Ring." in clauses
    assert "Do not connect it this way." in clauses


def test_sentence_context_distinguishes_questions_from_assertions() -> None:
    text = "Can the Quick Clip be attached to a D Ring? It can be used elsewhere."
    match = re.search(r"\bQuick\s+Clip\s+be\s+attached\s+to\s+a\s+D\s+Ring\b", text, re.I)
    assert match is not None

    assert evidence_sentence_for_match(text, match) == (
        "Can the Quick Clip be attached to a D Ring?"
    )
    assert match_is_interrogative(text, match)
