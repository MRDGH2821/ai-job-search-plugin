# Plugin layout (design)

Status: draft for review · Date: 2026-09-24 · Branch: `plugin/2-plugin-layout` (stacked on
`plugin/1-profile-separation`)

Roadmap and shared decisions: `docs/superpowers/specs/2026-09-24-plugin-profile-separation-design.md`
("Roadmap", "Portability across harnesses (capa)"). This spec designs step 2 of that roadmap.

## Goal

Move the whole framework into a Claude Code plugin marketplace **without a second copy**:
one plugin tree that both the clone (loaded in place) and plugin installs (copied to a
cache) run. It also has to survive capa's verbatim copy into other harnesses, which means
following the hybrid portability rule.

## Decisions (made with the user during brainstorming)

| Decision | Choice |
|---|---|
| Command packaging | Convert all 12 commands into skills (`skills/<name>/SKILL.md`) |
| Plugin split | Core plugin `ai-job-search` + market plugin `danish-job-portals` |
| Names | Marketplace `ai-job-search`; install id `ai-job-search@ai-job-search` |
| Script home | One non-user-invocable skill `job-tools` holding every runtime script |
| Shipped portals | Move into the plugins; `.agents/skills/` keeps only user-generated portals |

## Verified platform facts (probes run 2026-09-24, Claude Code 2.1.280)

| Fact | How it was checked |
|---|---|
| A plugin skill is invocable as `/<name>` and as `/<plugin>:<name>`; `$ARGUMENTS` is substituted | Headless probe `/greet Ada` → `HELLO-Ada-END` |
| `disable-model-invocation: true` and `user-invocable: false` are accepted in plugin skills | `claude plugin details` lists both skills |
| `${CLAUDE_SKILL_DIR}/../job-tools/scripts/t.py` works in a skill body **and** grants permission when written the same way in `allowed-tools` | Headless run with only `Skill` allowed → `TOOLS_OK` |
| A skill from plugin B loaded through the Skill tool by a skill in plugin A grants B's own `allowed-tools` | Two `--plugin-dir` probe, only `Skill` allowed → `PORTAL_OK` |
| Bun auto-install fails for the Danish CLIs without `node_modules` (resolves a newer `@bunli/runtime` that needs React) | `bun run src/cli.ts --help` in a copy without `node_modules` |
| `salary_lookup.py` reads `salary_data.json` from the script's own directory | `DATA_FILE = Path(__file__).parent / "salary_data.json"` |
| Commands have no frontmatter today; they run under session permissions (the `settings.json` allowlist plus prompts) | `head -1 .claude/commands/*.md` |

## Target layout

```
.claude-plugin/marketplace.json     name "ai-job-search"; plugins:
                                      ai-job-search       source ./plugins/ai-job-search
                                      danish-job-portals  source ./plugins/danish-job-portals
plugins/ai-job-search/
  .claude-plugin/plugin.json
  agents/gemini-research-expert.md
  skills/
    job-application-assistant/      03-10 + SKILL.md + profile-templates/   (from .claude/skills)
    job-scraper/                    skill name stays `scrape`                (from .claude/skills)
    upskill/                                                                  (from .claude/skills)
    add-portal/ add-template/ apply/ expand/ gmail-sync/ html-report/
    interview/ notion-sync/ outcome/ rank/ reset/ setup/                      (from .claude/commands)
    job-tools/                      SKILL.md (user-invocable: false) + scripts/:
                                      rank_state.py job_key.py verify_pdf.py verify_layout.py
                                      robots_check.py salary_lookup.py convert_salary_excel.py
                                      README_SALARY_TOOL.md
    linkedin-search/ freehire-search/                                         (from .agents/skills)
plugins/danish-job-portals/
  .claude-plugin/plugin.json
  skills/jobbank-search/ jobdanmark-search/ jobindex-search/ jobnet-search/  (from .agents/skills)
.claude/settings.json               extraKnownMarketplaces + enabledPlugins (both) + remaining allowlist
.agents/skills/README.md            "/add-portal writes your own portals here"
tools/                              dev/CI only: lint_skills, security_guards, check_framework_version,
                                    check_upstream_updates, upstream_triage
```

`.claude/commands/` and `.claude/skills/` no longer exist. The clone loads both plugins in
place once the folder is trusted:

