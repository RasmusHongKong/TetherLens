from tetherlens_ingest.adapters.base import ManufacturerAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceRequest, SourceType
from tetherlens_ingest.runner import IngestionRunner


class NonRecursiveAdapter(ManufacturerAdapter):
    manufacturer = "Test"

    def extract(self, identity, artifacts):
        return []

    def related_sources(self, identity, artifact):
        role = artifact.metadata.get("role") or "primary"
        if role == "primary":
            return [SourceRequest(url="https://example.test/child", metadata={"role": "child"})]
        return [SourceRequest(url="https://example.test/grandchild", metadata={"role": "grandchild"})]


class RedirectAdapter(ManufacturerAdapter):
    manufacturer = "Test"

    def extract(self, identity, artifacts):
        return []

    def related_sources(self, identity, artifact):
        return [
            SourceRequest(url="https://example.test/alias", metadata={"role": "alias"}),
            SourceRequest(url="https://example.test/canonical", metadata={"role": "canonical"}),
        ]


class CanonicalFirstRedirectAdapter(ManufacturerAdapter):
    manufacturer = "Test"

    def extract(self, identity, artifacts):
        return []

    def related_sources(self, identity, artifact):
        return [
            SourceRequest(url="https://example.test/canonical", metadata={"role": "canonical"}),
            SourceRequest(url="https://example.test/alias", metadata={"role": "alias"}),
        ]


class FakeFetcher:
    def __init__(self):
        self.calls = []

    def get(self, url, source_type=SourceType.MANUFACTURER_WEBPAGE):
        self.calls.append(url)
        if url == "https://example.test/alias":
            resolved_url = "https://example.test/canonical"
        else:
            resolved_url = url
        return SourceArtifact(
            url=resolved_url,
            source_type=source_type,
            content_type="text/html",
            body=f"<h1>{resolved_url}</h1>",
        )


def _identity():
    return ProductIdentity(
        manufacturer="Test",
        name="Test product",
        sku="TEST-1",
        product_type=ProductType.TOOL,
        url="https://example.test/primary",
    )


def test_runner_does_not_recurse_for_adapters_that_do_not_opt_in():
    fetcher = FakeFetcher()
    result = IngestionRunner(fetcher).ingest(_identity(), NonRecursiveAdapter())

    assert fetcher.calls == ["https://example.test/primary", "https://example.test/child"]
    assert len(result.artifacts) == 2


def test_runner_dedupes_canonical_request_after_alias_redirect():
    fetcher = FakeFetcher()
    result = IngestionRunner(fetcher).ingest(_identity(), RedirectAdapter())

    assert fetcher.calls == ["https://example.test/primary", "https://example.test/alias"]
    assert [artifact.url for artifact in result.artifacts] == [
        "https://example.test/primary",
        "https://example.test/canonical",
    ]


def test_runner_discards_alias_artifact_when_it_resolves_to_already_seen_canonical_url():
    fetcher = FakeFetcher()
    result = IngestionRunner(fetcher).ingest(_identity(), CanonicalFirstRedirectAdapter())

    assert fetcher.calls == [
        "https://example.test/primary",
        "https://example.test/canonical",
        "https://example.test/alias",
    ]
    assert [artifact.url for artifact in result.artifacts] == [
        "https://example.test/primary",
        "https://example.test/canonical",
    ]
    assert result.artifacts[1].metadata["role"] == "canonical"
