from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

TARGET_URL = "https://www.hilti.com/c/CLS_POWER_TOOLS_7125/CLS_DRILL_DRIVERS_SCREW_DRIVERS__7125/r13275669"
RESULT_PATH = Path("hilti-relationship-probe.json")
USER_AGENT = "TetherLensIngestionBenchmark/0.1"

KEYWORDS = (
    "battery",
    "batteries",
    "configurator",
    "configuration",
    "compatible",
    "compatibility",
    "relatedproduct",
    "related-product",
    "related_products",
    "recommendation",
    "accessory",
)
TARGET_MODELS = ("B 22-55", "B 22-85")
TARGET_REFS = ("r13250264", "r13250303")
MODEL_RE = re.compile(r"\bB\s*22-\d+\b", re.I)
FAMILY_RE = re.compile(r"\br\d{7,}\b", re.I)
URLISH_RE = re.compile(r'''["']((?:https?://|/)[^"'<>\s]{3,500})["']''')


def _normalize(text: str) -> str:
    return html.unescape(text).replace("\\/", "/")


def _interesting(value: str) -> bool:
    lower = value.lower()
    return any(keyword in lower for keyword in KEYWORDS) or bool(MODEL_RE.search(value))


def _candidate_urls(text: str, base_url: str, limit: int = 100) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for match in URLISH_RE.finditer(_normalize(text)):
        raw = match.group(1)
        if not _interesting(raw):
            continue
        value = urljoin(base_url, raw)
        if value not in seen:
            seen.add(value)
            out.append(value)
        if len(out) >= limit:
            break
    return out


def _snippets(text: str, needles: tuple[str, ...] = KEYWORDS, limit: int = 40) -> list[str]:
    normalized = _normalize(text)
    lower = normalized.lower()
    hits: list[str] = []
    seen: set[str] = set()
    positions: list[int] = []
    for needle in needles:
        start = 0
        needle_lower = needle.lower()
        while True:
            idx = lower.find(needle_lower, start)
            if idx < 0:
                break
            positions.append(idx)
            start = idx + len(needle_lower)
    for idx in sorted(positions):
        start = max(0, idx - 160)
        end = min(len(normalized), idx + 320)
        snippet = re.sub(r"\s+", " ", normalized[start:end]).strip()
        if snippet not in seen:
            seen.add(snippet)
            hits.append(snippet)
        if len(hits) >= limit:
            break
    return hits


def _structured_script_summary(soup: BeautifulSoup) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for script in soup.find_all("script"):
        if script.get("src"):
            continue
        body = script.string or script.get_text(" ", strip=False)
        if not body:
            continue
        script_type = str(script.get("type") or "")
        script_id = str(script.get("id") or "")
        if "json" not in script_type.lower() and not _interesting(body):
            continue
        results.append(
            {
                "type": script_type,
                "id": script_id,
                "length": len(body),
                "battery_models": sorted({re.sub(r"\s+", " ", m.group(0)).upper() for m in MODEL_RE.finditer(body)}),
                "family_refs": sorted({m.group(0).lower() for m in FAMILY_RE.finditer(body)}),
                "candidate_urls": _candidate_urls(body, TARGET_URL, limit=30),
                "snippets": _snippets(body, limit=12),
            }
        )
        if len(results) >= 30:
            break
    return results


def _compact(value, depth: int = 0):
    if depth >= 4:
        if isinstance(value, dict):
            return {"_truncated_dict_keys": list(value)[:12]}
        if isinstance(value, list):
            return {"_truncated_list_length": len(value)}
        return value
    if isinstance(value, dict):
        out = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 24:
                out["_truncated_key_count"] = len(value) - 24
                break
            out[str(key)] = _compact(item, depth + 1)
        return out
    if isinstance(value, list):
        values = [_compact(item, depth + 1) for item in value[:16]]
        if len(value) > 16:
            values.append({"_truncated_item_count": len(value) - 16})
        return values
    if isinstance(value, str) and len(value) > 500:
        return value[:500] + "…"
    return value


