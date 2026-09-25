# Plugin Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move every command, skill, agent, shipped portal and runtime script into a two-plugin Claude Code marketplace that the clone loads in place, with no second copy.

**Architecture:** `.claude-plugin/marketplace.json` at the repo root lists `plugins/ai-job-search` (core workflow, 12 commands converted to skills, `job-tools` scripts skill, LinkedIn and freehire portals) and `plugins/danish-job-portals` (4 Danish portals). Skills reach each other as siblings through `${CLAUDE_SKILL_DIR}/../<skill>/…`, which works in Claude Code and survives capa's as-is copy. Permissions move from `.claude/settings.json` into each skill's `allowed-tools`, and `security_guards.py` reviews them there.

**Tech Stack:** Markdown skills (the spec *is* the implementation), Python 3 stdlib (`unittest`, `json`, `pathlib`, `re`), PyYAML (already used by `lint_skills.py`), Bun for the portal CLIs, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-24-plugin-layout-design.md`. Read it fully before starting. Branch 1's spec (`2026-09-24-plugin-profile-separation-design.md`) holds the roadmap and the capa findings this branch relies on.

## Global Constraints

- Branch `plugin/2-plugin-layout`, stacked on `plugin/1-profile-separation`. The working tree must be clean before Task 1 (it is at plan time; `stash@{0}` is unrelated, leave it).
- Move files with `git mv` so history follows. Never copy and delete.
- Plugin roots: `plugins/ai-job-search/` (below: `CORE/`), `plugins/danish-job-portals/` (below: `MARKET/`). Skills folder: `CORE/skills/` (below: `SK/`).
- Marketplace name `ai-job-search`; plugin names `ai-job-search` and `danish-job-portals`, exactly.
- The 12 converted skills, exactly: `add-portal add-template apply expand gmail-sync html-report interview notion-sync outcome rank reset setup`. Each gets `disable-model-invocation: true`.
- Runtime scripts that move to `SK/job-tools/scripts/`, exactly: `rank_state.py job_key.py verify_pdf.py verify_layout.py robots_check.py convert_salary_excel.py` (from `tools/`), `salary_lookup.py` (from the repo root), and `tools/README_SALARY_TOOL.md`. Dev tools stay in `tools/`: `lint_skills.py security_guards.py check_framework_version.py check_upstream_updates.py upstream_triage.py`.
- Path form for anything inside the plugin, exactly: `${CLAUDE_SKILL_DIR}/../<skill>/<file>` (sibling) or `${CLAUDE_SKILL_DIR}/<file>` (own folder). The fallback sentence, exactly: `` `${CLAUDE_SKILL_DIR}` is this skill's folder. If your tool does not expand it, read paths as relative to the folder containing this SKILL.md. ``
- Workspace data (`profile/ cv/ cover_letters/ documents/ job_scraper/ job_search_tracker.csv company_research/ upskill/ reports/ templates/ gmail_sync/ salary_data.json`) is always relative to the current directory (the workspace root), never to a skill's folder.
- Tests: stdlib `unittest`; run one module with `python3 -m unittest tests.<module> -v`, the suite with `python3 -m unittest discover -s tests -t . -v`.
- This machine's git has `log.showSignature=true` and `merge.ff=only`: use `git log --no-show-signature` in any scripted `git log`. `lualatex`/`xelatex` are not installed.
- Headless probes: use `--model claude-haiku-4-5-20251001` (Sonnet refuses to run unreviewed scripts in `-p` mode).
- Commit messages: conventional commits, ending with
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01C8revGiLzJ6ZYvz6LZMmZa
  ```

## Review Focus

1. **A skill writes workspace state relative to its own folder** (observed before for `job-scraper` and `upskill`, see the comments in `security_guards.py`). Inside a plugin that folder is the plugin cache, so `seen_jobs.json` or upskill reports would vanish on the next update. Expected: every write lands in the workspace root. Pinned in Task 4 (`test_state_writing_skills_pin_workspace_root`).
2. **`/scrape` runs portal CLIs in parallel subagents.** Those used to be pre-approved by `settings.json`, which this branch empties. Expected: each subagent loads its portal skill with the Skill tool first, so the portal's `allowed-tools` apply. Pinned in Task 6 (`test_scrape_subagents_load_portal_skill`) plus a probe.
3. **A converted destructive command becomes model-invocable** (`/reset` deleting data because the model decided to). Expected: all 12 carry `disable-model-invocation: true`. Pinned in Task 2 (`test_converted_skills_are_user_only`).
4. **Danish portal after a plugin update** (fresh cache folder, no `node_modules`). Expected: the skill installs its dependencies first instead of failing with the React error. Pinned in Task 6 (`test_danish_portals_self_install`).
5. **A mistyped `${CLAUDE_SKILL_DIR}/../<skill>/<file>` reference** points at nothing, and the model improvises. Expected: every such reference resolves to a real file. Pinned in Task 4 (`test_skill_dir_references_resolve`).

---

### Task 1: Central test paths

**Files:**
- Create: `tests/paths.py`, `tests/test_paths.py`
- Modify: every `tests/test_*.py` that builds a path into `.claude/`, `.agents/`, `tools/<runtime script>` or `salary_lookup.py`

