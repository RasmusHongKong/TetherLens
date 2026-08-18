from __future__ import annotations

import html
import re
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import quote_plus, urljoin, urlparse
from typing import Protocol

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
from .search import SearchProvider, SearchResult


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


@dataclass(frozen=True)
class IndexedMassCandidate:
    result: SearchResult
    raw_mass: str
    mass_kg: float
    domain: str
    qualified_domain: bool


class SearchIndexedToolMassResolver:
    """Resolve tool-body mass from qualified search-index evidence.

    The resolver is provider-neutral. Search discovers candidate evidence; this
    class independently requires exact manufacturer/SKU identity and explicit
    tool-mass language. A single indexed result is accepted only from a
    qualified industrial-distribution domain. Otherwise two independent domains
    must corroborate the same mass before it is promoted to a claim.
    """

    extractor = "search_index.tool_mass.v0.1"
    qualified_domains = {
        "grainger.ca",
        "grainger.com",
        "fastenal.com",
        "mscdirect.com",
        "rs-online.com",
        "uk.rs-online.com",
        "us.rs-online.com",
    }

    def __init__(self, provider: SearchProvider, *, max_results: int = 8):
        self.provider = provider
        self.max_results = max_results

    def resolve(self, identity, artifacts, claims, fetcher) -> Resolution:
        if identity.product_type != ProductType.TOOL or not identity.sku:
            return Resolution()
        if any(claim.property_key == "tool_body_mass_kg" for claim in claims):
            return Resolution(observations=[AcquisitionObservation(
                code="REQUIRED_FACT_ALREADY_SATISFIED",
                value="tool_body_mass_kg",
                detail="Manufacturer acquisition already resolved tool body mass; search resolution was skipped.",
                source_url=identity.url,
                extractor=self.extractor,
            )])

        out = Resolution()
        candidates: list[IndexedMassCandidate] = []
        queries = self._queries(identity)

        for query_number, query in enumerate(queries, start=1):
            try:
                results = self.provider.search(query, limit=self.max_results)
            except Exception as exc:
                out.observations.append(AcquisitionObservation(
                    code="SEARCH_PROVIDER_UNAVAILABLE",
                    value="tool_body_mass_kg",
                    detail=f"{self.provider.name} search failed: {type(exc).__name__}: {exc}",
                    source_url=identity.url,
                    extractor=self.extractor,
                ))
                return out

            out.observations.append(AcquisitionObservation(
                code="SEARCH_QUERY_EXECUTED",
                value=query_number,
                detail=f"provider={self.provider.name}; results={len(results)}; query={query}",
                source_url=identity.url,
                extractor=self.extractor,
            ))
            candidates.extend(self._candidate(result, identity) for result in results if self._candidate(result, identity))

            accepted = self._accepted(candidates)
            if accepted:
                return self._resolved(out, accepted)

        out.observations.append(AcquisitionObservation(
            code="REQUIRED_FACT_SEARCH_UNRESOLVED",
            value="tool_body_mass_kg",
            detail=f"Search exhausted {len(queries)} queries without sufficiently qualified exact-SKU tool-mass evidence.",
            source_url=identity.url,
            extractor=self.extractor,
        ))
        return out

    @staticmethod
    def _queries(identity: ProductIdentity) -> list[str]:
        sku = identity.sku or ""
        manufacturer = identity.manufacturer
        return [
            f'"{manufacturer}" "{sku}" "tool weight"',
            f'"{manufacturer}" "{sku}" "bare tool" weight',
            f'"{manufacturer}" "{sku}" weight -shipping',
        ]

    def _candidate(self, result: SearchResult, identity: ProductIdentity) -> IndexedMassCandidate | None:
        text = re.sub(r"\s+", " ", html.unescape(f"{result.title} {result.snippet}")).strip()
        if not self._identity_matches(text, identity):
            return None
        raw_mass = self._explicit_tool_mass(text)
        mass = parse_mass(raw_mass) if raw_mass else None
        if not mass:
            return None
        domain = self._domain(result.url)
        return IndexedMassCandidate(
            result=result,
            raw_mass=raw_mass,
            mass_kg=float(mass.value),
            domain=domain,
            qualified_domain=self._is_qualified_domain(domain),
        )

    @staticmethod
    def _identity_matches(text: str, identity: ProductIdentity) -> bool:
        sku = identity.sku or ""
        sku_ok = bool(re.search(rf"(?<![A-Z0-9]){re.escape(sku)}(?![A-Z0-9])", text, re.I))
        manufacturer_ok = identity.manufacturer.lower() in text.lower()
        return sku_ok and manufacturer_ok

    @staticmethod
    def _explicit_tool_mass(text: str) -> str | None:
        patterns = [
            r"\bTool\s+Weight\s*[:#-]?\s*(\d+(?:\.\d+)?)\s*(lb|lbs|kg)\.?\b",
            r"\bBare\s+Tool\s+Weight\s*[:#-]?\s*(\d+(?:\.\d+)?)\s*(lb|lbs|kg)\.?\b",
            r"\bWeight\s*\(?\s*Tool\s+Only\s*\)?\s*[:#-]?\s*(\d+(?:\.\d+)?)\s*(lb|lbs|kg)\.?\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return f"{match.group(1)} {match.group(2)}"
        return None

    def _accepted(self, candidates: list[IndexedMassCandidate]) -> list[IndexedMassCandidate]:
        # One exact-SKU result from a pre-qualified industrial distributor is
        # sufficient for this evidence tier.
        qualified = sorted((c for c in candidates if c.qualified_domain), key=lambda c: c.result.rank)
        if qualified:
            return [qualified[0]]

        # Other sources require independent-domain corroboration. Bucket values
        # at gram precision so lb/kg rendering differences converge.
        by_mass: dict[float, list[IndexedMassCandidate]] = defaultdict(list)
        for candidate in candidates:
            by_mass[round(candidate.mass_kg, 3)].append(candidate)
        for group in by_mass.values():
            domains = {candidate.domain for candidate in group if candidate.domain}
            if len(domains) >= 2:
                return sorted(group, key=lambda c: c.result.rank)
        return []

    def _resolved(self, out: Resolution, accepted: list[IndexedMassCandidate]) -> Resolution:
        primary = accepted[0]
        out.claims.append(CandidateClaim(
            subject_type=ClaimSubjectType.PRODUCT,
            subject_ref="self",
            property_key="tool_body_mass_kg",
            value=round(primary.mass_kg, 6),
            unit="kg",
            raw_value=primary.raw_mass,
            source_url=primary.result.url,
            supporting_source_urls=[c.result.url for c in accepted[1:]],
            evidence_method="search_indexed_qualified_secondary",
            extractor=self.extractor,
        ))
        out.observations.append(AcquisitionObservation(
            code="REQUIRED_FACT_RESOLVED_SEARCH",
            value="tool_body_mass_kg",
            detail=(
                f"Resolved from {self.provider.name} indexed evidence; "
                f"domain={primary.domain}; corroborating_domains="
                f"{','.join(sorted({c.domain for c in accepted[1:]})) or 'none'}"
            ),
            source_url=primary.result.url,
            extractor=self.extractor,
        ))
        return out

    @staticmethod
    def _domain(url: str) -> str:
        host = urlparse(url).hostname or ""
        return host.lower().removeprefix("www.")

    def _is_qualified_domain(self, domain: str) -> bool:
        return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in self.qualified_domains)


