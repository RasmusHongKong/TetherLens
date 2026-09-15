from __future__ import annotations

import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ConstraintOperator,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.normalize import parse_mass

from .base import ManufacturerAdapter
from .common import page_text


_EXTRACTOR = "falltech.v0.2"
_TOOL_WEIGHT_CAPACITY = re.compile(
    r"\b(?:tool\s+weight\s+capacity|max(?:imum)?\s+tool\s+weight)\b\s*:?\s*"
    r"(?P<raw>\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b(?:\s+max\.?)?)",
    re.I,
)
_CINCH_LOOP = re.compile(r"\b(?:choke[-\s]?on\s+)?cinch[-\s]?loop\b", re.I)
_STEEL_CARABINER = re.compile(r"\bsteel\s+carabiner\b", re.I)
_BATTERY_BOOT = re.compile(r"\bbattery\s+boot\b", re.I)
_BATTERY_BOOT_FIT = re.compile(
    r"\bfits?\s+most\s+cordless\s+power\s+tool\s+batter(?:y|ies)\b"
    r".{0,260}?\bup\s+to\s+"
    r"(?P<length>\d+(?:\.\d+)?)\s*(?:in(?:ches)?|[\"”])\s*L\s*[x×]\s*"
    r"(?P<width>\d+(?:\.\d+)?)\s*(?:in(?:ches)?|[\"”])\s*W\s*[x×]\s*"
    r"(?P<height>\d+(?:\.\d+)?)\s*(?:in(?:ches)?|[\"”])\s*H\b",
    re.I | re.S,
)
_BATTERY_CAPACITY = re.compile(
    r"\bcordless\s+power\s+tool\s+batter(?:y|ies)\b.{0,100}?"
    r"\bweighing\s+up\s+to\s+(?P<raw>\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b)",
    re.I | re.S,
)
_D_RING = re.compile(r"\bsteel\s+D[-\s]?ring\b", re.I)


class FallTechAdapter(ManufacturerAdapter):
    """Extract FallTech tether and reusable ToolAttachment evidence."""

    manufacturer = "FallTech"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        if identity.product_type == ProductType.TOOL_ATTACHMENT:
            return _battery_boot_claims(identity, artifacts)
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


def _battery_boot_claims(
    identity: ProductIdentity,
    artifacts: list[SourceArtifact],
) -> list[CandidateClaim]:
    claims: list[CandidateClaim] = []
    for artifact in artifacts:
        if not _is_verified_product_detail(identity, artifact):
            continue
        heading = _product_heading(artifact.body)
        if heading is None or _BATTERY_BOOT.search(heading) is None:
            continue

        text = page_text(artifact.body)
        fit = _BATTERY_BOOT_FIT.search(text)
        if fit is not None:
            raw_fit = " ".join(fit.group(0).split())
            claims.extend(
                [
                    _claim(
                        "attachment_selection_class",
                        "external_section_attachment",
                        None,
                        raw_fit,
                        artifact.url,
                    ),
                    _claim(
                        "attachment_eligibility.feature_kind",
                        "external_section",
                        None,
                        raw_fit,
                        artifact.url,
                        ClaimSubjectType.PHYSICAL_INTERFACE,
                        "tool_side_fit",
                    ),
                    _claim(
                        "attachment_eligibility.dimension.section_length",
                        float(fit.group("length")),
                        "in",
                        raw_fit,
                        artifact.url,
                        ClaimSubjectType.PHYSICAL_INTERFACE,
                        "tool_side_fit",
                        ConstraintOperator.LTE,
                    ),
                    _claim(
                        "attachment_eligibility.dimension.section_width",
                        float(fit.group("width")),
                        "in",
                        raw_fit,
                        artifact.url,
                        ClaimSubjectType.PHYSICAL_INTERFACE,
                        "tool_side_fit",
                        ConstraintOperator.LTE,
                    ),
                    _claim(
                        "attachment_eligibility.dimension.section_height",
                        float(fit.group("height")),
                        "in",
                        raw_fit,
                        artifact.url,
                        ClaimSubjectType.PHYSICAL_INTERFACE,
                        "tool_side_fit",
                        ConstraintOperator.LTE,
                    ),
                ]
            )

        capacity = _BATTERY_CAPACITY.search(text)
        if capacity is not None and (quantity := parse_mass(capacity.group("raw"))) is not None:
            claims.append(
                _claim(
                    "rated_capacity_kg",
                    quantity.value,
                    "kg",
                    capacity.group("raw"),
                    artifact.url,
                )
            )

        ring = _D_RING.search(text)
        if ring is not None:
            claims.extend(
                [
                    _claim(
                        "interface.role",
                        "tool_attachment_tether_side",
                        None,
                        ring.group(0),
                        artifact.url,
                        ClaimSubjectType.PHYSICAL_INTERFACE,
                        "tether_side_ring",
                    ),
                    _claim(
                        "interface.type",
                        "ring",
                        None,
                        ring.group(0),
                        artifact.url,
                        ClaimSubjectType.PHYSICAL_INTERFACE,
                        "tether_side_ring",
                    ),
                    _claim(
                        "interface.attribute.ring_form",
                        "d_ring",
                        None,
                        ring.group(0),
                        artifact.url,
                        ClaimSubjectType.PHYSICAL_INTERFACE,
                        "tether_side_ring",
                    ),
                ]
            )

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


def _is_verified_product_detail(identity: ProductIdentity, artifact: SourceArtifact) -> bool:
    if (
        artifact.source_type != SourceType.MANUFACTURER_WEBPAGE
        or str(artifact.metadata.get("role") or "primary") != "primary"
        or not identity.sku
    ):
        return False
    parts = urlsplit(artifact.url)
    segments = [segment for segment in parts.path.split("/") if segment]
    if len(segments) != 2 or segments[0].casefold() != "product":
        return False
    if segments[1].casefold() != identity.sku.casefold():
        return False
    return re.search(
        rf"(?<![A-Z0-9]){re.escape(identity.sku)}(?![A-Z0-9])",
        page_text(artifact.body),
        re.I,
    ) is not None


def _claim(
    property_key: str,
    value,
    unit: str | None,
    raw_value: str | None,
    source_url: str,
    subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT,
    subject_ref: str = "self",
    constraint_operator: ConstraintOperator | None = None,
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
        claim_type=(
            ClaimType.DECLARED_CONSTRAINT
            if constraint_operator is not None
            else ClaimType.DIRECT
        ),
        constraint_operator=constraint_operator,
    )


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen: set[tuple[str, str, str, str, str | None, str, str | None]] = set()
    out: list[CandidateClaim] = []
    for claim in claims:
        key = (
            claim.subject_type.value,
            claim.subject_ref,
            claim.property_key,
            str(claim.value),
            claim.unit,
            claim.source_url,
            claim.constraint_operator.value if claim.constraint_operator else None,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(claim)
    return out
