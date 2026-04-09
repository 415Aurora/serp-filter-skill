from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook, load_workbook


INPUT_FIELDNAMES = [
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

REVIEW_FIELDNAMES = INPUT_FIELDNAMES + ["classification", "decision", "review_reason"]

AI_SIGNALS = ["ai ", "ai-", "aitool", "artificial intelligence", "llm"]
DIRECTORY_SIGNALS = ["directory", "catalog", "catalogue", "library", "database", "resource", "guide", "toolbox"]
SUBMIT_SIGNALS = ["submit", "add", "list your tool", "tool-submit", "submit your tool"]


@dataclass(slots=True)
class CleanedRow:
    row: dict[str, str]
    classification: str
    decision: str
    review_reason: str

    def as_review_row(self) -> dict[str, str]:
        payload = dict(self.row)
        payload["classification"] = self.classification
        payload["decision"] = self.decision
        payload["review_reason"] = self.review_reason
        return payload


def load_results_file(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if path.suffix.lower() == ".xlsx":
        workbook = load_workbook(path, read_only=True, data_only=True)
        sheet = workbook["results"]
        rows = list(sheet.iter_rows(values_only=True))
        headers = [str(value) for value in rows[0]]
        results: list[dict[str, str]] = []
        for values in rows[1:]:
            results.append({header: "" if value is None else str(value) for header, value in zip(headers, values)})
        return results
    raise ValueError(f"Unsupported input file: {path}")


def classify_rows(rows: list[dict[str, str]]) -> list[CleanedRow]:
    return [classify_row(row) for row in rows]


def classify_row(row: dict[str, str]) -> CleanedRow:
    haystack = " ".join(
        [
            row.get("site_name", ""),
            row.get("title", ""),
            row.get("url", ""),
            row.get("snippet", ""),
        ]
    ).lower()
    url = row.get("url", "").lower()

    if any(token in haystack for token in ["youtube.com", "youtu.be", "x.com/", "twitter.com/", "linkedin.com/", "facebook.com/", "tiktok.com/"]):
        return CleanedRow(row=row, classification="video_or_social", decision="drop", review_reason="social or video result")

    if any(token in haystack for token in ["forum.", "/forum", "community.", "/community/", "idea-exchange", "productideas", "discourse"]):
        return CleanedRow(row=row, classification="forum_or_community", decision="drop", review_reason="forum or community discussion page")

    if any(token in haystack for token in ["docs.", "/docs/", "support.", "manual", "documentation", "help center", "help:", "tutorial", "learn.microsoft.com", "oracle help center"]):
        return CleanedRow(row=row, classification="product_doc", decision="drop", review_reason="product documentation or help page")

    if any(token in haystack for token in SUBMIT_SIGNALS):
        has_ai = any(token in haystack for token in AI_SIGNALS)
        has_dir = any(token in haystack for token in DIRECTORY_SIGNALS)
        if has_ai or has_dir:
            return CleanedRow(
                row=row,
                classification="submission_candidate",
                decision="keep",
                review_reason="submission page with ai/directory signal",
            )
        return CleanedRow(
            row=row,
            classification="submission_candidate",
            decision="flag",
            review_reason="submission page without ai/directory signal",
        )

    if any(token in haystack for token in DIRECTORY_SIGNALS):
        return CleanedRow(
            row=row,
            classification="catalog_or_resource_candidate",
            decision="flag",
            review_reason="catalog or resource page that may accept submissions",
        )

    return CleanedRow(
        row=row,
        classification="likely_irrelevant",
        decision="drop",
        review_reason="does not look like a submission or catalog candidate",
    )


def write_clean_results(rows: list[CleanedRow], output_prefix: Path) -> tuple[Path, Path, Path, Path]:
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output_prefix.with_suffix(".csv")
    xlsx_path = output_prefix.with_suffix(".xlsx")
    review_path = output_prefix.with_name(f"{output_prefix.name}.review.csv")
    manifest_path = output_prefix.with_name(f"{output_prefix.name}.manifest.json")

    kept_or_flagged = [row.as_review_row() for row in rows if row.decision in {"keep", "flag"}]
    review_rows = [row.as_review_row() for row in rows]

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDNAMES)
        writer.writeheader()
        writer.writerows(kept_or_flagged)

    with review_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDNAMES)
        writer.writeheader()
        writer.writerows(review_rows)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "results"
    sheet.append(REVIEW_FIELDNAMES)
    for row in kept_or_flagged:
        sheet.append([row.get(field, "") for field in REVIEW_FIELDNAMES])
    workbook.save(xlsx_path)

    decision_counts = Counter(row.decision for row in rows)
    classification_counts = Counter(row.classification for row in rows)
    manifest = {
        "input_count": len(rows),
        "output_count": len(kept_or_flagged),
        "decision_counts": dict(decision_counts),
        "classification_counts": dict(classification_counts),
        "csv_path": str(csv_path),
        "xlsx_path": str(xlsx_path),
        "review_csv_path": str(review_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return csv_path, xlsx_path, review_path, manifest_path
