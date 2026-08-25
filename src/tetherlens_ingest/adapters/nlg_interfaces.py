from __future__ import annotations

import re

from bs4 import BeautifulSoup

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
)
from .nlg_compat import NLGAdapter as BaseNLGAdapter


_BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
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

_RING = r"d[\s-]?rings?"
_TETHER_POINT = r"(?:an?\s+|the\s+)?(?:secure\s+|ultra[-\s]?secure\s+|permanent\s+)?tether\s+point"
_LANYARD = r"(?:an?\s+|the\s+)?(?:tool\s+)?lanyards?"
_WORD = r"[\w®™°/%+.-]+"

# A D-ring subject/complement may carry a few compact product descriptors, but the
# modifier slots must not swallow determiners, prepositions, competing interface heads,
# coordinators, or finite/modal verbs. That keeps ``D Ring`` as the noun-phrase head:
# ``Mini Adhesive D Ring`` is valid, while ``strap behind the D Ring`` is not.
_NON_RING_MODIFIER = (
    r"(?:"
    r"the|this|our|a|an|"
    r"loop|strap|cord|lanyard|tether|point|ring|connector|carabiner|clip|hook|bracket|"
    r"behind|before|after|above|below|under|over|around|through|via|with|without|"
    r"on|in|into|onto|at|by|from|for|of|to|near|beside|between|within|outside|inside|"
    r"and|but|while|whereas|or|"
    r"is|are|was|were|be|been|being|has|have|had|do|does|did|"
    r"can|cannot|could|may|might|must|should|shall|will|would"
    r")"
)
_RING_MODIFIER = rf"(?!{_NON_RING_MODIFIER}\b){_WORD}"
_RING_NOUN_PHRASE = rf"(?:(?:the|this|our|a)\s+)?(?:{_RING_MODIFIER}\s+){{0,3}}{_RING}"
_RING_SUBJECT = _RING_NOUN_PHRASE
_RING_COMPLEMENT = _RING_NOUN_PHRASE

# Only an explicitly affirmative introductory construction may precede a D-ring
# subject. This is intentionally an allowlist, not a generic short-prefix rule: direct
# interface claims must not be inferred through epistemic/denial wrappers such as
# ``It cannot be assumed that ...`` or ``It is unclear whether ...``.
_AFFIRMATIVE_INTRO = re.compile(
    rf"^(?:"
    rf"(?:utilising|utilizing|using|featuring|incorporating|leveraging|employing)\s+"
    rf"(?P<body_a>(?:{_WORD}\s*){{1,5}})"
    rf"|(?:built|made|designed|engineered|equipped)\s+with\s+"
    rf"(?P<body_b>(?:{_WORD}\s*){{1,5}})"
    rf")$",
    re.I,
)
_AFFIRMATIVE_INTRO_CONTENT_FORBIDDEN = re.compile(
    r"\b(?:"
    r"loop|strap|cord|ring|lanyard|tether|point|connector|carabiner|clip|hook|bracket|"
    r"attach\w*|connect\w*|clip\w*|hook\w*|creat\w*|provid\w*|form\w*|mak\w*|"
    r"avoid\w*|not|never|no|without|cannot|can't|prohibit\w*|forbid\w*|"
    r"unsafe|unsuitable|unclear|uncertain|assum\w*|suppos\w*|believ\w*|suggest\w*|"
    r"may|might|could|possibly|potentially"
    r")\b",
    re.I,
)


class NLGAdapter(BaseNLGAdapter):
    """Add explicit ToolAttachment-provided tether-side interfaces.

    Tool-side installation eligibility remains owned by ``nlg_compat``. This layer
    records the distinct interface the installed ToolAttachment provides only when
    manufacturer copy itself ties a D-ring to the created tether point or lanyard
    connection. The attachment's cinch/retention loop is therefore not confused with
    its tether-side D-ring.
    """

    extractor = "nlg.v0.10"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims = list(super().extract(identity, artifacts))
        if identity.product_type != ProductType.TOOL_ATTACHMENT:
            return claims

        for artifact in artifacts:
            if evidence := _provided_ring_evidence(artifact.body):
                claims.extend(
                    [
                        CandidateClaim(
                            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                            subject_ref="tether_side_ring",
                            property_key="interface.role",
                            value="tool_attachment_tether_side",
                            raw_value=evidence,
                            source_url=artifact.url,
                            evidence_method="manufacturer_stated",
                            extractor=self.extractor,
                            claim_type=ClaimType.DIRECT,
                        ),
                        CandidateClaim(
                            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                            subject_ref="tether_side_ring",
                            property_key="interface.type",
                            value="ring",
                            raw_value=evidence,
                            source_url=artifact.url,
                            evidence_method="manufacturer_stated",
                            extractor=self.extractor,
                            claim_type=ClaimType.DIRECT,
                        ),
                    ]
                )

        return _dedupe_claims(claims)


def _provided_ring_evidence(html: str) -> str | None:
    """Return a tightly bound positive D-ring tether-interface assertion.

    A product title, bare ``D Ring`` label, or co-occurrence of ring/lanyard terms is
    insufficient. HTML is normalized into rendered clauses, then each clause is split
    at strong subject-switch/title boundaries. The remaining grammar accepts only a
    few positive relation shapes in which the D-ring is explicitly the subject or the
    local complement of the tether-point/lanyard relation. Negative wrappers therefore
    do not need a clause-wide token blacklist, and a later predicate owned by another
    subject cannot be accidentally attributed to the D-ring.
    """

    for clause in _rendered_clauses(html):
        for segment in _relation_segments(clause):
            if evidence := _positive_ring_relation_evidence(segment):
                return evidence
    return None


