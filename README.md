# serp-filter-skill

`serp-filter-skill` is a small Python CLI for fetching Google SERP results, excluding domains already present in a local blocklist, enriching domains with registration dates, and exporting the filtered results to spreadsheet-friendly files.

## Requirements

- Python 3.11+
- Optional: a SerpApi key for live Google queries

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e '.[dev]'
```

## What It Does

- Accepts a single query or a query file
- Reads blocklisted domains from spreadsheet or text-like inputs
- Deduplicates by registrable domain
- Optionally enriches domains with registration dates via RDAP
- Writes `.csv`, `.xlsx`, and `.manifest.json` outputs

## Repository Layout

- `src/serp_filter/`: CLI and pipeline implementation
- `tests/`: pytest coverage
- `config/`: example configuration files
- `serp-filter-skill/`: Codex skill definition
- `private/`: local-only provider keys and input files, ignored by git
- `output/`: generated exports, ignored by git

## Quick Start

Create your local-only working directories and copy the example provider config:

```bash
mkdir -p private output
cp config/providers.example.toml private/providers.toml
```

### Live SerpApi Run

Put your key in `private/providers.toml`, then run:

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

### Offline Replay

Use the `static-json` provider for replay or local verification:

```bash
PYTHONPATH=src python -m serp_filter run \
  --query-file private/queries.txt \
  --blocklist-file private/blocklists/sites.xlsx \
  --provider static-json \
  --provider-config private/providers.toml \
  --output-prefix output/google-serp-replay \
  --domain-date-provider noop
```

## CLI Reference

```bash
PYTHONPATH=src python -m serp_filter --help
PYTHONPATH=src python -m serp_filter run --help
```

Main flags:

- `--query` or `--query-file`
- `--blocklist-file`
- `--provider {serpapi,static-json}`
- `--provider-config`
- `--output-prefix`
- `--domain-date-provider {rdap,noop}`
- `--domain-delay`

## Test

```bash
PYTHONPATH=src python -m pytest -q
```

## Notes

- The recorded "creation date" is the domain registration date, not the site's real launch date.
- `private/` and `output/` are intentionally excluded from version control.
- The package exposes a console script named `serp-filter` after installation.
