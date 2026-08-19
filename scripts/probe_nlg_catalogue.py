from __future__ import annotations

import argparse
import json

from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.http import HttpxFetcher
from tetherlens_ingest.models import SourceType

DEFAULT_COLLECTIONS = [
    "https://neverletgo.com/collections/tool-lanyards/products.json?limit=250",
    "https://neverletgo.com/collections/tether-points/products.json?limit=250",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe NLG collection JSON and report SKU-bound catalogue candidates."
    )
    parser.add_argument(
        "urls",
        nargs="*",
        default=DEFAULT_COLLECTIONS,
        help="Collection products.json URLs to inspect.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    fetcher = HttpxFetcher(timeout=30)
    adapter = NLGAdapter()
    records: list[dict] = []

    try:
        for url in args.urls:
            artifact = fetcher.get(url, SourceType.MANUFACTURER_JSON)
            identities = adapter.discover_collection(artifact)
            records.append(
                {
                    "requested_url": url,
                    "resolved_url": artifact.url,
                    "content_type": artifact.content_type,
                    "candidate_count": len(identities),
                    "sku_bound_count": sum(bool(identity.sku) for identity in identities),
                    "candidates": [
                        {
                            "name": identity.name,
                            "sku": identity.sku,
                            "url": identity.url,
                            "manufacturer_ids": identity.manufacturer_ids,
                        }
                        for identity in identities
                    ],
                }
            )
    finally:
        fetcher.close()

    print(json.dumps({"manufacturer": "NLG", "collections": records}, indent=2))


if __name__ == "__main__":
    main()
