# serp-filter-skill

[![CI](https://github.com/415Aurora/serp-filter-skill/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/415Aurora/serp-filter-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python 3.11%2B](https://img.shields.io/badge/python-3.11%2B-blue.svg)](./pyproject.toml)
[![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-black.svg)](./CHANGELOG.md)

`serp-filter-skill` is a Python CLI for collecting Google SERP results, removing domains that already exist in a local blocklist, enriching the remaining domains with registration dates, and exporting clean results to spreadsheet-friendly output files.

It is designed for workflows where you need to:

- search for candidate websites from one or more Google queries
- exclude sites you already have in a spreadsheet or domain list
- deduplicate by registrable domain
- export filtered prospects as `.csv`, `.xlsx`, and `.manifest.json`

## Features

- Single-query or batch-query input
- Spreadsheet-aware blocklist loading
- Domain normalization and deduplication
- Optional RDAP lookup for domain registration dates
- `serpapi` provider for live collection
- `static-json` provider for local replay and testing

## Quickstart

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e '.[dev]'
```

### 2. Prepare local-only working directories

```bash
mkdir -p private/blocklists output
cp config/providers.example.toml private/providers.toml
```

`private/` and `output/` are intentionally ignored by git so you can keep API keys, input spreadsheets, and generated exports out of the repository.

### 3. Run the CLI

Live query run with SerpApi:

```bash
PYTHONPATH=src python -m serp_filter run \
  --query-file private/queries.txt \
  --blocklist-file private/blocklists/sites.xlsx \
  --provider serpapi \
  --provider-config private/providers.toml \
  --output-prefix output/google-serp-run \
  --domain-date-provider rdap \
  --domain-delay 1.0
```

Offline replay with local example files:

```bash
mkdir -p output
PYTHONPATH=src python -m serp_filter run \
  --query-file examples/queries.txt \
  --blocklist-file examples/blocklist-sites.csv \
  --provider static-json \
  --provider-config examples/providers.static-json.toml \
  --output-prefix output/example-run \
  --domain-date-provider noop
```

## Example Files

The [`examples/`](./examples) directory contains small public inputs you can inspect and adapt:

- [`examples/queries.txt`](./examples/queries.txt): sample search queries
- [`examples/blocklist-sites.csv`](./examples/blocklist-sites.csv): sample domains to exclude
- [`examples/static-provider.json`](./examples/static-provider.json): offline provider payload for replay
- [`examples/providers.static-json.toml`](./examples/providers.static-json.toml): config pointing the CLI at the offline payload

## CLI Reference

```bash
PYTHONPATH=src python -m serp_filter --help
PYTHONPATH=src python -m serp_filter run --help
```

Main flags:

- `--query` or `--query-file`
- `--blocklist-file`
- `--sheet-name`
- `--url-column`
- `--domain-column`
- `--provider {serpapi,static-json}`
- `--provider-config`
- `--provider-data`
- `--output-prefix`
- `--domain-date-provider {rdap,noop}`
- `--domain-delay`

## Repository Layout

- `src/serp_filter/`: implementation
- `tests/`: pytest coverage
- `config/`: example configuration templates
- `examples/`: public sample inputs for docs and local replay
- `serp-filter-skill/`: Codex skill definition

## Development

Run the test suite:

```bash
PYTHONPATH=src python -m pytest -q
```

The repository also includes GitHub Actions CI for pushes and pull requests to `main`.

## Contributing

Contribution guidelines live in [`CONTRIBUTING.md`](./CONTRIBUTING.md). The short version is:

- keep changes focused
- add or update tests when behavior changes
- do not commit secrets, `private/`, or generated `output/` files

## Changelog

Release history lives in [`CHANGELOG.md`](./CHANGELOG.md).

## Notes

- The recorded "creation date" is the domain registration date, not the site's true launch date.
- The installed package exposes a console script named `serp-filter`.
