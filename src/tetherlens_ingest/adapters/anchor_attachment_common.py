from __future__ import annotations

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ConstraintOperator,
)


ANCHOR_TETHER_INTERFACE_REF = "anchor_attachment_tether_connection"


def claim(
    property_key: str,
    value,
    *,
    raw_value: str | None,
    source_url: str,
    extractor: str,
    unit: str | None = None,
    subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT,
    subject_ref: str = "self",
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
        extractor=extractor,
        claim_type=(
            ClaimType.DECLARED_CONSTRAINT
            if operator is not None
            else ClaimType.DIRECT
        ),
        constraint_operator=operator,
    )


def d_ring_interface_claims(
    *,
    raw_value: str,
    source_url: str,
    extractor: str,
) -> list[CandidateClaim]:
    return [
        claim(
            "interface.role",
            "anchor_attachment_tether_side",
            raw_value=raw_value,
            source_url=source_url,
            extractor=extractor,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref=ANCHOR_TETHER_INTERFACE_REF,
        ),
        claim(
            "interface.type",
            "ring",
            raw_value=raw_value,
            source_url=source_url,
            extractor=extractor,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref=ANCHOR_TETHER_INTERFACE_REF,
        ),
        claim(
            "interface.attribute.ring_form",
            "d_ring",
            raw_value=raw_value,
            source_url=source_url,
            extractor=extractor,
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref=ANCHOR_TETHER_INTERFACE_REF,
        ),
    ]


def installation_method_claim(
    method: str,
    *,
    raw_value: str,
    source_url: str,
    extractor: str,
) -> CandidateClaim:
    return claim(
        "anchor_installation.method",
        method,
        raw_value=raw_value,
        source_url=source_url,
        extractor=extractor,
    )


def installation_path_claim(
    subject_ref: str,
    property_key: str,
    value,
    *,
    raw_value: str,
    source_url: str,
    extractor: str,
    unit: str | None = None,
    operator: ConstraintOperator | None = None,
) -> CandidateClaim:
    return claim(
        property_key,
        value,
        raw_value=raw_value,
        source_url=source_url,
        extractor=extractor,
        unit=unit,
        subject_type=ClaimSubjectType.ANCHOR_INSTALLATION_PATH,
        subject_ref=subject_ref,
        operator=operator,
    )


def dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen: set[tuple[str, str, str, str, str | None, str, str | None]] = set()
    out: list[CandidateClaim] = []
    for item in claims:
        key = (
            item.subject_type.value,
            item.subject_ref,
            item.property_key,
            str(item.value),
            item.unit,
            item.source_url,
            item.constraint_operator.value if item.constraint_operator else None,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
