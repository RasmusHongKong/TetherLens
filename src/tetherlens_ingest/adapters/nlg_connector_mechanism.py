from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString, Tag

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
)

from .nlg_container import NLGAdapter as BaseNLGAdapter


_QUICK_CLIP_REF = "quick_clip"
_OPENING_MECHANISM_KEY = "connector.attribute.opening_mechanism"
_TRIGGER_OPERATED = "trigger_operated"
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


class NLGAdapter(BaseNLGAdapter):
    """Add evidence-backed connector mechanism semantics above the NLG adapter stack.

    ``Quick Clip`` remains an interface label, not an alias for carabiner or snap hook.
    The first reusable mechanism primitive is intentionally narrower: manufacturer copy
    must tie the Quick Clip itself to a built-in/ergonomic trigger used for connection
    or disconnection. That establishes a trigger-operated opening mechanism without
    inventing an opening-action count or locking mode.
    """

    extractor = "nlg.v0.11"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims = list(super().extract(identity, artifacts))
        if identity.product_type != ProductType.TETHER:
            return claims

        has_quick_clip_ref = any(
            claim.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT
            and claim.property_key == "connection_point.connector_spec_ref"
            and claim.value == _QUICK_CLIP_REF
            for claim in claims
        )
        if not has_quick_clip_ref:
            return claims

        for artifact in artifacts:
            if evidence := _quick_clip_trigger_evidence(artifact.body):
                claims.append(
                    CandidateClaim(
                        subject_type=ClaimSubjectType.CONNECTOR_SPEC,
                        subject_ref=_QUICK_CLIP_REF,
                        property_key=_OPENING_MECHANISM_KEY,
                        value=_TRIGGER_OPERATED,
                        raw_value=evidence,
                        source_url=artifact.url,
                        evidence_method="manufacturer_stated",
                        extractor=self.extractor,
                        claim_type=ClaimType.DIRECT,
                    )
                )

        return _dedupe_claims(claims)


def _quick_clip_trigger_evidence(html: str) -> str | None:
    """Return a tightly bound positive Quick Clip/trigger mechanism assertion.

    HTML block boundaries are preserved before sentence splitting so adjacent paragraphs
    or list items cannot manufacture one apparent evidence clause. Within one clause,
    the accepted grammar requires the trigger mechanism to follow the Quick Clip action
    directly; wording that instead attaches the trigger to another object is rejected.
    """

    quick_clip = r"\bQuick\s*Clips?™?\b"
    action = (
        r"\b(?:quick\s+|easy\s+)?(?:"
        r"connection(?:\s+and\s+disconnection)?|"
        r"disconnection|attachment"
        r")\b"
    )
    mechanism = (
        r"(?:"
        r"(?:with|using|via)\s+(?:an?\s+|its\s+)?"
        r"(?:built[-\s]?in\s+trigger|ergonomic\s+trigger(?:\s+design)?)"
        r"|due\s+to\s+(?:its\s+)?ergonomic\s+trigger(?:\s+design)?"
        r")"
    )
    relation = re.compile(
        rf"{quick_clip}[^.!?;{_BLOCK_MARKER}]{{0,180}}{action}\s*[,:-]?\s*{mechanism}",
        re.I,
    )

    for clause in _html_evidence_clauses(html):
        if relation.search(clause) is None:
            continue
        if re.search(
            r"\b(?:no|not|without|does\s+not|do\s+not|doesn't|don't)\b[^.!?;]{0,60}\btrigger\b",
            clause,
            re.I,
        ):
            continue
        return clause.strip()
    return None


def _html_evidence_clauses(html: str) -> list[str]:
    """Render HTML while preserving semantic block boundaries as hard delimiters."""

    soup = BeautifulSoup(html, "html.parser")
    rendered = _render_with_block_markers(soup)
    clauses: list[str] = []
    for block in rendered.split(_BLOCK_MARKER):
        normalized = re.sub(r"\s+", " ", block).strip()
        if not normalized:
            continue
        clauses.extend(
            part.strip()
            for part in re.split(r"(?<=[.!?;])\s+", normalized)
            if part.strip()
        )
    return clauses


def _render_with_block_markers(node: Tag | NavigableString) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    parts = [_render_with_block_markers(child) for child in node.children]
    text = " ".join(part for part in parts if part)
    if getattr(node, "name", None) in _BLOCK_TAGS:
        return f"{_BLOCK_MARKER}{text}{_BLOCK_MARKER}"
    return text


def _dedupe_claims(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    out: list[CandidateClaim] = []
    seen: set[tuple[object, ...]] = set()
    for claim in claims:
        key = (
            claim.subject_type,
            claim.subject_ref,
            claim.property_key,
            str(claim.value),
            claim.unit,
            claim.source_url,
            claim.constraint_operator,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(claim)
    return out
