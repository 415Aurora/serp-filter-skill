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
- 你希望先拿到第一轮候选，再做第二轮噪音清洗，而不是一次性只保留极少数高置信结果。

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
4. 第二轮清洗输入：
   - 第一轮输出的 `csv/xlsx`
   - 用于生成“候选结果 + review 文件”

## Default usage
先准备私有配置文件 `private/providers.toml`，可参考 `config/providers.example.toml`。

第一轮抓取：
```bash
cd meizhao/search-for-web
PYTHONPATH=src ../../.venv/bin/python -m serp_filter run \
  --query-file private/queries.txt \
  --blocklist-file private/blocklists/ai-tool-submit-260327.xlsx \
  --provider serpapi \
  --provider-config private/providers.toml \
  --output-prefix output/google-serp-run \
  --limit 50 \
  --page-size 10 \
  --max-pages 10 \
  --max-raw-results 100 \
  --domain-date-provider rdap \
  --domain-delay 1.0
```

第二轮清洗：
```bash
cd meizhao/search-for-web
PYTHONPATH=src ../../.venv/bin/python -m serp_filter clean \
  --input-file output/google-serp-run.csv \
  --output-prefix output/google-serp-run-cleaned
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
  --limit 20 \
  --page-size 10 \
  --max-pages 10 \
  --max-raw-results 100 \
  --domain-date-provider noop
```

## Behavior
- `--limit` 表示最终保留结果数目标，不是单页抓取数。
- provider 会按页抓取，直到达到目标保留数、没有更多页，或触发 `--max-pages` / `--max-raw-results` 上限。
- 同一主域名只查询一次域名注册时间。
- 相同 URL 跨页不会重复写入结果。
- `tldextract` 使用内置后缀表，不会为后缀解析额外联网。
- `rdap` 查询可用 `--domain-delay` 控制节流；如果 `rdap.org` 超时或返回异常，任务不会失败，而是把该域名标成 `rdap_error`。
- `clean` 子命令会根据 URL、标题、摘要做规则分类，默认尽量保留候选页，并在 review 文件中标出为什么保留、标记或丢弃。
- 输出文件：
  - `*.csv`
  - `*.xlsx`
  - `*.manifest.json`
  - `*.review.csv`（第二轮清洗时）

## Notes
- “网站创建时间”当前实现为域名注册时间，不是站点真实上线时间。
- `*.manifest.json` 会记录原始抓取数、抓取页数和停止原因，便于判断结果偏少是因为 Google 本身少、过滤过多，还是达到抓取上限。
- 第二轮清洗默认是“多保留候选”，因此 `clean` 的结果里会同时出现 `keep` 和 `flag` 两类记录；明显的文档、论坛、视频和社交页面会被排除到 review 文件里。
- 如果名单文件列名不固定，优先用 `--url-column`/`--domain-column` 明确指定；不指定时会自动扫描 `url/link/site/domain/website/submit` 相关列。
