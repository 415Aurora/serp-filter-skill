---
name: serp-filter-google-results
description: Use when you need to fetch Google search results or clean first-pass SERP exports, exclude sites already present in a local website list, enrich with domain registration dates, and write reviewable spreadsheet outputs while keeping provider credentials and private input files isolated. Also use when the user wants an offline replay with `static-json` before using a real SerpApi key.
---

# Google 搜索结果筛选

## Trigger guide
- 你已经有一条或多条 Google 搜索指令，需要批量拿到站点结果。
- 你手上有 `.xlsx/.csv/.txt` 网站名单文件，想排除已经出现过的站点。
- 你需要把剩余站点导出成 `xlsx + csv`，并附带域名注册时间。
- 你已经有第一轮 `csv/xlsx`，只想做第二轮清洗。
- 你还没有 `SerpApi` key，想先用 `static-json` 离线回放验证流程。
- 你希望 API key、名单文件、输出文件和 skill 逻辑隔离。
- 你希望先拿到第一轮候选，再做第二轮噪音清洗，而不是一次性只保留极少数高置信结果。

## Project layout
- 逻辑代码：`meizhao/search-for-web/src/serp_filter/`
- 示例配置：`meizhao/search-for-web/config/`
- 私有输入：`meizhao/search-for-web/private/`
- 结果输出：`meizhao/search-for-web/output/`

## Decide the path first

先判断用户要哪条路径，不要默认走完整流程：

1. 第一轮抓取：用户要从查询语句出发抓 Google 结果、排除 blocklist、输出第一轮候选。
2. 第二轮清洗：用户已经有第一轮 `csv/xlsx`，只需要 `clean`。
3. 离线回放：用户不想联网、没有 `SerpApi` key、或只是想先验证工作流，这时优先用 `static-json`。

如果目标明显属于其中一条路径，只问缺失的输入，不要把另外两条路径的参数都一起追问一遍。

## Preflight

在执行任何命令前，先确认这 4 件事：

1. 当前目录是 `meizhao/search-for-web`。
2. Python 环境已经安装项目依赖；如果没有，先按 `pyproject.toml` / `README.md` 准备环境。
3. provider 模式明确：
   - 真实 Google 抓取用 `serpapi`
   - 离线验证用 `static-json`
4. 输出前缀明确，避免覆盖已有结果。

如果连 `python -m serp_filter --help` 都跑不起来，先处理依赖问题，再继续。

## Ask only for missing inputs

### 第一轮抓取至少需要
- `--query` 或 `--query-file`
- `--blocklist-file`
- `--output-prefix`
- provider 相关输入：
  - `serpapi` 需要 `--provider-key` 或 `--provider-config`
  - `static-json` 需要 `--provider-data` 或 `providers.toml` 中的 `[static_json].data_path`

### 第二轮清洗至少需要
- `--input-file`
- `--output-prefix`

### 只有在 blocklist 自动识别不可靠时才补问
- `--sheet-name`
- `--url-column`
- `--domain-column`

## Inputs
1. 查询：
   - 单条查询：`--query "best ai directories"`
   - 批量查询：`--query-file private/queries.txt`
   - 模板查询：`--query-template-file config/query-templates.txt`
   - 模板文件示例：
```bash
cd meizhao/search-for-web
PYTHONPATH=src ../../.venv/bin/python -m serp_filter run \
  --query-template-file config/query-templates.txt \
  --blocklist-file private/blocklists/ai-tool-submit-260327.xlsx \
  --provider static-json \
  --provider-config private/providers.toml \
  --output-prefix output/google-serp-template-replay
```
2. 名单文件：
   - `--blocklist-file private/blocklists/sites.xlsx`
   - 可选 `--sheet-name`、`--url-column`、`--domain-column`
3. provider：
   - `serpapi`
   - `static-json`
4. 第二轮清洗输入：
   - 第一轮输出的 `csv/xlsx`
   - 用于生成“候选结果 + review 文件”

## Default usage
先准备私有配置文件 `private/providers.toml`，可参考 `config/providers.example.toml`。

如果用户没有明确说要离线回放，默认先判断是否具备 `serpapi` 真实抓取条件；如果没有 key，就主动切到 `static-json` 做验证，而不是卡住。

第一轮抓取：
```bash
cd meizhao/search-for-web
PYTHONPATH=src ../../.venv/bin/python -m serp_filter run \
  --query-file private/queries.txt \
  --query-template-file config/query-templates.txt \
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

如果用户只给自然语言需求，没有给足参数，优先补齐：
- 查询语句或 query 文件
- blocklist 文件路径
- 输出前缀
- provider 模式和对应配置

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
  --query-template-file config/query-templates.txt \
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

## Fast paths

### Clean-only

如果用户已经有第一轮输出，不要再追问 query、blocklist 或 SerpApi key，直接走：

```bash
cd meizhao/search-for-web
PYTHONPATH=src ../../.venv/bin/python -m serp_filter clean \
  --input-file output/first-pass.csv \
  --output-prefix output/first-pass-cleaned
```

### Offline validation first

如果用户说“先不要联网”或“还没有 key”，优先走 `static-json`，并把 `--domain-date-provider noop` 作为默认低摩擦选择，先验证主流程能跑通，再决定是否切换到 `rdap`。

## Behavior
- `--limit` 表示最终保留结果数目标，不是单页抓取数。
- provider 会按页抓取，直到达到目标保留数、没有更多页，或触发 `--max-pages` / `--max-raw-results` 上限。
- 同一主域名只查询一次域名注册时间。
- 相同 URL 跨页不会重复写入结果。
- `tldextract` 使用内置后缀表，不会为后缀解析额外联网。
- `rdap` 查询可用 `--domain-delay` 控制节流；如果 `rdap.org` 超时或返回异常，任务不会失败，而是把该域名标成 `rdap_error`。
- `clean` 子命令会根据 URL、标题、摘要做规则分类，采用“严格 keep + 宽口径 flag”策略：只有高置信 AI submit / directory 信号进入 `keep`，其余可疑候选尽量进入 `flag` 供人工复核，并在 review 文件中标出原因。
- 输出文件：
  - `*.csv`
  - `*.xlsx`
  - `*.manifest.json`
  - `*.review.csv`（第二轮清洗时）

## Failure handling
- 缺少依赖时，先修环境，不要硬继续拼命重试业务命令。
- 缺少 `SerpApi` key 时：
  - 如果用户明确要真实 Google 结果，就要求补 key 或 `providers.toml`
  - 如果用户只是想验证流程，就切到 `static-json`
- 用户只要求第二轮清洗时，不要把问题扩展回第一轮抓取。

## Notes
- “网站创建时间”当前实现为域名注册时间，不是站点真实上线时间。
- `*.manifest.json` 会记录原始抓取数、抓取页数和停止原因，便于判断结果偏少是因为 Google 本身少、过滤过多，还是达到抓取上限。
- 第二轮清洗面向 AI submit 站点，默认采用“strict keep + wide flag”：`keep` 控制更严格，`flag` 覆盖更广；明显的文档、论坛、视频和社交页面会被排除到 review 文件里。
- 如果名单文件列名不固定，优先用 `--url-column`/`--domain-column` 明确指定；不指定时会自动扫描 `url/link/site/domain/website/submit` 相关列。
