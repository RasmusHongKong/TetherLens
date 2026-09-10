from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from tetherlens_ingest.models import (
    AcquisitionObservation,
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ConstraintOperator,
    ProductIdentity,
    ProductType,
    ReadinessIssue,
    SourceArtifact,
    SourceRequest,
    SourceType,
)
from tetherlens_ingest.normalize import length_to_mm, parse_mass

from .base import ManufacturerAdapter
from .common import page_text


_EXTRACTOR = "tyflot.v0.1"
_GUIDE_INDEX_URL = "https://guardianfall.com/media/catalog/dropped-object-prevention-product-guide"
_FIRST_PARTY_HOSTS = frozenset({"guardianfall.com", "www.guardianfall.com"})

_COLLAPSE_RETENTION = re.compile(
    r"\b(?:shrink\s+tubing|sleeve|attachment)\b.{0,140}\b(?:collapse|contract)\w*\b"
    r".{0,100}\b(?:onto|around)\s+(?:the\s+)?tool\b.{0,120}"
    r"\b(?:fix|secure|grip|retain)\w*\b",
    re.I | re.S,
)
_FITS_DIAMETER = re.compile(
    r"\bfits?\s+diameter\b\s*:?\s*(?P<min>\d+(?:\.\d+)?)\s*(?:in(?:ches)?|[\"”])?"
    r"\s*(?:to|[-–])\s*(?P<max>\d+(?:\.\d+)?)\s*(?:in(?:ches)?|[\"”])",
    re.I,
)
_MAX_TOOL_WEIGHT = re.compile(
    r"\bmax(?:imum)?\s+tool\s+weight\b\s*:?\s*(?:up\s+to\s+)?"
    r"(?P<raw>\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b)",
    re.I,
)
_MAX_TETHER_LENGTH = re.compile(
    r"\bmax(?:imum)?\s+tether\s+length\b\s*:?\s*(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>mm|cm|m|in(?:ches)?|[\"”])",
    re.I,
)
_DECLARED_SIZE = re.compile(
    r"\bcold[-\s]?shrink\s+attachment\b[^\n]{0,100}?"
    r"(?P<a>\d+(?:\.\d+)?)\s*[\"”]?\s*(?:by|x|×)\s*"
    r"(?P<b>\d+(?:\.\d+)?)\s*[\"”]",
    re.I,
)
_FEATURE_SIZE = re.compile(
    r"\bdimensions?\s+before\s+shrinking\b\s*:?\s*"
    r"(?P<a>\d+(?:\.\d+)?)\s*[\"”]?\s*(?:dia(?:meter)?\s*)?[x×]\s*"
    r"(?P<b>\d+(?:\.\d+)?)\s*[\"”]?",
    re.I,
)