**Interfaces:**
- Produces (in `tests/paths.py`, used by every later task): `REPO: Path`; `FW: Path` (job-application-assistant folder); `TPL: Path` (`FW / "profile-templates"`); `JOB_TOOLS: Path` (folder holding the runtime scripts); `SETTINGS: Path`; `command_file(name: str) -> Path`; `skill_file(name: str) -> Path` (a skill's `SKILL.md`, looked up by folder name); `portal_dirs() -> list[Path]` (every shipped portal skill folder); `framework_markdown() -> list[Path]` (every `.md` under the command and skill trees); `add_job_tools_to_sys_path() -> None`.
- In this task the implementations still point at today's locations. Task 2 changes only `tests/paths.py`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_paths.py`:

```python
"""tests/paths.py is the single place tests learn where framework files live."""
import unittest

from tests import paths


class TestPaths(unittest.TestCase):
    def test_constants_exist(self):
        for p in (paths.REPO, paths.FW, paths.TPL, paths.JOB_TOOLS, paths.SETTINGS):
            self.assertTrue(p.exists(), p)

    def test_every_command_resolves(self):
        for name in ("add-portal", "add-template", "apply", "expand", "gmail-sync", "html-report",
                     "interview", "notion-sync", "outcome", "rank", "reset", "setup"):
            self.assertTrue(paths.command_file(name).is_file(), name)

    def test_skills_and_portals_resolve(self):
        for name in ("job-application-assistant", "job-scraper", "upskill"):
            self.assertTrue(paths.skill_file(name).is_file(), name)
        names = sorted(p.name for p in paths.portal_dirs())
        self.assertEqual(names, ["freehire-search", "jobbank-search", "jobdanmark-search",
                                 "jobindex-search", "jobnet-search", "linkedin-search"])

    def test_job_tools_hold_every_runtime_script(self):
        for script in ("rank_state.py", "job_key.py", "verify_pdf.py", "verify_layout.py",
                       "robots_check.py", "convert_salary_excel.py"):
            self.assertTrue((paths.JOB_TOOLS / script).is_file(), script)
        self.assertTrue(paths.SALARY_LOOKUP.is_file())  # Task 2 moves it into JOB_TOOLS

    def test_framework_markdown_covers_commands_and_skills(self):
        md = paths.framework_markdown()
        self.assertIn(paths.command_file("apply"), md)
        self.assertIn(paths.FW / "04-job-evaluation.md", md)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_paths -v`
Expected: ERROR `ImportError: cannot import name 'paths' from 'tests'`.

- [ ] **Step 3: Create `tests/paths.py`**

`salary_lookup.py` still sits at the repo root in this task, so `paths.SALARY_LOOKUP` points there; Task 2 moves it under `JOB_TOOLS`.

```python
"""Where framework files live. Tests import paths from here and nowhere else,
so moving the framework means editing this one file."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FW = REPO / ".claude" / "skills" / "job-application-assistant"
TPL = FW / "profile-templates"
JOB_TOOLS = REPO / "tools"
SETTINGS = REPO / ".claude" / "settings.json"
_COMMANDS = REPO / ".claude" / "commands"
_SKILLS = REPO / ".claude" / "skills"
_PORTALS = REPO / ".agents" / "skills"
SALARY_LOOKUP = REPO / "salary_lookup.py"  # Task 2: moves under JOB_TOOLS


def command_file(name: str) -> Path:
    return _COMMANDS / f"{name}.md"


def skill_file(name: str) -> Path:
    return _SKILLS / name / "SKILL.md"


def portal_dirs() -> list[Path]:
    return sorted(p for p in _PORTALS.glob("*-search") if (p / "SKILL.md").is_file())


def framework_markdown() -> list[Path]:
    return sorted(_COMMANDS.glob("*.md")) + sorted(_SKILLS.rglob("*.md"))


def add_job_tools_to_sys_path() -> None:
    for folder in (JOB_TOOLS, SALARY_LOOKUP.parent):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
```

- [ ] **Step 4: Rewrite path expressions in tests**

Run this codemod once. It rewrites the common forms; Step 5 lists what is left.

```bash
python3 - <<'PYEOF'
import re
from pathlib import Path
BASE = r'(?:REPO_ROOT|REPO|ROOT)'
rules = [
    (BASE + r' / "\.claude" / "commands" / "([a-z-]+)\.md"', r'paths.command_file("\1")'),
    (BASE + r' / "\.claude" / "skills" / "job-application-assistant"', 'paths.FW'),
    (BASE + r' / "\.claude" / "skills" / "([a-z-]+)" / "SKILL\.md"', r'paths.skill_file("\1")'),
    (BASE + r' / "\.claude" / "settings\.json"', 'paths.SETTINGS'),
    (BASE + r' / "salary_lookup\.py"', 'paths.SALARY_LOOKUP'),
    (BASE + r' / "tools" / "(rank_state|job_key|verify_pdf|verify_layout|robots_check|convert_salary_excel)\.py"',
     r'paths.JOB_TOOLS / "\1.py"'),
]
for f in sorted(Path("tests").glob("test_*.py")):
    if f.name == "test_paths.py":
        continue
    s = f.read_text(encoding="utf-8")
    new = s
    for pat, rep in rules:
        new = re.sub(pat, rep, new)
    if new != s:
        if "from tests import paths" not in new:
            # insert after the last top-level import line
            lines = new.split("\n")
            last = max(i for i, l in enumerate(lines) if l.startswith(("import ", "from ")))
            lines.insert(last + 1, "from tests import paths")
            new = "\n".join(lines)
        f.write_text(new, encoding="utf-8")
        print("rewrote", f)
PYEOF
```

- [ ] **Step 5: Fix the remaining forms by hand**

Run: `grep -nE '"\.claude"|"\.agents"|"tools" /|sys\.path\.insert|from tools\.|^import salary_lookup|^from (salary_lookup|job_key|robots_check) ' tests/test_*.py`

Handle each hit like this (the list below is every case present at plan time):
- `tests/test_scrape_contract.py`: `PORTAL_CLIS = sorted((REPO_ROOT / ".agents" / "skills").glob("*-search"))` → `PORTAL_CLIS = paths.portal_dirs()`.
- `tests/test_profile_separation.py`: in `pointer_sources()` and `TestNoLegacyReferences`, replace `sorted((REPO / ".claude").rglob("*.md"))` / `list((REPO / ".claude").rglob("*.md"))` with `paths.framework_markdown()`. Replace its local `FW`/`TPL` definitions with `FW = paths.FW` and `TPL = paths.TPL`; `APPLY = paths.command_file("apply")`; the scraper path → `paths.skill_file("job-scraper")`; the `LEGACY` path `REPO / ".claude" / "skills" / "job-scraper" / "search-queries.md"` stays literal (it asserts a *deleted* path).
- `tests/test_setup_command.py`, `tests/test_reset_command.py`: local `SKILL_DIR`/`TPL` → `paths.FW` / `paths.TPL`.
- `tests/test_job_key.py`, `tests/test_robots_check.py`, `tests/test_salary_lookup.py`, `tests/test_convert_salary_excel.py`, `tests/test_convert_salary_excel_integration.py`, `tests/test_verify_pdf.py`, `tests/test_verify_layout.py`: replace any `sys.path.insert(... "tools" ...)` with `paths.add_job_tools_to_sys_path()` placed before the tool import; change `from tools.verify_pdf import` → `from verify_pdf import` and `from tools.verify_layout import` → `from verify_layout import` and `from tools.convert_salary_excel import` → `from convert_salary_excel import`.
- `tests/test_tools_utf8_output.py`: build script paths from `paths.JOB_TOOLS` / `paths.SALARY_LOOKUP`; the `sys.path.insert(0, {str(REPO)!r})` inside a generated child script stays.
- `tests/test_security_guards.py` string paths like `".claude/skills/upskill/upskill/report-2026-08-11.md"` are gitignore-rule inputs, not file lookups: leave them.
- `tests/test_check_upstream_updates.py` string list, `tests/test_placeholder_integrity.py` CI strings, `tests/test_lint_skills.py` fixture strings, `tests/test_rank_command.py` and `tests/test_apply_page_count.py` command-text strings: leave them; Tasks 2, 4 and 5 update those alongside the text they assert.
- Any `REPO / ".claude" / "commands"` used as a directory to glob → `paths.framework_markdown()` filtered by the caller's need, or the explicit `paths.command_file(...)` list.

Re-run the grep. Expected: only the "leave them" cases above.

- [ ] **Step 6: Run to verify it passes**

Run: `python3 -m unittest discover -s tests -t . -v 2>&1 | tail -3`
Expected: `OK (skipped=3)`, test count = previous count + 5.

- [ ] **Step 7: Commit**

```bash
git add tests
git commit -m "test: route framework paths through tests/paths.py"   # plus the two trailer lines
```

---

### Task 2: Move into the plugins, convert commands, retarget tooling

**Files:**
- Create: `.claude-plugin/marketplace.json`, `CORE/.claude-plugin/plugin.json`, `MARKET/.claude-plugin/plugin.json`, `SK/job-tools/SKILL.md`, `.agents/skills/README.md`, `tests/test_plugin_layout.py`
- Move (`git mv`): `.claude/skills/*` → `SK/`; `.claude/commands/<x>.md` → `SK/<x>/SKILL.md`; `.claude/agents/gemini-research-expert.md` → `CORE/agents/`; `.agents/skills/{linkedin-search,freehire-search}` → `SK/`; `.agents/skills/{jobbank,jobdanmark,jobindex,jobnet}-search` → `MARKET/skills/`; runtime scripts → `SK/job-tools/scripts/`
- Modify: `tests/paths.py`, `tests/test_paths.py`, `tools/lint_skills.py`, `tests/test_lint_skills.py`, `tools/security_guards.py` (package-manifest glob only), `tools/check_framework_version.py`, `tools/check_upstream_updates.py`, `tests/test_check_upstream_updates.py`, `.github/workflows/ci.yml`, `.gitignore`

**Interfaces:**
- Consumes: `tests/paths.py` API (Task 1).
- Produces: the final file layout; `tests/paths.py` pointing at it; converted skills with frontmatter; `lint_skills.py` that understands plugins.

- [ ] **Step 1: Write the failing test**

Create `tests/test_plugin_layout.py`:

```python
"""Structure of the plugin marketplace (spec: 2026-09-24-plugin-layout-design.md)."""
import json
import re
import unittest

import yaml

from tests import paths

REPO = paths.REPO
CONVERTED = ("add-portal", "add-template", "apply", "expand", "gmail-sync", "html-report",
             "interview", "notion-sync", "outcome", "rank", "reset", "setup")


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return yaml.safe_load(m.group(1)) if m else {}


class TestMarketplace(unittest.TestCase):
    def test_marketplace_lists_both_plugins(self):
        data = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "ai-job-search")
        entries = {p["name"]: p["source"] for p in data["plugins"]}
        self.assertEqual(entries, {"ai-job-search": "./plugins/ai-job-search",
                                   "danish-job-portals": "./plugins/danish-job-portals"})
        for name, source in entries.items():
            manifest = json.loads((REPO / source / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["name"], name)

    def test_old_trees_are_gone(self):
        for old in (".claude/commands", ".claude/skills", ".claude/agents"):
            self.assertFalse((REPO / old).exists(), old)
        leftovers = [p.name for p in (REPO / ".agents" / "skills").iterdir() if p.is_dir()]
        self.assertEqual(leftovers, [], "shipped portals must live in the plugins")


class TestConvertedCommands(unittest.TestCase):
    def test_converted_skills_are_user_only(self):
        for name in CONVERTED:
            fm = frontmatter(paths.command_file(name))
            self.assertEqual(fm.get("name"), name)
            self.assertTrue(fm.get("description"), name)
            self.assertIs(fm.get("disable-model-invocation"), True, name)

    def test_converted_skills_keep_their_title(self):
        for name in CONVERTED:
            body = paths.command_file(name).read_text(encoding="utf-8").split("\n---\n", 1)[1]
            self.assertTrue(body.lstrip().startswith(f"# /{name} "), name)

    def test_argument_hints(self):
        for name in CONVERTED:
            fm = frontmatter(paths.command_file(name))
            if name in ("expand", "html-report"):
                self.assertNotIn("argument-hint", fm, name)
            else:
                self.assertTrue(fm.get("argument-hint"), name)

    def test_job_tools_is_hidden_from_the_slash_menu(self):
        fm = frontmatter(paths.skill_file("job-tools"))
        self.assertIs(fm.get("user-invocable"), False)
```

Also in `tests/test_paths.py`, add `"salary_lookup.py"` to the `test_job_tools_hold_every_runtime_script` loop and change the separate assertion to `self.assertEqual(paths.SALARY_LOOKUP, paths.JOB_TOOLS / "salary_lookup.py")`.

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_plugin_layout tests.test_paths -v`
Expected: FAIL/ERROR — `marketplace.json` missing, `.claude/commands` exists, `job-tools` missing, `salary_lookup.py` not under `tools/`.

- [ ] **Step 3: Move the files**

```bash
set -e
CORE=plugins/ai-job-search; SK=$CORE/skills; MARKET=plugins/danish-job-portals
mkdir -p $SK $CORE/agents $CORE/.claude-plugin $MARKET/skills $MARKET/.claude-plugin $SK/job-tools/scripts
for d in .claude/skills/*/; do git mv "$d" "$SK/$(basename "$d")"; done
for f in .claude/commands/*.md; do n=$(basename "$f" .md); mkdir -p "$SK/$n"; git mv "$f" "$SK/$n/SKILL.md"; done
git mv .claude/agents/gemini-research-expert.md $CORE/agents/
for p in linkedin-search freehire-search; do git mv .agents/skills/$p $SK/$p; done
for p in jobbank-search jobdanmark-search jobindex-search jobnet-search; do git mv .agents/skills/$p $MARKET/skills/$p; done
for s in rank_state job_key verify_pdf verify_layout robots_check convert_salary_excel; do git mv tools/$s.py $SK/job-tools/scripts/; done
git mv salary_lookup.py $SK/job-tools/scripts/
git mv tools/README_SALARY_TOOL.md $SK/job-tools/scripts/
rmdir .claude/skills .claude/commands .claude/agents 2>/dev/null || true
```

- [ ] **Step 4: Write the manifests and the job-tools skill**

`.claude-plugin/marketplace.json`:

```json
{
  "name": "ai-job-search",
  "owner": { "name": "Mads Lorentzen" },
  "description": "AI job search workflow for Claude Code: fit evaluation, tailored LaTeX CVs and cover letters, job scraping and ranking, interview prep.",
  "plugins": [
    {
      "name": "ai-job-search",
      "source": "./plugins/ai-job-search",
      "description": "Core job-application workflow plus the country-agnostic LinkedIn and freehire portals."
    },
    {
      "name": "danish-job-portals",
      "source": "./plugins/danish-job-portals",
      "description": "Job portal search skills for Denmark: Jobbank, Jobdanmark, Jobindex, Jobnet."
    }
  ]
}
```

`CORE/.claude-plugin/plugin.json`:

```json
{
  "name": "ai-job-search",
  "version": "1.8.0",
  "description": "Job application workflow: fit evaluation, tailored LaTeX CVs and cover letters, job scraping and ranking, interview prep. Candidate data lives in your workspace's profile/ folder.",
  "author": { "name": "Mads Lorentzen" },
  "homepage": "https://github.com/MadsLorentzen/ai-job-search",
  "repository": "https://github.com/MadsLorentzen/ai-job-search",
  "license": "MIT"
}
```

`MARKET/.claude-plugin/plugin.json`: same shape, `"name": "danish-job-portals"`, `"version": "1.8.0"`, `"description": "Job portal search skills for Denmark (Jobbank, Jobdanmark, Jobindex, Jobnet), used by /scrape from the ai-job-search plugin."`.

`SK/job-tools/SKILL.md`:

````markdown
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
| `scripts/convert_salary_excel.py` | you, once | `python3 ${CLAUDE_SKILL_DIR}/scripts/convert_salary_excel.py <file.xlsx>` |
````

`.agents/skills/README.md`:

```markdown
# Your own portal skills

`/add-portal` writes the job-portal search skills you generate here, one folder per portal (`<name>-search/`). `/scrape` picks them up automatically, alongside the portals shipped in the `ai-job-search` and `danish-job-portals` plugins.
```

- [ ] **Step 5: Add frontmatter to the 12 converted skills**

```bash
python3 - <<'PYEOF'
from pathlib import Path
SK = Path("plugins/ai-job-search/skills")
HINTS = {
    "add-portal": "[portal-url | --list]",
    "add-template": "[template-path | --list | --use <name>]",
    "apply": "<job-posting-url-or-text>",
    "gmail-sync": "[company]",
    "interview": "[company [role]]",
    "notion-sync": "[filter]",
    "outcome": "[company]",
    "rank": "[count | filter]",
    "reset": "[profile | documents | all]",
    "setup": "[--section <name>]",
}
for name in ["add-portal","add-template","apply","expand","gmail-sync","html-report",
             "interview","notion-sync","outcome","rank","reset","setup"]:
    p = SK / name / "SKILL.md"
    body = p.read_text(encoding="utf-8")
    title = body.lstrip().splitlines()[0]
    assert title.startswith(f"# /{name} - "), (name, title)
    desc = title.split(" - ", 1)[1].strip().replace('"', "'")
    fm = [ "---", f"name: {name}",
           f'description: "{desc}. Use when the user runs /{name}."' ]
    if name in HINTS:
        fm.append(f'argument-hint: "{HINTS[name]}"')
    fm += ["disable-model-invocation: true", "---", ""]
    p.write_text("\n".join(fm) + body, encoding="utf-8")
    print("converted", name)
PYEOF
```

- [ ] **Step 6: Point `tests/paths.py` at the new layout**

Replace the constants and function bodies in `tests/paths.py`:

```python
REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugins" / "ai-job-search"
MARKET = REPO / "plugins" / "danish-job-portals"
SKILLS = PLUGIN / "skills"
FW = SKILLS / "job-application-assistant"
TPL = FW / "profile-templates"
JOB_TOOLS = SKILLS / "job-tools" / "scripts"
SETTINGS = REPO / ".claude" / "settings.json"
SALARY_LOOKUP = JOB_TOOLS / "salary_lookup.py"


def command_file(name: str) -> Path:
    return SKILLS / name / "SKILL.md"


def skill_file(name: str) -> Path:
    return SKILLS / name / "SKILL.md"


def portal_dirs() -> list[Path]:
    found = list(SKILLS.glob("*-search")) + list((MARKET / "skills").glob("*-search"))
    return sorted((p for p in found if (p / "SKILL.md").is_file()), key=lambda p: p.name)


def all_skill_files() -> list[Path]:
    return sorted(REPO.glob("plugins/*/skills/*/SKILL.md"))


def framework_markdown() -> list[Path]:
    return sorted(p for p in REPO.glob("plugins/*/skills/**/*.md"))


def add_job_tools_to_sys_path() -> None:
    if str(JOB_TOOLS) not in sys.path:
        sys.path.insert(0, str(JOB_TOOLS))
```

(`all_skill_files()` is new; Tasks 4-6 use it.)

- [ ] **Step 7: Retarget the dev tools and CI**

`tools/lint_skills.py`:
- `main()`: `skills = sorted(ROOT.glob("plugins/*/skills/*/SKILL.md")) + sorted(ROOT.glob(".agents/skills/*/SKILL.md"))`; drop the `commands` glob and the "no command files" error; after `check_skill(skill)`, call `check_user_command(skill)`.
- Replace `check_command` with:

  ```python
  def check_user_command(path: Path) -> None:
      """A converted command (disable-model-invocation: true) keeps its '# /<name>' title."""
      text = path.read_text(encoding="utf-8")
      m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
      if not m:
          return
      data = yaml.safe_load(m.group(1)) or {}
      if data.get("disable-model-invocation") is not True:
          return
      body = text[m.end():].lstrip()
      if not body.startswith(f"# /{data.get('name')} "):
          errors.append(f"{rel(path)}: user-invoked skill must start its body with '# /{data.get('name')} - ...'")
  ```
- In `check_skill`'s `allowed-tools` loop, expand `${CLAUDE_SKILL_DIR}` before checking: `target = match.group(1).rstrip("*").replace("${CLAUDE_SKILL_DIR}", str(path.parent.relative_to(ROOT)))`, and resolve relative paths with `(ROOT / target).resolve()`, so `plugins/x/skills/a/../job-tools/...` normalizes.
- Final message: `print(f"lint_skills: OK ({len(skills)} skills, settings.json)")`.

`tests/test_lint_skills.py`: its fixtures build fake trees under a temp root with `.claude/skills/...` and `.claude/commands/...`. Change fixture paths to `plugins/p/skills/<name>/SKILL.md`. Change any test that fed a `commands/*.md` file to feed a skill with `disable-model-invocation: true` frontmatter and assert the title rule. Change assertion strings that expect `commands` in the OK message to the new message.

`tools/security_guards.py` `check_package_manifests`: `ROOT.glob(".agents/**/package.json")` → `list(ROOT.glob("plugins/**/package.json")) + list(ROOT.glob(".agents/**/package.json"))`, error text `"no package.json files found under plugins/ or .agents/"`. (Permission changes come in Task 5.)

`tools/check_framework_version.py`: `SKILL_DIR = ROOT / "plugins/ai-job-search/skills/job-application-assistant"`; docstring path to match.

`tools/check_upstream_updates.py` and `tests/test_check_upstream_updates.py`: in both `FRAMEWORK_FILES` lists, replace the prefix `.claude/skills/job-application-assistant/` with `plugins/ai-job-search/skills/job-application-assistant/` (keep `AGENTS.md`).

`.github/workflows/ci.yml`:
- `discover-clis` step: `tools=$(find plugins/*/skills .agents/skills -mindepth 3 -maxdepth 3 -path '*/cli/package.json' 2>/dev/null | xargs -r -n1 dirname | xargs -r -n1 dirname | sort | jq -R . | jq -cs .)` — the matrix value becomes the skill folder path (e.g. `plugins/danish-job-portals/skills/jobnet-search`).
- `cli-checks`: `name: CLI checks ${{ matrix.tool }}` stays; each `working-directory: .agents/skills/${{ matrix.tool }}/cli` → `working-directory: ${{ matrix.tool }}/cli`.
- Every `python3 tools/verify_pdf.py` → `python3 plugins/ai-job-search/skills/job-tools/scripts/verify_pdf.py`.
- Placeholder checks: `.claude/skills/job-application-assistant/profile-templates/` → `plugins/ai-job-search/skills/job-application-assistant/profile-templates/` (both lines).
- Update the comment above `discover-clis` that mentions `.agents/**/package.json` to `plugins/**/package.json and .agents/**/package.json`.

`tests/test_placeholder_integrity.py`: the expected CI string becomes `check plugins/ai-job-search/skills/job-application-assistant/profile-templates/candidate.md '\\[YOUR_EMAIL\\]'`.

`.gitignore`: under the existing `.agents/**/node_modules/` line add `plugins/**/node_modules/`.

- [ ] **Step 8: Run to verify it passes**

Run: `python3 -m unittest discover -s tests -t . 2>&1 | tail -3` then `python3 tools/lint_skills.py && python3 tools/security_guards.py`
Expected: suite `OK`; `lint_skills: OK (22 skills, settings.json)`; security guards OK. If a text-asserting test fails because it asserts an old path string (for example `tests/test_scrape_contract.py` reading `.agents/skills/<portal>/SKILL.md` content that says `bun run .agents/skills/...`), leave it failing only if Task 4 or 6 owns that text. Record it in the ledger as `Task 2: expected-red <test> (owned by Task N)` and make sure it is green at the end of the owning task. Everything else must be green here.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor: move framework into ai-job-search and danish-job-portals plugins"   # plus trailers
```

---

### Task 3: salary tools read and write the workspace root

**Files:**
- Modify: `SK/job-tools/scripts/salary_lookup.py:27`, `SK/job-tools/scripts/convert_salary_excel.py:16,351,376`, `SK/job-tools/scripts/README_SALARY_TOOL.md`
- Test: `tests/test_salary_lookup.py`, `tests/test_convert_salary_excel.py`

**Interfaces:**
- Consumes: `paths.add_job_tools_to_sys_path()`.
- Produces: `salary_lookup.DATA_FILE == Path.cwd() / "salary_data.json"` at import time. `convert_salary_excel`'s default output is `Path.cwd() / "salary_data.json"`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_salary_lookup.py`:

```python
class TestDataFileLocation(unittest.TestCase):
    def test_data_file_is_read_from_the_workspace_root(self):
        import importlib, os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                module = importlib.reload(salary_lookup)
                self.assertEqual(module.DATA_FILE, Path(tmp).resolve() / "salary_data.json")
            finally:
                os.chdir(old)
                importlib.reload(salary_lookup)
```

(Add `from pathlib import Path` to the imports if it is missing.)

Append to `tests/test_convert_salary_excel.py`:

```python
class TestDefaultOutputLocation(unittest.TestCase):
    def test_default_output_is_the_workspace_root(self):
        src = (paths.JOB_TOOLS / "convert_salary_excel.py").read_text(encoding="utf-8")
        self.assertIn('Path.cwd() / "salary_data.json"', src)
        self.assertNotIn("Path(__file__).parent.parent", src)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_salary_lookup.TestDataFileLocation tests.test_convert_salary_excel.TestDefaultOutputLocation -v`
Expected: FAIL — `DATA_FILE` points at the scripts folder; the source still has `Path(__file__).parent.parent`.

- [ ] **Step 3: Implement**

- `salary_lookup.py` line 27: `DATA_FILE = Path.cwd().resolve() / "salary_data.json"`, with the comment `# The workspace root (where you run Claude), never the plugin folder: plugin updates replace that folder.` directly above it.
- `convert_salary_excel.py`: line 376 `Path(__file__).parent.parent / "salary_data.json"` → `Path.cwd() / "salary_data.json"`; line 16 docstring "written to the repository root" → "written to the current directory (your workspace root)"; line 351 help text "(default: salary_data.json in repo root)" → "(default: salary_data.json in the current directory)".
- `README_SALARY_TOOL.md`: "in the repo root" → "in your workspace root (the folder you run Claude in)"; replace any `python salary_lookup.py` / `python tools/convert_salary_excel.py` example with `python3 plugins/ai-job-search/skills/job-tools/scripts/<script>.py` and add one line: "Plugin installs: ask Claude to run it, the skills know the path."

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_salary_lookup tests.test_convert_salary_excel tests.test_convert_salary_excel_integration tests.test_tools_utf8_output -v 2>&1 | tail -3`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add plugins/ai-job-search/skills/job-tools tests/test_salary_lookup.py tests/test_convert_salary_excel.py
git commit -m "fix(job-tools): salary data lives in the workspace root, not the plugin"   # plus trailers
```

---

### Task 4: Rewrite paths inside the skills

**Files:**
- Modify: every `plugins/*/skills/*/SKILL.md` and every `.md` under `SK/job-application-assistant/`, `CLAUDE.md`
- Modify tests that assert command text: `tests/test_rank_command.py` (lines asserting `tools/rank_state.py …`), `tests/test_apply_page_count.py:35`, plus any `expected-red` test Task 2 ledgered against Task 4
- Test: `tests/test_plugin_layout.py`

**Interfaces:**
- Consumes: `paths.all_skill_files()`, `paths.framework_markdown()`.
- Produces: skill text free of `.claude/commands/`, `.claude/skills/`, `tools/<runtime>.py`, root-level `salary_lookup.py`; the fallback sentence in every skill that uses `${CLAUDE_SKILL_DIR}`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plugin_layout.py`:

```python
RUNTIME = ("rank_state", "job_key", "verify_pdf", "verify_layout", "robots_check",
           "convert_salary_excel")


def strip_setup_migration(text):
    """/setup's Legacy fork migration reads old paths from git history; they stay literal."""
    marker = "#### Legacy fork migration"
    if marker not in text:
        return text
    head, tail = text.split(marker, 1)
    rest = tail.split("\n### ", 1)
    return head + ("\n### " + rest[1] if len(rest) > 1 else "")
FALLBACK = ("`${CLAUDE_SKILL_DIR}` is this skill's folder. If your tool does not expand it, "
            "read paths as relative to the folder containing this SKILL.md.")
SKILL_DIR_REF = re.compile(r"\$\{CLAUDE_SKILL_DIR\}(/[^\s`'\")|*]+)")


class TestSkillPaths(unittest.TestCase):
    def test_no_legacy_paths_in_framework_text(self):
        bad = re.compile(r"\.claude/(commands|skills|agents)/|(?<![\w/.])tools/(%s)\.py|python3? salary_lookup\.py"
                         % "|".join(RUNTIME))
        offenders = []
        for md in paths.framework_markdown() + [REPO / "CLAUDE.md"]:
            text = strip_setup_migration(md.read_text(encoding="utf-8"))
            for i, line in enumerate(text.splitlines(), 1):
                if bad.search(line):
                    offenders.append(f"{md.relative_to(REPO)}:{i}")
        self.assertEqual(offenders, [])

    def test_skill_dir_references_resolve(self):
        broken = []
        for md in paths.framework_markdown():
            skill_dir = md.parent
            while skill_dir.parent.name != "skills":
                skill_dir = skill_dir.parent
            for ref in SKILL_DIR_REF.findall(md.read_text(encoding="utf-8")):
                target = ref.rstrip(".,:;")
                if "<" in target or "node_modules" in target:  # placeholder, or created at first run
                    continue
                if not (skill_dir / target.lstrip("/")).resolve().exists():
                    broken.append(f"{md.relative_to(REPO)}: {target}")
        self.assertEqual(broken, [])

    def test_skills_using_skill_dir_carry_the_fallback_line(self):
        missing = [str(p.relative_to(REPO)) for p in paths.all_skill_files()
                   if "${CLAUDE_SKILL_DIR}" in p.read_text(encoding="utf-8")
                   and FALLBACK not in p.read_text(encoding="utf-8")]
        self.assertEqual(missing, [])

    def test_state_writing_skills_pin_workspace_root(self):
        for name in ("job-scraper", "upskill"):
            text = paths.skill_file(name).read_text(encoding="utf-8")
            self.assertIn("relative to the workspace root", text, name)
            self.assertIn("never inside this skill's folder", text, name)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_plugin_layout.TestSkillPaths -v`
Expected: FAIL — legacy paths listed (`apply/SKILL.md`, `rank/SKILL.md`, `job-application-assistant/SKILL.md`, `05-cv-templates.md`, …), fallback line missing, workspace-root sentence missing.

- [ ] **Step 3: Codemod the paths**

```bash
python3 - <<'PYEOF'
import re
from pathlib import Path
REPO = Path(".")
RUNTIME = "rank_state|job_key|verify_pdf|verify_layout|robots_check|convert_salary_excel"
FALLBACK = ("`${CLAUDE_SKILL_DIR}` is this skill's folder. If your tool does not expand it, "
            "read paths as relative to the folder containing this SKILL.md.")
MARK = "#### Legacy fork migration"
files = sorted(p for p in REPO.glob("plugins/*/skills/**/*.md") if "node_modules" not in p.parts)
for f in files:
    s = f.read_text(encoding="utf-8")
    skill = f.relative_to(REPO).parts[3]          # plugins/<p>/skills/<skill>/...
    kept = ""
    if MARK in s:                                  # legacy git-history paths stay literal
        head, tail = s.split(MARK, 1)
        parts = tail.split("\n### ", 1)
        kept = MARK + parts[0]
        s_work = head + "\x00KEEP\x00" + ("\n### " + parts[1] if len(parts) > 1 else "")
    else:
        s_work = s
    new = s_work
    # 1. commands referenced as files
    new = re.sub(r"`?\.claude/commands/([a-z-]+)\.md`?", r"`${CLAUDE_SKILL_DIR}/../\1/SKILL.md`", new)
    # 2. skill files referenced by repo path
    def skill_ref(m):
        target, rest = m.group(1), m.group(2)
        if target == skill:
            return "${CLAUDE_SKILL_DIR}/" + rest
        return f"${{CLAUDE_SKILL_DIR}}/../{target}/{rest}"
    new = re.sub(r"\.claude/skills/([a-z-]+)/([\w./-]*)", skill_ref, new)
    # 3. runtime scripts (python / python3 prefixes kept)
    new = re.sub(r"(?<![\w/])tools/(%s)\.py" % RUNTIME, r"${CLAUDE_SKILL_DIR}/../job-tools/scripts/\1.py", new)
    new = re.sub(r"(python3? )salary_lookup\.py", r"\1${CLAUDE_SKILL_DIR}/../job-tools/scripts/salary_lookup.py", new)
    if skill == "job-tools":
        new = new.replace("${CLAUDE_SKILL_DIR}/../job-tools/", "${CLAUDE_SKILL_DIR}/")
    new = new.replace("\x00KEEP\x00", kept)
    if new != s:
        f.write_text(new, encoding="utf-8")
        print("rewrote", f)
PYEOF
```

- [ ] **Step 4: Handle what the codemod cannot**

1. Files **inside** `job-application-assistant/` that are not `SKILL.md` (`04-…`, `05-…`, `09-…`, `10-verification.md`): `${CLAUDE_SKILL_DIR}` is not expanded in a file the skill *reads*, only in `SKILL.md` itself. In those files, rewrite script references to the plain relative form `../job-tools/scripts/<x>.py` and add, once near the top of each such file that now has one, `Paths starting with \`../\` are relative to this file's folder.` Check with: `grep -n 'CLAUDE_SKILL_DIR' plugins/ai-job-search/skills/job-application-assistant/0*.md plugins/ai-job-search/skills/job-application-assistant/10-*.md` → must print nothing.
2. Insert the `FALLBACK` sentence (Global Constraints) as its own paragraph directly after the H1 of every `SKILL.md` that contains `${CLAUDE_SKILL_DIR}` (for converted commands: after the `# /<name> - …` title line).
3. In `SK/job-scraper/SKILL.md` and `SK/upskill/SKILL.md`, add directly after the fallback line: `All state and report files (\`job_scraper/\`, \`upskill/\`, \`job_search_tracker.csv\`) are relative to the workspace root, the folder you run Claude in, and never inside this skill's folder.`
4. `/setup`'s `#### Legacy fork migration` subsection was skipped by the codemod on purpose: its `git show <ref>:.claude/skills/…` paths name files in a fork's *history* and must stay literal. Edit only its references to the *current* templates: in step 5, `.claude/skills/job-application-assistant/profile-templates/candidate.md` (and the `behavioral.md`/`search-queries.md` mentions) → `${CLAUDE_SKILL_DIR}/../job-application-assistant/profile-templates/…`, and the restore command → `git checkout upstream/master -- plugins/ai-job-search/skills/job-application-assistant/profile-templates/`. In step 6, the `git checkout --theirs` example path → `plugins/ai-job-search/skills/job-application-assistant/04-job-evaluation.md`.
5. `CLAUDE.md` Repo Structure: replace the lines `- \`.claude/skills/\` - AI skill definitions…` and `- \`.agents/skills/\` - Job search CLI tools` with `- \`plugins/ai-job-search/\` - The workflow as a Claude Code plugin (skills, portals, helper scripts)`, `- \`plugins/danish-job-portals/\` - Danish job-portal search skills`, `- \`.agents/skills/\` - Your own portal skills from \`/add-portal\``. Replace the `Follow \`.claude/skills/job-application-assistant/10-verification.md\`` sentence with `Follow \`plugins/ai-job-search/skills/job-application-assistant/10-verification.md\``.
6. Update text-asserting tests to the new strings:
   - `tests/test_rank_command.py`: every expected `"tools/rank_state.py …"` → `"${CLAUDE_SKILL_DIR}/../job-tools/scripts/rank_state.py …"`. Leave the `Bash(python tools/rank_state.py:*)` settings assertion at line ~637 for Task 5.
   - `tests/test_apply_page_count.py:35`: regex `"^python tools/verify_pdf\.py (\S+) --pages (\d+)\s*$"` → `"^python3? \$\{CLAUDE_SKILL_DIR\}/\.\./job-tools/scripts/verify_pdf\.py (\S+) --pages (\d+)\s*$"`.

- [ ] **Step 5: Run to verify it passes**

Run: `python3 -m unittest discover -s tests -t . 2>&1 | tail -3` and `python3 tools/lint_skills.py`
Expected: `OK` except tests ledgered as owned by Tasks 5-6; lint OK.

- [ ] **Step 6: Commit**

```bash
git add -A plugins CLAUDE.md tests
git commit -m "refactor(skills): reference plugin files relative to the skill"   # plus trailers
```

---

### Task 5: Permissions live in the skills; the clone loads the plugins

**Files:**
- Modify: `.claude/settings.json`, `tools/security_guards.py`, `tests/test_security_guards.py`, `tests/test_rank_command.py` (settings assertion), `SK/{apply,rank,outcome,gmail-sync,job-scraper,job-application-assistant}/SKILL.md` (`allowed-tools`)
- Test: `tests/test_plugin_layout.py`

**Interfaces:**
- Consumes: path form from Task 4.
- Produces: `security_guards.ALLOWED_SKILL_TOOLS: set[str]` and `check_skill_tools()`.

- [ ] **Step 1: Verify the `Skill(...)` rule form**

```bash
P=/home/mr-fw16/Projects/Source-Codes/ai-job-search/plugins/ai-job-search
for RULE in "Skill(job-application-assistant)" "Skill(ai-job-search:job-application-assistant)"; do
  S=$(mktemp -d); cd $S
  echo "== $RULE"
  timeout 150 claude -p "Load the skill ai-job-search:job-application-assistant with the Skill tool, then reply with exactly LOADED or the exact permission error." \
    --plugin-dir "$P" --model claude-haiku-4-5-20251001 \
    --settings "{\"permissions\":{\"allow\":[\"$RULE\"]}}" 2>&1 | tail -2
  cd - >/dev/null
done
```
Expected: at least one form prints `LOADED`. Use that form in Step 4 (if both do, use the namespaced `Skill(ai-job-search:job-application-assistant)`, which cannot match another plugin's skill). If neither is needed because the Skill tool never prompts, drop the entry from both `settings.json` and `ALLOWED_PERMISSIONS`. Record the outcome in the ledger as a `Ruling:`.

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_plugin_layout.py`:

```python
class TestPermissions(unittest.TestCase):
    def test_settings_load_both_plugins_and_hold_no_script_paths(self):
        data = json.loads(paths.SETTINGS.read_text(encoding="utf-8"))
        self.assertEqual(data["extraKnownMarketplaces"]["ai-job-search"]["source"],
                         {"source": "directory", "path": "./"})
        self.assertIs(data["enabledPlugins"]["ai-job-search@ai-job-search"], True)
        self.assertIs(data["enabledPlugins"]["danish-job-portals@ai-job-search"], True)
        allow = data["permissions"]["allow"]
        self.assertFalse([a for a in allow if "tools/" in a or "salary_lookup" in a or ".agents/skills/" in a], allow)

    def test_script_callers_preapprove_their_scripts(self):
        expected = {
            "apply": ["verify_pdf.py", "verify_layout.py", "salary_lookup.py"],
            "rank": ["rank_state.py"], "outcome": ["rank_state.py"], "gmail-sync": ["rank_state.py"],
            "job-scraper": ["job_key.py"],
        }
        for skill, scripts in expected.items():
            fm = frontmatter(paths.skill_file(skill))
            tools = fm.get("allowed-tools", "")
            for script in scripts:
                self.assertIn(f"Bash(python3 ${{CLAUDE_SKILL_DIR}}/../job-tools/scripts/{script}:*)", tools, skill)
```

Append to `tests/test_security_guards.py` (follow the file's existing temp-repo fixture style; the class below uses its own minimal fixture):

```python
class TestSkillAllowedTools(unittest.TestCase):
    def _run(self, tools_line):
        import importlib, tempfile, shutil
        from pathlib import Path
        tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        skill = tmp / "plugins" / "p" / "skills" / "x"; skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: x\ndescription: d\nallowed-tools: {tools_line}\n---\n# x\n", encoding="utf-8")
        import security_guards
        mod = importlib.reload(security_guards)
        mod.ROOT = tmp
        mod.errors.clear()
        mod.check_skill_tools()
        return list(mod.errors)

    def test_unreviewed_bash_entry_fails(self):
        errs = self._run("Read, Bash(curl:*)")
        self.assertTrue(any("not in the reviewed allowlist" in e for e in errs), errs)

    def test_reviewed_entry_passes(self):
        errs = self._run("Read, Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/rank_state.py:*)")
        self.assertEqual(errs, [])
```

(If `tests/test_security_guards.py` imports `security_guards` differently, reuse its existing import helper instead of `import security_guards`; the dev tools stay in `tools/`, so add `sys.path.insert(0, str(paths.REPO / "tools"))` if that module is not already importable.)

- [ ] **Step 3: Run to verify it fails**

Run: `python3 -m unittest tests.test_plugin_layout.TestPermissions tests.test_security_guards.TestSkillAllowedTools -v`
Expected: FAIL — settings lacks `extraKnownMarketplaces`; skills lack the entries; `check_skill_tools` missing.

- [ ] **Step 4: Implement**

`.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "ai-job-search": { "source": { "source": "directory", "path": "./" } }
  },
  "enabledPlugins": {
    "ai-job-search@ai-job-search": true,
    "danish-job-portals@ai-job-search": true
  },
  "permissions": {
    "allow": [
      "Skill(ai-job-search:job-application-assistant)",
      "Bash(pdftotext:*)"
    ]
  }
}
```

(Use the rule form Step 1 settled on.)

`allowed-tools` lines (add the key to converted skills; append to existing values for `job-scraper`, keeping its current entries except the `tools/job_key.py` ones):
- `apply`: `Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/verify_pdf.py:*), Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/verify_layout.py:*), Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/salary_lookup.py:*), Bash(pdftotext:*)`
- `rank`, `outcome`, `gmail-sync`: `Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/rank_state.py:*)`
- `job-scraper`: replace `Bash(python tools/job_key.py:*), Bash(python3 tools/job_key.py:*)` with `Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/job_key.py:*)`

Make each skill's body invoke scripts as `python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/<x>.py` (not `python`), so the call matches the permission text. Check: `grep -rnE '(^|[^3])python \$\{CLAUDE_SKILL_DIR\}' plugins/` → nothing.

`tools/security_guards.py`:
- `ALLOWED_PERMISSIONS` = `{"Skill(ai-job-search:job-application-assistant)", "Bash(pdftotext:*)"}` (form from Step 1). Keep its comment block, reworded: entries now live in skills.
- Add below it:

  ```python
  # Bash entries a plugin skill may pre-approve in its allowed-tools. Permissions
  # moved out of settings.json into the skills in the plugin layout change, so the
  # review moved with them: a new entry needs a line here in the same PR.
  ALLOWED_SKILL_TOOLS = {
      "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/rank_state.py:*)",
      "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/job_key.py:*)",
      "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/verify_pdf.py:*)",
      "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/verify_layout.py:*)",
      "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/salary_lookup.py:*)",
      "Bash(pdftotext:*)",
      "Bash(bun --version)",
      "Bash(bun run .agents/skills/*/cli/src/cli.ts *)",
      "Bash(bun run ${CLAUDE_SKILL_DIR}/cli/src/cli.ts *)",
      "Bash(bun install --cwd ${CLAUDE_SKILL_DIR}/cli)",
  }


  def check_skill_tools() -> None:
      for skill in sorted(ROOT.glob("plugins/*/skills/*/SKILL.md")):
          text = skill.read_text(encoding="utf-8")
          m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
          if not m:
              continue
          line = next((l for l in m.group(1).splitlines() if l.startswith("allowed-tools:")), "")
          for entry in re.findall(r"Bash\([^)]*\)", line):
              if entry not in ALLOWED_SKILL_TOOLS:
                  errors.append(
                      f"{skill.relative_to(ROOT)}: allowed-tools entry not in the reviewed allowlist: "
                      f"{entry!r}. Add it to ALLOWED_SKILL_TOOLS in tools/security_guards.py in the same PR."
                  )
  ```
  (add `import re` if absent) and call `check_skill_tools()` in `main()`; update the OK message to `security_guards: OK (permissions allowlist, skill allowed-tools, hooks allowlist, gitignore rules, package manifests)`.
- Update `tests/test_security_guards.py` cases that assert the old `ALLOWED_PERMISSIONS` contents or the old OK message.
- `tests/test_rank_command.py` ~line 637: the assertion that settings pre-approves `Bash(python tools/rank_state.py:*)` becomes: `rank/SKILL.md` frontmatter `allowed-tools` contains `Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/rank_state.py:*)`.

- [ ] **Step 5: Run to verify it passes**

Run: `python3 -m unittest discover -s tests -t . 2>&1 | tail -3`; `python3 tools/security_guards.py`; `python3 tools/lint_skills.py`
Expected: OK except tests ledgered for Task 6; both tools OK.

- [ ] **Step 6: Commit**

```bash
git add -A .claude tools tests plugins
git commit -m "feat(permissions): skills pre-approve their own scripts; clone loads the plugins"   # plus trailers
```

---

### Task 6: Portals and /scrape discovery

**Files:**
- Modify: 6 portal `SKILL.md` files (paths, `allowed-tools`, Danish install step), `SK/job-scraper/SKILL.md` (Step 1b, 1c), `SK/add-portal/SKILL.md`
- Test: `tests/test_plugin_layout.py`, `tests/test_scrape_contract.py` (if it asserts `.agents/skills/…` text)

**Interfaces:**
- Consumes: `paths.portal_dirs()`, `ALLOWED_SKILL_TOOLS` (Task 5, already contains the portal entries).
- Produces: portal skills runnable from any install location.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plugin_layout.py`:

```python
class TestPortals(unittest.TestCase):
    def test_portals_run_their_cli_from_their_own_folder(self):
        for d in paths.portal_dirs():
            text = (d / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn(".agents/skills/", text, d.name)
            self.assertIn("bun run ${CLAUDE_SKILL_DIR}/cli/src/cli.ts", text, d.name)
            self.assertIn("Bash(bun run ${CLAUDE_SKILL_DIR}/cli/src/cli.ts *)", frontmatter(d / "SKILL.md").get("allowed-tools", ""), d.name)

    def test_danish_portals_self_install(self):
        for d in paths.portal_dirs():
            deps = json.loads((d / "cli" / "package.json").read_text(encoding="utf-8")).get("dependencies", {})
            text = (d / "SKILL.md").read_text(encoding="utf-8")
            if deps:
                self.assertIn("bun install --cwd ${CLAUDE_SKILL_DIR}/cli", text, d.name)
                self.assertIn("Bash(bun install --cwd ${CLAUDE_SKILL_DIR}/cli)",
                              frontmatter(d / "SKILL.md").get("allowed-tools", ""), d.name)

    def test_scrape_discovers_plugin_and_workspace_portals(self):
        text = paths.skill_file("job-scraper").read_text(encoding="utf-8")
        self.assertIn("ends in `-search`", text)
        self.assertIn("Skill tool", text)
        self.assertIn(".agents/skills/*/SKILL.md", text)

    def test_scrape_subagents_load_portal_skill(self):
        text = paths.skill_file("job-scraper").read_text(encoding="utf-8")
        self.assertIn("each subagent must first load its portal skill with the Skill tool", text)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_plugin_layout.TestPortals -v`
