---
name: job-tools
description: Helper scripts used by the ai-job-search skills - tracker state, job keys, PDF checks, robots.txt check, salary lookup. Not for direct use.
user-invocable: false
---

# job-tools

`${CLAUDE_SKILL_DIR}` is this skill's folder. If your tool does not expand it, read paths as relative to the folder containing this SKILL.md.

Every script runs from the workspace root (the folder holding `profile/`) and reads and writes workspace files there.

| Script | Used by | Usage |
|---|---|---|
| `scripts/rank_state.py` | `/rank`, `/outcome`, `/gmail-sync` | `python3 ${CLAUDE_SKILL_DIR}/scripts/rank_state.py --help` |
| `scripts/job_key.py` | `/scrape` | `python3 ${CLAUDE_SKILL_DIR}/scripts/job_key.py --help` |
| `scripts/verify_pdf.py` | `/apply` | `python3 ${CLAUDE_SKILL_DIR}/scripts/verify_pdf.py <pdf> --pages N` |
| `scripts/verify_layout.py` | `/apply` | `python3 ${CLAUDE_SKILL_DIR}/scripts/verify_layout.py <pdf>` |
| `scripts/robots_check.py` | `job-application-assistant` (web research) | `python3 ${CLAUDE_SKILL_DIR}/scripts/robots_check.py --help` |
| `scripts/salary_lookup.py` | `/apply` | `python3 ${CLAUDE_SKILL_DIR}/scripts/salary_lookup.py "<Company>" --json` (reads `salary_data.json` in the workspace root; see `scripts/README_SALARY_TOOL.md`) |
| `scripts/init_workspace.py` | `/init-workspace`, `/setup` | `python3 ${CLAUDE_SKILL_DIR}/scripts/init_workspace.py` (copies missing files from `workspace-template/` into the workspace root; never overwrites) |
| `scripts/sync_instructions.py` | `/sync-instructions`, `/setup` | `python3 ${CLAUDE_SKILL_DIR}/scripts/sync_instructions.py [--check]` (writes `AGENTS.md`/`CLAUDE.md` in the workspace root; template: `scripts/agents-block.md`) |
| `scripts/convert_salary_excel.py` | you, once | `python3 ${CLAUDE_SKILL_DIR}/scripts/convert_salary_excel.py <file.xlsx>` |
