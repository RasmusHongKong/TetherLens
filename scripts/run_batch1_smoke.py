from __future__ import annotations

import json

from tetherlens_ingest.adapters import HiltiAdapter, MilwaukeeAdapter, NLGAdapter, StopDropAdapter
from tetherlens_ingest.http import HttpxFetcher
from tetherlens_ingest.models import ProductIdentity, ProductType
from tetherlens_ingest.runner import IngestionRunner

CASES = [
    (NLGAdapter(), ProductIdentity(manufacturer="NLG", name="Bungee Tool Lanyard", sku="101372", product_type=ProductType.TETHER, url="https://neverletgo.com/products/bungee-tool-lanyard")),
    (HiltiAdapter(), ProductIdentity(manufacturer="Hilti", name="Tool tether 15lbs double carabiner", sku="2261970", product_type=ProductType.TETHER, url="https://www.hilti.com/c/CLS_HEALTH_SAFETY/CLS_SAFETY_GEAR/2261970")),
    (StopDropAdapter(), ProductIdentity(manufacturer="StopDrop", name="Black Wire Coil Tool Lanyard", sku="SDCOIL32", product_type=ProductType.TETHER, url="https://stopdroptooling.com/product/black-wire-coil-lanyard-for-working-at-height-stopdrop-tooling/")),
    (MilwaukeeAdapter(), ProductIdentity(manufacturer="Milwaukee", name="M18 Cordless 1/2 in Hammer Drill/Driver", sku="2602-20", product_type=ProductType.TOOL, url="https://www.milwaukeetool.com/products/details/m18-cordless-1-2-hammer-drill-driver-tool-only/2602-20")),
]


def main() -> None:
    fetcher = HttpxFetcher(timeout=30)
    runner = IngestionRunner(fetcher)
    failures = 0
    try:
        for adapter, identity in CASES:
            try:
                result = runner.ingest(identity, adapter)
                print(json.dumps({
                    "manufacturer": identity.manufacturer,
                    "sku": identity.sku,
                    "claim_count": len(result.claims),
                    "claims": [c.model_dump(mode="json") for c in result.claims],
                    "issues": [i.model_dump(mode="json") for i in result.issues],
                }, indent=2))
            except Exception as exc:
                failures += 1
                print(json.dumps({"manufacturer": identity.manufacturer, "sku": identity.sku, "error": f"{type(exc).__name__}: {exc}"}, indent=2))
    finally:
        fetcher.close()
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
