from __future__ import annotations

import re

from tetherlens_ingest.models import CandidateClaim, ClaimSubjectType, ProductIdentity, SourceArtifact
from tetherlens_ingest.normalize import length_to_mm, mass_to_kg
from .base import ManufacturerAdapter
from .common import page_text


class StopDropAdapter(ManufacturerAdapter):
    manufacturer = "StopDrop"

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            text = page_text(artifact.body)

            for m in re.finditer(
                r"(?P<length>\d+(?:\.\d+)?)\s*(?P<lu>m|cm)\b.{0,40}?Max\.?\s*Weight\s*(?P<load>\d+(?:\.\d+)?)\s*(?P<mu>kg|lb)s?\b",
                text,
                re.I | re.S,
            ):
                length_mm = round(length_to_mm(float(m.group("length")), m.group("lu")), 3)
                variant_ref = f"length_{int(length_mm) if length_mm.is_integer() else length_mm}mm"
                raw = m.group(0)
                claims.append(self._claim(
                    "variant.length_mm", length_mm, "mm", raw, artifact.url,
                    ClaimSubjectType.PRODUCT_VARIANT, variant_ref,
                ))
                claims.append(self._claim(
                    "variant.rated_capacity_kg",
                    mass_to_kg(float(m.group("load")), m.group("mu")),
                    "kg",
                    raw,
                    artifact.url,
                    ClaimSubjectType.PRODUCT_VARIANT,
                    variant_ref,
                ))

            if re.search(r"2\s+locking\s+screwgate\s+carabiner", text, re.I):
                claims.append(self._claim("tether.connection_count", 2, None, "2 locking screwgate carabiner", artifact.url))
                claims.append(self._claim(
                    "connector.locking_mode",
                    "manual_locking",
                    None,
                    "locking screwgate",
                    artifact.url,
                    ClaimSubjectType.CONNECTOR_SPEC,
                    "tether_connector",
                ))

            if re.search(r"permanent\s+.*attachment\s+point", text, re.I | re.S):
                claims.append(self._claim(
                    "tool.native_tether_point_status",
                    "documented_present",
                    None,
                    "permanent attachment point",
                    artifact.url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "native_tether_point",
                ))
        return _dedupe(claims)

    @staticmethod
    def _claim(
        key: str,
        value,
        unit: str | None,
        raw: str | None,
        url: str,
        subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT,
        subject_ref: str = "self",
    ) -> CandidateClaim:
        return CandidateClaim(
            subject_type=subject_type,
            subject_ref=subject_ref,
            property_key=key,
            value=value,
            unit=unit,
            raw_value=raw,
            source_url=url,
            extractor="stopdrop.v0.2",
        )


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen = set()
    out = []
    for claim in claims:
        key = (claim.subject_type.value, claim.subject_ref, claim.property_key, str(claim.value), claim.raw_value)
        if key not in seen:
            out.append(claim)
            seen.add(key)
    return out
