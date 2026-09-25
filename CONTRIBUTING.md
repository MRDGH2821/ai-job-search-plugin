# Contributing

Thanks for considering a contribution. Read this first: it explains what fits this project and what a pull request needs.

## Scope

ai-job-search-plugin is a Claude Code plugin marketplace. The core plugin (`plugins/ai-job-search-plugin/`) stays market-agnostic, person-agnostic and Claude Code-native. A contribution is judged by fit to that first, execution quality second.

**What fits:**

- Robustness and correctness fixes, with the failing case demonstrated.
- Features that make the workflow better for everyone, whatever their market.
- Docs that close real gaps.
- Infrastructure that reduces review burden, argued from a problem that exists.

**What doesn't:**

- **Market- or country-specific portals and data in the core plugin.** They belong in their own market plugin, like `plugins/danish-job-portals/`, which users install only if they need it.
- **Personal profile data.** The templates ship placeholders; CI enforces it (`placeholder-integrity`) and the repository ignores `profile/`.
- **Duplicate workflow sources.** The skills are the implementation; a second copy for another harness drifts from the first. Other harnesses use capa (`capa registry add MRDGH2821/ai-job-search-plugin`), untested outside Claude Code.
- **Kitchen-sink PRs.** One concern per PR.

## What a pull request needs

- **The failing case**, for fixes: how to reproduce it on the real path (the documented command, real portal output, an actual data file), not only on a hand-built input.
- **Tests.** Python tool and skill tests go in `tests/`; CLI tests in `plugins/<plugin>/skills/<name>/cli/tests/` (bun test, network-free where possible).
- **The checks CI runs, passing locally:**
  - `python3 -m unittest discover -s tests -t .`
  - `python3 tools/lint_skills.py`
  - `python3 tools/security_guards.py`
  - in touched CLIs: `bun run typecheck` and `bun test`
- **A version bump.** A change under `plugins/<name>/` bumps `version` in that plugin's `.claude-plugin/plugin.json`: Claude Code only updates installs when it changes. CI enforces it.
- **Reviewed permissions.** A new `allowed-tools` Bash entry in a skill needs its line in `ALLOWED_SKILL_TOOLS` in `tools/security_guards.py`, in the same PR. Plugins ship no hooks, MCP or LSP servers.
- **A CHANGELOG entry** under the top section.

## Practical notes

- **Portal-skill contract:** `search`/`detail` commands, `--format json|table|plain`, stderr JSON errors with exit 1, backoff on 429/5xx, zero runtime dependencies by default. See `/add-portal` and `linkedin-search` as the reference implementation.
- **Personal-use boundaries:** portal skills that touch ToS-restricted sources carry a prominent personal-use-only warning, and CI makes no live portal requests. Keep it that way.
- **LaTeX changes:** both templates in `plugins/ai-job-search-plugin/skills/job-tools/workspace-template/` must compile (`lualatex` for the CV, `xelatex` for the cover letter) and hold their exact page counts. CI compiles them in a freshly initialized workspace.
- **Workspace paths:** skills read and write workspace data relative to the current directory, never the plugin folder, and run commands as one command with no `cd` and no `&&`.

## Porting from the original project

This project was forked from the original ai-job-search. Improvements there are worth porting when they fit the scope above. `python3 tools/upstream_triage.py --remote upstream` maps upstream paths to this layout and prints a `git show` line per commit. Port the change by hand, credit the original commit in your commit message, and add the SHA to `.github/upstream-handled.txt` (`<sha>  # ported: <note>`). Rejected commits go there too (`# rejected: <reason>`).

Questions and proposals are welcome as issues.
