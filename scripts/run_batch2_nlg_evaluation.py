from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.http import HttpxFetcher
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceType
from tetherlens_ingest.runner import IngestionRunner

from run_batch2_nlg_blind import MANIFEST_PATH, _catalogue_rows, _resolve_cohort, _summary

RESULT_PATH = Path("batch2-nlg-evaluation-results.json")


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    fetcher = HttpxFetcher(timeout=30)
    adapter = NLGAdapter()
    runner = IngestionRunner(fetcher)
    records: list[dict] = []
    started = perf_counter()

    try:
        catalogue_artifact = fetcher.get(
            manifest["selection_basis"]["catalogue_url"],
            SourceType.MANUFACTURER_JSON,
        )
        catalogue_sha256 = hashlib.sha256(catalogue_artifact.body.encode("utf-8")).hexdigest()
        rows = _catalogue_rows(json.loads(catalogue_artifact.body))
        cohort = _resolve_cohort(manifest, rows)

        print(json.dumps({
            "type": "post_blind_evaluation_contract",
            "benchmark": manifest["benchmark"],
            "blind_reference_preserved": True,
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
                    "manufacturer": "NLG",
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
                    "manufacturer": "NLG",
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
    payload = {
        "benchmark": manifest["benchmark"],
        "phase": "post_blind_generalization",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "blind_reference": {
            "workflow_run_id": 32273707247,
            "artifact_id": 9373169405,
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
    RESULT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"type": "benchmark_summary", **summary}, indent=2))

    if summary["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
