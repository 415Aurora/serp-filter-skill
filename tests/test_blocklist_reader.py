from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from serp_filter.blocklist import BlocklistSourceConfig, load_blocked_domains


def test_load_blocked_domains_prefers_explicit_column_mapping(tmp_path: Path) -> None:
    workbook_path = tmp_path / "blocklist.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sites"
    sheet.append(["Site", "Ignored", "Link"])
    sheet.append(["Example", "", "https://www.example.com/submit"])
    sheet.append(["Example Blog", "", "https://blog.example.com/page"])
    sheet.append(["BBC", "", "https://www.bbc.co.uk/news"])
    workbook.save(workbook_path)

    config = BlocklistSourceConfig(
        path=workbook_path,
        sheet_name="Sites",
        url_columns=["Link"],
    )

    assert load_blocked_domains(config) == {"example.com", "bbc.co.uk"}


def test_load_blocked_domains_falls_back_to_auto_detection(tmp_path: Path) -> None:
    workbook_path = tmp_path / "auto-detect.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Auto"
    sheet.append(["Name", "submit link", "Notes"])
    sheet.append(["Tumblr", "https://www.tumblr.com/", "done"])
    sheet.append(["Issuu", "https://issuu.com/", "done"])
    workbook.save(workbook_path)

    config = BlocklistSourceConfig(path=workbook_path)

    assert load_blocked_domains(config) == {"tumblr.com", "issuu.com"}
