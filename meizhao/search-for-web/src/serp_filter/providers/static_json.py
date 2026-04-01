from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from serp_filter.domain_utils import normalize_root_domain
from serp_filter.models import SearchResult


@dataclass(slots=True)
class StaticJsonProvider:
    data_path: Path

    def search(self, query: str, limit: int, locale: str | None = None) -> list[SearchResult]:
        payload = json.loads(self.data_path.read_text(encoding="utf-8"))
        results: list[SearchResult] = []
        for item in payload.get(query, [])[:limit]:
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

