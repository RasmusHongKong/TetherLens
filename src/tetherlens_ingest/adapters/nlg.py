from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

from tetherlens_ingest.models import CandidateClaim, ProductIdentity, SourceArtifact
from tetherlens_ingest.normalize import opening_action_count, parse_length_range_mm, parse_mass
from .base import ManufacturerAdapter
from .common import page_text


class NLGAdapter(ManufacturerAdapter):
    manufacturer = "NLG"

    def discover_collection(self, artifact: SourceArtifact) -> list[ProductIdentity]:
        payload = json.loads(artifact.body)
        rows: Iterable[Any]
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = payload.get("products") or payload.get("items") or payload.get("results") or []
        else:
            rows = []

        identities: list[ProductIdentity] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = row.get("title") or row.get("name")
            url = row.get("url") or row.get("product_url")
            handle = row.get("handle")
            if not url and handle:
                url = f"https://neverletgo.com/products/{handle}"
            if not title or not url:
                continue
            identities.append(
                ProductIdentity(
                    manufacturer=self.manufacturer,
                    name=str(title),
                    sku=str(row.get("sku")) if row.get("sku") else None,
                    url=str(url),
                    manufacturer_ids={k: str(row[k]) for k in ("id", "variant_id") if row.get(k) is not None},
                )
            )
        return identities

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            if "json" in artifact.content_type:
                continue
            text = page_text(artifact.body)
            mass_match = re.search(r"Max(?:imum)?\s+Load\s*:\s*([^\n]+)", text, re.I)
            if mass_match and (q := parse_mass(mass_match.group(1))):
                claims.append(self._claim("rated_capacity_kg", q.value, "kg", mass_match.group(1), artifact.url))

            if (lengths := parse_length_range_mm(text)):
                claims.extend([
                    self._claim("min_length_mm", lengths[0], "mm", None, artifact.url),
                    self._claim("max_length_mm", lengths[1], "mm", None, artifact.url),
                ])

            actions = opening_action_count(text)
            if actions:
                claims.append(self._claim("connector.opening_action_count", actions, None, None, artifact.url))
            if re.search(r"360\s*[°º].{0,20}(?:rot|swivel)|(?:rot|swivel).{0,20}360\s*[°º]", text, re.I | re.S):
                claims.append(self._claim("connector.swivel", True, None, "360 degree rotating/swivel connector", artifact.url))
            if re.search(r"climbing cord loop|loop allows|loop tool tether", text, re.I):
                claims.append(self._claim("interface.loop_present", True, None, None, artifact.url))
        return _dedupe(claims)

    @staticmethod
    def _claim(key: str, value, unit: str | None, raw: str | None, url: str) -> CandidateClaim:
        return CandidateClaim(property_key=key, value=value, unit=unit, raw_value=raw, source_url=url, extractor="nlg.v0.1")


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen: set[tuple[str, str]] = set()
    out: list[CandidateClaim] = []
    for claim in claims:
        key = (claim.property_key, str(claim.value))
        if key not in seen:
            out.append(claim)
            seen.add(key)
    return out
