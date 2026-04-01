---
name: serp-filter-google-results
description: Use when you need to fetch Google search results, exclude sites already present in a local website list, enrich with domain registration dates, and write the filtered sites to spreadsheet outputs while keeping private config isolated.
---

# Google 搜索结果筛选

## When to use
- 你已经有一条或多条 Google 搜索指令，需要批量拿到站点结果。
- 你手上有 `.xlsx/.csv/.txt` 网站名单文件，想排除已经出现过的站点。
- 你需要把剩余站点导出成 `xlsx + csv`，并附带域名注册时间。
- 你希望 API key、名单文件、输出文件和 skill 逻辑隔离。

## Project layout
- 逻辑代码：`meizhao/search-for-web/src/serp_filter/`
- 示例配置：`meizhao/search-for-web/config/`
- 私有输入：`meizhao/search-for-web/private/`
- 结果输出：`meizhao/search-for-web/output/`

## Inputs
1. 查询：
   - 单条查询：`--query "best ai directories"`
   - 批量查询：`--query-file private/queries.txt`
2. 名单文件：
   - `--blocklist-file private/blocklists/sites.xlsx`
   - 可选 `--sheet-name`、`--url-column`、`--domain-column`
3. provider：
   - `serpapi`
   - `static-json`（用于测试或离线回放）

## Default usage
先准备私有配置文件 `private/providers.toml`，可参考 `config/providers.example.toml`。

SerpApi 实际运行：
```bash
cd meizhao/search-for-web
PYTHONPATH=src ../../.venv/bin/python -m serp_filter run \
  --query-file private/queries.txt \
  --blocklist-file private/blocklists/ai-tool-submit-260327.xlsx \
  --provider serpapi \
  --provider-config private/providers.toml \
  --output-prefix output/google-serp-run \
  --domain-date-provider rdap \
  --domain-delay 1.0
```

离线回放：
```bash
cd meizhao/search-for-web
PYTHONPATH=src ../../.venv/bin/python -m serp_filter run \
  --query-file private/queries.txt \
  --blocklist-file private/blocklists/ai-tool-submit-260327.xlsx \
  --provider static-json \
  --provider-config private/providers.toml \
  --output-prefix output/google-serp-replay \
  --domain-date-provider noop
```

## Behavior
- 按主域名去重和排除。
- 同一主域名只查询一次域名注册时间。
- `tldextract` 使用内置后缀表，不会为后缀解析额外联网。
- `rdap` 查询可用 `--domain-delay` 控制节流。
- 输出文件：
  - `*.csv`
  - `*.xlsx`
  - `*.manifest.json`

## Notes
- “网站创建时间”当前实现为域名注册时间，不是站点真实上线时间。
- 如果名单文件列名不固定，优先用 `--url-column`/`--domain-column` 明确指定；不指定时会自动扫描 `url/link/site/domain/website/submit` 相关列。
