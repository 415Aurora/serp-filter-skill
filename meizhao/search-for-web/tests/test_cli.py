from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook

from serp_filter.cli import main


def test_cli_run_with_static_provider_writes_outputs(tmp_path: Path) -> None:
    query_file = tmp_path / "queries.txt"
    query_file.write_text("best ai directories\n", encoding="utf-8")

    provider_data = tmp_path / "provider.json"
    provider_data.write_text(
        json.dumps(
            {
                "best ai directories": [
                    {
                        "position": 1,
                        "title": "Example Result",
                        "link": "https://www.example.com/tools",
                        "displayed_link": "www.example.com",
                        "source": "Example",
                        "snippet": "example",
                    },
                    {
                        "position": 2,
                        "title": "BBC Result",
                        "link": "https://www.bbc.co.uk/news/ai",
                        "displayed_link": "www.bbc.co.uk",
                        "source": "BBC",
                        "snippet": "bbc",
                    },
                ]
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
    sheet.append(["Example", "https://example.com"])
    workbook.save(blocklist)

    output_prefix = tmp_path / "output" / "run-1"

    exit_code = main(
        [
            "run",
            "--query-file",
            str(query_file),
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
    assert output_prefix.with_suffix(".csv").exists()
    assert output_prefix.with_suffix(".xlsx").exists()
