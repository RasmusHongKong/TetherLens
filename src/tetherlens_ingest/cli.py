from __future__ import annotations

import argparse
import json

from .adapters import HiltiAdapter, MilwaukeeAdapter, NLGAdapter, StopDropAdapter
from .http import HttpxFetcher
from .models import ProductIdentity, ProductType
from .runner import IngestionRunner

ADAPTERS = {
    "nlg": NLGAdapter,
    "hilti": HiltiAdapter,
    "stopdrop": StopDropAdapter,
    "milwaukee": MilwaukeeAdapter,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a TetherLens manufacturer ingestion adapter against one product page.")
    parser.add_argument("manufacturer", choices=sorted(ADAPTERS))
    parser.add_argument("url")
    parser.add_argument("--sku")
    parser.add_argument("--name")
    parser.add_argument("--product-type", choices=[p.value for p in ProductType], default=ProductType.UNKNOWN.value)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    fetcher = HttpxFetcher()
    try:
        identity = ProductIdentity(
            manufacturer=args.manufacturer,
            name=args.name,
            sku=args.sku,
            product_type=ProductType(args.product_type),
            url=args.url,
        )
        adapter = ADAPTERS[args.manufacturer]()
        result = IngestionRunner(fetcher).ingest(identity, adapter)
        print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    finally:
        fetcher.close()


if __name__ == "__main__":
    main()
