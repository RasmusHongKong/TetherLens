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

from .base import ManufacturerAdapter
from .common import page_text


class KleinAdapter(ManufacturerAdapter):
    """Klein tool adapter for normalized physical-interface facts.

    Extraction is wording/geometry based rather than SKU based. A manufacturer-
    described tether hole is normalized as one captive through-opening. Its role is
    only promoted to ``tether_interface`` when the source explicitly calls it a
    tether hole / tethering hole.
    """

    manufacturer = "Klein Tools"
    extractor = "klein.v0.1"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        if identity.product_type != ProductType.TOOL:
            return []

        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            text = page_text(artifact.body)
            tether_hole = _tether_hole_evidence(text)
            if tether_hole is None:
                continue

            subject_ref = "tether_hole"
            claims.extend(
                [
                    self._feature_claim(
                        subject_ref,
                        "feature.kind",
                        "through_opening",
                        tether_hole,
                        artifact.url,
                    ),
                    self._feature_claim(
                        subject_ref,
                        "feature.role",
                        "tether_interface",
                        tether_hole,
                        artifact.url,
                    ),
                    self._feature_claim(
                        subject_ref,
                        "feature.captive_state",
                        "captive",
                        tether_hole,
                        artifact.url,
                    ),
                ]
            )
            if _handle_location(tether_hole):
                claims.append(
                    self._feature_claim(
                        subject_ref,
                        "feature.location_description",
                        "handle",
                        tether_hole,
                        artifact.url,
                    )
                )

        return _dedupe(claims)

    def _feature_claim(
        self,
        subject_ref: str,
        property_key: str,
        value: str,
        raw_value: str,
        source_url: str,
    ) -> CandidateClaim:
        return CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref=subject_ref,
            property_key=property_key,
            value=value,
            raw_value=raw_value,
            source_url=source_url,
            evidence_method="manufacturer_stated",
            extractor=self.extractor,
            claim_type=ClaimType.DIRECT,
        )


def _tether_hole_evidence(text: str) -> str | None:
    patterns = (
        r".{0,80}\b(?:integrated|built[-\s]?in|dedicated)?\s*tether(?:ing)?\s+hole\b.{0,100}",
        r".{0,80}\bhole\b.{0,50}\bfor\s+(?:tool\s+)?tether(?:ing)?\b.{0,100}",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            return re.sub(r"\s+", " ", match.group(0)).strip()
    return None


def _handle_location(evidence: str) -> bool:
    return bool(re.search(r"\bhandle\b", evidence, re.I))


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen: set[tuple[str, str, str]] = set()
    out: list[CandidateClaim] = []
    for claim in claims:
        key = (claim.subject_ref, claim.property_key, str(claim.value))
        if key in seen:
            continue
        seen.add(key)
        out.append(claim)
    return out
