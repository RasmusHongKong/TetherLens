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
_CAPACITY_PATTERNS = (
    re.compile(
        r"\bmaximum\s+working\s+capacity\s+of\s+(?P<value>\d+(?:\.\d+)?)\s*"
        r"(?P<unit>pounds?|lbs?|kg|kgs?)\b",
        re.I,
    ),
    re.compile(
        r"\b(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>lbs?|kg|kgs?)\s+weight\s+rating\b",
        re.I,
    ),
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

            capacity = next(
                (match for pattern in _CAPACITY_PATTERNS if (match := pattern.search(text))),
                None,
            )
            if capacity is not None:
                unit = capacity.group("unit")
                if unit.casefold().startswith("pound"):
                    unit = "lb"
                claims.append(
                    claim(
                        "rated_capacity_kg",
                        mass_to_kg(float(capacity.group("value")), unit),
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
        if _has_anchor_attachment_evidence(claims):
            return None
        return super().readiness_issues(claims, observations)


def _has_anchor_attachment_evidence(claims: list[CandidateClaim]) -> bool:
    return any(
        claim.subject_type == ClaimSubjectType.ANCHOR_INSTALLATION_PATH
        or claim.property_key in {"anchor_installation.method", "rated_capacity_kg"}
        or (
            claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
            and claim.property_key == "interface.role"
            and claim.value == "anchor_attachment_tether_side"
        )
        for claim in claims
    )
