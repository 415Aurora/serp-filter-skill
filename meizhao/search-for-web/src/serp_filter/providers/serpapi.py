from __future__ import annotations

from dataclasses import dataclass

import requests

from serp_filter.domain_utils import normalize_root_domain
from serp_filter.models import SearchResult


@dataclass(slots=True)
class SerpApiProvider:
    api_key: str
    session: requests.Session | object | None = None
    base_url: str = "https://serpapi.com/search.json"

    def search(self, query: str, limit: int, locale: str | None = None) -> list[SearchResult]:
        client = self.session or requests.Session()
        response = client.get(
            self.base_url,
            params={
                "engine": "google",
                "q": query,
                "num": limit,
                "api_key": self.api_key,
                "gl": locale or "us",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        results: list[SearchResult] = []
        for item in payload.get("organic_results", []):
            link = item.get("link", "")
            results.append(
                SearchResult(
                    query=query,
                    rank=int(item.get("position", len(results) + 1)),
                    title=item.get("title", ""),
                    site_name=item.get("source") or item.get("displayed_link", ""),
                    url=link,
                    displayed_domain=item.get("displayed_link", ""),
                    root_domain=normalize_root_domain(link),
                    snippet=item.get("snippet", ""),
                    provider_raw_date=item.get("date"),
                )
            )
        return results

