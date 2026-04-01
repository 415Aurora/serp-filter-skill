from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class SearchResult:
    query: str
    rank: int
    title: str
    site_name: str
    url: str
    displayed_domain: str
    root_domain: str
    snippet: str
    provider_raw_date: str | None


@dataclass(slots=True)
class SearchPage:
    results: list[SearchResult]
    next_start: int | None


@dataclass(slots=True)
class EnrichedResult(SearchResult):
    domain_created_at: str | None
    domain_created_source: str
    exclude_reason: str | None
    status: str

    def as_row(self) -> dict[str, str | int | None]:
        return asdict(self)


@dataclass(slots=True)
class PipelineRunResult:
    query: str
    target_kept_count: int
    kept_results: list[EnrichedResult]
    excluded_results: list[EnrichedResult]
    raw_fetched_count: int
    pages_fetched: int
    stop_reason: str
    csv_path: Path
    xlsx_path: Path
    manifest_path: Path
