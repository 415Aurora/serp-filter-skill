from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import requests

from serp_filter.domain_utils import normalize_root_domain
from serp_filter.models import SearchPage, SearchResult


@dataclass(slots=True)
class SerpApiProvider:
    api_key: str
    session: requests.Session | object | None = None
    base_url: str = "https://serpapi.com/search.json"

    def fetch_page(
        self,
        query: str,
        page_size: int,
        locale: str | None = None,
        start: int = 0,
    ) -> SearchPage:
        client = self.session or requests.Session()
        response = client.get(
            self.base_url,
            params={
                "engine": "google",
                "q": query,
                "num": page_size,
                "api_key": self.api_key,
                "gl": locale or "us",
                "start": start,
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
        return SearchPage(results=results, next_start=_extract_next_start(payload))


def _extract_next_start(payload: dict) -> int | None:
    next_url = payload.get("serpapi_pagination", {}).get("next")
    if not next_url:
        return None
    parsed = urlparse(next_url)
    start_values = parse_qs(parsed.query).get("start", [])
    if not start_values:
        return None
    try:
        return int(start_values[0])
    except ValueError:
        return None
