from __future__ import annotations

import argparse
import tomllib
from pathlib import Path
from typing import Sequence

from serp_filter.blocklist import BlocklistSourceConfig, load_blocked_domains
from serp_filter.cleaner import classify_rows, load_results_file, write_clean_results
from serp_filter.domain_dates import RdapDomainDateLookup
from serp_filter.pipeline import run_pipeline
from serp_filter.providers.serpapi import SerpApiProvider
from serp_filter.providers.static_json import StaticJsonProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="serp-filter")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--query", help="Single Google query to execute.")
    run_parser.add_argument("--query-file", type=Path, help="Text file containing one query per line.")
    run_parser.add_argument("--query-template-file", type=Path, help="Text file containing query templates.")
    run_parser.add_argument("--blocklist-file", type=Path, required=True)
    run_parser.add_argument("--sheet-name")
    run_parser.add_argument("--url-column", action="append", default=[])
    run_parser.add_argument("--domain-column", action="append", default=[])
    run_parser.add_argument("--provider", choices=["serpapi", "static-json"], default="serpapi")
    run_parser.add_argument("--provider-key", help="SerpApi key.")
    run_parser.add_argument("--provider-config", type=Path, help="TOML file storing provider credentials or paths.")
    run_parser.add_argument("--provider-data", type=Path, help="JSON payload for static-json provider.")
    run_parser.add_argument("--output-prefix", type=Path, required=True)
    run_parser.add_argument("--limit", type=int, default=20, help="Target number of kept results.")
    run_parser.add_argument("--page-size", type=int, default=10, help="Raw results requested per provider page.")
    run_parser.add_argument("--max-pages", type=int, default=10, help="Maximum provider pages to fetch per query.")
    run_parser.add_argument("--max-raw-results", type=int, default=100, help="Hard cap on raw fetched results per query.")
    run_parser.add_argument("--locale", default="us")
    run_parser.add_argument("--domain-date-provider", choices=["rdap", "noop"], default="rdap")
    run_parser.add_argument("--domain-delay", type=float, default=0.0)

    clean_parser = subparsers.add_parser("clean")
    clean_parser.add_argument("--input-file", type=Path, required=True, help="First-pass CSV or XLSX result file.")
    clean_parser.add_argument("--output-prefix", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "clean":
        rows = load_results_file(args.input_file)
        classified = classify_rows(rows)
        write_clean_results(classified, args.output_prefix)
        return 0
    if args.command != "run":
        parser.error("Unsupported command")

    queries = _load_queries(args.query, args.query_file, args.query_template_file)
    blocklist_config = BlocklistSourceConfig(
        path=args.blocklist_file,
        sheet_name=args.sheet_name,
        url_columns=args.url_column,
        domain_columns=args.domain_column,
    )
    blocked_domains = load_blocked_domains(blocklist_config)
    provider = _build_provider(args)
    domain_lookup = _build_domain_lookup(args)

    for index, query in enumerate(queries, start=1):
        output_prefix = args.output_prefix
        if len(queries) > 1:
            output_prefix = args.output_prefix.parent / f"{args.output_prefix.name}-{index:02d}"
        run_pipeline(
            query=query,
            provider=provider,
            blocked_domains=blocked_domains,
            domain_lookup=domain_lookup,
            output_prefix=output_prefix,
            limit=args.limit,
            page_size=args.page_size,
            max_pages=args.max_pages,
            max_raw_results=args.max_raw_results,
            locale=args.locale,
        )
    return 0


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

    seen: set[str] = set()
    deduped: list[str] = []
    for item in merged:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _build_provider(args: argparse.Namespace) -> object:
    provider_config = _load_provider_config(args.provider_config)
    if args.provider == "static-json":
        data_path = args.provider_data or _config_path(provider_config.get("static_json", {}), "data_path")
        if not data_path:
            raise ValueError("--provider-data or [static_json].data_path is required.")
        return StaticJsonProvider(data_path=data_path)
    provider_key = args.provider_key or provider_config.get("serpapi", {}).get("api_key")
    if not provider_key:
        raise ValueError("--provider-key is required for serpapi provider.")
    return SerpApiProvider(api_key=provider_key)


def _build_domain_lookup(args: argparse.Namespace):
    if args.domain_date_provider == "noop":
        return lambda domain: (None, "skipped")
    return RdapDomainDateLookup(min_interval_seconds=args.domain_delay)


def _load_provider_config(path: Path | None) -> dict:
    if not path:
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _config_path(section: dict, key: str) -> Path | None:
    value = section.get(key)
    return Path(value) if value else None


if __name__ == "__main__":
    raise SystemExit(main())
