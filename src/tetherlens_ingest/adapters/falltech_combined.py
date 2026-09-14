from __future__ import annotations

import re
from urllib.parse import urlsplit

from tetherlens_ingest.models import CandidateClaim, ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.normalize import mass_to_kg

from .anchor_attachment_common import (
    dedupe,
    d_ring_interface_claims,
    installation_method_claim,
    installation_path_claim,
    claim,
)
from .common import page_text
from .falltech import FallTechAdapter as _TetherFallTechAdapter


_EXTRACTOR = "falltech.v0.2"
_CHOKE_ON = re.compile(r"\b(?:simple\s+)?choke[-\s]?on\s+(?:loop\s+)?installation\b", re.I)
_HARNESS_BELT = re.compile(r"\bfits?\s+most\s+full[-\s]?body\s+harness\s+belts?\b", re.I)
_D_RING = re.compile(r"\bsteel\s+D[-\s]?ring\b", re.I)
_MAX_TOOL_CAPACITY = re.compile(
    r"\b(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>lb|lbs?|kg|kgs?)\s*"
    r"(?:max\.?|capacity)\b",
    re.I,
)


class FallTechAdapter(_TetherFallTechAdapter):
    """Preserve tether extraction while adding AnchorAttachment installation evidence."""

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        if identity.product_type != ProductType.ANCHOR_ATTACHMENT:
            return super().extract(identity, artifacts)
        if not identity.sku:
            return []

        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            if not _is_verified_product_detail(artifact, identity.sku):
                continue
            text = page_text(artifact.body)

            choke = _CHOKE_ON.search(text)
            belt = _HARNESS_BELT.search(text)
            if choke is not None and belt is not None:
                claims.append(
                    installation_method_claim(
                        "cinch",
                        raw_value=choke.group(0),
                        source_url=artifact.url,
                        extractor=_EXTRACTOR,
                    )
                )
                claims.append(
                    installation_path_claim(
                        "belt",
                        "anchor_installation.feature_kind",
                        "belt",
                        raw_value=belt.group(0),
                        source_url=artifact.url,
                        extractor=_EXTRACTOR,
                    )
                )

            ring = _D_RING.search(text)
            if ring is not None:
                claims.extend(
                    d_ring_interface_claims(
                        raw_value=ring.group(0),
                        source_url=artifact.url,
                        extractor=_EXTRACTOR,
                    )
                )

            capacity = _MAX_TOOL_CAPACITY.search(text)
            if capacity is not None:
                claims.append(
                    claim(
                        "rated_capacity_kg",
                        mass_to_kg(
                            float(capacity.group("value")),
                            capacity.group("unit"),
                        ),
                        unit="kg",
                        raw_value=capacity.group(0),
                        source_url=artifact.url,
                        extractor=_EXTRACTOR,
                    )
                )

        return dedupe(claims)


def _is_verified_product_detail(artifact: SourceArtifact, expected_sku: str) -> bool:
    if artifact.source_type != SourceType.MANUFACTURER_WEBPAGE or not expected_sku:
        return False
    parts = urlsplit(artifact.url)
    segments = [segment for segment in parts.path.split("/") if segment]
    if len(segments) != 2 or segments[0].casefold() != "product":
        return False
    if segments[1].casefold() != expected_sku.casefold():
        return False
    return re.search(
        rf"(?<![A-Z0-9]){re.escape(expected_sku)}(?![A-Z0-9])",
        page_text(artifact.body),
        re.I,
    ) is not None
