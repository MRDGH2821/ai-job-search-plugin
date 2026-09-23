# Claude Code plugin conversion: roadmap and profile separation (design)

Status: draft for review · Date: 2026-09-24 · Branch: `plugin/1-profile-separation`

## Goal

Make ai-job-search installable as a Claude Code plugin **without a second copy of the
workflow specs**, while keeping the current fork-and-clone workflow working. The same
work also removes the reason personalized forks conflict on every upstream merge:
personal data is written into files upstream also edits.

Constraints taken from `CONTRIBUTING.md`:

- **No duplicate workflow sources.** Previous PRs were declined for this (#44, #49, #66).
  The plugin and the clone must run the same files.
- **One concern per PR.** The work is delivered as a stack of branches in the fork.
  Each PR targets the branch before it, so each diff can be reviewed on its own.
- **Person-agnostic upstream.** Upstream ships placeholders only (`placeholder-integrity`).

## Verified platform facts

These were tested in this session, or taken from the docs where noted:

| Fact | How it was checked |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}` is substituted inside plugin **skill and command** markdown; `${CLAUDE_SKILL_DIR}` inside skills | Headless probe plugin |
| `allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/t.py:*)` in a plugin skill grants that command | Headless run with only `Skill` allowed; script ran |
| A local-directory marketplace with a relative `./plugins/x` source loads the plugin **in place** (not copied) | Docs, plugin-marketplaces |
| A plugin installed from GitHub is **copied** to a cache; `../` paths outside the plugin directory are not available | Docs |
| Project `.claude/settings.json` `extraKnownMarketplaces` and `enabledPlugins` apply only after the folder is trusted | Docs, settings; a headless `-p` run in an untrusted folder did not load the plugin |
| Custom `agents` paths in `plugin.json` did not load an agent; the default `agents/` directory did | `claude plugin details` probe |

## Roadmap (stacked branches)

```
master
 └─ plugin/1-profile-separation   ← this spec
     └─ plugin/2-plugin-layout
         └─ plugin/3-workspace-init
