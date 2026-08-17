from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

RESULT_PATH = Path("milwaukee-specs-probe.json")
USER_AGENT = "TetherLensIngestionBenchmark/0.1"

TARGETS = {
    "2602-20": "https://www.milwaukeetool.com/products/details/m18-cordless-1-2-hammer-drill-driver-tool-only/2602-20",
    "48-11-1815": "https://www.milwaukeetool.com/products/details/m18-compact-redlithium-battery/48-11-1815",
    "48-11-1828": "https://www.milwaukeetool.com/products/details/m18-redlithium-xc-extended-capacity-battery/48-11-1828",
}

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
    try:
        for sku, url in TARGETS.items():
            page, script_sources = _page_probe(client, sku, url)
            pages[sku] = page
            all_script_sources.extend(script_sources)

        bundle_hits, bundle_scan_bytes = _bundle_probe(client, all_script_sources, tuple(TARGETS))
    finally:
        client.close()

    payload = {
        "targets": TARGETS,
        "pages": pages,
        "unique_script_source_count": len(set(all_script_sources)),
        "bundle_scan_bytes": bundle_scan_bytes,
        "bundle_hits": bundle_hits,
    }
    RESULT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    compact = {
        "type": "milwaukee_specs_probe",
        "pages_fetched": sum("error" not in page for page in pages.values()),
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
