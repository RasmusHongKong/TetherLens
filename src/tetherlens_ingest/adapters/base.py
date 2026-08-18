from __future__ import annotations

from abc import ABC, abstractmethod

from tetherlens_ingest.models import (
    AcquisitionObservation,
    CandidateClaim,
    ProductIdentity,
    ReadinessIssue,
    SourceArtifact,
    SourceRequest,
)


class ManufacturerAdapter(ABC):
    manufacturer: str

    @abstractmethod
    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        raise NotImplementedError

    def related_sources(self, identity: ProductIdentity, source_artifact: SourceArtifact) -> list[SourceRequest]:
        return []

    def observe(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[AcquisitionObservation]:
        return []

    def source_fetch_failed_observation(self, identity: ProductIdentity, error: dict[str, str]) -> AcquisitionObservation:
        return AcquisitionObservation(
            code="RELATED_SOURCE_FETCH_FAILED",
            value=error.get("role") or "related",
            detail=error.get("error"),
            source_url=error.get("url"),
            extractor=f"{self.manufacturer.lower()}.runner",
        )

    def source_graph_limit_observation(self, identity: ProductIdentity, limit: int) -> AcquisitionObservation:
        return AcquisitionObservation(
            code="SOURCE_GRAPH_LIMIT_REACHED",
            value=limit,
            detail="Related-source traversal stopped at the configured safety limit.",
            source_url=identity.url,
            extractor=f"{self.manufacturer.lower()}.runner",
        )

    def readiness_issues(
        self,
        claims: list[CandidateClaim],
        observations: list[AcquisitionObservation],
    ) -> list[ReadinessIssue] | None:
        return None
