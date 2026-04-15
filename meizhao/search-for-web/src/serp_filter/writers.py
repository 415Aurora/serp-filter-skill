from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import Workbook

from serp_filter.models import AggregatedResult, EnrichedResult


FIELDNAMES = [
    "query",
    "rank",
    "site_name",
    "title",
    "url",
    "displayed_domain",
    "root_domain",
    "snippet",
    "provider_raw_date",
    "domain_created_at",
    "domain_created_source",
    "exclude_reason",
    "status",
]

MERGED_FIELDNAMES = FIELDNAMES + [
    "best_rank",
    "query_hit_count",
    "matched_queries",
    "best_url",
    "best_title",
]


def _write_xlsx(path: Path, fieldnames: list[str], rows: list[dict[str, str | int | None]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "results"
    sheet.append(fieldnames)
    for row in rows:
        sheet.append([row.get(field, "") for field in fieldnames])
    workbook.save(path)


def write_results(
    query: str,
    target_kept_count: int,
    kept_results: list[EnrichedResult],
    excluded_results: list[EnrichedResult],
    raw_fetched_count: int,
    pages_fetched: int,
    page_size: int,
    max_pages: int,
    max_raw_results: int,
    stop_reason: str,
    output_prefix: Path,
) -> tuple[Path, Path, Path]:
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output_prefix.with_suffix(".csv")
    xlsx_path = output_prefix.with_suffix(".xlsx")
    manifest_path = output_prefix.with_name(f"{output_prefix.name}.manifest.json")

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in kept_results:
            writer.writerow(row.as_row())

    _write_xlsx(xlsx_path, FIELDNAMES, [row.as_row() for row in kept_results])

    manifest = {
        "query": query,
        "target_kept_count": target_kept_count,
        "kept_count": len(kept_results),
        "excluded_count": len(excluded_results),
        "raw_fetched_count": raw_fetched_count,
        "pages_fetched": pages_fetched,
        "page_size": page_size,
        "max_pages": max_pages,
        "max_raw_results": max_raw_results,
        "stop_reason": stop_reason,
        "csv_path": str(csv_path),
        "xlsx_path": str(xlsx_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return csv_path, xlsx_path, manifest_path


def write_merged_results(
    aggregated_results: list[AggregatedResult],
    output_prefix: Path,
) -> tuple[Path, Path, Path]:
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output_prefix.with_suffix(".csv")
    xlsx_path = output_prefix.with_suffix(".xlsx")
    manifest_path = output_prefix.with_name(f"{output_prefix.name}.manifest.json")

    rows = [row.as_row() for row in aggregated_results]

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MERGED_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    _write_xlsx(xlsx_path, MERGED_FIELDNAMES, rows)

    manifest = {
        "aggregated_count": len(aggregated_results),
        "csv_path": str(csv_path),
        "xlsx_path": str(xlsx_path),
        "fieldnames": MERGED_FIELDNAMES,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return csv_path, xlsx_path, manifest_path
