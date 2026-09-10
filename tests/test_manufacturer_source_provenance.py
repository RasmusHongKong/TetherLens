from __future__ import annotations

from tetherlens_ingest.adapters.base import ManufacturerAdapter
from tetherlens_ingest.models import (
    CandidateClaim,
    ProductIdentity,
    SourceArtifact,
    SourceRequest,
    SourceType,
)
from tetherlens_ingest.runner import IngestionRunner


PRIMARY_URL = "https://manufacturer.example/products/fixture"
FIRST_PARTY_DOC_URL = "https://docs.manufacturer.example/fixture.pdf"
EXTERNAL_DOC_URL = "https://external.example/fixture.pdf"
SECONDARY_URL = "https://secondary.example/products/fixture"


class _ArtifactMapFetcher:
    def __init__(self, artifacts: dict[str, SourceArtifact]):
        self.artifacts = artifacts
        self.calls: list[tuple[str, SourceType]] = []

    def get(self, url: str, source_type: SourceType) -> SourceArtifact:
        self.calls.append((url, source_type))
        artifact = self.artifacts[url].model_copy(deep=True)
        assert artifact.source_type == source_type
        return artifact


class _RecordingAdapter(ManufacturerAdapter):
    manufacturer = "Fixture Manufacturer"
    recursive_related_sources = True

    def __init__(self, requests: list[SourceRequest] | None = None):
        self.requests = requests or []
        self.related_calls: list[str] = []

    def related_sources(
        self,
        identity: ProductIdentity,
        source_artifact: SourceArtifact,
    ) -> list[SourceRequest]:
        self.related_calls.append(source_artifact.url)
        if source_artifact.metadata.get("role"):
            return []
        return list(self.requests)

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        return [
            CandidateClaim(
                property_key="seen_source",
                value=artifact.url,
                source_url=artifact.url,
                evidence_method=(
                    "manufacturer_stated"
                    if artifact.source_type != SourceType.SECONDARY_WEBPAGE
                    else "qualified_secondary_exact_sku"
                ),
                extractor="fixture.v0",
            )
            for artifact in artifacts
        ]


def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Fixture Manufacturer",
        name="Fixture",
        sku="FIXTURE-1",
        url=PRIMARY_URL,
    )


def _artifact(
    url: str,
    source_type: SourceType,
    *,
    final_url: str | None = None,
) -> SourceArtifact:
    return SourceArtifact(
        url=final_url or url,
        source_type=source_type,
        content_type=("application/pdf" if source_type == SourceType.MANUFACTURER_DOCUMENT else "text/html"),
        body="fixture evidence",
    )


def test_runner_rejects_external_manufacturer_request_before_fetch() -> None:
    fetcher = _ArtifactMapFetcher({
        PRIMARY_URL: _artifact(PRIMARY_URL, SourceType.MANUFACTURER_WEBPAGE),
    })
    adapter = _RecordingAdapter([
        SourceRequest(
            url=EXTERNAL_DOC_URL,
            source_type=SourceType.MANUFACTURER_DOCUMENT,
            metadata={"role": "manufacturer_manual"},
        )
    ])

    result = IngestionRunner(fetcher).ingest(_identity(), adapter)

    assert fetcher.calls == [(PRIMARY_URL, SourceType.MANUFACTURER_WEBPAGE)]
    assert [claim.source_url for claim in result.claims] == [PRIMARY_URL]
    rejection = next(
        observation
        for observation in result.acquisition_observations
        if observation.code == "MANUFACTURER_SOURCE_PROVENANCE_REJECTED"
    )
    assert rejection.source_url == EXTERNAL_DOC_URL
    assert "source discovery" in (rejection.detail or "")


def test_runner_revalidates_final_host_after_manufacturer_redirect() -> None:
    fetcher = _ArtifactMapFetcher({
        PRIMARY_URL: _artifact(PRIMARY_URL, SourceType.MANUFACTURER_WEBPAGE),
        FIRST_PARTY_DOC_URL: _artifact(
            FIRST_PARTY_DOC_URL,
            SourceType.MANUFACTURER_DOCUMENT,
            final_url=EXTERNAL_DOC_URL,
        ),
    })
    adapter = _RecordingAdapter([
        SourceRequest(
            url=FIRST_PARTY_DOC_URL,
            source_type=SourceType.MANUFACTURER_DOCUMENT,
            metadata={"role": "manufacturer_manual"},
        )
    ])

    result = IngestionRunner(fetcher).ingest(_identity(), adapter)

    assert fetcher.calls == [
        (PRIMARY_URL, SourceType.MANUFACTURER_WEBPAGE),
        (FIRST_PARTY_DOC_URL, SourceType.MANUFACTURER_DOCUMENT),
    ]
    assert [artifact.url for artifact in result.artifacts] == [PRIMARY_URL, EXTERNAL_DOC_URL]
    assert [claim.source_url for claim in result.claims] == [PRIMARY_URL]
    assert EXTERNAL_DOC_URL not in adapter.related_calls
    rejection = next(
        observation
        for observation in result.acquisition_observations
        if observation.code == "MANUFACTURER_SOURCE_PROVENANCE_REJECTED"
    )
    assert rejection.source_url == EXTERNAL_DOC_URL
    assert "artifact resolution" in (rejection.detail or "")


def test_runner_keeps_explicit_external_secondary_sources_available() -> None:
    fetcher = _ArtifactMapFetcher({
        PRIMARY_URL: _artifact(PRIMARY_URL, SourceType.MANUFACTURER_WEBPAGE),
        SECONDARY_URL: SourceArtifact(
            url=SECONDARY_URL,
            source_type=SourceType.SECONDARY_WEBPAGE,
            content_type="text/html",
            body="qualified exact-SKU secondary evidence",
        ),
    })
    adapter = _RecordingAdapter([
        SourceRequest(
            url=SECONDARY_URL,
            source_type=SourceType.SECONDARY_WEBPAGE,
            metadata={"role": "secondary_detail"},
        )
    ])

    result = IngestionRunner(fetcher).ingest(_identity(), adapter)

    assert [claim.source_url for claim in result.claims] == [PRIMARY_URL, SECONDARY_URL]
    assert not any(
        observation.code == "MANUFACTURER_SOURCE_PROVENANCE_REJECTED"
        for observation in result.acquisition_observations
    )


def test_manufacturer_trust_root_accepts_subdomains_and_explicit_additional_hosts() -> None:
    adapter = _RecordingAdapter()
    identity = _identity()

    assert adapter.is_first_party_url(identity, FIRST_PARTY_DOC_URL)
    assert not adapter.is_first_party_url(identity, EXTERNAL_DOC_URL)

    class _AdditionalHostAdapter(_RecordingAdapter):
        additional_first_party_hosts = frozenset({"official-docs.example"})

    additional = _AdditionalHostAdapter()
    assert additional.is_first_party_url(identity, "https://cdn.official-docs.example/manual.pdf")
