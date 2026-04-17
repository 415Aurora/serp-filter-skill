# serp-filter-skill

[![CI](https://github.com/415Aurora/serp-filter-skill/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/415Aurora/serp-filter-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python 3.11%2B](https://img.shields.io/badge/python-3.11%2B-blue.svg)](./pyproject.toml)
[![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-black.svg)](./CHANGELOG.md)

Google SERP filtering toolkit for blocklist-aware site discovery, domain enrichment, and spreadsheet exports.

用于抓取 Google 搜索结果、排除已存在站点、补充域名信息并导出表格结果的 Python CLI 工具。

## What It Does

`serp-filter-skill` is a small Python package for workflows where you need to:

- collect candidate websites from one or more Google queries
- exclude sites that already exist in a spreadsheet or local domain list
- normalize and deduplicate results by registrable domain
- optionally enrich domains with registration dates through RDAP
- export filtered output to `.csv`, `.xlsx`, and `.manifest.json`

当前默认分支 `main` 聚焦于第一轮搜索结果收集与筛选。

## Current Capability Boundaries

The current `main` branch supports:

- `run` command for live or replayed collection
- blocklist-aware filtering
- spreadsheet input handling
- domain date enrichment
- spreadsheet-friendly exports

The current `main` branch does **not** yet ship:

- second-pass `clean` workflows
- built-in quality scoring or keep / flag / drop review outputs
- merged multi-query summary exports
- product-specific asset-library integration

这些能力仍属于后续演进方向，不能视为 `main` 已上线能力。

## Features

- Single-query or batch-query input
- Spreadsheet-aware blocklist loading
- Domain normalization and deduplication
- Optional RDAP lookup for domain registration dates
- `serpapi` provider for live collection
- `static-json` provider for local replay and testing
- Spreadsheet export outputs for downstream review

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

`private/` and `output/` are intentionally ignored by git so API keys, local spreadsheets, and generated exports stay out of version control.

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

Main flags on `main`:

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

- `src/serp_filter/`: package implementation and CLI entrypoints
- `tests/`: pytest coverage for CLI, providers, pipeline, and blocklist handling
- `config/`: example configuration templates
- `examples/`: public sample inputs for docs and local replay
- `serp-filter-skill/`: Codex skill definition and agent-facing instructions
- `docs/`: reserved for longer-form documentation and design notes

当前仓库结构保持“开源工具仓库”定位，不默认暴露任何内部绝对路径或私有资产库约定。

## Public vs Internal Usage

This repository is usable as a standalone open source tool.

At the same time, it can be embedded into larger internal workflows that manage product-specific query sets, blocklists, or review pipelines outside this repository.

如果你是在内部系统中调用它，建议把产品级输入、运行结果和机会库放在仓库外部管理，而不是直接提交到本仓库。

## Development

Run the test suite:

```bash
PYTHONPATH=src python -m pytest -q
```

The repository also includes GitHub Actions CI for pushes and pull requests to `main`.

## Roadmap

Planned next steps include:

- richer second-pass review workflows
- better multi-query aggregation
- clearer quality heuristics for candidate prioritization
- stronger integration patterns for larger asset pipelines

这些 roadmap 项目并不代表 `main` 当前已经实现。

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
