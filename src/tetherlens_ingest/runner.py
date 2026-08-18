from __future__ import annotations

from collections import deque

from .adapters.base import ManufacturerAdapter
from .http import Fetcher
from .models import IngestionResult, ProductIdentity, SourceType


class IngestionRunner:
    def __init__(self, fetcher: Fetcher, max_related_sources: int = 24):
        self.fetcher = fetcher
        self.max_related_sources = max_related_sources

    def ingest(self, identity: ProductIdentity, adapter: ManufacturerAdapter) -> IngestionResult:
        primary = self.fetcher.get(identity.url, SourceType.MANUFACTURER_WEBPAGE)
        artifacts = [primary]
        pending = deque([primary])
        seen_urls = {identity.url, primary.url}
        fetch_errors: list[dict[str, str]] = []
        related_fetches = 0

        while pending and related_fetches < self.max_related_sources:
            source_artifact = pending.popleft()
            if source_artifact is not primary and not adapter.recursive_related_sources:
                continue
            for request in adapter.related_sources(identity, source_artifact):
                if request.url in seen_urls:
                    continue
                seen_urls.add(request.url)
                related_fetches += 1
                try:
                    artifact = self.fetcher.get(request.url, request.source_type)
                except Exception as exc:
                    fetch_errors.append({
                        "url": request.url,
                        "role": str(request.metadata.get("role") or "related"),
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                    if related_fetches >= self.max_related_sources:
                        break
                    continue

                if artifact.url != request.url and artifact.url in seen_urls:
                    if related_fetches >= self.max_related_sources:
                        break
                    continue

                artifact.metadata.update(request.metadata)
                seen_urls.add(artifact.url)
                artifacts.append(artifact)
                pending.append(artifact)
                if related_fetches >= self.max_related_sources:
                    break

        claims = adapter.extract(identity, artifacts)
        observations = adapter.observe(identity, artifacts)
        for error in fetch_errors:
            observations.append(adapter.source_fetch_failed_observation(identity, error))
        if pending:
            observations.append(adapter.source_graph_limit_observation(identity, self.max_related_sources))
        readiness = adapter.readiness_issues(claims, observations)
        return IngestionResult(
            identity=identity,
            artifacts=artifacts,
            claims=claims,
            acquisition_observations=observations,
            issues=readiness or [],
            readiness_assessed=readiness is not None,
        )