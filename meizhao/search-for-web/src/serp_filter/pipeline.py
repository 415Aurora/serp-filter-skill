from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Callable

from serp_filter.models import EnrichedResult, PipelineRunResult, SearchResult
from serp_filter.writers import write_results


DomainLookup = Callable[[str], tuple[str | None, str]]


def run_pipeline(
    query: str,
    provider: object,
    blocked_domains: set[str],
    domain_lookup: DomainLookup,
    output_prefix: Path,
    limit: int,
    locale: str | None = None,
) -> PipelineRunResult:
    raw_results: list[SearchResult] = provider.search(query=query, limit=limit, locale=locale)
    domain_cache: dict[str, tuple[str | None, str]] = {}
    kept_results: list[EnrichedResult] = []
    excluded_results: list[EnrichedResult] = []

    for result in raw_results:
        if result.root_domain not in domain_cache:
            domain_cache[result.root_domain] = domain_lookup(result.root_domain)
        created_at, source = domain_cache[result.root_domain]
        enriched = EnrichedResult(
            **asdict(result),
            domain_created_at=created_at,
            domain_created_source=source,
            exclude_reason="blocked_domain" if result.root_domain in blocked_domains else None,
            status="excluded" if result.root_domain in blocked_domains else "kept",
        )
        if enriched.exclude_reason:
            excluded_results.append(enriched)
        else:
            kept_results.append(enriched)

    csv_path, xlsx_path, manifest_path = write_results(
        kept_results=kept_results,
        excluded_results=excluded_results,
        output_prefix=output_prefix,
    )
    return PipelineRunResult(
        kept_results=kept_results,
        excluded_results=excluded_results,
        csv_path=csv_path,
        xlsx_path=xlsx_path,
        manifest_path=manifest_path,
    )
