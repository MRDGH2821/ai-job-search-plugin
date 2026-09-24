# Independent project: ai-job-search-plugin (design)

Status: draft for review · Date: 2026-09-25 · Branch: `plugin/5-independent` (stacked on
`plugin/4-workspace-init`)

## Goal

Turn the fork `MRDGH2821/ai-job-search` into an independent project, `ai-job-search-plugin`,
where everything is managed through the plugin. The repository is plugin source only: users
install the plugin and create their workspace with `/init-workspace` in a private folder. The
fork keeps a way to see what the original author changes, so improvements can still be
ported.

## Decisions (made with the user)

| Decision | Choice |
|---|---|
| Independence | Drop upstream-compatibility tooling and migrations; own identity (author, URLs, funding, templates); rename |
| Name | `ai-job-search-plugin` everywhere: GitHub repo, marketplace, core plugin, command prefix, instruction markers |
| Danish plugin | Kept, name unchanged (`danish-job-portals`); author and URLs updated |
| Upstream tracking | Kept for porting: `upstream_triage.py` + the weekly watch issue, taught the new layout |
| Delivery | Branch `plugin/5-independent` off `plugin/4-workspace-init`, PR #5 on the fork; GitHub repo rename last, only after the user confirms |

## 1. Names and identity

| Thing | New value |
|---|---|
| GitHub repo | `MRDGH2821/ai-job-search-plugin` (`gh repo rename ai-job-search-plugin`, final step, after explicit confirmation; GitHub redirects the old URL) |
| Marketplace (`.claude-plugin/marketplace.json` `name`) | `ai-job-search-plugin` |
| Core plugin folder / `plugin.json` `name` | `plugins/ai-job-search-plugin/` / `ai-job-search-plugin` |
| Install id | `ai-job-search-plugin@ai-job-search-plugin`; Danish: `danish-job-portals@ai-job-search-plugin` |
| Command prefix | `/ai-job-search-plugin:<skill>` (short `/<skill>` still works) |
| Instruction markers | `<!-- ai-job-search-plugin:start vX -->` / `<!-- ai-job-search-plugin:end -->` |
| Author / owner | `MRDGH2821` in `plugin.json` (both plugins) and `marketplace.json` `owner` |
| homepage / repository | `https://github.com/MRDGH2821/ai-job-search-plugin` |
| `.github/FUNDING.yml` | removed (the original author's accounts); the user can add their own later |
| `.github/ISSUE_TEMPLATE/config.yml`, `PULL_REQUEST_TEMPLATE.md`, `SECURITY.md` | links point at this repo; fork-index and upstream-discussion links removed |
| `LICENSE` | keeps `Copyright (c) 2026 Mads Lorentzen` and adds `Copyright (c) 2026 MRDGH2821` |
| README | a "Credits" section: forked from MadsLorentzen/ai-job-search (MIT) |

`sync_instructions.py` recognizes the old `<!-- ai-job-search:start … -->` / `<!-- ai-job-search:end -->`
pair as the block to replace (treated exactly like the new markers) and writes the new markers,
so a workspace created by an earlier build upgrades on its next `/setup` or
`/sync-instructions`. Mixing one old and one new marker counts as malformed (exit 2).

## 2. Everything through the plugin

- **Removed from the repository root:** `cv/`, `cover_letters/`, `templates/`, `documents/`,
  `job_scraper/`, `company_research/`, `upskill/`. `plugins/ai-job-search-plugin/skills/job-tools/workspace-template/`
  is the only copy. The root-vs-template sync tests are deleted.
- **Root `.gitignore`:** development entries only (Python caches, `node_modules/`, `bun.lock`,
  build output, editor/OS files, `.superpowers/`, and personal-data guards that still make
  sense in a plugin repo: `profile/`, `salary_data.json`, `.env`, `.env.*`). The workspace
  privacy rules live in `gitignore.template` only.
- **`security_guards.py`:** `REQUIRED_IGNORE_RULES` and `ALLOWED_IGNORE_NEGATIONS` are checked
  against `gitignore.template` (the file that protects user data); the root `.gitignore` is
  checked for its own short required list (`profile/`, `salary_data.json`, `.env`).
- **Root `.claude/settings.json`:** unchanged in role (loads the plugins in place for
  development), marketplace/plugin names updated; `ALLOWED_MARKETPLACES`/`ALLOWED_PLUGINS`
  updated.
- **Root `AGENTS.md` and `CLAUDE.md`:** a contributor guide for working on the plugin (layout,
  how to run tests/lint/guards, conventions: one concern per PR, every permission reviewed,
  skills run commands as one command). `CLAUDE.md` stays `@AGENTS.md`. The managed workspace
  block is not used at the root; the repo-root sync test is removed.
- **CI (`.github/workflows/ci.yml`):**
  - The LaTeX smoke job runs `init_workspace.py --root "$RUNNER_TEMP/ws"` and compiles that
    workspace's `cv/main_example.tex` and `cover_letters/cover_example.tex` (also exercising
    init).
  - Placeholder integrity checks the template files: `workspace-template/cv/main_example.tex`,
    `workspace-template/cover_letters/cover_example.tex`, `profile-templates/candidate.md`,
    `profile-templates/evaluation.md`; plus "no `profile/` in the repository".
  - Every `if: github.repository == 'MadsLorentzen/ai-job-search'` condition is removed (the
    checks always run).