```

1. **`plugin/1-profile-separation`** (this spec). Move all user data out of framework
   files into a workspace `profile/` folder, and ship a `/setup` migration for existing
   personalized forks. No files move between `.claude/` and a plugin tree yet. This PR
   is useful on its own: upstream merges into personalized forks stop conflicting.
2. **`plugin/2-plugin-layout`** (later spec). Move `.claude/{commands,skills,agents}`,
   the shipped portal skills and the runtime tools (`tools/{rank_state,job_key,verify_pdf,verify_layout,robots_check}.py`,
   `salary_lookup.py`) into `plugins/ai-job-search/`. Rewrite paths to
   `${CLAUDE_PLUGIN_ROOT}` and move permissions into per-skill and per-command
   `allowed-tools`. Add `.claude-plugin/marketplace.json` at the repo root. The clone
   loads the plugin in place through `.claude/settings.json`
   (`extraKnownMarketplaces` with a `directory` source of `./`, plus `enabledPlugins`).
   Retarget `lint_skills.py`, `security_guards.py`, `check_framework_version.py`,
   `check_upstream_updates.py` and CI. `/scrape` discovers portals in both
   `${CLAUDE_PLUGIN_ROOT}/portals/*` and the workspace `.agents/skills/*` (where
   `/add-portal` writes).
3. **`plugin/3-workspace-init`** (later spec). A plugin command that turns the current
   folder into a workspace. It copies the workspace template (from
   `profile-templates/`, `cv/main_example.tex`, `cover_letters/cover.cls`,
   `cover_letters/OpenFonts/`, the `documents/` tree and a personal-data `.gitignore`),
   offers `git init`, writes the workspace settings, and hands over to `/setup`. It
   reuses the templates from branch 1, so no second copy is created.

The uncommitted thin-wrapper `.claude-plugin/` manifests from the earlier exploration
are superseded by branch 2. They are not part of branch 1.

## Branch 1 design: profile separation

### Where user data is written today

`/setup`, `/expand` and `/add-template` currently write into framework files:

| Framework file | User regions |
|---|---|
| `01-candidate-profile.md` | Whole file |
| `02-behavioral-profile.md` | Whole file |
| `03-writing-style.md` | `## Patterns Observed in Past Applications` (Path A) |
| `04-job-evaluation.md` | Strong/Moderate/Weak skill match areas; Strong/Moderate/Entry-level experience; career goals; energizing and draining tasks; life-situation lines; the permit hours/start-date second gate under Eligibility; `## Calibration from Past Applications` |
| `05-cv-templates.md` | Contact block and `pdftitle` in the LaTeX template; profile statement templates (including Path A `[Used for: …]` extracts); `ACTIVE-TEMPLATE` block |
| `06-cover-letter-templates.md` | `\namesection` contact line and `\signature`; Path A opening, bullet and closing patterns; `ACTIVE-TEMPLATE` block |
| `07-interview-prep.md` | `## Ready-Made STAR Examples`; `## STAR Candidates (Complete Manually)` |
| `job-scraper/search-queries.md` | Nearly the whole file |
| `CLAUDE.md` | Candidate profile summary. It also holds framework rules (workflow and verification checklist) |

### Target layout

```
.claude/skills/job-application-assistant/
  01..09-*.md, SKILL.md       framework only: rules, no [YOUR_*] tokens, never written by commands
  profile-templates/          NEW, framework-owned: the only pristine copy of each profile file
    candidate.md behavioral.md writing-patterns.md evaluation.md
    cv.md cover-letter.md star.md search-queries.md
profile/                      NEW, workspace-owned, not tracked upstream
  (the same 8 files, created from profile-templates/ by /setup, edited only by commands)
CLAUDE.md                     candidate summary + Role + Repo Structure + pointer to profile/
cv/main_example.tex           unchanged (tracked placeholders, personalized by /setup)
cover_letters/cover_example.tex  unchanged
```

`01-candidate-profile.md` and `02-behavioral-profile.md` have no framework content left
once their data moves. They are **deleted**, and `profile-templates/candidate.md` and
`profile-templates/behavioral.md` replace them. `search-queries.md` moves from
`job-scraper/` to `profile-templates/search-queries.md`. The template keeps its
structure notes (query categories, filters, "Adapting Queries") as HTML comments, so
the framework guidance travels with the file.

### Mapping: old region → new home

| Old region | New home |
|---|---|
| `01-candidate-profile.md` (all) | `profile/candidate.md`. Sections unchanged: Identity (incl. Languages), Education, Professional Experience, Independent Projects, Technical Skills, Publications, Awards, References |
| `02-behavioral-profile.md` (all) | `profile/behavioral.md` |
| `03` § Patterns Observed in Past Applications | `profile/writing-patterns.md` |
| `04` skill match, experience, goals, motivation, life-situation lines | `profile/evaluation.md` § Skill Match Areas, § Experience Areas, § Career Goals, § Motivation, § Life Situation |
| `04` permit second gate | `profile/evaluation.md` § Eligibility Constraints |
| `04` § Calibration from Past Applications | `profile/evaluation.md` § Calibration |
| `05` contact block, `pdftitle` | **Not stored twice.** The template in `05` keeps its tokens and states: fill them from `profile/candidate.md` § Identity at draft time. `/setup` Steps 3.5 and 3.6 no longer edit contact data in `05`/`06` |
| `05` profile statements and `[Used for:]` extracts | `profile/cv.md` § Profile Statements |
| `05` ACTIVE-TEMPLATE | `profile/cv.md` § Active Template (same BEGIN/END markers) |
| `06` contact line and signature | Same as `05`: tokens stay, filled from `profile/candidate.md` at draft time |
| `06` extracted patterns | `profile/cover-letter.md` § Patterns From Past Letters |
| `06` ACTIVE-TEMPLATE | `profile/cover-letter.md` § Active Template |
| `07` Ready-Made STAR Examples, STAR Candidates | `profile/star.md` |
| `search-queries.md` | `profile/search-queries.md` |
| `CLAUDE.md` § Workflow for New Job Applications, § Verification Checklist | `job-application-assistant/10-verification.md` (new, framework-owned, versioned), linked from `SKILL.md` and `/apply` |

In each framework file, the place where the data used to be gets a one-line pointer
such as: *"Score against `profile/evaluation.md` § Skill Match Areas."* The pointer
names a heading, so a reader can find it and the tests can check it.

### Command changes

| Command / skill | Change |
|---|---|
| `/setup` | New Step 0a: if `profile/` is missing, run legacy detection (below); otherwise copy `profile-templates/*` to `profile/`. Path A/B/C and Step 3 write to `profile/*.md` using the mapping table. Steps 3.5 and 3.6 lose their contact-block edits. Step 3.9 targets `profile/search-queries.md`. Step 4's summary lists `profile/` files |
| `/reset profile` | Replace each `profile/*.md` with its `profile-templates/` counterpart after the existing confirmation gate. Reset `CLAUDE.md` and `cv/main_example.tex` as today. Delete the embedded skeletons and the token-restore tables |
| `/expand` | Writes to `profile/candidate.md` |
| `/add-template` | Reads and writes the Active Template section in `profile/cv.md` / `profile/cover-letter.md` |
| `/apply` | Resolves the active template from `profile/cv.md` / `profile/cover-letter.md`. Reads `10-verification.md` for the checklist. Fills template contact tokens from `profile/candidate.md` |
| `/interview`, `/outcome`, `/rank`, `/add-portal`, `/notion-sync`, `upskill`, `job-scraper` | Change their read paths to `profile/…` |
| `job-application-assistant/SKILL.md` | The reference table is split into framework files and profile files. Adds the profile guard below |
| `AGENTS.md` | Pointer 1 changes to `profile/` and `CLAUDE.md` |

### Profile guard (single shared check)

It goes in `job-application-assistant/SKILL.md`, which every profile-reading command
already routes through, and is referenced once from `/apply`, `/rank` and
`job-scraper`:

> If `profile/` does not exist, or `profile/candidate.md` still contains `[YOUR_EMAIL]`,
> stop and tell the user to run `/setup`. Never score, rank or draft against placeholders.

### Legacy-fork migration (inside `/setup` Step 0a)

Trigger: `profile/` is missing **and** step 1 below finds a personalized legacy
`.claude/skills/job-application-assistant/01-candidate-profile.md` (one without a
`[YOUR_EMAIL]` token).

Steps:

1. Find the newest ref that has a personalized legacy `01-candidate-profile.md`: working
   tree, then `ORIG_HEAD`, then walk `git log --format=%H -- <path>` until a personalized
   version is found. If none is found, fall through to a fresh setup.
2. Read the legacy `01`–`07`, `search-queries.md` and `CLAUDE.md` from that ref with
   `git show <ref>:<path>`.
3. Extract each user region using the mapping table. Region boundaries are the headings
   and `<!-- SETUP -->` markers listed above. Contact data from the `05`/`06` LaTeX blocks
   is used only to cross-check `candidate.md` § Identity. Conflicts are reported, never
   silently merged.
4. Show the proposed `profile/*.md` files and write them only after the user confirms.
5. Tell the user to resolve any remaining merge conflicts in framework files by taking
   upstream's version (`git checkout --theirs <path>`). Their data is now in `profile/`
   and still in git history. Migration deletes nothing.

Documentation: add a SETUP.md section "Merging the profile-separation change into a
personalized fork" with the three commands, and a CHANGELOG entry marked as a breaking
change for forks.

### CI and tool changes

- `placeholder-integrity` job (upstream-only):
  - Change the checks from `01-candidate-profile.md` / `04-job-evaluation.md` to
    `profile-templates/candidate.md` (`[YOUR_EMAIL]`) and
    `profile-templates/evaluation.md` (`[YOUR_PRIMARY_SKILLS]`).
  - Add a failing check if `profile/` exists in the upstream tree.
  - Keep the `CLAUDE.md` and `cv/main_example.tex` checks.
- `check_framework_version.py`: the glob includes `profile-templates/*.md`, so template
  edits need a version bump too.
- `check_upstream_updates.py`: update `FRAMEWORK_FILES` (drop `01`/`02`, add
  `10-verification.md` and the templates).
- `security_guards.py`: no `REQUIRED_IGNORE_RULES` change. `profile/` must stay
  committable in forks. Upstream protection comes from the placeholder-integrity check.
- `lint_skills.py`: no change (no skill or command moves in this branch).

### Tests

| Test | Change |
|---|---|
| `test_placeholder_integrity.py` | Point at `profile-templates/`. Add: no `01`–`10` framework file contains a `[YOUR_` token (fails on master, passes on branch) |
| `test_reset_command.py` | Assert `/reset` restores from `profile-templates/`, with no embedded skeletons |
| `test_setup_command.py` | Assert write targets are `profile/*`. Assert Step 0a migration and template-copy steps exist |
| `test_check_framework_version.py`, `test_check_upstream_updates.py` | New file lists |
| `test_apply_page_count.py`, `test_latex_guidance.py`, `test_rank_command.py`, `test_company_research_cache.py`, others that grep moved paths | Path updates only |
| New `test_profile_templates.py` | Every template exists, is referenced by at least one command, and every framework pointer (`profile/<file>.md` § `<Heading>`) resolves to a real heading in the template |

### Versioning

Bump `framework_version` on every edited framework file (minor bump for files whose
contract changed: `04`, `05`, `06`, `07`, `SKILL.md`, `03`). New files start at `1.0.0`.

### Verification before opening the PR (run locally, because upstream-only CI jobs skip in forks)

1. `python -m unittest discover -s tests -t . -v`
2. `python tools/lint_skills.py && python tools/security_guards.py`
3. The placeholder-integrity shell block from `ci.yml`, run by hand
4. `python tools/check_framework_version.py` against `master`
5. LaTeX smoke compiles of `cv/main_example.tex` (lualatex) and `cover_letters/cover_example.tex` (xelatex)
6. End-to-end in a scratch clone: `/setup` Path C with made-up data → `/apply` on a
   sample posting → confirm the CV and cover letter use `profile/` data and the
   contact tokens are filled from `profile/candidate.md`
7. Migration in a scratch clone: personalize `master` with made-up data and commit,
   merge the branch, run `/setup` → confirm `profile/` reproduces the made-up data and
   nothing is lost

## Out of scope for branch 1

- Any move into `plugins/`, `${CLAUDE_PLUGIN_ROOT}` rewrites, or marketplace files (branch 2)
- The workspace-init command (branch 3)
- The duplication between `CLAUDE.md` § Candidate Profile and `profile/candidate.md`.
  This already exists today; `CLAUDE.md` keeps its summary so it still loads every session
- Market-specific portal changes

## Risks

- **Upstream may decline the whole direction.** Mitigation: branch 1 is argued from an
  existing, documented problem (manual merges into forks, the tooling built around
  `framework_version`). Link the discussion in #78 before opening the PR.
- **The verification checklist no longer loads every session.** It now loads with the
  `job-application-assistant` skill and `/apply`, which are the only places it is used.
  `CLAUDE.md` keeps a one-line pointer to `10-verification.md`.
- **Migration picks the wrong ref.** Mitigation: it shows every proposed file before
  writing, and never deletes.
