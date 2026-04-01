# Open Source Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `serp-filter-skill` from a minimally published repository into a lightweight but complete open-source project with better onboarding, examples, and CI.

**Architecture:** Keep the codebase unchanged unless needed for testability. Add repository-level assets that make the project easier to understand and contribute to, and validate those assets with a small repository-shape pytest module plus a GitHub Actions workflow that runs the existing test suite.

**Tech Stack:** Python 3.11+, pytest, GitHub Actions, Markdown docs

---

### Task 1: Add repository-shape regression tests

**Files:**
- Create: `tests/test_repository_assets.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_open_source_docs_and_examples_exist() -> None:
    root = repo_root()
    assert (root / "README.md").exists()
    assert (root / "CONTRIBUTING.md").exists()
    assert (root / "CHANGELOG.md").exists()
    assert (root / "examples" / "queries.txt").exists()
    assert (root / "examples" / "blocklist-sites.csv").exists()
    assert (root / ".github" / "workflows" / "ci.yml").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src /Users/seven/workspace/.worktrees/feature-search-for-web-skill/.venv/bin/python -m pytest tests/test_repository_assets.py -q`
Expected: FAIL because the files do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create the referenced files with lightweight but real content.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src /Users/seven/workspace/.worktrees/feature-search-for-web-skill/.venv/bin/python -m pytest tests/test_repository_assets.py -q`
Expected: PASS

### Task 2: Improve public-facing repository docs

**Files:**
- Modify: `README.md`
- Create: `CONTRIBUTING.md`
- Create: `CHANGELOG.md`
- Create: `examples/queries.txt`
- Create: `examples/blocklist-sites.csv`

- [ ] **Step 1: Rewrite README**

Add badges, a stronger project summary, quickstart, example-file guidance, repository layout, development/testing instructions, and contribution pointers.

- [ ] **Step 2: Add contributor-facing docs**

Create a concise `CONTRIBUTING.md` with setup, test commands, and PR expectations, plus a `CHANGELOG.md` with an initial `0.1.0` entry.

- [ ] **Step 3: Add public example inputs**

Create minimal, non-sensitive example query and blocklist files that match the README examples.

- [ ] **Step 4: Re-run repository-shape test**

Run: `PYTHONPATH=src /Users/seven/workspace/.worktrees/feature-search-for-web-skill/.venv/bin/python -m pytest tests/test_repository_assets.py -q`
Expected: PASS

### Task 3: Add GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Add workflow**

Create a single CI workflow for `push` and `pull_request` on `main`, using a small Python matrix and running `pytest -q`.

- [ ] **Step 2: Validate workflow presence via test**

Run: `PYTHONPATH=src /Users/seven/workspace/.worktrees/feature-search-for-web-skill/.venv/bin/python -m pytest tests/test_repository_assets.py -q`
Expected: PASS

### Task 4: Full verification and publish

**Files:**
- Modify: any files above as needed

- [ ] **Step 1: Run full test suite**

Run: `PYTHONPATH=src /Users/seven/workspace/.worktrees/feature-search-for-web-skill/.venv/bin/python -m pytest -q`
Expected: PASS with all tests green.

- [ ] **Step 2: Review git status and diff**

Run: `git status --short --branch` and `git diff --stat`
Expected: Only intended repo-polish changes.

- [ ] **Step 3: Commit and push**

Run:

```bash
git add README.md CONTRIBUTING.md CHANGELOG.md examples .github/workflows/ci.yml tests/test_repository_assets.py docs/superpowers/plans/2026-04-01-open-source-polish.md
git commit -m "chore: polish open source repository"
git push
```
