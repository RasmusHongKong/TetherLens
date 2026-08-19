from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.http import HttpxFetcher
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceType
from tetherlens_ingest.runner import IngestionRunner

MANIFEST_PATH = Path("benchmarks/batch2_nlg_holdout.json")
RESULT_PATH = Path("batch2-nlg-blind-results.json")


def _normalized_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _git_blob_sha(path: str) -> str:
    return subprocess.check_output(["git", "hash-object", path], text=True).strip()


def _verify_freeze(manifest: dict[str, Any]) -> dict[str, dict[str, str | bool]]:
    checks: dict[str, dict[str, str | bool]] = {}
    failures: list[str] = []
    for path, expected in manifest["freeze"]["git_blob_shas"].items():
        actual = _git_blob_sha(path)
        matches = actual == expected
        checks[path] = {"expected": expected, "actual": actual, "matches": matches}
        if not matches:
            failures.append(f"{path}: expected {expected}, got {actual}")
    if failures:
        raise RuntimeError("Batch 2 NLG freeze violated before blind run: " + "; ".join(failures))
    return checks


def _catalogue_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("products") or payload.get("items") or payload.get("results") or []
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []
    return [row for row in rows if isinstance(row, dict)]


def _first_sku(row: dict[str, Any]) -> str | None:
    if row.get("sku"):
        return str(row["sku"])
    for variant in row.get("variants") or []:
        if isinstance(variant, dict) and variant.get("sku"):
            return str(variant["sku"])
    return None


def _product_url(row: dict[str, Any]) -> str:
    if row.get("url"):
        url = str(row["url"])
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return "https://neverletgo.com" + (url if url.startswith("/") else "/" + url)
    handle = row.get("handle")
    if not handle:
        raise ValueError(f"Catalogue row has no URL or handle: {row.get('title') or row.get('name')}")
    return f"https://neverletgo.com/products/{handle}"


