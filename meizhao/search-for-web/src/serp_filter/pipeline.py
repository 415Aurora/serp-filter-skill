from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from serp_filter.models import AggregatedResult, EnrichedResult, PipelineRunResult, SearchResult
from serp_filter.writers import write_results


DomainLookup = Callable[[str], tuple[str | None, str]]


def _representative_result_priority(result: EnrichedResult) -> tuple[int, int, int, int, int]:
    url = result.url.lower()
    title = result.title.lower()
    path = urlparse(result.url).path
    submit_signal = any(token in url or token in title for token in ["/submit", "submit", "add-tool", "list-your-tool"])
    no_query_string = 0 if "?" in result.url else 1
    path_depth = len([part for part in path.split("/") if part])
    return (
        1 if submit_signal else 0,
        no_query_string,
        -min(path_depth, 20),
        -result.rank,
        -len(result.url),
    )


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


def aggregate_pipeline_results(run_results: list[PipelineRunResult]) -> list[AggregatedResult]:
    grouped: dict[str, list[EnrichedResult]] = {}
    for run in run_results:
        for result in run.kept_results:
            grouped.setdefault(result.root_domain, []).append(result)

    aggregated: list[AggregatedResult] = []
    for root_domain, results in grouped.items():
        representative = max(results, key=_representative_result_priority)
        matched_queries: list[str] = []
        seen_queries: set[str] = set()
        for result in results:
            if result.query in seen_queries:
                continue
            seen_queries.add(result.query)
            matched_queries.append(result.query)
        aggregated.append(
            AggregatedResult(
                **asdict(representative),
                best_rank=min(result.rank for result in results),
                query_hit_count=len(matched_queries),
                matched_queries="; ".join(matched_queries),
                best_url=representative.url,
                best_title=representative.title,
            )
        )

    aggregated.sort(
        key=lambda row: (
            -row.query_hit_count,
            row.best_rank,
            row.root_domain,
        )
    )
    return aggregated
