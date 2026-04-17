# Google SERP Filter Skill

这个项目继续作为 `search-for-web` 的代码执行引擎使用，但业务输入和结果输出已统一接入 `meizhao/database` 资产库。

## 当前职责

- 代码与逻辑：保留在本项目目录
- provider 凭据：默认保留在 `private/providers.toml`
- 示例配置：保留在 `config/`
- 历史 `output/`：视为 legacy 调试输出，不再作为正式业务结果目录

## Canonical 业务路径

- 共享 blocklist：
  - `/Users/seven/workspace/meizhao/database/02_raw_exports/submission_lists/_shared/blocklists/ai-tool-submit-260327.xlsx`
- ZeroGPT Plus 默认 query 集：
  - `/Users/seven/workspace/meizhao/database/02_raw_exports/submission_lists/zerogpt.plus/query_sets/default_queries.txt`
- ZeroGPT Plus 运行结果：
  - `/Users/seven/workspace/meizhao/database/02_raw_exports/submission_lists/zerogpt.plus/search_for_web/runs/{run_id}/run/`
- ZeroGPT Plus 清洗结果：
  - `/Users/seven/workspace/meizhao/database/02_raw_exports/submission_lists/zerogpt.plus/search_for_web/runs/{run_id}/clean/`

## 推荐运行方式

优先通过资产库入口脚本运行，而不是手动把业务文件放进本项目的 `private/` 或 `output/`。

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

## 低层命令

如果需要直接调试底层 CLI，仍可在本项目目录运行 `python -m serp_filter`。只是默认业务文件应来自资产库路径。

示例：

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

## 输出约定

- `run/` 目录保留第一轮结果：
  - `*.csv`
  - `*.xlsx`
  - `*.manifest.json`
  - 多 query 时的 `*-merged.*`
- `clean/` 目录保留第二轮结果：
  - `*.csv`
  - `*.xlsx`
  - `*.review.csv`
  - `*.manifest.json`
- `asset_manifest.json` 写在每个 `run_id` 根目录，用于记录该次运行的输入、命令和生成文件。

## 注意事项

- `private/providers.toml` 仍是默认凭据位置，不迁入数据库。
- 产品级 query 文件、共享 blocklist、正式结果文件一律以 `database/` 下的 canonical 路径为准。
- 如果要扩展到新产品，复用同一目录模板：
  - `database/02_raw_exports/submission_lists/{product_slug}/query_sets/`
  - `database/02_raw_exports/submission_lists/{product_slug}/search_for_web/runs/`
