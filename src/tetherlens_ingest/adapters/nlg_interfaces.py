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


class NLGAdapter(BaseNLGAdapter):
    """Add explicit ToolAttachment-provided tether-side interfaces.

    Tool-side installation eligibility remains owned by ``nlg_compat``. This layer
    records the distinct interface the installed ToolAttachment provides only when
    manufacturer copy itself ties a D-ring to the created tether point or lanyard
    connection. The attachment's cinch/retention loop is therefore not confused with
    its tether-side D-ring.
    """

    extractor = "nlg.v0.9"

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
    """Return strong local evidence that a D-ring is the provided tether interface.

    A product title, a bare ``D Ring`` feature label, or a generic navigation mention
    is insufficient. Inline HTML is normalized into its rendered clause while block
    elements remain hard boundaries. The same sentence/clause must link the D-ring to
    creation of a tether point or to a lanyard connection.
    """

    ring = r"d[\s-]?rings?"
    tether_point = r"(?:secure\s+|ultra[-\s]?secure\s+|permanent\s+)?tether\s+point"
    lanyard = r"(?:tool\s+)?lanyards?"
    gap = r"[^.!?;]"
    patterns = (
        rf"\b{ring}\b{gap}{{0,120}}\b(?:create|provide|form|make)\w*\b{gap}{{0,100}}\b{tether_point}\b",
        rf"\b{tether_point}\b{gap}{{0,80}}\b(?:with|using|via|through)\b{gap}{{0,80}}\b{ring}\b",
        rf"\b{ring}\b{gap}{{0,120}}\b(?:attach|connect|clip|hook)\w*\b{gap}{{0,80}}\b{lanyard}\b",
    )

    for clause in _rendered_clauses(html):
        for pattern in patterns:
            match = re.search(pattern, clause, re.I)
            if match is None or _ring_relation_is_negated(clause, match):
                continue
            return re.sub(r"\s+", " ", match.group(0)).strip()
    return None


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


def _ring_relation_is_negated(clause: str, match: re.Match[str]) -> bool:
    """Reject explicit prohibition of the matched D-ring relationship."""

    matched = match.group(0)
    if re.search(
        r"\b(?:no|not|without|never|cannot|can't|doesn't|does\s+not|prohibited|forbidden|unsafe|unsuitable)\b",
        matched,
        re.I,
    ):
        return True

    ring_match = re.search(r"\bd[\s-]?rings?\b", matched, re.I)
    if ring_match is None:
        return False

    ring_end = match.start() + ring_match.end()
    before_ring = clause[:ring_end]
    ring = r"d[\s-]?rings?"
    relation = r"(?:use|using|attach|attaching|connect|connecting|clip|clipping|hook|hooking)"
    permission = r"(?:permitted|allowed|approved|authorized|acceptable|safe|suitable|recommended)"

    pre_ring_prohibitions = (
        rf"\b(?:do|must|should|may|can)\s+not\b[^.!?;]{{0,100}}\b{relation}\b[^.!?;]{{0,50}}\b(?:the\s+)?{ring}\b",
        rf"\b(?:is|are|was|were|be|been|being)\s+not\s+{permission}\b[^.!?;]{{0,100}}\b(?:to\s+)?{relation}\b[^.!?;]{{0,50}}\b(?:the\s+)?{ring}\b",
        rf"\bnot\s+{permission}\b[^.!?;]{{0,100}}\b(?:to\s+)?{relation}\b[^.!?;]{{0,50}}\b(?:the\s+)?{ring}\b",
        rf"\b(?:never|cannot|can't)\b[^.!?;]{{0,100}}\b{relation}\b[^.!?;]{{0,50}}\b(?:the\s+)?{ring}\b",
        rf"\b(?:prohibited|forbidden|unsafe|unsuitable)\b[^.!?;]{{0,100}}\b(?:to\s+)?{relation}\b[^.!?;]{{0,50}}\b(?:the\s+)?{ring}\b",
        rf"\bwithout\b[^.!?;]{{0,60}}\b(?:using\s+)?(?:the\s+)?{ring}\b",
    )
    if any(re.search(pattern, before_ring, re.I) for pattern in pre_ring_prohibitions):
        return True

    post_ring_prohibition = rf"\b(?:use|using)\s+of\s+(?:the\s+)?{ring}\b[^.!?;]{{0,100}}\b(?:is|are|was|were|remains?)\s+(?:not\s+{permission}|prohibited|forbidden|unsafe|unsuitable)\b"
    return bool(re.search(post_ring_prohibition, clause, re.I))


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
