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
