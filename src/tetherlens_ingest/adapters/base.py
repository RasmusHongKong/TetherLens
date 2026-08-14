from __future__ import annotations

from abc import ABC, abstractmethod

from tetherlens_ingest.models import AcquisitionObservation, CandidateClaim, ProductIdentity, ReadinessIssue, SourceArtifact


class ManufacturerAdapter(ABC):
    manufacturer: str

    @abstractmethod
    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        raise NotImplementedError

    def observe(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[AcquisitionObservation]:
        return []

    def readiness_issues(
        self,
        claims: list[CandidateClaim],
        observations: list[AcquisitionObservation],
    ) -> list[ReadinessIssue] | None:
        return None
