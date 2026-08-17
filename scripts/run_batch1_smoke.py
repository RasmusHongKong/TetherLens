from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from tetherlens_ingest.adapters import HiltiAdapter, MilwaukeeAdapter, NLGAdapter, StopDropAdapter
from tetherlens_ingest.http import HttpxFetcher
from tetherlens_ingest.models import ProductIdentity, ProductType
from tetherlens_ingest.resolvers import GraingerToolMassResolver
from tetherlens_ingest.runner import IngestionRunner

RESULT_PATH = Path("batch1-benchmark-results.json")

NLG = NLGAdapter()
HILTI = HiltiAdapter()
STOPDROP = StopDropAdapter()
MILWAUKEE = MilwaukeeAdapter()

CASES = [
    # NLG — four different product roles on a highly regular manufacturer site.
    (
        NLG,
        ProductIdentity(
            manufacturer="NLG",
            name="Bungee Tool Lanyard",
            sku="101372",
            product_type=ProductType.TETHER,
            url="https://neverletgo.com/products/bungee-tool-lanyard",
        ),
    ),
    (
        NLG,
        ProductIdentity(
            manufacturer="NLG",
            name="360 D Ring Loop Tool Tether",
            sku="101363",
            product_type=ProductType.TOOL_ATTACHMENT,
            url="https://neverletgo.com/products/360-d-ring-loop-tool-tether",
        ),
    ),
    (
        NLG,
        ProductIdentity(
            manufacturer="NLG",
            name="Superlight Safety Tool Belt",
            sku="101420",
            product_type=ProductType.ANCHOR_ATTACHMENT,
            url="https://neverletgo.com/products/superlight-safety-tool-belt",
        ),
    ),
    (
        NLG,
        ProductIdentity(
            manufacturer="NLG",
            name="MEWP Bag",
            sku="101423",
            product_type=ProductType.CONTAINER,
            url="https://neverletgo.com/products/mewp-bag",
        ),
    ),
    # Hilti — product-family identity, tether product and retaining-strap relationship.
    (
        HILTI,
        ProductIdentity(
            manufacturer="Hilti",
            name="SF 4-22 Cordless drill driver",
            sku="2253847",
            product_type=ProductType.TOOL,
            url="https://www.hilti.com/c/CLS_POWER_TOOLS_7125/CLS_DRILL_DRIVERS_SCREW_DRIVERS__7125/r13275669",
            manufacturer_ids={"technical_family": "r13275669"},
        ),
    ),
    (
        HILTI,
        ProductIdentity(
            manufacturer="Hilti",
            name="Tool tether 15lbs double carabiner",
            sku="2261970",
            product_type=ProductType.TETHER,
            url="https://www.hilti.com/c/CLS_HEALTH_SAFETY/CLS_SAFETY_GEAR/2261970",
        ),
    ),
    (
        HILTI,
        ProductIdentity(
            manufacturer="Hilti",
            name="Retaining strap 15lb cordl.",
            sku="2293133",
            product_type=ProductType.TOOL_ATTACHMENT,
            url="https://www.hilti.com/c/CLS_HEALTH_SAFETY/CLS_SAFETY_GEAR/2293133",
        ),
    ),
    # StopDrop — sparse tool, two lanyard patterns and a sparse container page.
    (
        STOPDROP,
        ProductIdentity(
            manufacturer="StopDrop",
            name="Crimp tool for working at height",
            sku="SDKN1802",
            product_type=ProductType.TOOL,
            url="https://stopdroptooling.com/product/stopdrop-tooling-crimp-tool-for-working-at-height/",
        ),
    ),
    (
        STOPDROP,
        ProductIdentity(
            manufacturer="StopDrop",
            name="Black Wire Coil Tool Lanyard",
            sku="SDCOIL32",
            product_type=ProductType.TETHER,
            url="https://stopdroptooling.com/product/black-wire-coil-lanyard-for-working-at-height-stopdrop-tooling/",
        ),
    ),
    (
        STOPDROP,
        ProductIdentity(
            manufacturer="StopDrop",
            name="Wire Tool Lanyard",
            sku="SDLANWIRE10",
            product_type=ProductType.TETHER,
            url="https://stopdroptooling.com/product/stopdrop-tooling-wire-lanyard-with-locking-screwgate-carabiner-for-working-at-height/",
        ),
    ),
    (
        STOPDROP,
        ProductIdentity(
            manufacturer="StopDrop",
            name="Waist and Shoulder Bag",
            sku="SDBAG2",
            product_type=ProductType.CONTAINER,
            url="https://stopdroptooling.com/product/stopdrop-tooling-waist-and-shoulder-bags-for-working-at-height/",
        ),
    ),
    # Milwaukee — dynamic-spec / battery-configuration stress case.
    (
        MILWAUKEE,
        ProductIdentity(
            manufacturer="Milwaukee",
            name="M18 Cordless 1/2 in Hammer Drill/Driver",
            sku="2602-20",
            product_type=ProductType.TOOL,
            url="https://www.milwaukeetool.com/products/details/m18-cordless-1-2-hammer-drill-driver-tool-only/2602-20",
        ),
    ),
]


def _mandatory_scalar_status(product_type: ProductType, claim_keys: set[str]) -> tuple[list[str], bool]:
    """Benchmark-only scalar check; this is not full recommendation readiness."""
    if product_type == ProductType.TOOL:
        required = ["operational_mass_kg"]
    elif product_type in {
        ProductType.TETHER,
        ProductType.TOOL_ATTACHMENT,
        ProductType.ANCHOR_ATTACHMENT,
        ProductType.CONTAINER,
    }:
        required = ["rated_capacity_kg", "variant.rated_capacity_kg"]
    else:
        return [], False

    # For variant pages, either the product-level or variant-level rated capacity
    # is enough to establish that a mandatory scalar was surfaced by this pass.
    if product_type != ProductType.TOOL:
        return required, any(key in claim_keys for key in required)
    return required, all(key in claim_keys for key in required)


