from __future__ import annotations

from .adapters.base import ManufacturerAdapter
from .http import Fetcher
from .models import IngestionResult, ProductIdentity, ReadinessIssue, SourceType


class IngestionRunner:
    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher

    def ingest(self, identity: ProductIdentity, adapter: ManufacturerAdapter) -> IngestionResult:
        artifact = self.fetcher.get(identity.url, SourceType.MANUFACTURER_WEBPAGE)
        claims = adapter.extract(identity, [artifact])
        issues: list[ReadinessIssue] = []
        readiness = getattr(adapter, "readiness_issues", None)
        if readiness:
            issues = readiness(claims)
        return IngestionResult(identity=identity, artifacts=[artifact], claims=claims, issues=issues)