def _resolve_cohort(manifest: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_title: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        title = row.get("title") or row.get("name")
        if title:
            by_title.setdefault(_normalized_title(str(title)), []).append(row)

    excluded = {_normalized_title(title) for title in manifest["selection_basis"]["batch1_exclusions"]}
    resolved: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for case in manifest["cases"]:
        selector = _normalized_title(case["catalogue_title"])
        matches = by_title.get(selector, [])
        if len(matches) != 1:
            raise RuntimeError(
                f"Holdout selector {case['catalogue_title']!r} resolved to {len(matches)} catalogue rows; expected exactly one"
            )
        row = matches[0]
        title = str(row.get("title") or row.get("name"))
        if _normalized_title(title) in excluded:
            raise RuntimeError(f"Batch 1 product leaked into Batch 2 holdout: {title}")
        url = _product_url(row)
        if url in seen_urls:
            raise RuntimeError(f"Duplicate Batch 2 product URL: {url}")
        seen_urls.add(url)
        resolved.append(
            {
                "case_id": case["case_id"],
                "catalogue_title": title,
                "sku": _first_sku(row),
                "product_type": case["product_type"],
                "url": url,
                "catalogue_id": str(row["id"]) if row.get("id") is not None else None,
            }
        )
    return resolved


def _summary(records: list[dict[str, Any]], elapsed_ms: int) -> dict[str, Any]:
    claim_keys = Counter(
        claim["property_key"]
        for record in records
        for claim in record.get("claims", [])
        if claim.get("property_key")
    )
    observation_codes = Counter(
        observation["code"]
        for record in records
        for observation in record.get("acquisition_observations", [])
        if observation.get("code")
    )
    issue_codes = Counter(
        issue["code"]
        for record in records
        for issue in record.get("readiness_issues", [])
        if issue.get("code")
    )
    return {
        "attempted": len(records),
        "acquired": sum(bool(record["acquisition_succeeded"]) for record in records),
        "failed": sum(not bool(record["acquisition_succeeded"]) for record in records),
        "total_claims": sum(int(record.get("claim_count", 0)) for record in records),
        "products_with_claims": sum(bool(record.get("claims")) for record in records),
        "products_with_readiness_issues": sum(bool(record.get("readiness_issues")) for record in records),
        "elapsed_ms": elapsed_ms,
        "claim_key_counts": dict(sorted(claim_keys.items())),
        "acquisition_observation_codes": dict(sorted(observation_codes.items())),
        "readiness_issue_codes": dict(sorted(issue_codes.items())),
    }


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    freeze_checks = _verify_freeze(manifest)
    fetcher = HttpxFetcher(timeout=30)
    adapter = NLGAdapter()
    runner = IngestionRunner(fetcher)
    records: list[dict[str, Any]] = []
    started = perf_counter()

    try:
        catalogue_artifact = fetcher.get(
            manifest["selection_basis"]["catalogue_url"],
            SourceType.MANUFACTURER_JSON,
        )
        catalogue_sha256 = hashlib.sha256(catalogue_artifact.body.encode("utf-8")).hexdigest()
        payload = json.loads(catalogue_artifact.body)
        rows = _catalogue_rows(payload)
        cohort = _resolve_cohort(manifest, rows)

        print(json.dumps({
            "type": "blind_run_contract",
            "benchmark": manifest["benchmark"],
            "freeze_verified": True,
            "golden_answers_present": False,
            "catalogue_url": catalogue_artifact.url,
            "catalogue_sha256": catalogue_sha256,
            "catalogue_product_count": len(rows),
            "cohort": cohort,
        }, indent=2))

        for case in cohort:
            identity = ProductIdentity(
                manufacturer="NLG",
                name=case["catalogue_title"],
                sku=case["sku"],
                product_type=ProductType(case["product_type"]),
                url=case["url"],
                manufacturer_ids={"catalogue_id": case["catalogue_id"]} if case["catalogue_id"] else {},
            )
            case_started = perf_counter()
            try:
                result = runner.ingest(identity, adapter)
                claims = [claim.model_dump(mode="json") for claim in result.claims]
                record = {
                    **case,
                    "requested_url": identity.url,
                    "resolved_urls": [artifact.url for artifact in result.artifacts],
                    "acquisition_succeeded": True,
                    "elapsed_ms": round((perf_counter() - case_started) * 1000),
                    "artifact_count": len(result.artifacts),
                    "claim_count": len(claims),
                    "claims": claims,
                    "acquisition_observations": [
                        observation.model_dump(mode="json") for observation in result.acquisition_observations
                    ],
                    "readiness_assessed": result.readiness_assessed,
                    "readiness_issues": [issue.model_dump(mode="json") for issue in result.issues],
                }
            except Exception as exc:
                record = {
                    **case,
                    "requested_url": identity.url,
                    "resolved_urls": [],
                    "acquisition_succeeded": False,
                    "elapsed_ms": round((perf_counter() - case_started) * 1000),
                    "artifact_count": 0,
                    "claim_count": 0,
                    "claims": [],
                    "acquisition_observations": [],
                    "readiness_assessed": False,
                    "readiness_issues": [],
                    "error": f"{type(exc).__name__}: {exc}",
                }
            records.append(record)
            print(json.dumps({"type": "product_result", **record}, indent=2))
    finally:
        fetcher.close()

    elapsed_ms = round((perf_counter() - started) * 1000)
    summary = _summary(records, elapsed_ms)
    result_payload = {
        "benchmark": manifest["benchmark"],
        "phase": "blind_first_run",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "golden_answers_present": False,
        "adapter_changes_allowed_before_inspection": False,
        "freeze": {
            "base_commit": manifest["freeze"]["base_commit"],
            "verified": True,
            "checks": freeze_checks,
        },
        "catalogue": {
            "requested_url": manifest["selection_basis"]["catalogue_url"],
            "resolved_url": catalogue_artifact.url,
            "sha256": catalogue_sha256,
            "product_count": len(rows),
        },
        "cohort": cohort,
        "results": records,
        "summary": summary,
    }
    RESULT_PATH.write_text(json.dumps(result_payload, indent=2), encoding="utf-8")
    print(json.dumps({"type": "benchmark_summary", **summary}, indent=2))
    print(f"Blind Batch 2 result written to {RESULT_PATH}")

    if summary["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
