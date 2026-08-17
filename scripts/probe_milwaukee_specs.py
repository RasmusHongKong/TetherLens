from __future__ import annotations

import html
import json
import re
from collections import deque
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

RESULT_PATH = Path("milwaukee-specs-probe.json")
USER_AGENT = "TetherLensIngestionBenchmark/0.1"

TARGETS = {
    "2602-20": "https://www.milwaukeetool.com/products/details/m18-cordless-1-2-hammer-drill-driver-tool-only/2602-20",
    "48-11-1815": "https://www.milwaukeetool.com/products/details/m18-compact-redlithium-battery/48-11-1815",
    "48-11-1828": "https://www.milwaukeetool.com/products/details/m18-redlithium-xc-extended-capacity-battery/48-11-1828",
}
FAMILY_IDENTIFIER = "2602"

KEYWORDS = (
    "spec",
    "specification",
    "weight",
    "graphql",
    "/api/",
    "productdetail",
    "product-detail",
    "productnumber",
    "modelnumber",
    "sku",
)
URLISH_RE = re.compile(r'''["']((?:https?://|/)[^"'<>\\s]{3,600})["']''')
ENDPOINT_RE = re.compile(
    r'''(?:fetch\(|axios(?:\.get|\.post)?\(|url\s*[:=])\s*["'`]([^"'`]{3,600})["'`]''',
    re.I,
)
RSC_PUSH_RE = re.compile(
    r'''self\.__next_f\.push\(\[1,(?P<payload>"(?:\\.|[^"\\])*")\]\)''',
    re.S,
)
RSC_RECORD_RE = re.compile(r"^([0-9a-f]+):(.*)$", re.I)
RSC_REF_RE = re.compile(r"^\$([0-9a-f]+)$", re.I)
PAGE_LANGUAGE_RE = re.compile(r'''["']page_language["']\s*:\s*["']([^"']+)["']''', re.I)


def _normalize(text: str) -> str:
    return html.unescape(text).replace("\\/", "/")


def _interesting(text: str, skus: tuple[str, ...] = ()) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in KEYWORDS) or any(sku.lower() in lower for sku in skus)


def _snippets(text: str, needles: tuple[str, ...], limit: int = 50) -> list[str]:
    normalized = _normalize(text)
    lower = normalized.lower()
    positions: list[int] = []
    for needle in needles:
        start = 0
        token = needle.lower()
        while True:
            idx = lower.find(token, start)
            if idx < 0:
                break
            positions.append(idx)
            start = idx + len(token)

    out: list[str] = []
    seen: set[str] = set()
    for idx in sorted(positions):
        start = max(0, idx - 220)
        end = min(len(normalized), idx + 520)
        snippet = re.sub(r"\s+", " ", normalized[start:end]).strip()
        if snippet and snippet not in seen:
            seen.add(snippet)
            out.append(snippet)
        if len(out) >= limit:
            break
    return out


def _candidate_urls(text: str, base_url: str, limit: int = 120) -> list[str]:
    normalized = _normalize(text)
    out: list[str] = []
    seen: set[str] = set()

    candidates = [match.group(1) for match in URLISH_RE.finditer(normalized)]
    candidates.extend(match.group(1) for match in ENDPOINT_RE.finditer(normalized))

    for raw in candidates:
        raw = raw.strip()
        if not _interesting(raw):
            continue
        if raw.startswith("//"):
            raw = "https:" + raw
        value = urljoin(base_url, raw)
        if value not in seen:
            seen.add(value)
            out.append(value)
        if len(out) >= limit:
            break
    return out


def _rsc_chunks(soup: BeautifulSoup) -> list[str]:
    chunks: list[str] = []
    for script in soup.find_all("script"):
        if script.get("src"):
            continue
        body = script.string or script.get_text(" ", strip=False)
        if not body or "self.__next_f.push" not in body:
            continue
        for match in RSC_PUSH_RE.finditer(body):
            try:
                decoded = json.loads(match.group("payload"))
            except (TypeError, ValueError):
                continue
            if isinstance(decoded, str):
                chunks.append(decoded)
    return chunks


