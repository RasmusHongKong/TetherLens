from __future__ import annotations

from .adapters.base import ManufacturerAdapter
from .http import Fetcher
from .models import IngestionResult, ProductIdentity, SourceType


class IngestionRunner:
    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher

    def ingest(self, identity: ProductIdentity, adapter: ManufacturerAdapter) -> IngestionResult:
        artifact = self.fetcher.get(identity.url, SourceType.MANUFACTURER_WEBPAGE)
        artifacts = [artifact]
        claims = adapter.extract(identity, artifacts)
        observations = adapter.observe(identity, artifacts)
        readiness = adapter.readiness_issues(claims, observations)
        return IngestionResult(
            identity=identity,
            artifacts=artifacts,
            claims=claims,
            acquisition_observations=observations,
            issues=readiness or [],
            readiness_assessed=readiness is not None,
        )
