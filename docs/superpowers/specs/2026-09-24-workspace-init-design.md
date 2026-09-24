# Workspace init (design)

Status: draft for review · Date: 2026-09-24 · Branch: `plugin/4-workspace-init` (stacked on
`plugin/3-instruction-sync`)

Origin: the user's original request ("a setup command which initialises a repo with a
directory as the original author intended"), issue
[#493](https://github.com/MadsLorentzen/ai-job-search/issues/493) (`/init-folder`), and step 4
of the roadmap in `docs/superpowers/specs/2026-09-24-plugin-profile-separation-design.md`.

## Goal

After installing the plugin, one command lays out the author's workspace in any folder:
`cv/`, `cover_letters/` (class and fonts), `templates/`, the `documents/` tree, the state
folders, and a personal-data `.gitignore`, then writes the instruction files and points the
user at `/setup`. Starting with `/setup` directly must also produce a working workspace.

## Decisions (made with the user)

| Decision | Choice |
|---|---|
| Shape | One script (`init_workspace.py` in `job-tools`) used by a dedicated `/init-workspace` command **and** by `/setup` Step 0a |
| Name | `/init-workspace` |
| Template home | `plugins/ai-job-search/skills/job-tools/workspace-template/`, next to the script; the clone's root keeps its own working copy, and a test enforces sync |
| git init | `/init-workspace` offers it once, with a private-repository warning |

## Template

```
plugins/ai-job-search/skills/job-tools/workspace-template/
  cv/main_example.tex
  cover_letters/cover.cls
  cover_letters/cover_example.tex
  cover_letters/OpenFonts/...          (the 19 font and license files, same paths as at the root)
  templates/README.md
  documents/README.md
  documents/{applications,cv,diplomas,linkedin,postings,projects,references}/.gitkeep
  job_scraper/.gitkeep
  company_research/.gitkeep
  upskill/.gitkeep
  gitignore.template                    (copied to the workspace as .gitignore)
```

`gitignore.template` is named so because a real `.gitignore` inside the plugin folder would
apply its patterns to the plugin tree.

### Staying in sync with the clone's root

Identical files are one git blob, so the second copy costs no repository size. A test
(`tests/test_workspace_init.py`) enforces:

- Always: `cover_letters/cover.cls`, every file under `cover_letters/OpenFonts/`,
  `templates/README.md`, `documents/README.md` and every tracked `.gitkeep` under `documents/`,
  `job_scraper/`, `company_research/`, `upskill/` are byte-identical at the root and in the
  template, and the template has no file the root lacks.
- Upstream only (skipped in forks, like the existing placeholder-integrity checks, because
  forks personalize them): `cv/main_example.tex` and `cover_letters/cover_example.tex` are
  byte-identical.
- `gitignore.template` equals the root `.gitignore` with its repo-only lines removed:
  `plugins/**/node_modules/` and the `# Brainstorm mockups …` comment plus `.superpowers/`.
- `security_guards.py` checks `REQUIRED_IGNORE_RULES` and `ALLOWED_IGNORE_NEGATIONS` against
  `gitignore.template` as well as the root `.gitignore`.

## Script

`python3 <job-tools>/scripts/init_workspace.py [--root DIR]` (stdlib only). `--root` defaults to
the current directory (the workspace root). The template is found next to the script
(`Path(__file__).resolve().parent.parent / "workspace-template"`), which is plugin content.

- Walks the template and, for each file, copies it to the same relative path under the
  workspace **only if that path does not exist**. Never overwrites. Creates parent folders.
  Copies bytes exactly (fonts are binary).
- `gitignore.template` → `.gitignore`:
  - Missing `.gitignore`: copy the template.
  - Existing `.gitignore`: append, under a line
    `# Added by /init-workspace: personal data must never be committed`, only the template's
    rule lines (non-comment, non-blank) that the file does not already contain, in template
    order. Never changes or removes existing lines. Nothing to add → unchanged.
- Output, one line per path it acted on: `created: <path>`, `updated: .gitignore (+N rules)`,
  then a summary line `kept: N existing files`. Exit 0.
- Before writing anything, it checks every target: a target path that exists as the wrong
  kind (a directory where a file goes, or the reverse) → exit 2 with the path, nothing written.
  An unwritable folder → exit 2 with the error.
- It never touches `profile/` (that is `/setup`'s job, from `profile-templates/`), `AGENTS.md`
  or `CLAUDE.md` (that is `sync_instructions.py`'s job).

## `/init-workspace` skill

`plugins/ai-job-search/skills/init-workspace/SKILL.md`:

- Frontmatter: `name: init-workspace`, a description, `disable-model-invocation: true`,
  `allowed-tools` with the three entries below.
- Body: the user typing `/init-workspace` is the request. Run each command now, without asking
  for confirmation, from the current directory, as one command with no `cd` and no `&&`:
  1. `python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py`, and report its lines.
  2. `python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py`, and report its lines.
  3. If the folder is not inside a git repository (no `.git` in it or any parent), ask once with
     AskUserQuestion whether to run `git init`, stating: "This folder will hold your personal
     data. If you push it anywhere, use a private repository." On yes, run `git init`.
  4. Tell the user to run `/setup` next (it fills `profile/` and your details).
- Exit 2 from either script: show its message and stop.

## `/setup` reuse

`/setup` Step 0a gains a first item, before creating `profile/`: run
`python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py` exactly as written, as one
command, and mention in one line what it created. On exit 2, show the message and continue.
Its `allowed-tools` gains the entry.

## Permissions

New `security_guards.ALLOWED_SKILL_TOOLS` entries:

- `Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py:*)`
- `Bash(git init)`

(`sync_instructions.py`'s entry exists from branch 3.)

## Docs

- README "Install as a plugin": after the install lines, "run `/init-workspace` in an empty
  folder, then `/setup`" (replacing "run Claude in an empty folder and `/setup`" and the
  "arrives in a later release" note). Add `/init-workspace` to "Other commands".
- SETUP.md: a short "Starting from the plugin instead of a clone" note in section 2 pointing to
  `/init-workspace`.
- CHANGELOG `### Added` entry.

## Tests

`tests/test_workspace_init.py`:

- Empty folder → every template path created (`.gitignore` from `gitignore.template`); font
  files byte-identical; exit 0.
- Second run → no `created:` lines; `kept:` count equals the template's file count.
- An existing `cv/main_example.tex` with user content is never overwritten.
- Existing `.gitignore` with the user's own rules → user lines unchanged, only missing
  template rules appended once under the header; a second run appends nothing.
- A directory where `cv/main_example.tex` should be → exit 2 and nothing written anywhere.
- `--root` targets another folder.
- The sync checks from "Staying in sync with the clone's root".
- Wiring: the skill is user-only with the three permissions; `/setup` Step 0a calls the
  script; guards list both new entries.

Verification: a headless `/ai-job-search:init-workspace` run in an empty folder from a plugin
install (only the Skill tool allowed) creates the tree and `AGENTS.md`/`CLAUDE.md` with no
permission denials.

## Out of scope

- Personalizing anything (that is `/setup`).
- Installing Bun dependencies for portals (portals install themselves on first use).

## Risks

- **Template drift:** a PR edits `cover.cls` at the root but not in the template. The sync
  test fails the PR.
- **A workspace nested inside another git repository** gets no `git init` offer; that is
  intended (step 3 checks parents).
