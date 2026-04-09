# Google SERP Filter Skill

这个目录包含一个可在 Codex、Claude Code 等平台中使用的 skill，以及支撑它运行的本地 Python 实现。

它的目标是把 Google 搜索结果筛成可复核的候选站点列表，适合下面这类工作：

- 按搜索指令抓取 Google 结果
- 根据本地网站名单排除已经处理过的站点
- 导出首轮候选结果到 `csv/xlsx`
- 对首轮结果做第二轮规则清洗，保留更多候选并标记明显噪音

## 目录结构

- `serp-filter-skill/`
  AI skill 包本体，包含 `SKILL.md`、`agents/openai.yaml` 和参考文档。
- `src/serp_filter/`
  skill 背后的本地 Python 实现。
- `config/`
  示例配置（包含 `providers.example.toml`、`blocklist.example.toml`、`query-templates.txt`）。
- `private/`
  私有输入和私有配置，不应该提交真实凭据。
- `output/`
  默认输出目录。

## Skill 名称

- Skill 名称：`serp-filter-google-results`
- Codex UI 元数据：`serp-filter-skill/agents/openai.yaml`

## 在 Codex 中配置

推荐做法是把 `serp-filter-skill/` 作为一个独立 skill 目录链接到 `~/.codex/skills/` 下。

示例：

```bash
mkdir -p ~/.codex/skills
ln -s /absolute/path/to/search-for-web/serp-filter-skill \
  ~/.codex/skills/serp-filter-google-results
```

如果之前已经存在同名目录或链接，先删除旧的，再重新创建。

配置完成后：

1. 重启 Codex 会话
2. 确认新会话能识别 `serp-filter-google-results`
3. 在对话里使用 `$serp-filter-google-results` 触发

说明：

- 已经启动的旧会话通常不会自动刷新技能列表。
- `agents/openai.yaml` 用于 Codex 的技能列表和默认提示词展示。

## 在 Claude Code 中配置

Claude Code 一般从 `~/.claude/skills/` 读取 skill。

示例：

```bash
mkdir -p ~/.claude/skills
ln -s /absolute/path/to/search-for-web/serp-filter-skill \
  ~/.claude/skills/serp-filter-google-results
```

如果你不想用软链接，也可以直接复制整个 `serp-filter-skill/` 目录。

配置完成后建议重新打开 Claude Code 会话，再通过技能名称或自然语言任务触发。

## 本地运行前准备

### 1. Python 环境

在项目目录执行：

```bash
cd meizhao/search-for-web
python3 -m venv ../../.venv
../../.venv/bin/pip install -e ".[dev]"
```

如果仓库里已经有可复用的虚拟环境，可以直接使用现有环境。

### 2. Provider 配置

复制示例配置：

```bash
cp config/providers.example.toml private/providers.toml
```

编辑 `private/providers.toml`：

```toml
[serpapi]
api_key = "replace-with-your-serpapi-key"

[static_json]
data_path = "private/provider-data/example-results.json"
```

如果只做离线验证，可以只保留 `[static_json]`。

### 3. Query 模板文件

仓库内置了 `config/query-templates.txt`，用于 AI submit 场景的批量 query 模板。`run` 支持把模板文件和 `--query` / `--query-file` 合并后去重执行。

示例：

```bash
cd meizhao/search-for-web
PYTHONPATH=src ../../.venv/bin/python -m serp_filter run \
  --query-template-file config/query-templates.txt \
  --blocklist-file private/blocklists/ai-tool-submit-260327.xlsx \
  --provider static-json \
  --provider-config private/providers.toml \
  --output-prefix output/google-serp-template-replay
```

### 4. Blocklist 文件

示例参考：

```toml
path = "private/blocklists/ai-tool-submit-260327.xlsx"
sheet_name = "AI提交"
url_columns = ["Submit Link"]
```

## 使用方式

### 第一轮抓取：`run`

