from __future__ import annotations

from .adapters.base import ManufacturerAdapter
from .http import Fetcher
from .models import IngestionResult, ProductIdentity, SourceType
from .resolvers import RequiredFactResolver, derive_operational_mass_profiles


class IngestionRunner:
    def __init__(self, fetcher: Fetcher, resolvers: list[RequiredFactResolver] | None = None):
        self.fetcher = fetcher
        self.resolvers = resolvers or []

    def ingest(self, identity: ProductIdentity, adapter: ManufacturerAdapter) -> IngestionResult:
        primary = self.fetcher.get(identity.url, SourceType.MANUFACTURER_WEBPAGE)
        artifacts = [primary]

        for request in adapter.related_sources(identity, primary):
            artifact = self.fetcher.get(request.url, request.source_type)
            artifact.metadata.update(request.metadata)
            artifacts.append(artifact)

        claims = adapter.extract(identity, artifacts)
        observations = adapter.observe(identity, artifacts)

        # Required-fact resolution is intentionally separate from manufacturer
        # adapters. Resolvers only run after primary acquisition, and may stop
        # immediately when a higher-quality source has already satisfied a fact.
        for resolver in self.resolvers:
            resolution = resolver.resolve(identity, artifacts, claims, self.fetcher)
            artifacts.extend(resolution.artifacts)
            claims.extend(resolution.claims)
            observations.extend(resolution.observations)

        claims.extend(derive_operational_mass_profiles(identity, claims))
        readiness = adapter.readiness_issues(claims, observations)
        return IngestionResult(
            identity=identity,
            artifacts=artifacts,
            claims=claims,
            acquisition_observations=observations,
            issues=readiness or [],
            readiness_assessed=readiness is not None,
        )