Expected: FAIL — portal text still says `.agents/skills/<name>/cli/...`; scrape text unchanged.

- [ ] **Step 3: Rewrite the portal skills**

```bash
python3 - <<'PYEOF'
import re, json
from pathlib import Path
FALLBACK = ("`${CLAUDE_SKILL_DIR}` is this skill's folder. If your tool does not expand it, "
            "read paths as relative to the folder containing this SKILL.md.")
for d in sorted(Path("plugins").glob("*/skills/*-search")):
    for other in d.rglob("*.md"):                 # url-reference.md, cli/README.md
        if other.name != "SKILL.md" and "node_modules" not in other.parts:
            t = other.read_text(encoding="utf-8")
            other.write_text(t.replace(f".agents/skills/{d.name}/", ""), encoding="utf-8")
    p = d / "SKILL.md"
    s = p.read_text(encoding="utf-8")
    s = s.replace(f".agents/skills/{d.name}/", "${CLAUDE_SKILL_DIR}/")
    deps = json.loads((d / "cli" / "package.json").read_text(encoding="utf-8")).get("dependencies", {})
    m = re.match(r"^---\n(.*?)\n---\n", s, re.DOTALL)
    fm, body = m.group(1), s[m.end():]
    if deps and "bun install --cwd" not in fm:
        fm = re.sub(r"^(allowed-tools: .*)$", r"\1, Bash(bun install --cwd ${CLAUDE_SKILL_DIR}/cli)", fm, flags=re.M)
    lines = body.split("\n")
    h1 = next(i for i, l in enumerate(lines) if l.startswith("# "))
    insert = ["", FALLBACK]
    if deps:
        insert += ["", "**First run after an install or update:** if `${CLAUDE_SKILL_DIR}/cli/node_modules` is missing, run `bun install --cwd ${CLAUDE_SKILL_DIR}/cli` before any command below. Bun's auto-install cannot resolve this CLI's dependencies."]
    if FALLBACK not in body:
        lines[h1 + 1:h1 + 1] = insert
    p.write_text("---\n" + fm + "\n---\n" + "\n".join(lines), encoding="utf-8")
    print("rewrote", p)
PYEOF
```

