# PR Title

feat: harden serp filter workflow and add human-facing skill docs

# PR Body

## Summary

This PR upgrades the Google SERP filtering skill from a basic fetch-and-export flow into a more usable multi-platform workflow for Codex / Claude Code users.

It adds repository-level setup and usage docs, keeps the AI-facing skill package lean, and improves the underlying filtering workflow with safer domain-date enrichment and a second-pass cleaning step.

## What Changed

- added a root `README.md` with:
  - project overview
  - Codex skill installation instructions
  - Claude Code skill installation instructions
  - local setup steps
  - `run` / `clean` / `static-json` usage examples
  - troubleshooting notes for SerpApi keys, RDAP fallback, and skill discovery
- added `PR.md` with reusable PR copy
- hardened RDAP enrichment:
  - RDAP timeouts and request failures no longer abort the whole run
  - failures now degrade to `rdap_error`
- added second-pass cleaning workflow:
  - new `clean` subcommand
  - rule-based classification for likely submission candidates vs. docs/forums/social/noise
  - review outputs for human validation
- updated skill package metadata and usage instructions:
  - refreshed `serp-filter-skill/SKILL.md`
  - refreshed `serp-filter-skill/agents/openai.yaml`

## Why

Before this change:

- human users had no repo-level documentation for installing and using the skill in Codex / Claude Code
- RDAP failures could break a full run
- the workflow stopped at first-pass Google filtering, which still left a lot of noise for manual review

After this change:

- the repository is self-explanatory for human operators
- first-pass fetch is more robust
- second-pass cleaning produces reviewable candidate outputs instead of a flat untriaged list

## Testing

Ran:

```bash
../../.venv/bin/python -m pytest -q
```

Result:

```text
14 passed
```

## Notes

- `serp-filter-skill/SKILL.md` remains focused on AI runtime guidance
- human-facing platform setup lives in the repo `README.md`
- Codex users should restart the session after adding the skill link so the new skill is discoverable