class GraingerToolMassResolver:
    """Legacy direct-fetch experiment retained for comparison only.

    Grainger currently returns 403 to direct automated requests in both GitHub
    Actions and local testing, so this is no longer the preferred production
    resolution path. It remains useful for regression/failure-isolation tests.
    """

    extractor = "grainger.tool_mass.v0.1"
    search_url = "https://www.grainger.ca/en/search?searchQuery={query}"

    def resolve(self, identity, artifacts, claims, fetcher) -> Resolution:
        if identity.product_type != ProductType.TOOL or not identity.sku:
            return Resolution()
        if any(claim.property_key == "tool_body_mass_kg" for claim in claims):
            return Resolution()

        search_url = self.search_url.format(query=quote_plus(identity.sku))
        try:
            search = fetcher.get(search_url, SourceType.QUALIFIED_SECONDARY_WEBPAGE)
        except Exception as exc:
            return Resolution(observations=[AcquisitionObservation(
                code="SECONDARY_SOURCE_BLOCKED_OR_UNAVAILABLE",
                value="tool_body_mass_kg",
                detail=f"Grainger search request failed: {type(exc).__name__}: {exc}",
                source_url=search_url,
                extractor=self.extractor,
            )])

        search.metadata.update({"role": "secondary_search", "provider": "Grainger"})
        out = Resolution(artifacts=[search])
        candidate_url = self._exact_candidate_url(search.body, identity.sku)
        if not candidate_url:
            return out

        try:
            product = fetcher.get(candidate_url, SourceType.QUALIFIED_SECONDARY_WEBPAGE)
        except Exception as exc:
            out.observations.append(AcquisitionObservation(
                code="SECONDARY_SOURCE_BLOCKED_OR_UNAVAILABLE",
                value="tool_body_mass_kg",
                detail=f"Grainger product request failed: {type(exc).__name__}: {exc}",
                source_url=candidate_url,
                extractor=self.extractor,
            ))
            return out

        product.metadata.update({"role": "secondary_product", "provider": "Grainger"})
        out.artifacts.append(product)
        text = SearchIndexedToolMassResolver._text(product.body) if hasattr(SearchIndexedToolMassResolver, "_text") else re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(product.body))).strip()
        if not SearchIndexedToolMassResolver._identity_matches(text, identity):
            return out
        raw_mass = SearchIndexedToolMassResolver._explicit_tool_mass(text)
        mass = parse_mass(raw_mass) if raw_mass else None
        if mass:
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
        return out

    @staticmethod
    def _exact_candidate_url(raw: str, sku: str) -> str | None:
        decoded = html.unescape(raw)
        for match in re.finditer(r'href=["\']([^"\']*?/en/product/[^"\']+/p/[^"\']+)["\']', decoded, re.I):
            context = decoded[max(0, match.start() - 400): min(len(decoded), match.end() + 400)]
            if re.search(rf"(?<![A-Z0-9]){re.escape(sku)}(?![A-Z0-9])", context, re.I):
                return urljoin("https://www.grainger.ca", match.group(1))
        return None


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
