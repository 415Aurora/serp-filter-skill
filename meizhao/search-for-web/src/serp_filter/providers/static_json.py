from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from serp_filter.domain_utils import normalize_root_domain
from serp_filter.models import SearchPage, SearchResult


@dataclass(slots=True)
class StaticJsonProvider:
    data_path: Path

    def fetch_page(
        self,
        query: str,
        page_size: int,
        locale: str | None = None,
        start: int = 0,
    ) -> SearchPage:
        payload = json.loads(self.data_path.read_text(encoding="utf-8"))
        results: list[SearchResult] = []
        items = payload.get(query, [])
        for item in items[start : start + page_size]:
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
        next_start = start + page_size if start + page_size < len(items) else None
        return SearchPage(results=results, next_start=next_start)
