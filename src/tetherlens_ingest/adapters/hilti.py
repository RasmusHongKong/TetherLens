from __future__ import annotations

import re

from tetherlens_ingest.models import CandidateClaim, ProductIdentity, SourceArtifact
from tetherlens_ingest.normalize import opening_action_count, parse_mass
from .base import ManufacturerAdapter
from .common import page_text


class HiltiAdapter(ManufacturerAdapter):
    manufacturer = "Hilti"

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            text = page_text(artifact.body)
            for label, key in (("Maximum load", "rated_capacity_kg"), ("Tool body weight", "tool_body_mass_kg")):
                m = re.search(rf"{re.escape(label)}\s*:?\s*([^\n]+)", text, re.I)
                if m and (q := parse_mass(m.group(1))):
                    claims.append(self._claim(key, q.value, "kg", m.group(1), artifact.url))

            m = re.search(r"Weight according[^\n]*without battery\s*:?\s*([^\n]+)", text, re.I)
            if m and (q := parse_mass(m.group(1))):
                claims.append(self._claim("tool_body_mass_kg", q.value, "kg", m.group(1), artifact.url))

            sku = re.search(r"#(\d{6,})", text)
            if sku:
                claims.append(self._claim("manufacturer_item_code", sku.group(1), None, sku.group(1), artifact.url))

            if re.search(r"self-locking carabiner", text, re.I):
                claims.append(self._claim("connector.locking_mode", "auto_locking", None, "self-locking carabiner", artifact.url))
            if re.search(r"double carabiner", text, re.I):
                claims.append(self._claim("tether.connection_count", 2, None, "double carabiner", artifact.url))
            actions = opening_action_count(text)
            if actions:
                claims.append(self._claim("connector.opening_action_count", actions, None, None, artifact.url))
        return _dedupe(claims)

    @staticmethod
    def operational_mass(tool_body_mass_kg: float, battery_mass_kg: float) -> float:
        return round(tool_body_mass_kg + battery_mass_kg, 6)

    @staticmethod
    def _claim(key: str, value, unit: str | None, raw: str | None, url: str) -> CandidateClaim:
        return CandidateClaim(property_key=key, value=value, unit=unit, raw_value=raw, source_url=url, extractor="hilti.v0.1")


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen = set()
    out = []
    for claim in claims:
        key = (claim.property_key, str(claim.value))
        if key not in seen:
            out.append(claim)
            seen.add(key)
    return out
