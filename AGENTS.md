# ai-job-search-plugin: contributor guide

This file is for working on the plugin. Your job-search workspace is a separate folder:
create one with `/init-workspace`, and its own `AGENTS.md` is written by `/sync-instructions`.

## Working on this plugin

This repository is a Claude Code plugin marketplace, not a workspace.

- `plugins/ai-job-search-plugin/` - the core plugin: skills (one folder per command or
  workflow), the research agent, and `skills/job-tools/` (helper scripts, the managed
  `AGENTS.md` block in `scripts/agents-block.md`, and `workspace-template/`).
- `plugins/danish-job-portals/` - Danish job-portal search skills (off by default).
- `plugins/ai-job-search-plugin/skills/job-tools/workspace-template/` - the only copy of the
  workspace files (`cv/`, `cover_letters/`, `documents/`, the privacy `gitignore.template`).
  Never add workspace files at the repository root.
- `tools/` - repository checks and upstream triage; `tests/` - the test suite.

Open Claude Code here and accept the folder-trust prompt: `.claude/settings.json` then loads
both plugins in place from `plugins/`. To try the workflow, run `/init-workspace` in a
separate, empty folder.

## Checks

Run all three before a PR:

- `python3 -m unittest discover -s tests -t .`
- `python3 tools/lint_skills.py`
- `python3 tools/security_guards.py`

## Conventions

- One concern per PR.
- A change under `plugins/<name>/` bumps that plugin's `version` in
  `.claude-plugin/plugin.json`; Claude Code only updates installs when it changes.
- Every permission is reviewed: a new `allowed-tools` Bash entry needs its line in
  `ALLOWED_SKILL_TOOLS` in `tools/security_guards.py`.
- A skill that runs a command says to run it as one command, with no `cd` and no `&&`.
- Workspace data is always read and written relative to the current directory, never the
  plugin folder. Candidate facts come from the workspace's `profile/`; never invent them.
- When a CV or cover letter mentions agentic coding or AI tooling, name Claude Code explicitly.

## Tracking the original project

This project was forked from the original ai-job-search (see README Credits). To see what
changed there, run `python3 tools/upstream_triage.py --remote upstream`; it maps upstream paths to this layout.
Record each upstream commit you port or reject in `.github/upstream-handled.txt`.
