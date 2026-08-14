from __future__ import annotations

import re

from tetherlens_ingest.models import CandidateClaim, ProductIdentity, SourceArtifact
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
                claims.append(self._claim("variant.length_mm", round(length_to_mm(float(m.group("length")), m.group("lu")), 3), "mm", m.group(0), artifact.url))
                claims.append(self._claim("variant.rated_capacity_kg", mass_to_kg(float(m.group("load")), m.group("mu")), "kg", m.group(0), artifact.url))

            if re.search(r"2\s+locking\s+screwgate\s+carabiner", text, re.I):
                claims.append(self._claim("tether.connection_count", 2, None, None, artifact.url))
                claims.append(self._claim("connector.locking_mode", "manual_locking", None, "locking screwgate", artifact.url))

            if re.search(r"permanent\s+.*attachment\s+point", text, re.I | re.S):
                claims.append(self._claim("tool.native_tether_point_status", "documented_present", None, None, artifact.url))
        return _dedupe(claims)

    @staticmethod
    def _claim(key: str, value, unit: str | None, raw: str | None, url: str) -> CandidateClaim:
        return CandidateClaim(property_key=key, value=value, unit=unit, raw_value=raw, source_url=url, extractor="stopdrop.v0.1")


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen = set()
    out = []
    for claim in claims:
        key = (claim.property_key, str(claim.value), claim.raw_value)
        if key not in seen:
            out.append(claim)
            seen.add(key)
    return out
