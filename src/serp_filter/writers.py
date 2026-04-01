from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import Workbook

from serp_filter.models import EnrichedResult


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

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "results"
    sheet.append(FIELDNAMES)
    for row in kept_results:
        sheet.append([row.as_row()[field] for field in FIELDNAMES])
    workbook.save(xlsx_path)

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