def _rsc_records(chunks: list[str]) -> dict[str, object]:
    # Next/RSC records can be split across adjacent push calls, so join the
    # decoded text before splitting it into record lines.
    text = "".join(chunks)
    records: dict[str, object] = {}
    for line in text.splitlines():
        match = RSC_RECORD_RE.match(line)
        if not match:
            continue
        record_id, raw_value = match.groups()
        try:
            records[record_id.lower()] = json.loads(raw_value)
        except (TypeError, ValueError):
            continue
    return records


def _record_refs(value: object) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, str):
        match = RSC_REF_RE.fullmatch(value)
        if match:
            refs.add(match.group(1).lower())
    elif isinstance(value, dict):
        for item in value.values():
            refs.update(_record_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(_record_refs(item))
    return refs


def _reachable_records(start_ids: list[str], records: dict[str, object], limit: int = 1200) -> set[str]:
    queue = deque(record_id.lower() for record_id in start_ids)
    visited: set[str] = set()
    while queue and len(visited) < limit:
        record_id = queue.popleft()
        if record_id in visited or record_id not in records:
            continue
        visited.add(record_id)
        for ref in _record_refs(records[record_id]):
            if ref not in visited:
                queue.append(ref)
    return visited


def _product_record_ids(records: dict[str, object], sku: str) -> list[str]:
    return [
        record_id
        for record_id, value in records.items()
        if isinstance(value, dict) and str(value.get("sku") or "").upper() == sku.upper()
    ]


def _is_spec(value: object) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("key"), str)
        and any(field in value for field in ("name", "value", "display"))
    )


def _specs_for_product(records: dict[str, object], sku: str) -> tuple[list[dict[str, object]], list[str]]:
    product_ids = _product_record_ids(records, sku)
    reachable = _reachable_records(product_ids, records)
    specs: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for record_id in reachable:
        value = records.get(record_id)
        if not _is_spec(value):
            continue
        assert isinstance(value, dict)
        signature = (
            str(value.get("key") or ""),
            str(value.get("value") or ""),
            str(value.get("display") or ""),
        )
        if signature in seen:
            continue
        seen.add(signature)
        specs.append({
            "record_id": record_id,
            "key": value.get("key"),
            "name": value.get("name"),
            "value": value.get("value"),
            "display": value.get("display"),
        })
    specs.sort(key=lambda item: (str(item.get("name") or ""), str(item.get("key") or "")))
    return specs, product_ids


