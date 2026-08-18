from __future__ import annotations

from .adapters.base import ManufacturerAdapter
from .http import Fetcher
from .models import IngestionResult, ProductIdentity, SourceType


class IngestionRunner:
    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher

    def ingest(self, identity: ProductIdentity, adapter: ManufacturerAdapter) -> IngestionResult:
        primary = self.fetcher.get(identity.url, SourceType.MANUFACTURER_WEBPAGE)
        artifacts = [primary]
        fetch_errors: list[dict[str, str]] = []

        for request in adapter.related_sources(identity, primary):
            try:
                artifact = self.fetcher.get(request.url, request.source_type)
            except Exception as exc:
                fetch_errors.append({
                    "url": request.url,
                    "role": str(request.metadata.get("role") or "related"),
                    "error": f"{type(exc).__name__}: {exc}",
                })
                continue
            artifact.metadata.update(request.metadata)
            artifacts.append(artifact)

        claims = adapter.extract(identity, artifacts)
        observations = adapter.observe(identity, artifacts)
        for error in fetch_errors:
            observations.append(adapter.source_fetch_failed_observation(identity, error))
        readiness = adapter.readiness_issues(claims, observations)
        return IngestionResult(
            identity=identity,
            artifacts=artifacts,
            claims=claims,
            acquisition_observations=observations,
            issues=readiness or [],
            readiness_assessed=readiness is not None,
        )
