from __future__ import annotations

from serp_filter.cleaner import classify_row


def test_cleaner_keep_requires_submit_and_ai_or_directory_signal() -> None:
    row = {
        "site_name": "AI Tools Directory",
        "title": "Submit your AI tool",
        "url": "https://example.com/submit",
        "snippet": "Submit your AI tool to our directory",
    }
    result = classify_row(row)
    assert result.decision == "keep"
    assert result.classification == "submission_candidate"


def test_cleaner_flag_submit_without_ai_or_directory() -> None:
    row = {
        "site_name": "General Tools",
        "title": "Submit your tool",
        "url": "https://example.com/submit",
        "snippet": "Submit your tool",
    }
    result = classify_row(row)
    assert result.decision == "flag"
    assert result.classification == "submission_candidate"


def test_cleaner_drop_docs_and_forums() -> None:
    row = {
        "site_name": "Vendor Docs",
        "title": "Add a tool",
        "url": "https://vendor.com/docs/add-a-tool",
        "snippet": "Documentation",
    }
    result = classify_row(row)
    assert result.decision == "drop"
    assert result.classification == "product_doc"