Check: `grep -n 'allowed-tools' plugins/*/skills/*-search/SKILL.md` — each shows `Bash(bun run ${CLAUDE_SKILL_DIR}/cli/src/cli.ts *)` (and the install entry for the 4 Danish ones).

- [ ] **Step 4: Rewrite `/scrape` discovery**

In `SK/job-scraper/SKILL.md` Step 1b, replace the paragraph starting `Discover all installed portal CLI skills by reading every \`SKILL.md\` found under \`.agents/skills/*/SKILL.md\`.` (up to the end of that paragraph) with:

```markdown
Discover the installed portal CLI skills in two places:

1. **Portals from installed plugins:** every available skill whose name ends in `-search` and whose instructions run a `cli/src/cli.ts` command. Load each one with the Skill tool; its content gives the exact `bun run …` invocation, flags and examples, and loading it pre-approves that CLI.
2. **Your own portals:** every `.agents/skills/*/SKILL.md` in the workspace (written by `/add-portal`). Read these files directly.

Each portal documents its own flags and usage. **Use each portal's own documented interface — do not guess flags.** List which portals you used, and from which of the two places, in the Step 5 summary.
```

Replace `Run all portal CLI calls in parallel where possible using the Agent tool.` with `Run all portal CLI calls in parallel where possible using the Agent tool: each subagent must first load its portal skill with the Skill tool (plugin portals), so the portal's own permissions apply inside the subagent.`

In Step 1c, replace `that do **not** have a corresponding directory under \`.agents/skills/\`` with `that have no portal skill in either place above`.

- [ ] **Step 5: Probe the subagent path**

```bash
S=$(mktemp -d) && cd $S && timeout 280 claude -p "Use the Agent tool to start one subagent. The subagent must load the skill linkedin-search with the Skill tool and then run its CLI with --help. Report the first 3 lines of output or the exact permission error." \
  --plugin-dir /home/mr-fw16/Projects/Source-Codes/ai-job-search/plugins/ai-job-search \
  --model claude-haiku-4-5-20251001 --allowedTools "Skill,Agent" 2>&1 | tail -6; cd -
```
Expected: CLI help output (no permission error). If it reports a permission error, record `Task 6: Ruling:` in the ledger and add `Bash(bun run ${CLAUDE_SKILL_DIR}/../linkedin-search/cli/src/cli.ts *)`-style sibling entries to `job-scraper`'s `allowed-tools` for the core portals (and to `ALLOWED_SKILL_TOOLS`), then re-probe.

- [ ] **Step 6: Update `/add-portal`**

In `SK/add-portal/SKILL.md`:
- `**Canonical reference:** read \`.agents/skills/linkedin-search/\`` → `**Canonical reference:** read \`${CLAUDE_SKILL_DIR}/../linkedin-search/\``.
- `--list` handling: `use Glob with \`.agents/skills/*/SKILL.md\`` → `list the available skills whose name ends in \`-search\` (plugin portals) plus \`.agents/skills/*/SKILL.md\` (your own)`.
- The `cli-checks` sentence: `the \`cli-checks\` job discovers every \`.agents/skills/*/cli/package.json\`` → `the \`cli-checks\` job discovers every \`cli/package.json\` under \`plugins/*/skills/\` and \`.agents/skills/\``.
- Generated portals keep `.agents/skills/<name>/` and cwd-relative `bun run .agents/skills/<name>/cli/src/cli.ts` (workspace skills are not in a plugin): leave those lines.
- Ensure the fallback line sits after its H1 (Task 4 may have added it already).

