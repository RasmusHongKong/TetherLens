from __future__ import annotations

from abc import ABC, abstractmethod

from tetherlens_ingest.models import CandidateClaim, ProductIdentity, SourceArtifact


class ManufacturerAdapter(ABC):
    manufacturer: str

    @abstractmethod
    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        raise NotImplementedError