class TyFlotAdapter(ManufacturerAdapter):
    """Extract Ty-Flot/Guardian Cold Shrink evidence into neutral core primitives.

    The attachment method records contraction as the retaining mechanism. Diameter fit
    remains ordinary interface geometry, while capacity and maximum tether length stay
    in their existing claim/constraint families. The current first-party product guide
    is traversed to retain exact-SKU dimensional evidence separately from the storefront
    page so conflicting variant copy cannot be silently reconciled.
    """

    manufacturer = "Ty-Flot"
    recursive_related_sources = True

    def related_sources(
        self,
        identity: ProductIdentity,
        source_artifact: SourceArtifact,
    ) -> list[SourceRequest]:
        if identity.product_type != ProductType.TOOL_ATTACHMENT:
            return []
        if not _is_first_party_url(source_artifact.url):
            return []

        role = str(source_artifact.metadata.get("role") or "primary")
        if role == "primary":
            text = page_text(source_artifact.body)
            if "cold shrink" not in text.lower():
                return []
            return [SourceRequest(
                url=_GUIDE_INDEX_URL,
                source_type=SourceType.MANUFACTURER_WEBPAGE,
                metadata={
                    "role": "dop_product_guide_index",
                    "relationship_basis": "manufacturer_product_family_reference",
                },
            )]

        if role != "dop_product_guide_index":
            return []

        soup = BeautifulSoup(source_artifact.body, "html.parser")
        requests: list[SourceRequest] = []
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "").strip()
            label = " ".join(anchor.stripped_strings).strip().lower()
            if "pdf" not in label and ".pdf" not in href.lower() and "/assets/" not in href.lower():
                continue
            candidate_url = urljoin(source_artifact.url, href)
            if not _is_first_party_url(candidate_url):
                continue
            requests.append(SourceRequest(
                url=candidate_url,
                source_type=SourceType.MANUFACTURER_DOCUMENT,
                metadata={
                    "role": "dop_product_guide",
                    "relationship_basis": "manufacturer_guide_download",
                },
            ))
        return _dedupe_requests(requests)

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        if identity.product_type != ProductType.TOOL_ATTACHMENT:
            return []

        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            if not _is_first_party_url(artifact.url):
                continue

            role = str(artifact.metadata.get("role") or "primary")
            if role == "dop_product_guide":
                claims.extend(_guide_claims(identity, artifact))
                continue
            if role != "primary":
                continue

            text = page_text(artifact.body)
            collapse = _COLLAPSE_RETENTION.search(text)
            if collapse is not None:
                raw = re.sub(r"\s+", " ", collapse.group(0)).strip()
                claims.extend([
                    _claim(
                        "attachment_method_code",
                        "contraction_capture",
                        None,
                        raw,
                        artifact.url,
                    ),
                    _claim(
                        "attachment_selection_class",
                        "external_section_attachment",
                        None,
                        raw,
                        artifact.url,
                    ),
                ])

            if capacity := _capacity(text):
                claims.append(_claim(
                    "rated_capacity_kg",
                    capacity[0],
                    "kg",
                    capacity[1],
                    artifact.url,
                ))

            if tether_length := _max_tether_length(text):
                claims.append(_claim(
                    "max_lanyard_length_mm",
                    tether_length[0],
                    "mm",
                    tether_length[1],
                    artifact.url,
                    claim_type=ClaimType.DECLARED_CONSTRAINT,
                    constraint_operator=ConstraintOperator.LTE,
                ))

            if diameter := _diameter_range(text):
                claims.extend(_diameter_fit_claims(
                    diameter[0],
                    diameter[1],
                    diameter[2],
                    artifact.url,
                ))

        return _dedupe_claims(claims)

    def observe(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[AcquisitionObservation]:
        if identity.product_type != ProductType.TOOL_ATTACHMENT:
            return []

        observations: list[AcquisitionObservation] = []
        for artifact in artifacts:
            if artifact.metadata.get("role"):
                continue
            text = page_text(artifact.body)
            declared = _size_pair(_DECLARED_SIZE, text)
            feature = _size_pair(_FEATURE_SIZE, text)
            if declared is None or feature is None or declared == feature:
                continue
            observations.append(AcquisitionObservation(
                code="PRODUCT_VARIANT_SCOPE_CONFLICT",
                value=True,
                detail=(
                    "The product-local Cold Shrink size wording does not match the "
                    "'dimensions before shrinking' feature block; retain the feature "
                    "block as conflicted variant evidence rather than exact-SKU truth."
                ),
                source_url=artifact.url,
                extractor=_EXTRACTOR,
            ))
        return observations

    def readiness_issues(
        self,
        claims: list[CandidateClaim],
        observations: list[AcquisitionObservation],
    ) -> list[ReadinessIssue] | None:
        issues: list[ReadinessIssue] = []

        if any(observation.code == "PRODUCT_VARIANT_SCOPE_CONFLICT" for observation in observations):
            issues.append(ReadinessIssue(
                code="EVIDENCE_CONFLICT",
                property_key="tool_attachment.variant_geometry",
                detail=(
                    "First-party product-local variant geometry is internally inconsistent; "
                    "the mismatched feature block is not recommendation-ready."
                ),
            ))

        ranges = _diameter_ranges_by_source(claims)
        unique_ranges = sorted(set(ranges.values()))
        if len(unique_ranges) > 1:
            rendered = ", ".join(
                f"{low / 25.4:g}-{high / 25.4:g} in"
                for low, high in unique_ranges
            )
            issues.append(ReadinessIssue(
                code="EVIDENCE_CONFLICT",
                property_key="interface.dimension.diameter_fit",
                detail=(
                    "Conflicting first-party exact-product diameter-fit evidence remains "
                    f"unreconciled ({rendered}); no diameter envelope is recommendation-ready."
                ),
            ))

        return issues or None


def _guide_claims(identity: ProductIdentity, artifact: SourceArtifact) -> list[CandidateClaim]:
    if not identity.sku:
        return []

    text = re.sub(r"[\u201c\u201d]", '"', artifact.body)
    text = re.sub(r"\s+", " ", text)
    sku = re.escape(identity.sku)
    row = re.search(
        rf"\b{sku}\b\s+Cold\s+Shrink\s+Attachment,?\s*"
        r"(?P<size_a>\d+(?:\.\d+)?)\s*\"\s*[xX]\s*"
        r"(?P<size_b>\d+(?:\.\d+)?)\s*\""
        r".{0,100}?(?P<min>\d+(?:\.\d+)?)\s*\"\s*to\s*"
        r"(?P<max>\d+(?:\.\d+)?)\s*\""
        r".{0,100}?up\s+to\s+(?P<capacity>\d+(?:\.\d+)?)\s*lb\b",
        text,
        re.I,
    )
    if row is None:
        return []

    raw = row.group(0)
    min_diameter = float(row.group("min"))
    max_diameter = float(row.group("max"))
    claims = _diameter_fit_claims(min_diameter, max_diameter, raw, artifact.url)
    capacity = parse_mass(f"{row.group('capacity')} lb")
    if capacity is not None:
        claims.append(_claim(
            "rated_capacity_kg",
            capacity.value,
            "kg",
            raw,
            artifact.url,
        ))
    return claims


def _diameter_fit_claims(
    min_diameter_in: float,
    max_diameter_in: float,
    raw: str,
    source_url: str,
) -> list[CandidateClaim]:
    subject_ref = "tool_side_fit"
    return [
        _claim(
            "interface.dimension.min_diameter",
            min_diameter_in,
            "in",
            raw,
            source_url,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref=subject_ref,
        ),
        _claim(
            "interface.dimension.max_diameter",
            max_diameter_in,
            "in",
            raw,
            source_url,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref=subject_ref,
        ),
    ]


def _diameter_range(text: str) -> tuple[float, float, str] | None:
    match = _FITS_DIAMETER.search(text)
    if match is None:
        return None
    return float(match.group("min")), float(match.group("max")), match.group(0)


def _capacity(text: str) -> tuple[float, str] | None:
    match = _MAX_TOOL_WEIGHT.search(text)
    if match is None:
        return None
    raw = match.group("raw")
    quantity = parse_mass(raw)
    if quantity is None:
        return None
    return quantity.value, raw


def _max_tether_length(text: str) -> tuple[float, str] | None:
    match = _MAX_TETHER_LENGTH.search(text)
    if match is None:
        return None
    unit = match.group("unit").replace("”", '"')
    try:
        value_mm = length_to_mm(float(match.group("value")), unit)
    except ValueError:
        return None
    return float(value_mm), match.group(0)


def _size_pair(pattern: re.Pattern[str], text: str) -> tuple[float, float] | None:
    match = pattern.search(text)
    if match is None:
        return None
    return float(match.group("a")), float(match.group("b"))


def _diameter_ranges_by_source(
    claims: list[CandidateClaim],
) -> dict[str, tuple[float, float]]:
    grouped: dict[str, dict[str, CandidateClaim]] = defaultdict(dict)
    for claim in claims:
        if claim.subject_type != ClaimSubjectType.PHYSICAL_INTERFACE:
            continue
        if claim.subject_ref != "tool_side_fit":
            continue
        if claim.property_key not in {
            "interface.dimension.min_diameter",
            "interface.dimension.max_diameter",
        }:
            continue
        grouped[claim.source_url][claim.property_key] = claim

    ranges: dict[str, tuple[float, float]] = {}
    for source_url, dimensions in grouped.items():
        minimum = dimensions.get("interface.dimension.min_diameter")
        maximum = dimensions.get("interface.dimension.max_diameter")
        if minimum is None or maximum is None:
            continue
        if not isinstance(minimum.value, (int, float)) or isinstance(minimum.value, bool):
            continue
        if not isinstance(maximum.value, (int, float)) or isinstance(maximum.value, bool):
            continue
        if minimum.unit is None or maximum.unit is None:
            continue
        try:
            ranges[source_url] = (
                float(length_to_mm(float(minimum.value), minimum.unit)),
                float(length_to_mm(float(maximum.value), maximum.unit)),
            )
        except ValueError:
            continue
    return ranges


def _is_first_party_url(url: str) -> bool:
    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").lower()
    return parsed.scheme.lower() in {"http", "https"} and hostname in _FIRST_PARTY_HOSTS


def _claim(
    property_key: str,
    value,
    unit: str | None,
    raw_value: str | None,
    source_url: str,
    *,
    subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT,
    subject_ref: str = "self",
    claim_type: ClaimType = ClaimType.DIRECT,
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
        claim_type=claim_type,
        constraint_operator=constraint_operator,
    )


def _dedupe_claims(claims: list[CandidateClaim]) -> list[CandidateClaim]:
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


def _dedupe_requests(requests: list[SourceRequest]) -> list[SourceRequest]:
    seen: set[tuple[str, str]] = set()
    out: list[SourceRequest] = []
    for request in requests:
        key = (request.url, request.source_type.value)
        if key in seen:
            continue
        seen.add(key)
        out.append(request)
    return out
