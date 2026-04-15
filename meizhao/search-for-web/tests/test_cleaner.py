from __future__ import annotations

from serp_filter.cleaner import classify_row


def test_cleaner_keep_requires_submit_and_quality_signals() -> None:
    row = {
        "site_name": "AI Tools Directory",
        "title": "Submit your AI tool",
        "url": "https://example.com/submit",
        "snippet": "Submit your AI tool to our directory",
        "best_rank": "2",
        "query_hit_count": "3",
        "domain_created_at": "2018-01-01",
    }
    result = classify_row(row)
    assert result.decision == "keep"
    assert result.classification == "submission_candidate"
    assert result.final_score >= 7
    assert "rank_top_5" in result.signal_summary


def test_cleaner_flag_high_quality_directory_home_without_submit_signal() -> None:
    row = {
        "site_name": "General AI Directory",
        "title": "AI Tools Directory",
        "url": "https://example.com/",
        "snippet": "Discover the best AI tools in our directory",
        "best_rank": "6",
        "query_hit_count": "2",
        "domain_created_at": "2017-05-01",
    }
    result = classify_row(row)
    assert result.decision == "flag"
    assert result.classification == "directory_home_candidate"


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


def test_cleaner_drop_blog_and_detail_pages() -> None:
    blog_row = {
        "site_name": "Next AI",
        "title": "Top 10 AI Writing Tools",
        "url": "https://thenextai.com/blog/top-10-ai-writing-tools",
        "snippet": "Best AI tools",
    }
    detail_row = {
        "site_name": "AIXplore",
        "title": "Jasper AI - aixplore",
        "url": "https://aixplore.in/tool_details?slug=jasper",
        "snippet": "Tool details",
    }

    blog_result = classify_row(blog_row)
    detail_result = classify_row(detail_row)

    assert blog_result.decision == "drop"
    assert blog_result.classification == "blog_or_article"
    assert detail_result.decision == "drop"
    assert detail_result.classification == "detail_page"


def test_cleaner_drop_manual_submission_service_pages() -> None:
    row = {
        "site_name": "Fiverr",
        "title": "I will submit your ai tool to over 300 ai directories manually",
        "url": "https://www.fiverr.com/example/submit-your-ai-tool",
        "snippet": "manual submission service",
    }

    result = classify_row(row)

    assert result.decision == "drop"
    assert result.classification == "service_vendor"
