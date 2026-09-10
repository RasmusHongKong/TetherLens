from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import urlsplit

from tetherlens_ingest.models import (
    AcquisitionObservation,
    CandidateClaim,
    ProductIdentity,
    ReadinessIssue,
    SourceArtifact,
    SourceRequest,
    SourceType,
)


_MANUFACTURER_SOURCE_TYPES = {
    SourceType.MANUFACTURER_WEBPAGE,
    SourceType.MANUFACTURER_JSON,
    SourceType.MANUFACTURER_DOCUMENT,
}


class ManufacturerAdapter(ABC):
    manufacturer: str
    recursive_related_sources = False
    additional_first_party_hosts: frozenset[str] = frozenset()

    @abstractmethod
    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        raise NotImplementedError

    def related_sources(self, identity: ProductIdentity, source_artifact: SourceArtifact) -> list[SourceRequest]:
        return []

    def observe(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[AcquisitionObservation]:
        return []

    def is_first_party_url(self, identity: ProductIdentity, url: str) -> bool:
        """Return whether ``url`` is inside this product's manufacturer trust boundary.

        The product identity URL is the default trust root. ``www`` is normalized away
        and subdomains of that root are accepted. An adapter may explicitly declare
        additional official hosts when a manufacturer serves documents or APIs from a
        separate domain. Request metadata and ``SourceType`` alone never establish
        first-party provenance.
        """

        candidate = _normalized_web_host(url)
        if candidate is None:
            return False

        roots = set(self.additional_first_party_hosts)
        identity_host = _normalized_web_host(identity.url)
        if identity_host is not None:
            roots.add(identity_host)

        for root in roots:
            normalized_root = _normalize_host(root)
            if candidate == normalized_root or candidate.endswith(f".{normalized_root}"):
                return True
        return False

    def is_first_party_artifact(
        self,
        identity: ProductIdentity,
        artifact: SourceArtifact,
    ) -> bool:
        return self.is_first_party_url(identity, artifact.url)

    def accepts_artifact_provenance(
        self,
        identity: ProductIdentity,
        artifact: SourceArtifact,
    ) -> bool:
        """Gate artifacts before adapter extraction/observation/source traversal.

        Explicit secondary sources remain available to adapters. Artifacts labelled as
        manufacturer sources must independently resolve inside the manufacturer trust
        boundary before they can support manufacturer-stated evidence.
        """

        if artifact.source_type not in _MANUFACTURER_SOURCE_TYPES:
            return True
        return self.is_first_party_artifact(identity, artifact)

    def accepts_request_provenance(
        self,
        identity: ProductIdentity,
        request: SourceRequest,
    ) -> bool:
        """Reject outbound manufacturer-labelled requests outside the trust boundary."""

        if request.source_type not in _MANUFACTURER_SOURCE_TYPES:
            return True
        return self.is_first_party_url(identity, request.url)

    def source_provenance_rejected_observation(
        self,
        identity: ProductIdentity,
        *,
        url: str,
        role: str | None,
        stage: str,
    ) -> AcquisitionObservation:
        return AcquisitionObservation(
            code="MANUFACTURER_SOURCE_PROVENANCE_REJECTED",
            value=role or "related",
            detail=(
                f"A manufacturer-labelled source was excluded at {stage} because its "
                "resolved/requested host is outside the product manufacturer's trust boundary."
            ),
            source_url=url,
            extractor=f"{self.manufacturer.lower()}.runner",
        )

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


def _normalized_web_host(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    hostname = parsed.hostname
    if not hostname:
        return None
    return _normalize_host(hostname)


def _normalize_host(host: str) -> str:
    normalized = host.strip().rstrip(".").casefold()
    if normalized.startswith("www."):
        normalized = normalized[4:]
    return normalized