def _weight_candidates(specs: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for spec in specs:
        key = str(spec.get("key") or "").lower()
        name = str(spec.get("name") or "").lower()
        if key in {"netweight", "weight", "productweight"} or "weight" in name:
            out.append(spec)
    return out


def _component_items(records: dict[str, object], start_ids: list[str]) -> list[dict[str, object]]:
    reachable = _reachable_records(start_ids, records)
    out: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for record_id in reachable:
        value = records.get(record_id)
        if not isinstance(value, dict):
            continue
        item_type = str(value.get("type") or "")
        if item_type not in {"SALEABLE_ITEM", "NONSALEABLE_ITEM"}:
            continue
        signature = (item_type, str(value.get("sku") or ""), str(value.get("title") or ""))
        if signature in seen:
            continue
        seen.add(signature)
        out.append({
            "record_id": record_id,
            "type": item_type,
            "quantity": value.get("quantity"),
            "sku": value.get("sku"),
            "title": value.get("title"),
            "reference_url": value.get("referenceUrl"),
        })
    out.sort(key=lambda item: (str(item.get("sku") or "~"), str(item.get("title") or "")))
    return out


def _rsc_product_summary(records: dict[str, object], sku: str) -> dict[str, object]:
    specs, product_ids = _specs_for_product(records, sku)
    products = [records[record_id] for record_id in product_ids if isinstance(records.get(record_id), dict)]
    primary = products[0] if products else {}
    return {
        "record_ids": product_ids,
        "found": bool(product_ids),
        "title": primary.get("title") if isinstance(primary, dict) else None,
        "family_identifier": primary.get("familyIdentifier") if isinstance(primary, dict) else None,
        "spec_count": len(specs),
        "specs": specs,
        "weight_candidates": _weight_candidates(specs),
        "components": _component_items(records, product_ids),
    }


def _resolve_ref(value: object, records: dict[str, object]) -> object:
    if isinstance(value, str):
        match = RSC_REF_RE.fullmatch(value)
        if match:
            return records.get(match.group(1).lower(), value)
    return value


def _family_graph(records: dict[str, object], family_identifier: str) -> dict[str, object]:
    supported_skus: list[str] = []
    for value in records.values():
        if not isinstance(value, dict) or str(value.get("pageIdentifier") or "") != family_identifier:
            continue
        resolved = _resolve_ref(value.get("supportedSkus"), records)
        if isinstance(resolved, list):
            supported_skus = [str(item) for item in resolved if isinstance(item, str)]
            break

    family_skus = set(supported_skus)
    for value in records.values():
        if not isinstance(value, dict):
            continue
        sku = str(value.get("sku") or "")
        if str(value.get("familyIdentifier") or "") == family_identifier or sku.startswith(family_identifier + "-"):
            family_skus.add(sku)

    products: dict[str, dict[str, object]] = {}
    for sku in sorted(sku for sku in family_skus if sku):
        product_ids = _product_record_ids(records, sku)
        product_values = [records[record_id] for record_id in product_ids if isinstance(records.get(record_id), dict)]
        primary = product_values[0] if product_values else {}
        products[sku] = {
            "record_ids": product_ids,
            "title": primary.get("title") if isinstance(primary, dict) else None,
            "family_identifier": primary.get("familyIdentifier") if isinstance(primary, dict) else None,
            "components": _component_items(records, product_ids),
        }

    return {
        "family_identifier": family_identifier,
        "supported_skus": supported_skus,
        "products": products,
    }


def _page_language(rsc_text: str, raw_html: str) -> str | None:
    for text in (rsc_text, _normalize(raw_html)):
        match = PAGE_LANGUAGE_RE.search(text)
        if match:
            return match.group(1)
    return None


def _structured_scripts(soup: BeautifulSoup, page_url: str, sku: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for script in soup.find_all("script"):
        if script.get("src"):
            continue
        body = script.string or script.get_text(" ", strip=False)
        if not body:
            continue
        script_type = str(script.get("type") or "")
        script_id = str(script.get("id") or "")
        if "json" not in script_type.lower() and not _interesting(body, (sku,)):
            continue

        parsed_summary: dict[str, object] | None = None
        if "json" in script_type.lower() or script_id in {"__NEXT_DATA__", "__NUXT_DATA__"}:
            try:
                payload = json.loads(body)
                parsed_summary = {
                    "top_level_type": type(payload).__name__,
                    "top_level_keys": list(payload)[:30] if isinstance(payload, dict) else None,
                }
            except Exception as exc:
                parsed_summary = {"parse_error": f"{type(exc).__name__}: {exc}"}

        results.append(
            {
                "type": script_type,
                "id": script_id,
                "length": len(body),
                "parsed": parsed_summary,
                "candidate_urls": _candidate_urls(body, page_url, limit=40),
                "snippets": _snippets(body, (sku,) + KEYWORDS, limit=20),
            }
        )
        if len(results) >= 40:
            break
    return results


def _page_probe(client: httpx.Client, sku: str, url: str) -> tuple[dict[str, object], list[str]]:
    try:
        response = client.get(url)
        response.raise_for_status()
    except Exception as exc:
        return {"requested_url": url, "error": f"{type(exc).__name__}: {exc}"}, []

    resolved_url = str(response.url)
    raw = response.text
    soup = BeautifulSoup(raw, "html.parser")
    script_sources = list(
        dict.fromkeys(
            urljoin(resolved_url, str(tag.get("src")))
            for tag in soup.find_all("script", src=True)
        )
    )

    rsc_chunks = _rsc_chunks(soup)
    rsc_text = "".join(rsc_chunks)
    rsc_records = _rsc_records(rsc_chunks)
    rsc_summary: dict[str, object] = {
        "chunk_count": len(rsc_chunks),
        "decoded_chars": len(rsc_text),
        "record_count": len(rsc_records),
        "page_language": _page_language(rsc_text, raw),
        "product": _rsc_product_summary(rsc_records, sku),
    }
    if sku.startswith(FAMILY_IDENTIFIER + "-"):
        rsc_summary["family_graph"] = _family_graph(rsc_records, FAMILY_IDENTIFIER)

    return (
        {
            "requested_url": url,
            "resolved_url": resolved_url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "page_bytes": len(response.content),
            "script_source_count": len(script_sources),
            "candidate_urls": _candidate_urls(raw, resolved_url),
            "snippets": _snippets(raw, (sku, "Specs", "Loading", "Weight") + KEYWORDS, limit=60),
            "structured_scripts": _structured_scripts(soup, resolved_url, sku),
            "rsc": rsc_summary,
        },
        script_sources,
    )


def _bundle_probe(client: httpx.Client, sources: list[str], skus: tuple[str, ...]) -> tuple[list[dict[str, object]], int]:
    results: list[dict[str, object]] = []
    total_bytes = 0
    for src in list(dict.fromkeys(sources))[:45]:
        if total_bytes >= 18_000_000:
            break
        try:
            response = client.get(src)
            response.raise_for_status()
        except Exception as exc:
            results.append({"url": src, "error": f"{type(exc).__name__}: {exc}"})
            continue

        text = response.text
        total_bytes += len(response.content)
        if not _interesting(text, skus):
            continue

        results.append(
            {
                "url": str(response.url),
                "host": urlparse(str(response.url)).netloc,
                "bytes": len(response.content),
                "candidate_urls": _candidate_urls(text, str(response.url), limit=80),
                "snippets": _snippets(text, skus + KEYWORDS, limit=35),
            }
        )
        if len(results) >= 25:
            break
    return results, total_bytes


def _walk_json(value: object, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_json(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_json(item, f"{path}[{index}]")


def _api_spec_objects(payload: object) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for path, value in _walk_json(payload):
        if not _is_spec(value):
            continue
        assert isinstance(value, dict)
        signature = (
            str(value.get("key") or ""),
            str(value.get("value") or ""),
            str(value.get("display") or ""),
        )
        if signature in seen:
            continue
        seen.add(signature)
        out.append({
            "path": path,
            "key": value.get("key"),
            "name": value.get("name"),
            "value": value.get("value"),
            "display": value.get("display"),
        })
    return out


def _api_weight_candidates(payload: object) -> list[dict[str, object]]:
    candidates = _weight_candidates(_api_spec_objects(payload))
    seen_paths = {str(item.get("path") or "") for item in candidates}
    for path, value in _walk_json(payload):
        leaf = path.rsplit(".", 1)[-1].lower()
        if "weight" not in leaf or isinstance(value, (dict, list)) or path in seen_paths:
            continue
        candidates.append({"path": path, "key": leaf, "value": value})
        seen_paths.add(path)
    return candidates


def _compact(value: object, depth: int = 0) -> object:
    if depth >= 5:
        if isinstance(value, dict):
            return {"_truncated_dict_keys": list(value)[:20]}
        if isinstance(value, list):
            return {"_truncated_list_length": len(value)}
        return value
    if isinstance(value, dict):
        out: dict[str, object] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 40:
                out["_truncated_key_count"] = len(value) - 40
                break
            out[str(key)] = _compact(item, depth + 1)
        return out
    if isinstance(value, list):
        items = [_compact(item, depth + 1) for item in value[:30]]
        if len(value) > 30:
            items.append({"_truncated_item_count": len(value) - 30})
        return items
    if isinstance(value, str) and len(value) > 1500:
        return value[:1500] + "…"
    return value


def _api_probe(client: httpx.Client, sku: str, page: dict[str, object]) -> dict[str, object]:
    resolved_url = str(page.get("resolved_url") or TARGETS[sku])
    rsc = page.get("rsc") if isinstance(page.get("rsc"), dict) else {}
    discovered_language = str(rsc.get("page_language") or "").strip() if isinstance(rsc, dict) else ""
    languages = list(dict.fromkeys(language for language in (discovered_language, "en", "en-US") if language))

    attempts: list[dict[str, object]] = []
    for language in languages:
        api_url = urljoin(resolved_url, f"/api/v1/products/{quote(sku, safe='')}?language={quote(language, safe='-')}")
        try:
            response = client.get(api_url, headers={"Accept": "application/json,*/*;q=0.8"})
        except Exception as exc:
            attempts.append({"url": api_url, "language": language, "error": f"{type(exc).__name__}: {exc}"})
            continue

        attempt: dict[str, object] = {
            "url": str(response.url),
            "language": language,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "response_bytes": len(response.content),
        }
        try:
            payload = response.json()
        except Exception as exc:
            attempt["json_error"] = f"{type(exc).__name__}: {exc}"
            attempt["body_preview"] = response.text[:1000]
            attempts.append(attempt)
            continue

        result = payload.get("data", {}).get("result") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else None
        api_specs = _api_spec_objects(payload)
        attempt.update({
            "api_status": payload.get("status") if isinstance(payload, dict) else None,
            "top_level_type": type(payload).__name__,
            "top_level_keys": list(payload)[:30] if isinstance(payload, dict) else None,
            "result_type": type(result).__name__ if result is not None else None,
            "result_keys": list(result)[:60] if isinstance(result, dict) else None,
            "spec_count": len(api_specs),
            "specs": api_specs,
            "weight_candidates": _api_weight_candidates(payload),
            "payload_compact": _compact(payload),
        })
        attempts.append(attempt)
        if response.is_success and isinstance(payload, dict) and payload.get("status") == "OK":
            break

    successful = next(
        (
            attempt
            for attempt in attempts
            if attempt.get("status_code") and 200 <= int(attempt["status_code"]) < 300 and attempt.get("api_status") == "OK"
        ),
        None,
    )
    return {
        "discovered_page_language": discovered_language or None,
        "attempt_count": len(attempts),
        "success": successful is not None,
        "successful_language": successful.get("language") if successful else None,
        "attempts": attempts,
    }


def main() -> None:
    client = httpx.Client(
        timeout=25.0,
        follow_redirects=True,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json,application/javascript,*/*;q=0.8",
        },
    )

    pages: dict[str, dict[str, object]] = {}
    all_script_sources: list[str] = []
    api: dict[str, dict[str, object]] = {}
    try:
        for sku, url in TARGETS.items():
            page, script_sources = _page_probe(client, sku, url)
            pages[sku] = page
            all_script_sources.extend(script_sources)

        for sku, page in pages.items():
            if "error" not in page:
                api[sku] = _api_probe(client, sku, page)

        bundle_hits, bundle_scan_bytes = _bundle_probe(client, all_script_sources, tuple(TARGETS))
    finally:
        client.close()

    payload = {
        "targets": TARGETS,
        "pages": pages,
        "api": api,
        "unique_script_source_count": len(set(all_script_sources)),
        "bundle_scan_bytes": bundle_scan_bytes,
        "bundle_hits": bundle_hits,
    }
    RESULT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    compact = {
        "type": "milwaukee_specs_probe",
        "pages_fetched": sum("error" not in page for page in pages.values()),
        "rsc_products_found": sum(bool(page.get("rsc", {}).get("product", {}).get("found")) for page in pages.values()),
        "rsc_weight_candidate_count": sum(
            len(page.get("rsc", {}).get("product", {}).get("weight_candidates", []))
            for page in pages.values()
        ),
        "api_success_count": sum(bool(result.get("success")) for result in api.values()),
        "api_weight_candidate_count": sum(
            len(attempt.get("weight_candidates", []))
            for result in api.values()
            for attempt in result.get("attempts", [])
            if attempt.get("api_status") == "OK"
        ),
        "page_candidate_url_count": sum(len(page.get("candidate_urls", [])) for page in pages.values()),
        "structured_script_count": sum(len(page.get("structured_scripts", [])) for page in pages.values()),
        "unique_script_source_count": len(set(all_script_sources)),
        "bundle_hit_count": len(bundle_hits),
        "bundle_candidate_url_count": sum(len(item.get("candidate_urls", [])) for item in bundle_hits),
        "bundle_scan_bytes": bundle_scan_bytes,
    }
    print(json.dumps(compact, indent=2))
    print(f"Milwaukee specs probe written to {RESULT_PATH}")


if __name__ == "__main__":
    main()