```json
{
  "extraKnownMarketplaces": { "ai-job-search": { "source": { "source": "directory", "path": "./" } } },
  "enabledPlugins": { "ai-job-search@ai-job-search": true, "danish-job-portals@ai-job-search": true }
}
```

## Converting commands to skills

For each `.claude/commands/<x>.md` → `plugins/ai-job-search/skills/<x>/SKILL.md`:

- Add frontmatter:
  - `name: <x>`
  - `description:` the command's title text after `# /<x> - ` plus one "Use when the user runs `/<x>`" sentence.
  - `argument-hint:` for the 10 commands whose body reads `$ARGUMENTS` (all except `expand` and `html-report`).
  - `disable-model-invocation: true` on all 12. Only the user triggers them, as today, and their descriptions stay out of every session's context.
  - `allowed-tools:` exactly the script and CLI calls this skill makes that today's `settings.json` pre-approves, rewritten to the new path form (see below). Nothing else: tools that prompt today still prompt.
- Keep the body, including its `# /<x> - …` title, byte-for-byte except for the path rewrites below.

## Path rules

1. **Workspace data** (`profile/`, `cv/`, `cover_letters/`, `documents/`, `job_scraper/`,
   `job_search_tracker.csv`, `company_research/`, `upskill/`, `reports/`, `templates/`,
   `gmail_sync/`) stays relative to the current directory. No change.
2. **Anything inside the plugin** is referenced relative to the calling skill:
   `${CLAUDE_SKILL_DIR}/../<skill>/<file>`. Examples:
   - `python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/rank_state.py …`
   - `${CLAUDE_SKILL_DIR}/../job-application-assistant/04-job-evaluation.md`
   - `/setup` copies from `${CLAUDE_SKILL_DIR}/../job-application-assistant/profile-templates/`
   - A file in the skill's own folder: `${CLAUDE_SKILL_DIR}/<file>`
3. Every skill that uses rule 2 carries this line once, near the top: *"`${CLAUDE_SKILL_DIR}`
   is this skill's folder. If your tool does not expand it, read paths as relative to the
   folder containing this SKILL.md."*
4. Files inside `job-application-assistant/` that name siblings in the same folder
   (`04-job-evaluation.md` naming `09-web-research.md`) keep bare names. They sit in the
   same folder, which is how today's text already reads them.
5. `salary_lookup.py` reads `salary_data.json` from the **current directory** (the
   workspace), not from its own folder. In a clone the two are the same place. Its error
   message and `README_SALARY_TOOL.md` say so.

## Portals

- A plugin portal's `SKILL.md` runs its CLI as `bun run ${CLAUDE_SKILL_DIR}/cli/src/cli.ts …`
  and lists that exact form in its own `allowed-tools`.
- The four Danish portals add a first step: *"If `${CLAUDE_SKILL_DIR}/cli/node_modules` is
  missing, run `bun install --cwd ${CLAUDE_SKILL_DIR}/cli` first."*, also in `allowed-tools`.
  This repeats automatically after each plugin update (a fresh cache folder).
- `/scrape` (the `job-scraper` skill) discovers portals in two places:
  1. Plugin portals: load every available skill whose name ends in `-search` with the Skill
     tool, and use the CLI usage it returns. Verified to grant each portal's permissions
     across plugins.
  2. The user's own portals: read `.agents/skills/*/SKILL.md` in the workspace directly, as
     today, with the existing `Bash(bun run .agents/skills/*/cli/src/cli.ts *)` permission.
- `/add-portal` keeps writing to the workspace `.agents/skills/<name>/`. Its "canonical
  reference" becomes `${CLAUDE_SKILL_DIR}/../linkedin-search/`.
- `.gitignore`: add `plugins/**/node_modules/` next to `.agents/**/node_modules/`.

## job-tools skill