第一轮负责：

- 按 query 抓 Google 结果
- 排除 blocklist 中已出现的站点
- 分页抓取直到达到目标保留数或触发抓取上限
- 导出 `csv/xlsx/manifest`

示例：

```bash
cd meizhao/search-for-web
PYTHONPATH=src ../../.venv/bin/python -m serp_filter run \
  --query-file private/queries.txt \
  --query-template-file config/query-templates.txt \
  --blocklist-file private/blocklists/ai-tool-submit-260327.xlsx \
  --sheet-name "AI提交" \
  --url-column "Submit Link" \
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

说明：

- `--limit` 表示目标保留结果数，不是单页抓取数。
- `--page-size`、`--max-pages`、`--max-raw-results` 用于控制分页深度和成本。

### 第二轮清洗：`clean`

第二轮负责：

- 读取第一轮输出的 `csv/xlsx`
- 依据 URL、标题、摘要做规则分类
- 产出更适合人工复核的候选结果

示例：

```bash
cd meizhao/search-for-web
PYTHONPATH=src ../../.venv/bin/python -m serp_filter clean \
  --input-file output/google-serp-run.csv \
  --output-prefix output/google-serp-run-cleaned
```

`clean` 当前针对 AI submit 发现流程采用“strict keep + wide flag”策略：

- `keep`：只保留高置信提交页（例如同时具备 submit + AI/directory 信号）。
- `flag`：保留更宽口径的可疑候选，供人工复核。
- `drop`：明显噪音（文档、论坛、视频、社交等）进入 review，不进入候选结果。

第二轮输出：

- `*.csv`
  保留 `keep` 和 `flag` 两类候选
- `*.xlsx`
  和上面的候选结果一致
- `*.review.csv`
  包含全部记录、分类、决策和原因，适合复核
- `*.manifest.json`
  包含输入数、输出数、各类决策统计

### 离线回放：`static-json`

适合测试和本地调试：

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

## 在 Codex / Claude Code 中如何提需求

可以直接用自然语言，也可以显式提 skill 名称。

示例：

- `使用 $serp-filter-google-results 查询 intitle:"submit a tool" OR "add a tool"，排除我的名单文件，输出 50 条候选`
- `用 serp-filter-google-results 先抓一轮 Google 结果，再做第二轮清洗`

推荐在需求里明确：

- 查询语句
- blocklist 文件路径
- sheet 名
- URL 列名 / 域名列名
- 目标保留数
- 输出目录

## 常见问题

### 1. 为什么提示缺少 `SerpApi` key

真实 Google 查询依赖 `serpapi`。

如果报错类似：

```text
--provider-key is required for serpapi provider
```

说明以下两种方式都没有提供 key：

- `--provider-key`
- `private/providers.toml` 里的 `[serpapi].api_key`

### 2. 为什么之前测试不需要 `SerpApi`

因为测试分两类：

- 单元测试：用 fake session / fake response，不会联网
- 离线 CLI 测试：用 `static-json`，数据来自本地 JSON 文件

### 3. RDAP 超时会不会导致整次任务失败

当前版本不会。

如果 `rdap.org` 超时或返回异常，域名创建时间会降级为：

- `domain_created_at = None`
- `domain_created_source = rdap_error`

抓取和导出会继续完成。

### 4. 为什么新装的 skill 在当前 Codex 会话里看不到

通常是因为技能列表在会话启动时已缓存。

处理方式：

1. 确认 `~/.codex/skills/serp-filter-google-results` 已正确链接到 `serp-filter-skill/`
2. 重启 Codex 会话
3. 在新会话里重新查看技能列表

## 验证

项目测试：

```bash
cd meizhao/search-for-web
../../.venv/bin/python -m pytest -q
```

当前主流程覆盖：

- blocklist 读取
- `SerpApi` 分页抓取
- pipeline 抓取与导出
- RDAP 失败降级
- `clean` 子命令输出
