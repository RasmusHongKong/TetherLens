from __future__ import annotations

import re

from tetherlens_ingest.manufacturer_instruction import (
    ISSUER_MANUFACTURER_KEY,
    REQUIRED_TETHER_MANUFACTURER_KEY,
    SCOPE_KEY,
    TARGET_INTERFACE_REF_KEY,
)
from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
)

from .common import page_text
from .three_m import ThreeMAdapter as BaseThreeMAdapter
from .three_m import _dedupe, _is_verified_d_ring_cord_manual


_EXTRACTOR = "three_m.v0.3"
_D_RING_CORD_SKU = "1500009"
_D_RING_INSTRUCTION_SUBJECT = "d_ring_tether_manufacturer_instruction"
_D_RING_TETHER_REQUIREMENT = re.compile(
    r"\bpython\s+safety\s+attachment\s+points?\s+require\s+the\s+use\s+of\s+an?\s+"
    r"appropriate\s+python\s+safety\s+lanyard\s*,?\s+tether\s+or\s+retractor\s+"
    r"for\s+safe\s+connection\b",
    re.I,
)


class ThreeMAdapter(BaseThreeMAdapter):
    """Extend the 3M family adapter with issuer-scoped connection instructions.

    The base adapter owns physical/topological ToolAttachment facts. This layer preserves
    manufacturer-position evidence that constrains the supported tether family without
    translating that wording into physical incompatibility.
    """

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims = list(super().extract(identity, artifacts))
        if (
            identity.product_type != ProductType.TOOL_ATTACHMENT
            or identity.sku != _D_RING_CORD_SKU
        ):
            return claims

        for artifact in artifacts:
            if not _is_verified_d_ring_cord_manual(identity, artifact):
                continue
            text = page_text(artifact.body)
            requirement = _D_RING_TETHER_REQUIREMENT.search(text)
            if requirement is None:
                continue
            raw = requirement.group(0)
            claims.extend(
                [
                    _instruction_claim(
                        REQUIRED_TETHER_MANUFACTURER_KEY,
                        "Python Safety",
                        raw_value=raw,
                        source_url=artifact.url,
                    ),
                    _instruction_claim(
                        TARGET_INTERFACE_REF_KEY,
                        "d_ring_tether_connection",
                        raw_value=raw,
                        source_url=artifact.url,
                    ),
                    _instruction_claim(
                        ISSUER_MANUFACTURER_KEY,
                        "3M",
                        raw_value=raw,
                        source_url=artifact.url,
                    ),
                    _instruction_claim(
                        SCOPE_KEY,
                        "1500009 D-Ring Cord tether connection",
                        raw_value=raw,
                        source_url=artifact.url,
                    ),
                ]
            )

        return _dedupe(claims)


def _instruction_claim(
    property_key: str,
    value: str,
    *,
    raw_value: str,
    source_url: str,
) -> CandidateClaim:
    return CandidateClaim(
        subject_type=ClaimSubjectType.PRODUCT,
        subject_ref=_D_RING_INSTRUCTION_SUBJECT,
        property_key=property_key,
        value=value,
        raw_value=raw_value,
        source_url=source_url,
        evidence_method="manufacturer_stated",
        extractor=_EXTRACTOR,
        claim_type=ClaimType.DIRECT,
    )
