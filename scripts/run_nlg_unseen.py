from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.adapters.common import page_text
from tetherlens_ingest.http import HttpxFetcher
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceType
from tetherlens_ingest.runner import IngestionRunner

COHORT_PATH = Path("benchmarks/nlg_unseen_cohort.json")
RESULT_PATH = Path("nlg-unseen-results.json")


def _load_cohort() -> dict:
    return json.loads(COHORT_PATH.read_text(encoding="utf-8"))


def _discover_catalogue(fetcher: HttpxFetcher, adapter: NLGAdapter, urls: list[str]) -> dict[str, ProductIdentity]:
    discovered: dict[str, ProductIdentity] = {}
    for url in urls:
        artifact = fetcher.get(url, SourceType.MANUFACTURER_JSON)
        for identity in adapter.discover_collection(artifact):
            if identity.sku:
                discovered.setdefault(identity.sku, identity)
    return discovered


def _bounded_excerpt(body: str, product_name: str | None, limit: int = 3200) -> str:
    text = page_text(body)
    if len(text) <= limit:
        return text

    needles = [product_name or "", "Max Load", "Dimensions", "Max Lanyard Length"]
    positions = [text.lower().find(needle.lower()) for needle in needles if needle]
    positions = [position for position in positions if position >= 0]
    if not positions:
        return text[:limit]

    center = min(positions)
    start = max(0, center - 600)
    return text[start:start + limit]


def main() -> None:
    cohort = _load_cohort()
    adapter = NLGAdapter()
    fetcher = HttpxFetcher(timeout=30)
    runner = IngestionRunner(fetcher)
    records: list[dict] = []
    started = perf_counter()

    try:
        discovered = _discover_catalogue(fetcher, adapter, cohort["collection_urls"])

        for frozen in cohort["products"]:
            sku = frozen["sku"]
            candidate = discovered.get(sku)
            if candidate is None:
                records.append({
                    "sku": sku,
                    "name": frozen["name"],
                    "product_type": frozen["product_type"],
                    "discovered": False,
                    "identity_matches_frozen": False,
                    "acquisition_succeeded": False,
                    "claims": [],
                    "claim_keys": [],
                    "source_evidence": [],
                    "error": "SKU not discovered in configured NLG collections",
                })
                continue

            identity_matches_frozen = (
                candidate.url == frozen["url"]
                and candidate.name == frozen["name"]
                and candidate.manufacturer_ids == frozen["manufacturer_ids"]
            )
            identity = ProductIdentity(
                manufacturer="NLG",
                name=candidate.name,
                sku=candidate.sku,
                url=candidate.url,
                manufacturer_ids=candidate.manufacturer_ids,
                product_type=ProductType(frozen["product_type"]),
            )

            case_started = perf_counter()
            try:
                result = runner.ingest(identity, adapter)
                claims = [claim.model_dump(mode="json") for claim in result.claims]
                source_evidence = [
                    {
                        "url": artifact.url,
                        "source_type": artifact.source_type.value,
                        "content_type": artifact.content_type,
                        "excerpt": _bounded_excerpt(artifact.body, frozen["name"]),
                    }
                    for artifact in result.artifacts
                    if artifact.source_type == SourceType.MANUFACTURER_WEBPAGE
                ]
                record = {
                    "sku": sku,
                    "name": frozen["name"],
                    "product_type": frozen["product_type"],
                    "discovered": True,
                    "identity_matches_frozen": identity_matches_frozen,
                    "acquisition_succeeded": True,
                    "elapsed_ms": round((perf_counter() - case_started) * 1000),
                    "resolved_urls": [artifact.url for artifact in result.artifacts],
                    "claim_count": len(claims),
                    "claim_keys": sorted({claim["property_key"] for claim in claims}),
                    "claims": claims,
                    "source_evidence": source_evidence,
                    "readiness_assessed": result.readiness_assessed,
                    "readiness_issues": [issue.model_dump(mode="json") for issue in result.issues],
                }
            except Exception as exc:
                record = {
                    "sku": sku,
                    "name": frozen["name"],
                    "product_type": frozen["product_type"],
                    "discovered": True,
                    "identity_matches_frozen": identity_matches_frozen,
                    "acquisition_succeeded": False,
                    "elapsed_ms": round((perf_counter() - case_started) * 1000),
                    "claims": [],
                    "claim_keys": [],
                    "source_evidence": [],
                    "error": f"{type(exc).__name__}: {exc}",
                }
            records.append(record)
    finally:
        fetcher.close()

    claim_key_counts = Counter(
        key for record in records for key in record.get("claim_keys", [])
    )
    summary = {
        "cohort_size": len(cohort["products"]),
        "discovered": sum(bool(record.get("discovered")) for record in records),
        "identity_matches_frozen": sum(bool(record.get("identity_matches_frozen")) for record in records),
        "acquired": sum(bool(record.get("acquisition_succeeded")) for record in records),
        "products_with_claims": sum(bool(record.get("claims")) for record in records),
        "total_claims": sum(len(record.get("claims", [])) for record in records),
        "claim_key_counts": dict(sorted(claim_key_counts.items())),
        "elapsed_ms": round((perf_counter() - started) * 1000),
    }
    payload = {
        "benchmark": "nlg-unseen-generalization-v0.2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort": cohort,
        "results": records,
        "summary": summary,
    }
    RESULT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"Unseen NLG results written to {RESULT_PATH}")

    if summary["discovered"] != summary["cohort_size"]:
        raise SystemExit("Not all frozen NLG SKUs were rediscovered")
    if summary["identity_matches_frozen"] != summary["cohort_size"]:
        raise SystemExit("One or more NLG catalogue identities changed from the frozen cohort")
    if summary["acquired"] != summary["cohort_size"]:
        raise SystemExit("One or more unseen NLG product pages failed acquisition")


if __name__ == "__main__":
    main()
