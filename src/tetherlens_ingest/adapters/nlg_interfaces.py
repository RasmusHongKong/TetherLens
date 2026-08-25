from __future__ import annotations

import re

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
)
from .common import page_text
from .nlg_compat import NLGAdapter as BaseNLGAdapter


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


def _provided_ring_evidence(text: str) -> str | None:
    """Return strong local evidence that a D-ring is the provided tether interface.

    A product title, a bare ``D Ring`` feature label, or a generic navigation mention
    is insufficient. The same sentence/clause must link the D-ring to creation of a
    tether point or to a lanyard connection.
    """

    ring = r"d[\s-]?rings?"
    tether_point = r"(?:secure\s+|ultra[-\s]?secure\s+|permanent\s+)?tether\s+point"
    lanyard = r"(?:tool\s+)?lanyards?"
    gap = r"[^.!?;\n]"
    patterns = (
        rf"\b{ring}\b{gap}{{0,120}}\b(?:create|provide|form|make)\w*\b{gap}{{0,100}}\b{tether_point}\b",
        rf"\b{tether_point}\b{gap}{{0,80}}\b(?:with|using|via|through)\b{gap}{{0,80}}\b{ring}\b",
        rf"\b{ring}\b{gap}{{0,120}}\b(?:attach|connect|clip|hook)\w*\b{gap}{{0,80}}\b{lanyard}\b",
    )

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match is None:
            continue
        evidence = re.sub(r"\s+", " ", match.group(0)).strip()
        if re.search(
            r"\b(?:no|not|without|never|cannot|can't|doesn't|does\s+not)\b",
            evidence,
            re.I,
        ):
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