- [ ] **Step 7: Run to verify it passes**

Run: `python3 -m unittest discover -s tests -t . 2>&1 | tail -3`; `python3 tools/lint_skills.py && python3 tools/security_guards.py`
Expected: all OK, no ledgered expected-reds left.

- [ ] **Step 8: Commit**

```bash
git add -A plugins tests
git commit -m "feat(portals): run portal CLIs from the plugin; /scrape finds plugin and workspace portals"   # plus trailers
```

---

### Task 7: Docs, versions, changelog

**Files:**
- Modify: `README.md`, `SETUP.md`, `AGENTS.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `framework_version` in edited `FW/*.md` files
- Test: `tests/test_plugin_layout.py`

**Interfaces:**
- Consumes: final layout.
- Produces: SETUP.md heading `## 10. Upgrading across the plugin layout change`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plugin_layout.py`:

```python
class TestDocs(unittest.TestCase):
    def test_readme_explains_both_install_routes_and_capa(self):
        text = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("/plugin marketplace add MadsLorentzen/ai-job-search", text)
        self.assertIn("/plugin install ai-job-search@ai-job-search", text)
        self.assertIn("capa registry add MadsLorentzen/ai-job-search", text)
        self.assertIn("untested outside Claude Code", text)
        self.assertNotIn(".claude/commands/", text)

    def test_setup_md_has_the_upgrade_section(self):
        text = (REPO / "SETUP.md").read_text(encoding="utf-8")
        section = text.split("## 10. Upgrading across the plugin layout change", 1)[1].split("\n## ", 1)[0]
        for needle in ("trust", "plugins/ai-job-search/skills/", "settings.local.json", "danish-job-portals"):
            self.assertIn(needle, section)

    def test_agents_md_and_contributing_point_at_capa(self):
        for name in ("AGENTS.md", "CONTRIBUTING.md"):
            text = (REPO / name).read_text(encoding="utf-8")
            self.assertIn("capa", text, name)
            self.assertNotIn("auto-discovered", text, name)

    def test_changelog_flags_the_layout_break(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = text.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0]
        self.assertIn("BREAKING (forks): the framework moves into plugins", unreleased)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_plugin_layout.TestDocs -v`
Expected: FAIL on all four.

- [ ] **Step 3: Write the docs**

README.md:
- File structure tree: replace the `.claude/` subtree and `.agents/skills/` subtree with `.claude-plugin/marketplace.json`, `plugins/ai-job-search/` (with `skills/` listing the 12 converted command skills, `job-application-assistant/`, `job-scraper/`, `upskill/`, `job-tools/`, `linkedin-search/`, `freehire-search/`, and `agents/`), `plugins/danish-job-portals/skills/` (4 portals), `.agents/skills/` ("your own portals from /add-portal"), `.claude/settings.json` ("loads both plugins in place"). Move `salary_lookup.py` and the runtime tools out of the root/`tools/` lines into `job-tools/scripts/`.
- Quick start, after the clone step, a new subsection `### Load the plugins`: "Start Claude Code in the clone and accept the folder-trust prompt. `.claude/settings.json` then loads both plugins from `plugins/` in place: `/apply`, `/setup` and the rest are plugin skills now. Nothing loads until the folder is trusted."
- A section `## Install as a plugin (without cloning)`: `/plugin marketplace add MadsLorentzen/ai-job-search`, `/plugin install ai-job-search@ai-job-search`, optionally `/plugin install danish-job-portals@ai-job-search`, then "run Claude in an empty folder and `/setup`" (workspace init arrives in a later release).
- A section `## Using other harnesses (capa)`: `capa registry add MadsLorentzen/ai-job-search` then `capa add ai-job-search:ai-job-search`; one sentence: "This is untested outside Claude Code: capa copies the skills into your harness, and each skill falls back to paths relative to its own folder."
- Replace every remaining `.claude/commands/<x>.md` / `.claude/skills/...` path with the plugin path.

SETUP.md: append before `## Troubleshooting`:

```markdown
## 10. Upgrading across the plugin layout change

The framework now ships as two Claude Code plugins inside this repo (`plugins/ai-job-search/`, `plugins/danish-job-portals/`).

1. After merging, start Claude Code in your clone and accept the folder-trust prompt once. Until you do, the plugins do not load and `/apply` and the other commands are missing.
2. If you had edited a command, your edit followed the rename: `.claude/commands/<x>.md` is now `plugins/ai-job-search/skills/<x>/SKILL.md`, with a short frontmatter block added on top. A conflict there resolves like any other.
3. Your own portals from `/add-portal` stay in `.agents/skills/`. The shipped ones moved into the plugins.
4. Not in Denmark? Turn the Danish portals off in `.claude/settings.local.json`: `{"enabledPlugins": {"danish-job-portals@ai-job-search": false}}`.
5. `salary_data.json` stays in your repo root; the salary tool now looks for it in the folder you run Claude in.
```

Also in SETUP.md section 9, change `git checkout MERGE_HEAD -- .claude/skills/job-application-assistant/profile-templates/` to `git checkout MERGE_HEAD -- plugins/ai-job-search/skills/job-application-assistant/profile-templates/` (a fork upgrading now receives the templates at their plugin path), and update the matching string in `tests/test_profile_separation.py` (`test_setup_md_restores_templates_before_committing_the_merge`).

AGENTS.md (bump `framework_version` 1.1.0 → 1.2.0): replace pointer 2's `.claude/` paths with `plugins/ai-job-search/skills/`; replace pointer 3 with: "Portal search skills ship inside the plugins (`plugins/*/skills/*-search/`) in the Agent Skills format. Other runtimes can install them, and the whole workflow, through capa (`capa registry add MadsLorentzen/ai-job-search`). Your own portals from `/add-portal` live in `.agents/skills/`."

CONTRIBUTING.md "Porting to another AI runtime": replace the bullet "The portal search skills in `.agents/skills/` use the portable Agent Skills format … auto-discovered by Codex and Antigravity today." with "The framework ships as Claude Code plugins in the portable Agent Skills format; capa (`capa registry add MadsLorentzen/ai-job-search`) installs them into other runtimes. Untested there, and CI cannot run those harnesses." Replace any other `.claude/commands`/`.claude/skills`/`tools/<runtime>` path with the plugin path, and "auto-discovered" wording with the capa sentence.

CHANGELOG.md, top of `## [Unreleased]` → `### Changed`:

```markdown
- **BREAKING (forks): the framework moves into plugins** (`.claude-plugin/marketplace.json`,
  `plugins/ai-job-search/`, `plugins/danish-job-portals/`, `.claude/settings.json`,
  `tools/security_guards.py`) - commands become user-only plugin skills (still `/apply`
  etc.), the six shipped portals and the runtime scripts move into the plugins, and each
  skill pre-approves its own scripts in `allowed-tools`, reviewed by a new
  `security_guards.py` check. The clone loads both plugins in place once the folder is
  trusted; `/plugin marketplace add MadsLorentzen/ai-job-search` installs them anywhere.
  `salary_data.json` is read from the workspace root. Upgrading: SETUP.md section 10.
```

Framework versions: run `GITHUB_BASE_REF=plugin/1-profile-separation python3 tools/check_framework_version.py` and bump (minor) every file it names.

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_plugin_layout tests.test_changelog_structure -v 2>&1 | tail -3`; `GITHUB_BASE_REF=plugin/1-profile-separation python3 tools/check_framework_version.py`
Expected: OK; `Framework Version Check: OK`.

- [ ] **Step 5: Commit**

```bash
git add README.md SETUP.md AGENTS.md CONTRIBUTING.md CHANGELOG.md plugins tests
git commit -m "docs: document the plugin layout, install routes and capa"   # plus trailers
```

---

### Task 8: Verification

**Files:** none unless a check fails.

- [ ] **Step 1: Everything CI runs**

```bash
python3 -m unittest discover -s tests -t . 2>&1 | tail -2
python3 tools/lint_skills.py && python3 tools/security_guards.py
GITHUB_BASE_REF=plugin/1-profile-separation python3 tools/check_framework_version.py
```
Expected: OK / exit 0 for each.

- [ ] **Step 2: Plugin validation**

```bash
claude plugin validate . 2>&1 | tail -3
claude --plugin-dir plugins/ai-job-search plugin details ai-job-search 2>&1 | sed -n 1,12p
claude --plugin-dir plugins/danish-job-portals plugin details danish-job-portals 2>&1 | grep Skills
```
Expected: validation passes; the core plugin lists 18 skills (12 converted + job-application-assistant, scrape, upskill, job-tools, linkedin-search, freehire-search) and 1 agent; the market plugin lists 4 skills.

- [ ] **Step 3: Portal CLIs from the plugin folders**

```bash
(cd plugins/ai-job-search/skills/linkedin-search/cli && bun run src/cli.ts --help | head -3)
D=$(mktemp -d) && cp -r plugins/danish-job-portals/skills/jobnet-search/cli $D/ && rm -rf $D/cli/node_modules \
  && bun install --cwd $D/cli >/dev/null && (cd $D/cli && bun run src/cli.ts --help | head -3)
```
Expected: both print help text (the second proves the documented self-install works from a fresh copy).

- [ ] **Step 4: Headless end-to-end from a plugin install**

```bash
S=$(mktemp -d) && cd $S && timeout 280 claude -p "/ai-job-search:apply Data Scientist at Nordlys Analytics (Copenhagen). Python, SQL, 3+ years ML." \
  --plugin-dir /home/mr-fw16/Projects/Source-Codes/ai-job-search/plugins/ai-job-search \
  --model claude-haiku-4-5-20251001 --allowedTools "Read,Glob,Grep,Skill" 2>&1 | tail -4; cd -
```
Expected: the Profile Guard stops it with "run `/setup` first" (an empty folder has no `profile/`). This proves the converted skill loads from the plugin and reaches the guard through `${CLAUDE_SKILL_DIR}/../job-application-assistant/`.

- [ ] **Step 5: Record and commit fixes**

Record every result in the ledger. If a step failed, fix it test-first and commit: `fix: address plugin layout verification findings` (plus trailers).
