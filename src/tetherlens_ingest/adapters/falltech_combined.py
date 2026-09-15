from __future__ import annotations

import re
from urllib.parse import urlsplit

from tetherlens_ingest.models import (
    CandidateClaim,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceRequest,
    SourceType,
)

from .anchor_attachment_common import (
    dedupe,
    d_ring_interface_claims,
    installation_method_claim,
    installation_path_claim,
    claim,
)
from .common import page_text
from .falltech import (
    FallTechAdapter as _TetherFallTechAdapter,
    _tool_weight_capacity,
)


_EXTRACTOR = "falltech.v0.3"
_WRIST_ANCHOR_INSTRUCTIONS_URL = (
    "https://cdn11.bigcommerce.com/s-1wxw1202sk/content/product_documents/"
    "instruction_manuals/MTOL05_Rev_B_013125_EN.pdf"
)
_CHOKE_ON = re.compile(r"\b(?:simple\s+)?choke[-\s]?on\s+(?:loop\s+)?installation\b", re.I)
_HARNESS_BELT = re.compile(r"\bfits?\s+most\s+full[-\s]?body\s+harness\s+belts?\b", re.I)
_D_RING = re.compile(r"\b(?:steel\s+)?D[-\s]?ring\b", re.I)
_WRIST_PRODUCT = re.compile(r"\b(?:adjustable\s+)?wrist(?:band|\s+attachment)\s+anchor\b", re.I)
_WRIST_INSTALL = re.compile(
    r"\bWristband\s+System\b(?P<section>.*?)"
    r"\b(?:To\s+install,?\s*)?loosen\s+the\s+velcro\s+strap\s+and\s+slide\s+the\s+wristband\s+over\s+the\s+hand\b"
    r"(?P<tail>.*?)\bTo\s+tighten,?\s*pull\s+on\s+the\s+strap\s+and\s+attach\s+the\s+velcro\b",
    re.I | re.S,
)


class FallTechAdapter(_TetherFallTechAdapter):
    """Preserve tether extraction while adding AnchorAttachment installation evidence."""

    def related_sources(
        self,
        identity: ProductIdentity,
        source_artifact: SourceArtifact,
    ) -> list[SourceRequest]:
        if (
            identity.product_type != ProductType.ANCHOR_ATTACHMENT
            or not identity.sku
            or not _is_verified_product_detail(source_artifact, identity.sku)
        ):
            return []
        if _WRIST_PRODUCT.search(page_text(source_artifact.body)) is None:
            return []
        return [
            SourceRequest(
                url=_WRIST_ANCHOR_INSTRUCTIONS_URL,
                source_type=SourceType.MANUFACTURER_DOCUMENT,
                metadata={"role": "wrist_anchor_instructions"},
            )
        ]

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        if identity.product_type != ProductType.ANCHOR_ATTACHMENT:
            return super().extract(identity, artifacts)
        if not identity.sku:
            return []
        if not any(_is_verified_product_detail(artifact, identity.sku) for artifact in artifacts):
            return []

        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            if _is_verified_product_detail(artifact, identity.sku):
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

                capacity = _tool_weight_capacity(text)
                if capacity is not None:
                    claims.append(
                        claim(
                            "rated_capacity_kg",
                            capacity[0],
                            unit="kg",
                            raw_value=capacity[1],
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        )
                    )
                continue

            if not _is_wrist_instruction_artifact(artifact):
                continue
            text = page_text(artifact.body)
            install = _WRIST_INSTALL.search(text)
            product_row = re.search(
                rf"(?<![A-Z0-9]){re.escape(identity.sku)}(?![A-Z0-9]).{{0,240}}\bWrist\s+Attachment\s+Point\b",
                text,
                re.I | re.S,
            )
            if install is None or product_row is None:
                continue

            raw_install = " ".join(install.group(0).split())
            claims.extend(
                [
                    installation_method_claim(
                        "fasten_around",
                        raw_value=raw_install,
                        source_url=artifact.url,
                        extractor=_EXTRACTOR,
                    ),
                    installation_path_claim(
                        "wrist",
                        "anchor_installation.feature_kind",
                        "wrist",
                        raw_value=product_row.group(0),
                        source_url=artifact.url,
                        extractor=_EXTRACTOR,
                    ),
                ]
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


def _is_wrist_instruction_artifact(artifact: SourceArtifact) -> bool:
    return bool(
        artifact.source_type == SourceType.MANUFACTURER_DOCUMENT
        and str(artifact.metadata.get("role") or "") == "wrist_anchor_instructions"
        and artifact.url.rstrip("/") == _WRIST_ANCHOR_INSTRUCTIONS_URL.rstrip("/")
    )