def _positive_ring_relation_evidence(segment: str) -> str | None:
    """Recognize one conservative positive relation with local subject binding."""

    text = re.sub(r"\s+", " ", segment).strip().rstrip(".!?;").strip()
    if not text:
        return None

    subject_match = _bound_ring_subject(text)
    if subject_match is not None:
        predicates = text[subject_match.end() :].strip()
        coordinator = r"(?:^|(?:,\s*)?\b(?:and|but)\s+)"
        relation_patterns = (
            rf"{coordinator}(?P<relation>(?:creates?|provides?|forms?|makes?)\s+{_TETHER_POINT})\b",
            rf"{coordinator}(?P<relation>(?:attaches?|connects?|clips?|hooks?)\s+(?:directly\s+)?(?:(?:to|with)\s+)?{_LANYARD})\b",
        )
        for pattern in relation_patterns:
            if relation_match := re.search(pattern, predicates, re.I):
                return f"{subject_match.group('subject')} {relation_match.group('relation')}"

    usage_match = re.fullmatch(
        rf"(?P<relation>(?:use|using)\s+(?:the\s+)?{_RING}\s+to\s+(?:attach|connect|clip|hook)\w*\s+(?:directly\s+)?(?:(?:to|with)\s+)?{_LANYARD})",
        text,
        re.I,
    )
    if usage_match is not None:
        return usage_match.group("relation")

    # ``Avoid snagging by using the D Ring...`` still contains a positive local
    # instrumental relation: avoidance governs ``snagging``, not D-ring use. Requiring
    # the explicit ``by using`` construction keeps this distinct from ``Avoid using``.
    by_using_match = re.search(
        rf"\b(?P<relation>by\s+using\s+(?:the\s+)?{_RING}\s+to\s+(?:attach|connect|clip|hook)\w*\s+(?:directly\s+)?(?:(?:to|with)\s+)?{_LANYARD})\b",
        text,
        re.I,
    )
    if by_using_match is not None:
        return by_using_match.group("relation")

    tether_point_match = re.fullmatch(
        rf"(?P<relation>{_TETHER_POINT}\s+(?:with|using|via|through)\s+{_RING_COMPLEMENT})",
        text,
        re.I,
    )
    if tether_point_match is not None:
        return tether_point_match.group("relation")

    return None


def _bound_ring_subject(text: str) -> re.Match[str] | None:
    """Find a D-ring-headed subject with at most one affirmative introduction.

    Marketing copy may lead with provenance or technology wording, e.g. ``Utilising
    trusted 3M adhesive technology the Mini Adhesive D Ring creates...``. The prefix
    must match a bounded affirmative introductory construction and its content must not
    introduce a competing interface/relation or epistemic qualification. Arbitrary
    short prefixes are not accepted.
    """

    for match in re.finditer(rf"(?P<subject>{_RING_SUBJECT})\b", text, re.I):
        prefix = text[: match.start()].strip(" ,")
        if not prefix:
            return match

        intro_match = _AFFIRMATIVE_INTRO.fullmatch(prefix)
        if intro_match is None:
            continue
        intro_body = intro_match.group("body_a") or intro_match.group("body_b") or ""
        if _AFFIRMATIVE_INTRO_CONTENT_FORBIDDEN.search(intro_body):
            continue
        return match
    return None


def _relation_segments(clause: str) -> list[str]:
    """Split boundaries that should not share a relation subject.

    ``while``/``whereas`` commonly introduce a contrasting subject. Em/en dashes and
    colons commonly separate a title/feature label from the actual assertion. Ordinary
    ``and``/``but`` stay intact so a D-ring subject can govern a coordinated predicate,
    e.g. ``does not require drilling and creates a secure tether point``.
    """

    segments = re.split(r"\s+[—–]\s+|:\s+", clause)
    out: list[str] = []
    for segment in segments:
        out.extend(
            piece.strip(" ,")
            for piece in re.split(
                r"\s*,?\s*\b(?:while|whereas)\b\s*",
                segment,
                flags=re.I,
            )
            if piece.strip(" ,")
        )
    return out


def _rendered_clauses(html: str) -> list[str]:
    """Normalize HTML while preserving semantic block boundaries.

    ``BeautifulSoup.stripped_strings`` loses the distinction between an inline tag and
    a block boundary because both become separate text nodes. Here inline elements are
    left untouched, while block elements and ``br`` explicitly create separators.
    """

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    for br in soup.find_all("br"):
        br.replace_with("\n")
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.insert_before("\n")
        tag.insert_after("\n")

    text = soup.get_text("", strip=False).replace("\xa0", " ")
    text = re.sub(r"[\t\r\f\v ]+", " ", text)
    text = re.sub(r" *\n+ *", "\n", text)

    clauses: list[str] = []
    for block in text.split("\n"):
        block = block.strip()
        if not block:
            continue
        clauses.extend(
            clause.strip()
            for clause in re.split(r"(?<=[.!?;])\s+", block)
            if clause.strip()
        )
    return clauses


def _dedupe_claims(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    out: list[CandidateClaim] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for claim in claims:
        key = (
            claim.subject_type.value,
            claim.subject_ref,
            claim.property_key,
            str(claim.value),
            claim.unit or "",
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(claim)
    return out
