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
    page_size: int,
    max_pages: int,
    max_raw_results: int,
    locale: str | None = None,
) -> PipelineRunResult:
    domain_cache: dict[str, tuple[str | None, str]] = {}
    kept_results: list[EnrichedResult] = []
    excluded_results: list[EnrichedResult] = []
    seen_urls: set[str] = set()
    pages_fetched = 0
    raw_fetched_count = 0
    stop_reason = "no_more_pages"
    next_start = 0

    while pages_fetched < max_pages and raw_fetched_count < max_raw_results:
        page = provider.fetch_page(query=query, page_size=page_size, locale=locale, start=next_start)
        pages_fetched += 1

        for result in page.results:
            if raw_fetched_count >= max_raw_results:
                stop_reason = "max_raw_results_reached"
                break
            raw_fetched_count += 1
            if result.url in seen_urls:
                continue
            seen_urls.add(result.url)

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
                if len(kept_results) >= limit:
                    stop_reason = "target_reached"
                    break

        if stop_reason in {"target_reached", "max_raw_results_reached"}:
            break
        if raw_fetched_count >= max_raw_results:
            stop_reason = "max_raw_results_reached"
            break
        if page.next_start is None:
            stop_reason = "no_more_pages"
            break
        next_start = page.next_start
    else:
        if pages_fetched >= max_pages:
            stop_reason = "max_pages_reached"

    csv_path, xlsx_path, manifest_path = write_results(
        query=query,
        target_kept_count=limit,
        kept_results=kept_results,
        excluded_results=excluded_results,
        raw_fetched_count=raw_fetched_count,
        pages_fetched=pages_fetched,
        page_size=page_size,
        max_pages=max_pages,
        max_raw_results=max_raw_results,
        stop_reason=stop_reason,
        output_prefix=output_prefix,
    )
    return PipelineRunResult(
        query=query,
        target_kept_count=limit,
        kept_results=kept_results,
        excluded_results=excluded_results,
        raw_fetched_count=raw_fetched_count,
        pages_fetched=pages_fetched,
        stop_reason=stop_reason,
        csv_path=csv_path,
        xlsx_path=xlsx_path,
        manifest_path=manifest_path,
    )
