import json

from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.models import SourceArtifact, SourceType


def test_nlg_discovers_shopify_variant_skus():
    payload = {
        "products": [
            {
                "id": 1001,
                "title": "Example Lanyard",
                "handle": "example-lanyard",
                "variants": [
                    {"id": 2001, "sku": "101001"},
                    {"id": 2002, "sku": "101002"},
                ],
            }
        ]
    }
    source = SourceArtifact(
        url="https://neverletgo.com/collections/tool-lanyards/products.json?limit=250",
        source_type=SourceType.MANUFACTURER_JSON,
        content_type="application/json",
        body=json.dumps(payload),
    )

    identities = NLGAdapter().discover_collection(source)

    assert [item.sku for item in identities] == ["101001", "101002"]
    assert all(item.url == "https://neverletgo.com/products/example-lanyard" for item in identities)
    assert identities[0].manufacturer_ids == {"id": "1001", "variant_id": "2001"}
    assert identities[1].manufacturer_ids == {"id": "1001", "variant_id": "2002"}


def test_nlg_collection_discovery_falls_back_to_product_level_sku_and_dedupes():
    payload = {
        "products": [
            {
                "id": 1001,
                "title": "Example Tether Point",
                "url": "/products/example-tether-point",
                "sku": "101010",
            },
            {
                "id": 1001,
                "title": "Example Tether Point",
                "url": "/products/example-tether-point",
                "sku": "101010",
            },
        ]
    }
    source = SourceArtifact(
        url="https://neverletgo.com/collections/tether-points/products.json",
        source_type=SourceType.MANUFACTURER_JSON,
        content_type="application/json",
        body=json.dumps(payload),
    )

    identities = NLGAdapter().discover_collection(source)

    assert len(identities) == 1
    assert identities[0].sku == "101010"
    assert identities[0].url == "https://neverletgo.com/products/example-tether-point"


def test_nlg_collection_discovery_resolves_bare_site_relative_url_from_root():
    payload = {
        "products": [
            {
                "id": 1001,
                "title": "Example Tool Lanyard",
                "url": "products/example-tool-lanyard",
                "sku": "101011",
            }
        ]
    }
    source = SourceArtifact(
        url="https://neverletgo.com/collections/tool-lanyards/products.json?limit=250",
        source_type=SourceType.MANUFACTURER_JSON,
        content_type="application/json",
        body=json.dumps(payload),
    )

    identities = NLGAdapter().discover_collection(source)

    assert len(identities) == 1
    assert identities[0].url == "https://neverletgo.com/products/example-tool-lanyard"
