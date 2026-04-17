---
name: serp-filter-google-results
description: Use when you need to fetch Google search results or clean first-pass SERP exports, exclude sites already present in a local website list, rank likely submission sites by quality signals such as query hit count and domain age, and write reviewable spreadsheet outputs while keeping provider credentials and private input files isolated. Also use when the user wants an offline replay with `static-json` before using a real SerpApi key.
---

# Google 搜索结果筛选

## Trigger guide

- 你要批量抓 Google 结果并筛出值得提交的网站
- 你有 blocklist，想排除已经做过的网站
- 你已经有首轮结果，只想做第二轮 `clean`
- 你想把结果写入统一资产库，而不是散落在项目目录
- 你没有 `SerpApi` key，想先用 `static-json` 做离线验证

## Canonical layout

- 逻辑代码：
  - `/Users/seven/workspace/.worktrees/feature-search-for-web-skill/meizhao/search-for-web`
- 共享 blocklist：
  - `/Users/seven/workspace/meizhao/database/02_raw_exports/submission_lists/_shared/blocklists/`
- 产品 query 集：
  - `/Users/seven/workspace/meizhao/database/02_raw_exports/submission_lists/{product_slug}/query_sets/`
- 结果输出：
  - `/Users/seven/workspace/meizhao/database/02_raw_exports/submission_lists/{product_slug}/search_for_web/runs/{run_id}/`
- provider 凭据：
  - `search-for-web/private/providers.toml`

## Default usage

优先使用资产库入口脚本，不要默认把业务文件继续塞进 `private/` 和 `output/`。

第一轮抓取：

```bash
python3 /Users/seven/workspace/meizhao/scripts/run_search_for_web_asset.py run \
  --product-slug zerogpt.plus \
  --run-id 2026-04-16_google-serp_ai-submit_v01 \
  --provider serpapi
```

第二轮清洗：

```bash
python3 /Users/seven/workspace/meizhao/scripts/run_search_for_web_asset.py clean \
  --product-slug zerogpt.plus \
  --run-id 2026-04-16_google-serp_ai-submit_v01
```

## Ask only for missing inputs

### 第一轮抓取至少需要

- `product_slug`
- `run_id`
- `provider` 模式
- 如果默认 query 文件不存在，则补 `--query` 或 `--query-file`

### 第二轮清洗至少需要

- `product_slug`
- `run_id`
- 如果默认 merged 文件不存在，则补 `--input-file`

## Low-level fallback

只有在需要调试底层命令时，才直接运行 `python -m serp_filter`。

```bash
cd /Users/seven/workspace/.worktrees/feature-search-for-web-skill/meizhao/search-for-web
PYTHONPATH=src /Users/seven/workspace/.venv/bin/python -m serp_filter run \
  --query-file /Users/seven/workspace/meizhao/database/02_raw_exports/submission_lists/zerogpt.plus/query_sets/default_queries.txt \
  --query-template-file config/query-templates.txt \
  --blocklist-file /Users/seven/workspace/meizhao/database/02_raw_exports/submission_lists/_shared/blocklists/ai-tool-submit-260327.xlsx \
  --provider serpapi \
  --provider-config private/providers.toml \
  --output-prefix /Users/seven/workspace/meizhao/database/02_raw_exports/submission_lists/zerogpt.plus/search_for_web/runs/2026-04-16_google-serp_ai-submit_v01/run/2026-04-16_google-serp_ai-submit_v01
```

## Behavior

- `run` 结果写入 `run/`
- `clean` 结果写入 `clean/`
- 每个 `run_id` 根目录会额外记录 `asset_manifest.json`
- 产品级 query 文件和 blocklist 以 `database/` 为准
- provider 凭据仍留在项目私有目录

## Failure handling

- 缺少依赖时，先修环境
- 缺少 `SerpApi` key 时：
  - 用户明确要真实抓取，就补 key 或 `providers.toml`
  - 只是验证流程，就切 `static-json`
- 用户只要第二轮清洗时，不要把问题扩展回第一轮抓取

## Notes

- “网站创建时间”当前仍是域名注册时间，不是页面上线时间
- `clean` 输出适合人工复核，不代表这些站点已经进入正式机会库
- 只有人工确认后的站点，才建议写入产品级 `search_candidates`