- **Tests** that read root workspace files switch to template paths through `tests/paths.py`
  (`WT` for the workspace template).

## 3. Upstream tracking (for porting)

- **Kept:** `tools/upstream_triage.py`, `.github/workflows/upstream-watch.yml` (weekly rolling
  issue), pointed at the `upstream` remote (`MadsLorentzen/ai-job-search`).
- **Path map** (`tools/upstream_paths.py`, one function `map_upstream_path(path: str) -> list[str]`; a list because `.gitignore` maps to two files):

  | Upstream path | This repository |
  |---|---|
  | `.claude/commands/<x>.md` | `plugins/ai-job-search-plugin/skills/<x>/SKILL.md` |
  | `.claude/skills/<s>/<rest>` | `plugins/ai-job-search-plugin/skills/<s>/<rest>` |
  | `.claude/agents/<a>` | `plugins/ai-job-search-plugin/agents/<a>` |
  | `.agents/skills/{jobbank,jobdanmark,jobindex,jobnet}-search/<rest>` | `plugins/danish-job-portals/skills/<same>/<rest>` |
  | `.agents/skills/<p>/<rest>` (other portals) | `plugins/ai-job-search-plugin/skills/<p>/<rest>` |
  | `tools/{rank_state,job_key,verify_pdf,verify_layout,robots_check,convert_salary_excel}.py`, `salary_lookup.py`, `tools/README_SALARY_TOOL.md` | `plugins/ai-job-search-plugin/skills/job-tools/scripts/<name>` |
  | `cv/…`, `cover_letters/…`, `templates/…`, `documents/…`, `job_scraper/…`, `company_research/…`, `upskill/…` | `plugins/ai-job-search-plugin/skills/job-tools/workspace-template/<same>` |
  | `.gitignore` | the same `workspace-template/gitignore.template` **and** `.gitignore` |
  | anything else (`tools/*`, `tests/*`, docs, CI) | the same path |

  Paths under `.claude/skills/job-application-assistant/` whose upstream file no longer exists
  here (`01-candidate-profile.md`, `02-behavioral-profile.md`) map to their profile templates
  (`profile-templates/candidate.md`, `behavioral.md`).
- **Triage uses the map:** a commit is "relevant" when any mapped path exists here. Each
  reported commit lists its touched files as `upstream → ours` plus one porting command:
  `git show <sha> -- <upstream paths>` (read it, then apply by hand to the mapped files).
- **Handled list:** `.github/upstream-wontport.txt` becomes `.github/upstream-handled.txt`;
  each line `<sha>  # ported|rejected: <note>`. Triage skips listed SHAs. A ported commit must be
  listed, because renames make the patch-id match fail.
- **Removed:** `tools/check_upstream_updates.py` and its tests (it depends on per-file version
  markers).

