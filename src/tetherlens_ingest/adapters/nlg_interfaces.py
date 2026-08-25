from __future__ import annotations

import re

from tetherlens_ingest.models import CandidateClaim, ClaimSubjectType, ProductIdentity, ProductType, SourceArtifact
from .common import page_text
from .nlg_compat import NLGAdapter as BaseNLGAdapter


class NLGAdapter(BaseNLGAdapter):
    """Add explicit ToolAttachment-provided connection interfaces.

    Tool-side installation eligibility remains owned by ``nlg_compat``. This layer
    records only a distinct tether-side interface when the manufacturer copy itself
    identifies a D-ring/ring as the tether point or connection interface.
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
            text = page_text(artifact.body)
            if evidence := _provided_ring_evidence(text):
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
                        ),
                    ]
                )

        return _dedupe_claims(claims)


def _provided_ring_evidence(text: str) -> str | None:
    """Require an explicit statement identifying the ring as the tether interface.

    Product names, generic ``D Ring`` labels, and nearby tether terminology are not
    sufficient. The statement itself must relate the ring to the tether point or
    connection point being provided.
    """

    ring = r"(?:d[\s-]?rings?|rings?)"
    gap = r"[^.!?;\n]"
    patterns = (
        # e.g. "secure tether point with 360° rotating D-ring"
        rf"\b(?:secure\s+)?tether\s+point\b{gap}{{0,80}}\bwith\b{gap}{{0,80}}\b{ring}\b",
        # e.g. "the D-ring provides/creates/forms a tether point"
        rf"\b{ring}\b{gap}{{0,80}}\b(?:provides?|creates?|forms?|acts?\s+as)\b"
        rf"{gap}{{0,60}}\b(?:a\s+)?(?:tether\s+point|connection\s+point)\b",
        # e.g. "connection point provided by the D-ring"
        rf"\b(?:tether\s+point|connection\s+point)\b{gap}{{0,80}}\b"
        rf"(?:provided|created|formed)\s+by\b{gap}{{0,60}}\b{ring}\b",
    )

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        evidence = re.sub(r"\s+", " ", match.group(0)).strip()
        if re.search(r"\b(?:no|not|without|never|cannot|can't|doesn't|does\s+not)\b", evidence, re.I):
            continue
        return evidence
    return None


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
