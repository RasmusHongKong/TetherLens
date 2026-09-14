from __future__ import annotations

import re

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    ReadinessIssue,
    SourceArtifact,
)
from tetherlens_ingest.normalize import mass_to_kg

from .anchor_attachment_common import (
    dedupe,
    d_ring_interface_claims,
    installation_method_claim,
    installation_path_claim,
    claim,
)
from .common import page_text
from .milwaukee import (
    MilwaukeeAdapter as _ToolMilwaukeeAdapter,
    _is_verified_manufacturer_page,
)


_EXTRACTOR = "milwaukee.v0.9"
_WRAP_BEAMS_RAILS = re.compile(
    r"\b(?:anchor\s+strap(?:'s)?\s+)?loop\s+securely\s+wraps?\s+around\s+beams?\s+and\s+rails?\b",
    re.I,
)
_D_RING = re.compile(r"\b(?:oversized\s+)?D[-\s]?ring\b", re.I)
_WEIGHT_RATING = re.compile(
    r"\b(?:weight\s+rating|max(?:imum)?\s+(?:working\s+)?(?:capacity|load))\b\s*:?\s*"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>lb|lbs?|kg|kgs?)\b",
    re.I,
)


class MilwaukeeAdapter(_ToolMilwaukeeAdapter):
    """Preserve Milwaukee tool ingestion while adding neutral AnchorAttachment claims."""

    extractor = _EXTRACTOR

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
            if not _is_verified_manufacturer_page(artifact, identity.sku):
                continue
            text = page_text(artifact.body)

            wrap = _WRAP_BEAMS_RAILS.search(text)
            if wrap is not None:
                raw = wrap.group(0)
                claims.append(
                    installation_method_claim(
                        "wrap",
                        raw_value=raw,
                        source_url=artifact.url,
                        extractor=self.extractor,
                    )
                )
                for feature_kind in ("beam", "rail"):
                    claims.append(
                        installation_path_claim(
                            feature_kind,
                            "anchor_installation.feature_kind",
                            feature_kind,
                            raw_value=raw,
                            source_url=artifact.url,
                            extractor=self.extractor,
                        )
                    )

            ring = _D_RING.search(text)
            if ring is not None:
                claims.extend(
                    d_ring_interface_claims(
                        raw_value=ring.group(0),
                        source_url=artifact.url,
                        extractor=self.extractor,
                    )
                )

            capacity = _WEIGHT_RATING.search(text)
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
                        extractor=self.extractor,
                    )
                )

        return dedupe(claims)

    def readiness_issues(
        self,
        claims: list[CandidateClaim],
        observations,
    ) -> list[ReadinessIssue] | None:
        if any(
            claim.subject_type == ClaimSubjectType.ANCHOR_INSTALLATION_PATH
            or claim.property_key == "anchor_installation.method"
            for claim in claims
        ):
            return None
        return super().readiness_issues(claims, observations)