## 4. Versioning

- The per-file `framework_version` frontmatter is removed from every framework and template
  file, and from `AGENTS.md`. `tools/check_framework_version.py` and its tests are removed.
- The plugin `version` in `plugins/ai-job-search-plugin/.claude-plugin/plugin.json` is the
  version (Claude Code uses it to detect updates). This branch sets `2.0.0` for both plugins.
- A new test: every commit range that changes files under `plugins/<p>/` must also change that
  plugin's `plugin.json` `version`, checked against `GITHUB_BASE_REF` (or skipped locally with
  no base), in `tests/test_plugin_version.py`.
- `agents-block.md` keeps its own `framework_version` only as the marker version source; it is
  renamed to `version:` in its frontmatter.

## 5. Removed upstream-compatibility paths

- `/setup`: the `#### Legacy fork migration` subsection, its call in Step 0a, the
  template-pollution check, and the tests that pin them.
- SETUP.md sections 8 ("Pulling upstream updates"), 9 and 10 (fork upgrades); the
  public-fork/private-remote warning in `/setup` Step 0b is rewritten for "your workspace
  folder" (still warns before writing personal data into a public repository).
- CONTRIBUTING.md rewritten for this project (see Section 6).
- `.github/upstream-wontport.txt` (renamed, Section 3).

## 6. Docs

- **README:** what it is; install (`/plugin marketplace add MRDGH2821/ai-job-search-plugin`,
  `/plugin install ai-job-search-plugin@ai-job-search-plugin`, optional Danish plugin); first
  run (`/init-workspace` in a private folder, then `/setup`); command list; capa (untested
  outside Claude Code); developing the plugin (clone, trust, tests); tracking the original
  project (upstream triage); credits.
- **SETUP.md:** prerequisites (Claude Code, Python 3, LaTeX, Bun), install, first run, salary
  data, troubleshooting.
- **CONTRIBUTING.md:** scope, one concern per PR, required checks (tests, lint, guards,
  version bump), permission changes need an allowlist entry, market-specific portals belong in
  their own market plugin.
- **CHANGELOG:** new top section `## [2.0.0] - Unreleased` — "Independent project, renamed
  ai-job-search-plugin; forked from MadsLorentzen/ai-job-search v1.7.1"; older entries kept.

## 7. Tests

- Renames: every test path goes through `tests/paths.py` (`PLUGIN`, `SKILLS`, `WT`, …). A
  test asserts that no tracked file contains `ai-job-search@ai-job-search`,
  `plugins/ai-job-search/` or `<!-- ai-job-search:start`, and that `MadsLorentzen` appears only
  in this allowlist: `LICENSE`, `README.md`, `SETUP.md` (upstream-tracking section),
  `CHANGELOG.md`, `docs/superpowers/**`, `tools/upstream_triage.py`, `tools/upstream_paths.py`,
  `.github/workflows/upstream-watch.yml`, `.github/upstream-handled.txt`, `tests/**`.
  `sync_instructions.py` may contain the legacy marker string (it recognizes it).
- Root is not a workspace: `cv/`, `cover_letters/`, `templates/`, `documents/`,
  `job_scraper/`, `company_research/`, `upskill/` do not exist at the root.
- `upstream_paths.map_upstream_path` table test (every row above); triage marks a commit that
  touches `.claude/commands/apply.md` as relevant and prints the mapped path; handled-list
  parsing.
- `sync_instructions.py`: old markers are replaced by new ones; a mixed old/new pair exits 2.
- Plugin version bump test (Section 4).
- Existing suites keep passing with renamed paths.

## Out of scope

- Detaching the GitHub fork network (the user did not choose it).
- Changing what any workflow does for users.

## Risks

- **Renaming the GitHub repo** changes the install URL. GitHub redirects the old URL, and the
  README names only the new one. Done last, after confirmation.
- **Stacked PRs #1–#4** still say `ai-job-search`; PR #5 renames. Merging them in order is
  unaffected.
- **Porting upstream changes gets manual** once paths differ; the path map and the handled
  list keep it tractable.