def _summary(records: list[dict], elapsed_ms: int) -> dict:
    by_manufacturer: dict[str, dict] = {}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        grouped[record["manufacturer"]].append(record)

    for manufacturer, manufacturer_records in sorted(grouped.items()):
        by_manufacturer[manufacturer] = {
            "attempted": len(manufacturer_records),
            "acquired": sum(bool(r["acquisition_succeeded"]) for r in manufacturer_records),
            "failed": sum(not bool(r["acquisition_succeeded"]) for r in manufacturer_records),
            "claims": sum(int(r.get("claim_count", 0)) for r in manufacturer_records),
            "mandatory_scalar_present": sum(bool(r.get("mandatory_scalar_present")) for r in manufacturer_records),
            "readiness_assessed": sum(bool(r.get("readiness_assessed")) for r in manufacturer_records),
            "readiness_issue_count": sum(len(r.get("readiness_issues", [])) for r in manufacturer_records),
            "acquisition_observation_count": sum(len(r.get("acquisition_observations", [])) for r in manufacturer_records),
        }

    issue_codes = Counter(
        issue["code"]
        for record in records
        for issue in record.get("readiness_issues", [])
        if issue.get("code")
    )
    observation_codes = Counter(
        observation["code"]
        for record in records
        for observation in record.get("acquisition_observations", [])
        if observation.get("code")
    )
    claim_keys = Counter(
        claim["property_key"]
        for record in records
        for claim in record.get("claims", [])
        if claim.get("property_key")
    )

    return {
        "attempted": len(records),
        "acquired": sum(bool(r["acquisition_succeeded"]) for r in records),
        "failed": sum(not bool(r["acquisition_succeeded"]) for r in records),
        "total_claims": sum(int(r.get("claim_count", 0)) for r in records),
        "mandatory_scalar_present": sum(bool(r.get("mandatory_scalar_present")) for r in records),
        "readiness_assessed": sum(bool(r.get("readiness_assessed")) for r in records),
        "readiness_unassessed": sum(not bool(r.get("readiness_assessed")) for r in records),
        "products_with_readiness_issues": sum(bool(r.get("readiness_issues")) for r in records),
        "elapsed_ms": elapsed_ms,
        "claim_key_counts": dict(sorted(claim_keys.items())),
        "readiness_issue_codes": dict(sorted(issue_codes.items())),
        "acquisition_observation_codes": dict(sorted(observation_codes.items())),
        "by_manufacturer": by_manufacturer,
    }


def main() -> None:
    fetcher = HttpxFetcher(timeout=30)
    runner = IngestionRunner(fetcher, resolvers=[GraingerToolMassResolver()])
    records: list[dict] = []
    benchmark_started = perf_counter()

    try:
        for adapter, identity in CASES:
            case_started = perf_counter()
            try:
                result = runner.ingest(identity, adapter)
                claims = [c.model_dump(mode="json") for c in result.claims]
                claim_keys = {claim["property_key"] for claim in claims}
                required_scalar_keys, scalar_present = _mandatory_scalar_status(identity.product_type, claim_keys)
                record = {
                    "manufacturer": identity.manufacturer,
                    "name": identity.name,
                    "sku": identity.sku,
                    "product_type": identity.product_type.value,
                    "requested_url": identity.url,
                    "resolved_urls": [artifact.url for artifact in result.artifacts],
                    "acquisition_succeeded": True,
                    "elapsed_ms": round((perf_counter() - case_started) * 1000),
                    "artifact_count": len(result.artifacts),
                    "claim_count": len(claims),
                    "claim_keys": sorted(claim_keys),
                    "claims": claims,
                    "acquisition_observations": [o.model_dump(mode="json") for o in result.acquisition_observations],
                    "mandatory_scalar_keys": required_scalar_keys,
                    "mandatory_scalar_present": scalar_present,
                    "readiness_assessed": result.readiness_assessed,
                    "readiness_issues": [i.model_dump(mode="json") for i in result.issues],
                }
            except Exception as exc:
                required_scalar_keys, _ = _mandatory_scalar_status(identity.product_type, set())
                record = {
                    "manufacturer": identity.manufacturer,
                    "name": identity.name,
                    "sku": identity.sku,
                    "product_type": identity.product_type.value,
                    "requested_url": identity.url,
                    "resolved_urls": [],
                    "acquisition_succeeded": False,
                    "elapsed_ms": round((perf_counter() - case_started) * 1000),
                    "artifact_count": 0,
                    "claim_count": 0,
                    "claim_keys": [],
                    "claims": [],
                    "acquisition_observations": [],
                    "mandatory_scalar_keys": required_scalar_keys,
                    "mandatory_scalar_present": False,
                    "readiness_assessed": False,
                    "readiness_issues": [],
                    "error": f"{type(exc).__name__}: {exc}",
                }

            records.append(record)
            print(json.dumps({"type": "product_result", **record}, indent=2))
    finally:
        fetcher.close()

    elapsed_ms = round((perf_counter() - benchmark_started) * 1000)
    summary = _summary(records, elapsed_ms)
    payload = {
        "benchmark": "batch1-nlg-hilti-stopdrop-milwaukee",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(CASES),
        "results": records,
        "summary": summary,
    }
    RESULT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps({"type": "benchmark_summary", **summary}, indent=2))
    print(f"Benchmark result written to {RESULT_PATH}")

    if summary["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
