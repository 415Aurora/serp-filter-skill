# AI Submit Sites Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize the Google SERP filtering skill to prioritize AI tool submission sites by adding query templates and stricter keep/flag/drop classification.

**Architecture:** Add a template-file query source merged with user queries, and harden second-pass cleaning rules to keep only explicit submission pages (AI/directory signals required for keep) while flagging broader candidates. Keep current pagination, blocklist filtering, and RDAP fallback intact.

**Tech Stack:** Python 3.11+, argparse CLI, openpyxl, requests.

---

### Task 1: Add query template file and merge logic

**Files:**
- Create: `config/query-templates.txt`
- Modify: `src/serp_filter/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing test for query template merging**

Add this test to `tests/test_cli.py`:

```python

def test_cli_run_with_query_template_file_merges_queries(tmp_path: Path) -> None:
    query_file = tmp_path / "queries.txt"
    query_file.write_text("submit your AI tool\n", encoding="utf-8")

    template_file = tmp_path / "templates.txt"
    template_file.write_text("submit your AI tool\nadd your AI tool directory\n", encoding="utf-8")

    provider_data = tmp_path / "provider.json"
    provider_data.write_text(
        json.dumps(
            {
                "submit your AI tool": [
                    {
                        "position": 1,
                        "title": "Example Result",
                        "link": "https://www.example.com/tools",
                        "displayed_link": "www.example.com",
                        "source": "Example",
                        "snippet": "example",
                    }
                ],
                "add your AI tool directory": [
                    {
                        "position": 1,
                        "title": "Second Result",
                        "link": "https://www.second.com/tools",
                        "displayed_link": "www.second.com",
                        "source": "Second",
                        "snippet": "second",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    provider_config = tmp_path / "providers.toml"
    provider_config.write_text(
        "\n".join(
            [
                "[static_json]",
                f"data_path = {json.dumps(str(provider_data))}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    blocklist = tmp_path / "blocklist.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sites"
    sheet.append(["name", "submit link"])
    workbook.save(blocklist)

    output_prefix = tmp_path / "output" / "run-templates"

    exit_code = main(
        [
            "run",
            "--query-file",
            str(query_file),
            "--query-template-file",
            str(template_file),
            "--blocklist-file",
            str(blocklist),
            "--provider",
            "static-json",
            "--provider-config",
            str(provider_config),
            "--domain-date-provider",
            "noop",
            "--output-prefix",
            str(output_prefix),
        ]
    )

    assert exit_code == 0
    assert output_prefix.with_name("run-templates-01.csv").exists()
    assert output_prefix.with_name("run-templates-02.csv").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
/Users/seven/workspace/.worktrees/feature-search-for-web-skill/.venv/bin/python -m pytest tests/test_cli.py::test_cli_run_with_query_template_file_merges_queries -q
```
Expected: FAIL with "unrecognized arguments: --query-template-file" or missing outputs.

- [ ] **Step 3: Implement template merge in CLI**

Update `src/serp_filter/cli.py`:

1) Add new argument:
```python
run_parser.add_argument("--query-template-file", type=Path, help="Text file containing query templates.")
```

2) Replace `_load_queries` with a merge-friendly implementation and add a helper:

```python
def _load_query_lines(path: Path | None) -> list[str]:
    if not path:
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_queries(query: str | None, query_file: Path | None, template_file: Path | None) -> list[str]:
    merged: list[str] = []
    if query:
        merged.append(query)
    merged.extend(_load_query_lines(query_file))
    merged.extend(_load_query_lines(template_file))

    if not merged:
        raise ValueError("Either --query, --query-file, or --query-template-file is required.")

    # de-duplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for item in merged:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
```

3) Update call site in `main()`:
```python
queries = _load_queries(args.query, args.query_file, args.query_template_file)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
/Users/seven/workspace/.worktrees/feature-search-for-web-skill/.venv/bin/python -m pytest tests/test_cli.py::test_cli_run_with_query_template_file_merges_queries -q
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config/query-templates.txt src/serp_filter/cli.py tests/test_cli.py
git commit -m "feat: add query templates for ai submit sites"
```

---

### Task 2: Create default template file

**Files:**
- Create: `config/query-templates.txt`

- [ ] **Step 1: Add template file**

Create `config/query-templates.txt` with these lines:
```
intitle:"submit a tool" (AI OR "AI tool" OR "AI tools" OR LLM)
"submit your AI tool" OR "submit your tool" "AI directory"
"add your AI tool" "directory" OR "AI tools directory"
"list your AI tool" "AI tools"
```

- [ ] **Step 2: Commit**

```bash
git add config/query-templates.txt
git commit -m "chore: add ai submit query templates"
```

---

### Task 3: Tighten AI-submit cleaning rules with strict keep

**Files:**
- Modify: `src/serp_filter/cleaner.py`
- Test: `tests/test_cleaner.py`

- [ ] **Step 1: Write failing tests for keep/flag/drop**

Create `tests/test_cleaner.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
/Users/seven/workspace/.worktrees/feature-search-for-web-skill/.venv/bin/python -m pytest tests/test_cleaner.py -q
```
Expected: FAIL until the stricter logic is applied.

- [ ] **Step 3: Implement stricter keep/flag logic**

Update `src/serp_filter/cleaner.py`:

1) Introduce AI and directory signal helpers:
```python
AI_SIGNALS = ["ai ", "ai-", "aitool", "artificial intelligence", "llm"]
DIRECTORY_SIGNALS = ["directory", "catalog", "catalogue", "library", "database", "resource", "guide", "toolbox"]
SUBMIT_SIGNALS = ["submit", "add", "list your tool", "tool-submit", "submit your tool"]
```

2) Replace the current submit rule with strict keep:
```python
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
```

3) Keep existing doc/forum/social drops, but ensure they run before submit rule.

- [ ] **Step 4: Run tests to verify pass**

Run:
```bash
/Users/seven/workspace/.worktrees/feature-search-for-web-skill/.venv/bin/python -m pytest tests/test_cleaner.py -q
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/serp_filter/cleaner.py tests/test_cleaner.py
git commit -m "feat: tighten ai submit cleaning rules"
```

---

### Task 4: Update docs for AI-submit optimization

**Files:**
- Modify: `serp-filter-skill/SKILL.md`
- Modify: `README.md`

- [ ] **Step 1: Update skill docs**

In `serp-filter-skill/SKILL.md`:
- Add the `--query-template-file` option under Inputs
- Add a short snippet showing how to use `config/query-templates.txt`
- Note that `clean` now uses strict keep + wide flag for AI submit sites

- [ ] **Step 2: Update README**

In `README.md`:
- Document `config/query-templates.txt`
- Add `--query-template-file config/query-templates.txt` to `run` examples
- Describe strict keep / wide flag behavior

- [ ] **Step 3: Commit**

```bash
git add serp-filter-skill/SKILL.md README.md
git commit -m "docs: document ai submit templates and cleaning"
```

---

### Task 5: Full test run

**Files:**
- Test: full suite

- [ ] **Step 1: Run full tests**

Run:
```bash
/Users/seven/workspace/.worktrees/feature-search-for-web-skill/.venv/bin/python -m pytest -q
```
Expected: PASS (all tests green).

- [ ] **Step 2: Final commit (if any changes left)**

```bash
git status --short
```
If clean, no commit needed.
