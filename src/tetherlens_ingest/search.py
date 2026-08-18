from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass(frozen=True)
class SearchResult:
    provider: str
    query: str
    rank: int
    title: str
    url: str
    snippet: str


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, limit: int = 8) -> list[SearchResult]: ...


class BraveSearchProvider:
    """Thin provider wrapper around Brave's supported Web Search API.

    Search is intentionally separated from fact resolution so provider choice
    can change without changing identity/property qualification logic.
    """

    name = "brave"
    endpoint = "https://api.search.brave.com/res/v1/web/search"

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 20.0,
        country: str = "US",
        search_lang: str = "en",
    ):
        self.api_key = api_key
        self.country = country
        self.search_lang = search_lang
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
                "User-Agent": "TetherLensIngestionBenchmark/0.1",
            },
        )

    @classmethod
    def from_env(cls) -> "BraveSearchProvider | None":
        api_key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
        return cls(api_key) if api_key else None

    def search(self, query: str, limit: int = 8) -> list[SearchResult]:
        response = self.client.get(
            self.endpoint,
            params={
                "q": query,
                "count": max(1, min(limit, 20)),
                "country": self.country,
                "search_lang": self.search_lang,
                "safesearch": "moderate",
            },
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("web", {}).get("results", []) if isinstance(payload, dict) else []
        out: list[SearchResult] = []
        for rank, row in enumerate(rows[:limit], start=1):
            if not isinstance(row, dict) or not row.get("url"):
                continue
            out.append(SearchResult(
                provider=self.name,
                query=query,
                rank=rank,
                title=str(row.get("title") or ""),
                url=str(row.get("url")),
                snippet=str(row.get("description") or ""),
            ))
        return out

    def close(self) -> None:
        self.client.close()
