from __future__ import annotations

from io import BytesIO
from typing import Protocol

import httpx
from pypdf import PdfReader

from .models import SourceArtifact, SourceType


class Fetcher(Protocol):
    def get(self, url: str, source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE) -> SourceArtifact: ...


class HttpxFetcher:
    def __init__(self, timeout: float = 20.0, user_agent: str = "TetherLensIngestionBenchmark/0.1"):
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": user_agent, "Accept": "text/html,application/json,application/pdf;q=0.9,*/*;q=0.8"},
        )

    def get(self, url: str, source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE) -> SourceArtifact:
        response = self._client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "application/octet-stream").split(";", 1)[0]
        metadata: dict[str, object] = {"status_code": response.status_code}
        if content_type == "application/pdf":
            reader = PdfReader(BytesIO(response.content))
            body = "\n".join(page.extract_text() or "" for page in reader.pages)
            metadata["page_count"] = len(reader.pages)
            if links := _pdf_external_links(reader):
                metadata["document_links"] = links
        else:
            body = response.text
        return SourceArtifact(
            url=str(response.url),
            source_type=source_type,
            content_type=content_type,
            body=body,
            metadata=metadata,
        )

    def close(self) -> None:
        self._client.close()


def _pdf_external_links(reader: PdfReader) -> list[str]:
    """Return external URI annotation targets without interpreting their semantics."""
    links: list[str] = []
    seen: set[str] = set()
    for page in reader.pages:
        for annotation_ref in page.get("/Annots", []):
            try:
                annotation = annotation_ref.get_object()
                if annotation.get("/Subtype") != "/Link":
                    continue
                action = annotation.get("/A")
                if not action or action.get("/S") != "/URI":
                    continue
                uri = str(action.get("/URI") or "").strip()
            except (AttributeError, KeyError, TypeError, ValueError):
                continue
            if uri and uri not in seen:
                seen.add(uri)
                links.append(uri)
    return links
