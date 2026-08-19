from __future__ import annotations

import re

from tetherlens_ingest.models import CandidateClaim, ClaimSubjectType, ProductIdentity, ProductType, SourceArtifact
from tetherlens_ingest.normalize import parse_mass

from .common import page_text
from .hilti import HiltiAdapter as _BaseHiltiAdapter


class HiltiAdapter(_BaseHiltiAdapter):
    """Hilti adapter with ToolAttachment product-option extraction layered onto the existing graph."""

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        claims = list(super().extract(identity, artifacts))
        if identity.product_type != ProductType.TOOL_ATTACHMENT:
            return claims

        for artifact in artifacts:
            if artifact.metadata.get("role"):
                continue
            raw_capacity = self._extract_retaining_strap_capacity(identity, artifact)
            if not raw_capacity or not (quantity := parse_mass(raw_capacity)):
                continue
            claims.append(CandidateClaim(
                subject_type=ClaimSubjectType.PRODUCT,
                subject_ref="self",
                property_key="rated_capacity_kg",
                value=quantity.value,
                unit="kg",
                raw_value=raw_capacity,
                source_url=artifact.url,
                evidence_method="manufacturer_stated",
                extractor="hilti.v0.6",
            ))
        return _dedupe_claims(claims)

    @staticmethod
    def _extract_retaining_strap_capacity(identity: ProductIdentity, artifact: SourceArtifact) -> str | None:
        text = re.sub(r"\s+", " ", page_text(artifact.body))
        if identity.sku and not re.search(rf"#\s*{re.escape(identity.sku)}\b", text):
            return None
        if "retaining strap" not in text.lower():
            return None

        # Hilti's option line currently renders as e.g. "1x 15lb (6.8kg) Retaining strap assy".
        # Prefer the manufacturer's metric value when both units are published rather than
        # converting the rounded imperial marketing value back to kg.
        patterns = (
            r"\d+(?:\.\d+)?\s*lb[s]?\s*\(\s*(\d+(?:\.\d+)?\s*kg)\s*\)\s*Retaining strap",
            r"Retaining strap.{0,100}?\d+(?:\.\d+)?\s*lb[s]?\s*\(\s*(\d+(?:\.\d+)?\s*kg)\s*\)",
            r"Retaining strap.{0,100}?(\d+(?:\.\d+)?\s*kg)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match and parse_mass(match.group(1)):
                return match.group(1).strip()
        return None


def _dedupe_claims(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen: set[tuple[str, str, str, str]] = set()
    out: list[CandidateClaim] = []
    for claim in claims:
        key = (claim.subject_type.value, claim.subject_ref, claim.property_key, str(claim.value))
        if key in seen:
            continue
        seen.add(key)
        out.append(claim)
    return out
