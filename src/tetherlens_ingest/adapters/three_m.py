from __future__ import annotations

import re

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ConstraintOperator,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceRequest,
    SourceType,
)
from tetherlens_ingest.normalize import mass_to_kg

from .base import ManufacturerAdapter
from .common import page_text


_EXTRACTOR = "three_m.v0.1"
_QUICK_SPIN_MANUAL = (
    "https://multimedia.3m.com/mws/media/1300988O/"
    "ifu-5903829-python-quick-spins-a3-a3-size-instructions-manual.pdf"
)
_QUICK_SPIN_SKUS = frozenset({"1500027", "1500028", "1500029", "1500030"})

_SLIDES_ON_HANDLE = re.compile(
    r"\bsimply\s+slides?\s+onto\s+the\s+handle\s+of\s+a\s+tool\b",
    re.I,
)
_QUICK_SPIN_CAPACITY = re.compile(
    r"\bquick\s+spin\s*,?\s*(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>kg|kgs?|lb|lbs?)\s*\([^)]*\)\s*capacity\b",
    re.I,
)
_QUICK_SPIN_CAPACITY_REVERSED = re.compile(
    r"\bquick\s+spin\s*,?\s*(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>lb|lbs?)\s*\([^)]*\)\s*capacity\b",
    re.I,
)
_TIGHT_HANDLE = re.compile(
    r"\bquick\s+spin\s+will\s+fit\s+tightly\s+on\s+a\s+handle\b",
    re.I,
)
_SNUG_FIT_REQUIRED = re.compile(
    r"\b(?:if\s+a\s+snug\s+fit\s+on\s+the\s+tool\s+cannot\s+be\s+secured|"
    r"some\s+force\s+should\s+be\s+necessary\s+to\s+create\s+a\s+snug\s+fit|"
    r"ensure\s+that\s+the\s+quick\s+spin\s+is\s+firmly\s+in\s+place\s+before\s+use)\b",
    re.I,
)
_TAPERED_SURFACE_PROHIBITION = re.compile(
    r"\bnever\s+attach\s+tool\s+lanyards?\s+or\s+attachment\s+points?\s+to\s+a\s+tapered\s+surface\b",
    re.I,
)
_ATTACHMENT_POINT = re.compile(
    r"\b(?:non[-\s]?metallic\s+)?attachment\s+point\b",
    re.I,
)


class ThreeMAdapter(ManufacturerAdapter):
    """Extract conservative 3M DBI-SALA Quick Spin semantics.

    Product diameter/size is intentionally not interpreted as a permitted tool-handle
    envelope. The family manual contributes only the manufacturer-stated handle path,
    secure installed-fit obligation, and hard tapered-surface prohibition.
    """

    manufacturer = "3M"

    def related_sources(
        self,
        identity: ProductIdentity,
        source_artifact: SourceArtifact,
    ) -> list[SourceRequest]:
        if (
            identity.product_type != ProductType.TOOL_ATTACHMENT
            or identity.sku not in _QUICK_SPIN_SKUS
            or source_artifact.url == _QUICK_SPIN_MANUAL
        ):
            return []
        return [
            SourceRequest(
                url=_QUICK_SPIN_MANUAL,
                source_type=SourceType.MANUFACTURER_DOCUMENT,
                metadata={"role": "quick_spin_installation_instructions"},
            )
        ]

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        if (
            identity.product_type != ProductType.TOOL_ATTACHMENT
            or identity.sku not in _QUICK_SPIN_SKUS
        ):
            return []

        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            text = page_text(artifact.body)

            handle = _SLIDES_ON_HANDLE.search(text)
            if handle is not None:
                claims.extend([
                    _claim(
                        "attachment_selection_class",
                        "handle_attachment",
                        raw_value=handle.group(0),
                        source_url=artifact.url,
                    ),
                    _claim(
                        "attachment_method_code",
                        "mechanical_capture",
                        raw_value=handle.group(0),
                        source_url=artifact.url,
                    ),
                ])

            # Only an explicit product capacity is normalized. The adjacent nominal
            # diameter remains descriptive evidence and is never emitted as min/max fit.
            capacity = _QUICK_SPIN_CAPACITY.search(text) or _QUICK_SPIN_CAPACITY_REVERSED.search(text)
            if capacity is not None:
                claims.append(_claim(
                    "rated_capacity_kg",
                    mass_to_kg(float(capacity.group("value")), capacity.group("unit")),
                    unit="kg",
                    raw_value=capacity.group(0),
                    source_url=artifact.url,
                ))

            secure_fit = _SNUG_FIT_REQUIRED.search(text) or _TIGHT_HANDLE.search(text)
            if secure_fit is not None:
                claims.append(_claim(
                    "secure_attachment_fit_required",
                    True,
                    raw_value=secure_fit.group(0),
                    source_url=artifact.url,
                    claim_type=ClaimType.DECLARED_CONSTRAINT,
                    operator=ConstraintOperator.REQUIRES,
                ))

            tapered = _TAPERED_SURFACE_PROHIBITION.search(text)
            if tapered is not None:
                claims.append(_claim(
                    "prohibited_surface_profile",
                    "tapered",
                    raw_value=tapered.group(0),
                    source_url=artifact.url,
                    claim_type=ClaimType.DECLARED_CONSTRAINT,
                    operator=ConstraintOperator.PROHIBITS,
                ))

            point = _ATTACHMENT_POINT.search(text)
            if point is not None:
                # Quick Spin clearly creates an attachment point, but the reviewed
                # first-party text does not establish a normalized ring/caribiner form.
                claims.append(_claim(
                    "interface.role",
                    "tool_attachment_tether_side",
                    raw_value=point.group(0),
                    source_url=artifact.url,
                    subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                    subject_ref="quick_spin_tether_connection",
                ))

        return _dedupe(claims)


def _claim(
    property_key: str,
    value,
    *,
    raw_value: str | None,
    source_url: str,
    unit: str | None = None,
    subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT,
    subject_ref: str = "self",
    claim_type: ClaimType = ClaimType.DIRECT,
    operator: ConstraintOperator | None = None,
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
        constraint_operator=operator,
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
