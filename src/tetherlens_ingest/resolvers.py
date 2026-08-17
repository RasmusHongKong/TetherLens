from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import quote_plus, urljoin

from .http import Fetcher
from .models import (
    AcquisitionObservation,
    CandidateClaim,
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from .normalize import parse_mass


@dataclass
class Resolution:
    artifacts: list[SourceArtifact] = field(default_factory=list)
    claims: list[CandidateClaim] = field(default_factory=list)
    observations: list[AcquisitionObservation] = field(default_factory=list)


class RequiredFactResolver(Protocol):
    def resolve(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
        claims: list[CandidateClaim],
        fetcher: Fetcher,
    ) -> Resolution: ...


class GraingerToolMassResolver:
    """Resolve missing physical tool mass from exact-SKU Grainger records.

    This is deliberately a channel-level resolver, not a Milwaukee resolver.
    It only accepts a candidate when the fetched product record contains the
    requested manufacturer, an exact manufacturer-model match, and an explicit
    Tool Weight field. Shipping/package weight is never accepted.
    """

    extractor = "grainger.tool_mass.v0.1"
    search_url = "https://www.grainger.ca/en/search?searchQuery={query}"

    def resolve(self, identity, artifacts, claims, fetcher) -> Resolution:
        if identity.product_type != ProductType.TOOL or not identity.sku:
            return Resolution()
        if any(claim.property_key == "tool_body_mass_kg" for claim in claims):
            return Resolution(observations=[AcquisitionObservation(
                code="REQUIRED_FACT_ALREADY_SATISFIED",
                value="tool_body_mass_kg",
                detail="Primary/manufacturer acquisition already resolved tool body mass; secondary lookup was skipped.",
                source_url=identity.url,
                extractor=self.extractor,
            )])

        search = fetcher.get(
            self.search_url.format(query=quote_plus(identity.sku)),
            SourceType.QUALIFIED_SECONDARY_WEBPAGE,
        )
        search.metadata.update({"role": "secondary_search", "provider": "Grainger"})
        out = Resolution(artifacts=[search])
        candidate_url = self._exact_candidate_url(search.body, identity.sku)
        if not candidate_url:
            out.observations.append(self._miss(identity, search.url, "No exact-SKU Grainger product candidate was discovered."))
            return out

        product = fetcher.get(candidate_url, SourceType.QUALIFIED_SECONDARY_WEBPAGE)
        product.metadata.update({"role": "secondary_product", "provider": "Grainger"})
        out.artifacts.append(product)
        text = self._text(product.body)
        if not self._identity_matches(text, identity):
            out.observations.append(self._miss(identity, product.url, "Candidate failed exact manufacturer/model identity qualification."))
            return out

        raw_mass = self._tool_weight(text)
        mass = parse_mass(raw_mass) if raw_mass else None
        if not mass:
            out.observations.append(self._miss(identity, product.url, "Exact-SKU record contains no explicit Tool Weight value."))
            return out

        out.claims.append(CandidateClaim(
            subject_type=ClaimSubjectType.PRODUCT,
            subject_ref="self",
            property_key="tool_body_mass_kg",
            value=mass.value,
            unit="kg",
            raw_value=raw_mass,
            source_url=product.url,
            evidence_method="qualified_secondary_exact_sku",
            extractor=self.extractor,
        ))
        out.observations.append(AcquisitionObservation(
            code="REQUIRED_FACT_RESOLVED_SECONDARY",
            value="tool_body_mass_kg",
            detail="Tool body mass resolved from a qualified secondary record with exact manufacturer/model identity.",
            source_url=product.url,
            extractor=self.extractor,
        ))
        return out

    @staticmethod
    def _exact_candidate_url(raw: str, sku: str) -> str | None:
        decoded = html.unescape(raw)
        # Grainger search results use /en/product/<slug>/p/<item>. Require the
        # manufacturer SKU in the href or nearby anchor context; do not choose
        # the first search result blindly.
        for match in re.finditer(r'href=["\']([^"\']+/en/product/[^"\']+/p/[^"\']+)["\']', decoded, re.I):
            href = match.group(1)
            context = decoded[max(0, match.start() - 400): min(len(decoded), match.end() + 400)]
            if re.search(rf"(?<![A-Z0-9]){re.escape(sku)}(?![A-Z0-9])", context, re.I):
                return urljoin("https://www.grainger.ca", href)
        return None

    @classmethod
    def _identity_matches(cls, text: str, identity: ProductIdentity) -> bool:
        sku_ok = bool(re.search(rf"Mfr\.?\s*Model\s*#?\s*{re.escape(identity.sku or '')}\b", text, re.I))
        manufacturer_ok = identity.manufacturer.lower() in text.lower()
        return sku_ok and manufacturer_ok

    @staticmethod
    def _tool_weight(text: str) -> str | None:
        match = re.search(r"\bTool\s+Weight\s*[:#]?\s*(\d+(?:\.\d+)?)\s*(lb|lbs|kg)\.?\b", text, re.I)
        return f"{match.group(1)} {match.group(2)}" if match else None

    @staticmethod
    def _text(raw: str) -> str:
        text = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
        text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", html.unescape(text)).strip()

    def _miss(self, identity: ProductIdentity, url: str, detail: str) -> AcquisitionObservation:
        return AcquisitionObservation(
            code="REQUIRED_FACT_SECONDARY_UNRESOLVED",
            value="tool_body_mass_kg",
            detail=detail,
            source_url=url,
            extractor=self.extractor,
        )


def derive_operational_mass_profiles(identity: ProductIdentity, claims: list[CandidateClaim]) -> list[CandidateClaim]:
    """Derive operational profiles after all fact resolvers have run."""
    if any(claim.property_key == "operational_mass_kg" for claim in claims):
        return []
    body = next((claim for claim in claims if claim.property_key == "tool_body_mass_kg"), None)
    if not body:
        return []

    derived: list[CandidateClaim] = []
    for battery in (claim for claim in claims if claim.property_key == "battery_mass_kg"):
        derived.append(CandidateClaim(
            subject_type=ClaimSubjectType.OPERATIONAL_PROFILE,
            subject_ref=f"{identity.sku or identity.model or 'tool'}+{battery.subject_ref}",
            property_key="operational_mass_kg",
            value=round(float(body.value) + float(battery.value), 6),
            unit="kg",
            raw_value=f"{body.raw_value} tool body + {battery.raw_value} battery",
            source_url=body.source_url,
            supporting_source_urls=[battery.source_url],
            evidence_method="derived",
            extractor="required_fact_resolver.v0.1",
        ))
    return derived
