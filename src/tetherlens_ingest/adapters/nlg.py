from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

from tetherlens_ingest.models import CandidateClaim, ClaimSubjectType, ProductIdentity, ProductType, SourceArtifact
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

            # Length has product-level tether semantics only for a Tether. Other NLG
            # products publish ranges such as belt adjustment, which must not become
            # tether min/max length.
            if identity.product_type == ProductType.TETHER and (lengths := parse_length_range_mm(text)):
                length_raw = _first_length_range(text)
                claims.extend([
                    self._claim("min_length_mm", lengths[0], "mm", length_raw, artifact.url),
                    self._claim("max_length_mm", lengths[1], "mm", length_raw, artifact.url),
                ])

            # Opening-action terminology is only mapped to the tether connector on
            # tether product pages. A triple-action belt buckle is not a connector.
            if identity.product_type == ProductType.TETHER:
                actions = opening_action_count(text)
                if actions:
                    claims.append(self._claim(
                        "connector.opening_action_count",
                        actions,
                        None,
                        _first_action_phrase(text),
                        artifact.url,
                        ClaimSubjectType.CONNECTOR_SPEC,
                        "tether_connector",
                    ))

            if re.search(r"360\s*[°º].{0,20}(?:rot|swivel)|(?:rot|swivel).{0,20}360\s*[°º]", text, re.I | re.S):
                subject_type = ClaimSubjectType.CONNECTOR_SPEC if identity.product_type == ProductType.TETHER else ClaimSubjectType.PHYSICAL_INTERFACE
                subject_ref = "tether_connector" if identity.product_type == ProductType.TETHER else "rotating_interface"
                claims.append(self._claim(
                    "connector.swivel",
                    True,
                    None,
                    "360 degree rotating/swivel interface",
                    artifact.url,
                    subject_type,
                    subject_ref,
                ))

            if re.search(r"climbing cord loop|loop allows|loop tool tether", text, re.I):
                claims.append(self._claim(
                    "interface.loop_present",
                    True,
                    None,
                    "loop",
                    artifact.url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "loop_interface",
                ))

            # The MEWP Bag page distinguishes the overall bag rating from the load
            # of each internal tether point. Preserve those as separate subjects.
            if identity.product_type == ProductType.CONTAINER:
                anchor_match = re.search(r"(?:anchor|daisy chain).{0,80}?(\d+(?:\.\d+)?)\s*(kg|lb)s?", text, re.I | re.S)
                if anchor_match and (q := parse_mass(anchor_match.group(0))):
                    claims.append(self._claim(
                        "rated_capacity_kg",
                        q.value,
                        "kg",
                        anchor_match.group(0),
                        artifact.url,
                        ClaimSubjectType.PHYSICAL_INTERFACE,
                        "internal_anchor",
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
            extractor="nlg.v0.2",
        )


def _first_length_range(text: str) -> str | None:
    m = re.search(r"\d+(?:\.\d+)?\s*(?:mm|cm|m|in(?:ches)?|\")?\s*(?:to|[-–])\s*\d+(?:\.\d+)?\s*(?:mm|cm|m|in(?:ches)?|\")", text, re.I)
    return m.group(0) if m else None


def _first_action_phrase(text: str) -> str | None:
    m = re.search(r"(?:single|dual|double|triple|one|two|three)[ -]?(?:stage|action)", text, re.I)
    return m.group(0) if m else None


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen: set[tuple[str, str, str, str]] = set()
    out: list[CandidateClaim] = []
    for claim in claims:
        key = (claim.subject_type.value, claim.subject_ref, claim.property_key, str(claim.value))
        if key not in seen:
            out.append(claim)
            seen.add(key)
    return out
