from __future__ import annotations

from typing import Protocol

import httpx

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
        if content_type == "application/pdf":
            raise ValueError("PDF acquisition is supported as a source channel, but PDF text extraction is not implemented in v0.1")
        return SourceArtifact(
            url=str(response.url),
            source_type=source_type,
            content_type=content_type,
            body=response.text,
            metadata={"status_code": response.status_code},
        )

    def close(self) -> None:
        self._client.close()