`plugins/ai-job-search/skills/job-tools/SKILL.md`, `user-invocable: false`, with a short
description ("Helper scripts used by the ai-job-search skills: tracker state, job keys, PDF
checks, robots.txt check, salary lookup") and one section per script giving its CLI usage.
Scripts move with `git mv` and keep their names.

## Permissions

- `.claude/settings.json` keeps only entries not tied to a moved script:
  `Skill(job-application-assistant)` and `Bash(pdftotext:*)`. Every `tools/…`,
  `salary_lookup.py` and `.agents/skills/<shipped portal>` entry moves into the
  `allowed-tools` of the skill that makes the call. The plan's first task verifies whether
  `Skill(job-application-assistant)` matches the namespaced plugin skill; if not, the entry
  becomes `Skill(ai-job-search:job-application-assistant)`.
- `security_guards.py` keeps reviewing permissions where they now live. A new check reads
  every `plugins/*/skills/*/SKILL.md` `allowed-tools` value and fails on any `Bash(...)` entry
  not in a reviewed `ALLOWED_SKILL_TOOLS` allowlist. The existing `settings.json` check stays.
  The package-manifest check also globs `plugins/**/package.json`.

## Tooling, CI and tests

- `tests/paths.py` (new): `REPO`, `PLUGIN = REPO/"plugins"/"ai-job-search"`, `SKILLS = PLUGIN/"skills"`,
  `FW = SKILLS/"job-application-assistant"`, `TPL = FW/"profile-templates"`,
  `JOB_TOOLS = SKILLS/"job-tools"/"scripts"`, `MARKET = REPO/"plugins"/"danish-job-portals"`,
  `skill(name) -> Path`. Every path-coupled test imports from it.
- `lint_skills.py`:
  - Globs `plugins/*/skills/*/SKILL.md` and workspace `.agents/skills/*/SKILL.md`.
  - The "`# /<name>` title" rule applies to skills with `disable-model-invocation: true`.
  - `allowed-tools` globs are resolved with `${CLAUDE_SKILL_DIR}` expanded to the skill's folder.
- `check_framework_version.py` and `check_upstream_updates.py`: new `FW` path.
- `ci.yml`:
  - The portal CLI discovery job finds `plugins/*/skills/*-search/cli`.
  - Placeholder checks use the new template paths.
  - Tool tests import scripts from `JOB_TOOLS`.
- New `tests/test_plugin_layout.py`:
  - `marketplace.json` lists exactly the two plugins with existing sources.
  - Each `plugin.json` name matches its marketplace entry.
  - `.claude/commands` and `.claude/skills` do not exist.
  - All 12 converted skills exist with `disable-model-invocation: true` and a `# /<name>` title.
  - No skill text references `.claude/commands/`, `.claude/skills/`, `tools/<runtime script>`,
    or a root-level `salary_lookup.py`.
  - Every `${CLAUDE_SKILL_DIR}/../<skill>/<path>` reference resolves to an existing file.
  - `.claude/settings.json` enables both plugins.
- `framework_version`: bump every moved `job-application-assistant` file whose text changed.
  Bump `AGENTS.md` too.

## Docs

- README:
  - File-structure tree.
  - Install: clone (trust the folder once), or `/plugin marketplace add MadsLorentzen/ai-job-search` + `/plugin install ai-job-search@ai-job-search` (workspace init arrives in branch 4).
  - A "Using other harnesses (capa)" section: `capa registry add MadsLorentzen/ai-job-search`, marked **untested outside Claude Code**.
- SETUP.md, new section "Upgrading across the plugin layout change":
  - Trust the folder once.
  - Your edits to `.claude/commands/<x>.md` now live in `plugins/ai-job-search/skills/<x>/SKILL.md` (git follows the rename).
  - Turn off `danish-job-portals` in `.claude/settings.local.json` if you don't need it.
- AGENTS.md and CONTRIBUTING:
  - Portals are installable into other runtimes through capa, not auto-discovered from `.agents/skills/`.
  - `.agents/skills/` is where `/add-portal` writes.
- CHANGELOG `### Changed` entry, marked `BREAKING (forks)`.

## Out of scope

- The instruction-sync skill (branch 3) and the workspace init command (branch 4).
- Testing other harnesses through capa.
- Any change to what the workflows do.

## Risks

- **Untrusted clone loads nothing.** Plugins declared in project settings only load after
  the folder is trusted. Mitigation: README and SETUP say so on the first step; headless
  `-p` runs in CI never need the plugins.
- **Skill discovery by name suffix.** A third-party skill named `*-search` would be loaded by
  `/scrape`. Mitigation: `/scrape` uses only skills whose SKILL.md documents a
  `cli/src/cli.ts` command, and states which portals it used.
- **Bun install at first use** needs network access on the first scrape after an update.
- **`allowed-tools` review drift.** Mitigated by the new `security_guards.py` check.
