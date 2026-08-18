import json

from tetherlens_ingest.adapters import HiltiAdapter, MilwaukeeAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.resolvers import GraingerToolMassResolver, SearchIndexedToolMassResolver
from tetherlens_ingest.runner import IngestionRunner
from tetherlens_ingest.search import SearchResult


class MilwaukeeFetcher:
    def __init__(self):
        self.calls = []

    def get(self, url, source_type=SourceType.MANUFACTURER_WEBPAGE):
        self.calls.append(url)
        if "/api/v1/products/2602-20" in url:
            body = json.dumps({"status":"OK","data":{"result":{"sku":"2602-20","specs":{"batterySystem":{"value":"M18"}}}}})
        elif "/api/v1/products/48-11-1828" in url:
            body = json.dumps({"status":"OK","data":{"result":{"sku":"48-11-1828","specs":{"weight":{"value":"1.54 lb"}}}}})
        elif "milwaukeetool.com" in url:
            body = '<div>2602-20 M18</div><div>battery 48-11-1828</div>'
        else:
            raise AssertionError(url)
        return SourceArtifact(url=url, source_type=source_type, content_type="text/html", body=body)


class FakeSearchProvider:
    name = "fixture"

    def __init__(self, results_by_query):
        self.results_by_query = results_by_query
        self.calls = []

    def search(self, query, limit=8):
        self.calls.append(query)
        return self.results_by_query.get(query, [])[:limit]


def _identity():
    return ProductIdentity(
        manufacturer="Milwaukee",
        name="M18 Hammer Drill/Driver",
        sku="2602-20",
        product_type=ProductType.TOOL,
        url="https://www.milwaukeetool.com/products/details/example/2602-20",
    )


def test_search_index_resolves_exact_sku_qualified_distributor_and_derives_operational_mass():
    identity = _identity()
    query = SearchIndexedToolMassResolver._queries(identity)[0]
    provider = FakeSearchProvider({query: [SearchResult(
        provider="fixture",
        query=query,
        rank=1,
        title="MILWAUKEE 2602-20 M18 Hammer Drill",
        url="https://www.grainger.ca/en/product/example/p/MTL2602-20",
        snippet="MILWAUKEE 2602-20. Tool Weight 3.5 lb. Includes Tool Only.",
    )]})

    result = IngestionRunner(MilwaukeeFetcher(), [SearchIndexedToolMassResolver(provider)]).ingest(identity, MilwaukeeAdapter())
    claims = {(c.subject_ref, c.property_key): c for c in result.claims}

    body = claims[("self", "tool_body_mass_kg")]
    assert body.raw_value == "3.5 lb"
    assert body.value == 1.587573
    assert body.evidence_method == "search_indexed_qualified_secondary"
    assert claims[("2602-20+48-11-1828", "operational_mass_kg")].value == 2.286105
    assert result.issues == []
    assert len(provider.calls) == 1
    assert any(o.code == "REQUIRED_FACT_RESOLVED_SEARCH" for o in result.acquisition_observations)


def test_search_index_rejects_mismatched_sku_and_shipping_weight():
    identity = _identity()
    queries = SearchIndexedToolMassResolver._queries(identity)
    provider = FakeSearchProvider({
        queries[0]: [SearchResult(
            provider="fixture", query=queries[0], rank=1,
            title="MILWAUKEE 2602-21 Hammer Drill",
            url="https://www.grainger.ca/en/product/wrong/p/MTL2602-21",
            snippet="MILWAUKEE 2602-21 Tool Weight 3.5 lb",
        )],
        queries[1]: [SearchResult(
            provider="fixture", query=queries[1], rank=1,
            title="MILWAUKEE 2602-20 Hammer Drill",
            url="https://www.grainger.ca/en/product/example/p/MTL2602-20",
            snippet="MILWAUKEE 2602-20 Shipping Weight 4.0 lb",
        )],
        queries[2]: [],
    })

    result = IngestionRunner(MilwaukeeFetcher(), [SearchIndexedToolMassResolver(provider)]).ingest(identity, MilwaukeeAdapter())
    assert not any(c.property_key == "tool_body_mass_kg" for c in result.claims)
    assert any(i.code == "MISSING_TOOL_BODY_MASS" for i in result.issues)
    assert any(o.code == "REQUIRED_FACT_SEARCH_UNRESOLVED" for o in result.acquisition_observations)


def test_unqualified_search_sources_require_two_domain_corroboration():
    identity = _identity()
    query = SearchIndexedToolMassResolver._queries(identity)[0]
    provider = FakeSearchProvider({query: [
        SearchResult(provider="fixture", query=query, rank=1, title="Milwaukee 2602-20", url="https://retailer-one.example/item", snippet="Milwaukee 2602-20 Tool Weight 3.5 lb"),
        SearchResult(provider="fixture", query=query, rank=2, title="Milwaukee 2602-20", url="https://retailer-two.example/item", snippet="Milwaukee 2602-20 Tool Weight 3.5 lb"),
    ]})

    result = IngestionRunner(MilwaukeeFetcher(), [SearchIndexedToolMassResolver(provider)]).ingest(identity, MilwaukeeAdapter())
    body = next(c for c in result.claims if c.property_key == "tool_body_mass_kg")
    assert body.value == 1.587573
    assert body.supporting_source_urls == ["https://retailer-two.example/item"]


def test_search_resolver_skips_lookup_when_manufacturer_already_supplies_mass():
    class HiltiFetcher:
        def __init__(self): self.calls = []
        def get(self, url, source_type=SourceType.MANUFACTURER_WEBPAGE):
            self.calls.append(url)
            return SourceArtifact(url=url, source_type=source_type, content_type="text/html", body="#2253847 Tool body weight 2.9 lb")

    provider = FakeSearchProvider({})
    fetcher = HiltiFetcher()
    identity = ProductIdentity(manufacturer="Hilti", sku="2253847", product_type=ProductType.TOOL, url="https://www.hilti.com/example")
    result = IngestionRunner(fetcher, [SearchIndexedToolMassResolver(provider)]).ingest(identity, HiltiAdapter())
    assert any(c.property_key == "tool_body_mass_kg" for c in result.claims)
    assert provider.calls == []
    assert any(o.code == "REQUIRED_FACT_ALREADY_SATISFIED" for o in result.acquisition_observations)


def test_legacy_grainger_block_is_non_fatal():
    class BlockingFetcher(MilwaukeeFetcher):
        def get(self, url, source_type=SourceType.MANUFACTURER_WEBPAGE):
            if "grainger.ca" in url:
                raise RuntimeError("403 Forbidden")
            return super().get(url, source_type)

    result = IngestionRunner(BlockingFetcher(), [GraingerToolMassResolver()]).ingest(_identity(), MilwaukeeAdapter())
    assert any(c.property_key == "battery_mass_kg" for c in result.claims)
    assert not any(c.property_key == "tool_body_mass_kg" for c in result.claims)
    assert any(o.code == "SECONDARY_SOURCE_BLOCKED_OR_UNAVAILABLE" for o in result.acquisition_observations)
