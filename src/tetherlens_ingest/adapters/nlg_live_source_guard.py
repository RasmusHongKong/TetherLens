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

from .nlg_datasheet_endpoint_assignment import NLGAdapter as BaseNLGAdapter


_ANONYMOUS_ANCHOR_REF_RE = re.compile(r"^anchor_\d+$")
_NUMERIC_SINGULAR_D_RING_RE = re.compile(
    r"^\s*(?P<count>\d+)\s+(?:(?:internal|external)\s+)?"
    r"(?:(?:load[-\s]?rated|integrated)\s+){0,2}d[\s-]?ring\s*$",
    re.I,
)
_INTERNAL_ANCHOR_RATING_RE = re.compile(
    r"internal\s+anchor\s+points?\s*/\s*daisy\s+chain"
    r".{0,60}?max\s+load\s*:?\s*"
    r"(?P<mass>\d+(?:\.\d+)?\s*(?:kg|lbs?))"
    r".{0,30}?\beach\b",
    re.I | re.S,
)


class NLGAdapter(BaseNLGAdapter):
    """Guard current NLG product pages against cross-product catalogue leakage.

    NLG product HTML can include related-product and collection copy alongside the
    selected product. Older broad extractors predate that page shape, so this final
    maintenance layer removes two claims that cannot be safely rebound to the selected
    product:

    * a numeric singular ``D Ring`` phrase such as a related-product title
      ``360 D Ring ...`` must not become hundreds of anonymous container interfaces;
    * the legacy anonymous ``loop_interface`` must not be admitted on container/belt
      products merely because related catalogue copy contains ``Loop Tool Tether``.

    The guard is intentionally downstream-only. It does not alter endpoint,
    compatibility, installation or recommendation semantics.
    """

    extractor = "nlg.v0.17"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims = list(super().extract(identity, artifacts))

        if identity.product_type == ProductType.CONTAINER:
            claims = self._remove_ambiguous_numeric_singular_d_ring_topology(
                claims,
                artifacts,
            )

        if identity.product_type in {
            ProductType.CONTAINER,
            ProductType.ANCHOR_ATTACHMENT,
        } and not re.search(r"\bloop\b", identity.name or "", re.I):
            claims = [
                claim
                for claim in claims
                if not (
                    claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
                    and claim.subject_ref == "loop_interface"
                    and claim.property_key == "interface.loop_present"
                    and claim.extractor == "nlg.v0.7"
                )
            ]

        return _dedupe_claims(claims)

    def _remove_ambiguous_numeric_singular_d_ring_topology(
        self,
        claims: list[CandidateClaim],
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        suspect_refs = {
            claim.subject_ref
            for claim in claims
            if claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
            and claim.property_key == "interface.role"
            and claim.value == "container_connection"
            and _ANONYMOUS_ANCHOR_REF_RE.fullmatch(claim.subject_ref)
            and _is_ambiguous_numeric_singular_d_ring(claim.raw_value)
        }
        if not suspect_refs:
            return claims

        filtered = [claim for claim in claims if claim.subject_ref not in suspect_refs]

        # The repeated-container layer intentionally replaces the older aggregate
        # ``internal_anchor`` rating once concrete topology exists. If the only concrete
        # topology was the ambiguous related-product phrase removed above, restore the
        # independently stated aggregate rating rather than losing valid evidence.
        has_concrete_container_interface = any(
            claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
            and claim.property_key == "interface.role"
            and claim.value == "container_connection"
            for claim in filtered
        )
        has_aggregate_rating = any(
            claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
            and claim.subject_ref == "internal_anchor"
            and claim.property_key == "rated_capacity_kg"
            for claim in filtered
        )
        if not has_concrete_container_interface and not has_aggregate_rating:
            if rating_claim := _aggregate_internal_anchor_rating(artifacts, self.extractor):
                filtered.append(rating_claim)

        return filtered


def _is_ambiguous_numeric_singular_d_ring(raw_value: str | None) -> bool:
    if not raw_value:
        return False
    match = _NUMERIC_SINGULAR_D_RING_RE.fullmatch(raw_value)
    if match is None:
        return False
    return int(match.group("count")) > 1


def _aggregate_internal_anchor_rating(
    artifacts: list[SourceArtifact],
    extractor: str,
) -> CandidateClaim | None:
    observations: list[tuple[float, str, str]] = []
    for artifact in artifacts:
        if "json" in artifact.content_type:
            continue
        text = BeautifulSoup(artifact.body, "html.parser").get_text(" ", strip=True)
        if match := _INTERNAL_ANCHOR_RATING_RE.search(text):
            if quantity := parse_mass(match.group("mass")):
                observations.append((quantity.value, match.group(0), artifact.url))

    values = {value for value, _, _ in observations}
    if len(values) != 1:
        return None
    value = next(iter(values))
    _, raw_value, source_url = next(
        observation for observation in observations if observation[0] == value
    )
    return CandidateClaim(
        subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
        subject_ref="internal_anchor",
        property_key="rated_capacity_kg",
        value=value,
        unit="kg",
        raw_value=raw_value,
        source_url=source_url,
        evidence_method="manufacturer_stated",
        extractor=extractor,
        claim_type=ClaimType.DIRECT,
    )


def _dedupe_claims(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    out: list[CandidateClaim] = []
    seen: set[tuple[object, ...]] = set()
    for claim in claims:
        key = (
            claim.subject_type,
            claim.subject_ref,
            claim.property_key,
            claim.value,
            claim.unit,
            claim.source_url,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(claim)
    return out
