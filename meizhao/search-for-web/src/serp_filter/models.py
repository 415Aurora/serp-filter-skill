from __future__ import annotations

from dataclasses import asdict, dataclass


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
class EnrichedResult(SearchResult):
    domain_created_at: str | None
    domain_created_source: str
    exclude_reason: str | None
    status: str

    def as_row(self) -> dict[str, str | int | None]:
        return asdict(self)


@dataclass(slots=True)
class PipelineRunResult:
    kept_results: list[EnrichedResult]
    excluded_results: list[EnrichedResult]
    csv_path: str
    xlsx_path: str
    manifest_path: str