def _walk(value, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")


def _contains_target(value) -> bool:
    try:
        text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    except TypeError:
        text = str(value)
    lower = text.lower()
    return any(model.lower() in lower for model in TARGET_MODELS) or any(ref in lower for ref in TARGET_REFS)


def _state_diagnostics(soup: BeautifulSoup) -> dict[str, object]:
    script = soup.find("script", id="hdms-website-state")
    if script is None:
        return {"present": False}
    body = script.string or script.get_text(" ", strip=False)
    if not body:
        return {"present": True, "parse_error": "empty state script"}
    try:
        state = json.loads(body)
    except Exception as exc:
        return {
            "present": True,
            "parse_error": f"{type(exc).__name__}: {exc}",
            "target_snippets": _snippets(body, needles=TARGET_MODELS + TARGET_REFS, limit=20),
        }

    target_nodes: list[dict[str, object]] = []
    relation_nodes: list[dict[str, object]] = []
    seen_paths: set[str] = set()
    for path, value in _walk(state):
        if not isinstance(value, (dict, list)):
            continue
        if not _contains_target(value):
            continue
        if path in seen_paths:
            continue
        seen_paths.add(path)
        target_nodes.append({"path": path, "value": _compact(value)})
        try:
            text = json.dumps(value, ensure_ascii=False).lower()
        except TypeError:
            text = str(value).lower()
        if any(keyword in text for keyword in ("battery", "configurator", "related", "compatible")):
            relation_nodes.append({"path": path, "value": _compact(value)})
        if len(target_nodes) >= 40:
            break

    exact_records: list[dict[str, object]] = []
    for path, value in _walk(state):
        if not isinstance(value, dict):
            continue
        values = [str(item) for item in value.values() if isinstance(item, (str, int, float))]
        joined = " | ".join(values).lower()
        if any(model.lower() in joined for model in TARGET_MODELS) or any(ref in joined for ref in TARGET_REFS):
            exact_records.append({"path": path, "value": _compact(value)})
        if len(exact_records) >= 30:
            break

    return {
        "present": True,
        "top_level_type": type(state).__name__,
        "top_level_keys": list(state)[:30] if isinstance(state, dict) else None,
        "exact_target_records": exact_records,
        "target_containing_nodes": target_nodes,
        "relationship_candidate_nodes": relation_nodes[:30],
    }


def main() -> None:
    client = httpx.Client(
        timeout=20.0,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/javascript,*/*;q=0.8"},
    )
    response = client.get(TARGET_URL)
    response.raise_for_status()
    page_url = str(response.url)
    raw = response.text
    soup = BeautifulSoup(raw, "html.parser")

    script_sources = [
        urljoin(page_url, str(tag.get("src")))
        for tag in soup.find_all("script", src=True)
    ]
    script_sources = list(dict.fromkeys(script_sources))

    page_models = sorted({re.sub(r"\s+", " ", m.group(0)).upper() for m in MODEL_RE.finditer(raw)})
    page_family_refs = sorted({m.group(0).lower() for m in FAMILY_RE.finditer(raw)})
    state_diagnostics = _state_diagnostics(soup)

    bundle_results: list[dict[str, object]] = []
    total_bundle_bytes = 0
    for src in script_sources[:30]:
        if total_bundle_bytes >= 12_000_000:
            break
        try:
            bundle = client.get(src)
            bundle.raise_for_status()
        except Exception as exc:  # diagnostic probe: record and continue
            bundle_results.append({"url": src, "error": f"{type(exc).__name__}: {exc}"})
            continue
        text = bundle.text
        total_bundle_bytes += len(bundle.content)
        if not _interesting(text):
            continue
        bundle_results.append(
            {
                "url": str(bundle.url),
                "host": urlparse(str(bundle.url)).netloc,
                "bytes": len(bundle.content),
                "battery_models": sorted({re.sub(r"\s+", " ", m.group(0)).upper() for m in MODEL_RE.finditer(text)}),
                "family_refs": sorted({m.group(0).lower() for m in FAMILY_RE.finditer(text)}),
                "candidate_urls": _candidate_urls(text, page_url, limit=40),
                "snippets": _snippets(text, limit=16),
            }
        )
        if len(bundle_results) >= 20:
            break

    payload = {
        "target_url": TARGET_URL,
        "resolved_url": page_url,
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "page_bytes": len(response.content),
        "page_battery_models": page_models,
        "page_family_refs": page_family_refs,
        "page_candidate_urls": _candidate_urls(raw, page_url),
        "page_snippets": _snippets(raw),
        "structured_scripts": _structured_script_summary(soup),
        "hdms_website_state": state_diagnostics,
        "script_source_count": len(script_sources),
        "script_sources": script_sources[:30],
        "bundle_scan_bytes": total_bundle_bytes,
        "bundle_hits": bundle_results,
    }
    RESULT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    compact = {
        "type": "hilti_relationship_probe",
        "page_battery_models": page_models,
        "page_candidate_url_count": len(payload["page_candidate_urls"]),
        "structured_script_count": len(payload["structured_scripts"]),
        "state_present": state_diagnostics.get("present"),
        "state_exact_target_record_count": len(state_diagnostics.get("exact_target_records", [])),
        "state_relationship_candidate_count": len(state_diagnostics.get("relationship_candidate_nodes", [])),
        "script_source_count": len(script_sources),
        "bundle_hit_count": len(bundle_results),
        "bundle_candidate_url_count": sum(len(item.get("candidate_urls", [])) for item in bundle_results),
    }
    print(json.dumps(compact, indent=2))
    print(f"Hilti relationship probe written to {RESULT_PATH}")
    client.close()


if __name__ == "__main__":
    main()
