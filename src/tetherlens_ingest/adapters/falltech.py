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
from tetherlens_ingest.normalize import parse_mass

from .base import ManufacturerAdapter
from .common import page_text


_EXTRACTOR = "falltech.v0.1"
_TOOL_WEIGHT_CAPACITY = re.compile(
    r"\b(?:tool\s+weight\s+capacity|max(?:imum)?\s+tool\s+weight)\b\s*:?\s*"
    r"(?P<raw>\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b(?:\s+max\.?)?)",
    re.I,
)
_CINCH_LOOP = re.compile(r"\b(?:choke[-\s]?on\s+)?cinch[-\s]?loop\b", re.I)
_STEEL_CARABINER = re.compile(r"\bsteel\s+carabiner\b", re.I)


class FallTechAdapter(ManufacturerAdapter):
    """Extract FallTech tether evidence into existing normalized core primitives.

    The product heading is used as the topology boundary so mixed-endpoint wording in
    related-product cards cannot retype the current product. Cinch is preserved as an
    endpoint mechanism; tool/anchor role remains unknown unless separately stated.
    """

    manufacturer = "FallTech"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        if identity.product_type != ProductType.TETHER:
            return []

        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            text = page_text(artifact.body)
            if capacity := _tool_weight_capacity(text):
                claims.append(_claim(
                    "rated_capacity_kg",
                    capacity[0],
                    "kg",
                    capacity[1],
                    artifact.url,
                ))

            heading = _product_heading(artifact.body)
            if heading is None:
                continue
            cinch_match = _CINCH_LOOP.search(heading)
            carabiner_match = _STEEL_CARABINER.search(heading)
            if cinch_match is None or carabiner_match is None:
                continue

            claims.append(_claim(
                "tether.connection_count",
                2,
                None,
                heading,
                artifact.url,
            ))
            claims.extend([
                _claim(
                    "connection_point.interface_type",
                    "loop",
                    None,
                    cinch_match.group(0),
                    artifact.url,
                    ClaimSubjectType.TETHER_CONNECTION_POINT,
                    "cinch_loop_end",
                ),
                _claim(
                    "connection_point.connector_spec_ref",
                    "cinch_loop",
                    None,
                    cinch_match.group(0),
                    artifact.url,
                    ClaimSubjectType.TETHER_CONNECTION_POINT,
                    "cinch_loop_end",
                ),
                _claim(
                    "connector.attribute.engagement_method",
                    "cinch",
                    None,
                    cinch_match.group(0),
                    artifact.url,
                    ClaimSubjectType.CONNECTOR_SPEC,
                    "cinch_loop",
                ),
                _claim(
                    "connection_point.interface_type",
                    "carabiner",
                    None,
                    carabiner_match.group(0),
                    artifact.url,
                    ClaimSubjectType.TETHER_CONNECTION_POINT,
                    "carabiner_end",
                ),
                _claim(
                    "connection_point.connector_spec_ref",
                    "steel_carabiner",
                    None,
                    carabiner_match.group(0),
                    artifact.url,
                    ClaimSubjectType.TETHER_CONNECTION_POINT,
                    "carabiner_end",
                ),
                _claim(
                    "connector.attribute.material",
                    "steel",
                    None,
                    carabiner_match.group(0),
                    artifact.url,
                    ClaimSubjectType.CONNECTOR_SPEC,
                    "steel_carabiner",
                ),
            ])

        return _dedupe(claims)


def _tool_weight_capacity(text: str) -> tuple[float, str] | None:
    match = _TOOL_WEIGHT_CAPACITY.search(text)
    if match is None:
        return None
    raw = match.group("raw")
    quantity = parse_mass(raw)
    if quantity is None:
        return None
    return quantity.value, raw


def _product_heading(html: str) -> str | None:
    heading = BeautifulSoup(html, "html.parser").find("h1")
    if heading is None:
        return None
    text = " ".join(heading.stripped_strings).strip()
    return text or None


def _claim(
    property_key: str,
    value,
    unit: str | None,
    raw_value: str | None,
    source_url: str,
    subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT,
    subject_ref: str = "self",
) -> CandidateClaim:
    return CandidateClaim(
        subject_type=subject_type,
        subject_ref=subject_ref,
        property_key=property_key,
        value=value,
        unit=unit,
        raw_value=raw_value,
        source_url=source_url,
        evidence_method="manufacturer_stated",
        extractor=_EXTRACTOR,
        claim_type=ClaimType.DIRECT,
    )


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen: set[tuple[str, str, str, str, str | None, str]] = set()
    out: list[CandidateClaim] = []
    for claim in claims:
        key = (
            claim.subject_type.value,
            claim.subject_ref,
            claim.property_key,
            str(claim.value),
            claim.unit,
            claim.source_url,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(claim)
    return out
