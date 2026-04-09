# AI Submit Sites Optimization Design

> Goal: Optimize the Google SERP filtering skill for AI tool submission sites, adding query templates and stricter keep/flag/drop logic.

## Summary
We will optimize the SERP filtering workflow to prioritize AI tool submission sites. The changes add a query template file, merge templates with user-provided queries, and strengthen second-pass cleaning into a strict keep + wide flag strategy. Output remains reviewable with explicit classification and decision reasons.

## Goals
- Prioritize "submit your AI tool" sites and directories
- Keep results in a layered output: keep / flag / drop
- Make query templates reusable and editable outside code
- Preserve current pagination, blocklist filtering, and RDAP fallback behavior

## Non-Goals
- No HTML scraping or live submission form validation (can be future work)
- No model-based classification
- No dependency on external APIs beyond existing SerpApi + RDAP

## User Experience
### First Pass: `run`
- Accept `--query`, `--query-file`, and new `--query-template-file`
- Merge all queries, de-duplicate, then execute
- Output: `.csv`, `.xlsx`, `.manifest.json`

### Second Pass: `clean`
- Rule-based classification and decision
- Outputs:
  - `.csv` + `.xlsx`: only `keep` + `flag`
  - `.review.csv`: full set with classification and decision
  - `.manifest.json`: counts of decision + classification

## Query Templates
Add `config/query-templates.txt`:
- One query per line
- Default templates target AI submission intent, e.g.:
  - `intitle:"submit a tool" (AI OR "AI tool" OR "AI tools" OR LLM)`
  - `"submit your AI tool" OR "submit your tool" "AI directory"`
  - `"add your AI tool" "directory" OR "AI tools directory"`
  - `"list your AI tool" "AI tools"`

CLI behavior:
- If user provides only template file, use it as the query set
- If user provides queries + template file, merge and de-duplicate

## Cleaning Rules (AI-submit optimized)
Priority order:
1. **Drop obvious noise**
   - Social/video: YouTube, X/Twitter, TikTok, etc.
   - Forums/communities: forum/community/idea-exchange/discourse
   - Docs/support: /docs/, help, manual, support, tutorials, vendor docs

2. **Submission pages**
   - Strong submit signals: `submit`, `add`, `list your tool`, `tool-submit`, `submit your tool`
   - If submit signal + AI/directory signals -> `keep`
   - If submit signal only -> `flag`

3. **Catalog/resource pages**
   - Signals: directory, catalog, toolbox, library, database, resource, guide
   - No submit signal -> `flag`

4. Everything else -> `drop`

Default policy: **keep strict, flag wide**, per user preference.

## Data Structures / Outputs
- Keep existing row fields
- Append:
  - `classification`
  - `decision`
  - `review_reason`

## Tests
- `clean`:
  - submit + AI/directory -> keep
  - submit only -> flag
  - docs/community/video -> drop
- `run`:
  - query templates merge + de-dup
- Regression: pagination, RDAP fallback, export formats

## Files to Modify / Add
- Add: `config/query-templates.txt`
- Update: `src/serp_filter/cli.py`
- Update: `src/serp_filter/cleaner.py`
- Update: `serp-filter-skill/SKILL.md`
- Update: `README.md`

## Risks
- Rule-based classification still imperfect. Kept/flagged results require review.
- Query template quality determines recall/precision balance.

## Future Work
- Optional HTML verification of submission form presence
- Optional allowlist/denylist file support for cleaning
