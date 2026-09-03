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

from .nlg_container import NLGAdapter as BaseNLGAdapter


_QUICK_CLIP_REF = "quick_clip"
_OPENING_MECHANISM_KEY = "connector.attribute.opening_mechanism"
_TRIGGER_OPERATED = "trigger_operated"


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

    The accepted forms require the Quick Clip subject and connection/disconnection
    wording to be tied locally to the trigger by mechanism wording such as ``with a
    built-in trigger`` or ``due to its ergonomic trigger design``. Co-occurrence in one
    clause is deliberately insufficient, so a trigger belonging to another tool cannot
    establish a connector mechanism merely because it appears nearby.
    """

    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    quick_clip = r"\bQuick\s*Clips?™?\b"
    connection = r"\b(?:connect|disconnect|connection|disconnection|attach)\w*\b"
    mechanism = (
        r"(?:"
        r"\b(?:with|using|via)\s+(?:an?\s+)?built[-\s]?in\s+trigger\b"
        r"|\bdue\s+to\s+(?:its\s+)?ergonomic\s+trigger(?:\s+design)?\b"
        r")"
    )
    relation = re.compile(
        rf"{quick_clip}[^.!?;]{{0,180}}{connection}[^.!?;]{{0,80}}{mechanism}",
        re.I,
    )

    for clause in re.split(r"(?<=[.!?;])\s+", text):
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
