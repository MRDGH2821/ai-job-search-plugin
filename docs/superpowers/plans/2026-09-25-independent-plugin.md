# Independent ai-job-search-plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the fork into the independent, plugin-only project `ai-job-search-plugin`, keeping a path-mapped view of upstream changes for porting.

**Architecture:** Rename the core plugin, marketplace, markers and identity. Delete the root workspace folders (the plugin's `workspace-template/` is the only copy) and point CI and tests at the template. Replace per-file `framework_version` with the plugin version and a bump test. Remove upstream-only migrations and tools. Teach `upstream_triage.py` a path map and a "handled" list. Rewrite the docs.

**Tech Stack:** Python 3 stdlib, markdown skills, stdlib `unittest`, GitHub Actions, git, `gh`.

**Spec:** `docs/superpowers/specs/2026-09-25-independent-plugin-design.md`.

## Global Constraints

- Branch `plugin/5-independent`, stacked on `plugin/4-workspace-init`. `stash@{0}` is unrelated; leave it.
- New names, exactly: marketplace `ai-job-search-plugin`; core plugin folder `plugins/ai-job-search-plugin/`, `plugin.json` `name` `ai-job-search-plugin`; install ids `ai-job-search-plugin@ai-job-search-plugin`, `danish-job-portals@ai-job-search-plugin`; command prefix `/ai-job-search-plugin:`; markers `<!-- ai-job-search-plugin:start v<version> -->` / `<!-- ai-job-search-plugin:end -->`.
- Identity: author/owner `MRDGH2821`; homepage/repository `https://github.com/MRDGH2821/ai-job-search-plugin`; both plugins `version` `2.0.0`.
- History files keep old names on purpose and are excluded from every rename and old-name check: `CHANGELOG.md` (entries below the new top section), `docs/superpowers/**`.
- `MadsLorentzen` may appear only in: `LICENSE`, `README.md`, `SETUP.md`, `CHANGELOG.md`, `docs/superpowers/**`, `tools/upstream_triage.py`, `tools/upstream_paths.py`, `.github/workflows/upstream-watch.yml`, `.github/upstream-handled.txt`, `tests/**`.
- The GitHub repo rename (`gh repo rename`) runs only in Task 6, only after the user confirms with AskUserQuestion.
- Tests: `python3 -m unittest discover -s tests -t . -v`. This machine: `git log --no-show-signature`; `claude -p` probes use `--model claude-haiku-4-5-20251001`. No LaTeX locally.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01C8revGiLzJ6ZYvz6LZMmZa`. Finish: keep the branch as-is.

## Review Focus

1. **A workspace created by an earlier build** (old `ai-job-search` markers in its `AGENTS.md`) → the next sync replaces the old block with the new one; no duplicate block. Pinned in Task 1 (`test_legacy_markers_are_upgraded`).
2. **An old id left in a skill** (`Skill(ai-job-search:…)`, `/ai-job-search:setup`, `plugins/ai-job-search/`) → a command or permission that silently doesn't match. Pinned in Task 1 (`test_no_old_ids_in_tracked_files`).
3. **CI compiling nothing** after the root `cv/` disappears → the LaTeX job must build from an init-created workspace. Pinned in Task 2 (`test_ci_compiles_from_an_init_workspace`).
4. **An upstream commit to `.claude/commands/apply.md`** → reported as relevant, mapped to our `SKILL.md`, not auto-skipped. Pinned in Task 4 (`test_command_commit_is_mapped_and_relevant`).
5. **A change under `plugins/` without a version bump** → users never get the update. Pinned in Task 3 (`test_changed_plugin_bumps_version`).

---

### Task 1: Rename to ai-job-search-plugin

**Files:** `git mv plugins/ai-job-search plugins/ai-job-search-plugin`; modify `.claude-plugin/marketplace.json`, both `plugin.json`, `.claude/settings.json`, `tools/security_guards.py`, `tests/paths.py`, `JT/sync_instructions.py` (`JT` = `plugins/ai-job-search-plugin/skills/job-tools/scripts`), every tracked text file outside the history files; create `tests/test_independent.py`.

**Interfaces:** Produces `tests/paths.py` constants pointing at `plugins/ai-job-search-plugin`; `sync_instructions.LEGACY_START_RE`, `LEGACY_END`.

- [ ] **Step 1: Failing tests**

`tests/test_independent.py`:

```python
"""Independent ai-job-search-plugin (spec: docs/superpowers/specs/2026-09-25-independent-plugin-design.md)."""
import json
import subprocess
import unittest

from tests import paths

REPO = paths.REPO
HISTORY = ("CHANGELOG.md", "docs/superpowers/")
OLD_IDS = ("ai-job-search@ai-job-search\"", "ai-job-search@ai-job-search`", "ai-job-search@ai-job-search ",
           "plugins/ai-job-search/", "<!-- ai-job-search:start", "<!-- ai-job-search:end",
           "/ai-job-search:", "Skill(ai-job-search:", "danish-job-portals@ai-job-search\"",
           "danish-job-portals@ai-job-search`", "danish-job-portals@ai-job-search ")


def tracked_text_files():
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    for rel in out.splitlines():
        if rel.startswith(HISTORY) or not (REPO / rel).is_file():
            continue
        try:
            yield rel, (REPO / rel).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


class TestNames(unittest.TestCase):
    def test_marketplace_and_plugins(self):
        m = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(m["name"], "ai-job-search-plugin")
        self.assertEqual(m["owner"]["name"], "MRDGH2821")
        self.assertEqual({p["name"]: p["source"] for p in m["plugins"]},
                         {"ai-job-search-plugin": "./plugins/ai-job-search-plugin",
                          "danish-job-portals": "./plugins/danish-job-portals"})
        for folder in ("ai-job-search-plugin", "danish-job-portals"):
            pj = json.loads((REPO / "plugins" / folder / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
            self.assertEqual(pj["author"]["name"], "MRDGH2821")
            self.assertEqual(pj["homepage"], "https://github.com/MRDGH2821/ai-job-search-plugin")
            self.assertEqual(pj["repository"], "https://github.com/MRDGH2821/ai-job-search-plugin")
        self.assertFalse((REPO / "plugins" / "ai-job-search").exists())

    def test_settings_use_new_ids(self):
        s = json.loads(paths.SETTINGS.read_text(encoding="utf-8"))
        self.assertIn("ai-job-search-plugin", s["extraKnownMarketplaces"])
        self.assertEqual(set(s["enabledPlugins"]),
                         {"ai-job-search-plugin@ai-job-search-plugin", "danish-job-portals@ai-job-search-plugin"})
        self.assertIn("Skill(ai-job-search-plugin:job-application-assistant)", s["permissions"]["allow"])

    def test_no_old_ids_in_tracked_files(self):
        offenders = []
        for rel, text in tracked_text_files():
            if rel.endswith("sync_instructions.py") or rel.startswith("tests/"):
                continue  # the script recognizes legacy markers; tests name them
            for old in OLD_IDS:
                if old in text:
                    offenders.append(f"{rel}: {old}")
        self.assertEqual(offenders, [])
```

Append to `tests/test_sync_instructions.py`:

```python
class LegacyMarkerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_legacy_markers_are_upgraded(self):
        (self.root / "AGENTS.md").write_text(
            "mine\n<!-- ai-job-search:start v1.0.0 -->\nold\n<!-- ai-job-search:end -->\ntail\n", encoding="utf-8")
        proc = run(self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("mine\n<!-- ai-job-search-plugin:start v"))
        self.assertTrue(text.endswith("<!-- ai-job-search-plugin:end -->\ntail\n"))
        self.assertNotIn("<!-- ai-job-search:start", text)
        self.assertEqual(run(self.root, "--check").returncode, 0)

    def test_mixed_old_and_new_markers_are_malformed(self):
        (self.root / "AGENTS.md").write_text(
            "<!-- ai-job-search:start v1 -->\nx\n<!-- ai-job-search-plugin:end -->\n", encoding="utf-8")
        self.assertEqual(run(self.root).returncode, 2)
```

In `tests/test_sync_instructions.py` also change the module constants `START`/`END` to the new markers: `START = "<!-- ai-job-search-plugin:start v"`, `END = "<!-- ai-job-search-plugin:end -->"`.

- [ ] **Step 2: Run RED.** `python3 -m unittest tests.test_independent tests.test_sync_instructions -v 2>&1 | tail -3` → FAIL/ERROR (old names everywhere; legacy markers unknown).

- [ ] **Step 3: Rename**

```bash
git mv plugins/ai-job-search plugins/ai-job-search-plugin
python3 - <<'PYEOF'
import re, subprocess
from pathlib import Path
HISTORY = ("CHANGELOG.md", "docs/superpowers/")
SKIP = {"tools/upstream_triage.py", ".github/workflows/upstream-watch.yml"}
rules = [
    (r"plugins/ai-job-search/", "plugins/ai-job-search-plugin/"),
    (r"ai-job-search@ai-job-search(?![\w-])", "ai-job-search-plugin@ai-job-search-plugin"),
    (r"danish-job-portals@ai-job-search(?![\w-])", "danish-job-portals@ai-job-search-plugin"),
    (r"(?<![\w-])/ai-job-search:", "/ai-job-search-plugin:"),
    (r"Skill\(ai-job-search:", "Skill(ai-job-search-plugin:"),
    (r"(?<![\w/-])ai-job-search:(?=[a-z])", "ai-job-search-plugin:"),
    (r"<!-- ai-job-search:start", "<!-- ai-job-search-plugin:start"),
    (r"<!-- ai-job-search:end -->", "<!-- ai-job-search-plugin:end -->"),
    (r"`ai-job-search` Claude Code plugin", "`ai-job-search-plugin` Claude Code plugin"),
    (r"Job search workspace \(ai-job-search\)", "Job search workspace (ai-job-search-plugin)"),
]
files = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split()
for rel in files:
    if rel.startswith(HISTORY) or rel in SKIP or rel.startswith("tests/") or rel.endswith("sync_instructions.py"):
        continue
    p = Path(rel)
    try:
        s = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
        continue
    new = s
    for pat, rep in rules:
        new = re.sub(pat, rep, new)
    if new != s:
        p.write_text(new, encoding="utf-8"); print("renamed in", rel)
PYEOF
```

Then by hand:
- `.claude-plugin/marketplace.json`: `name` → `ai-job-search-plugin`; `owner` → `{"name": "MRDGH2821"}`; the core entry `name`/`source` → `ai-job-search-plugin` / `./plugins/ai-job-search-plugin`; description unchanged otherwise.
- Both `plugin.json`: core `name` → `ai-job-search-plugin`; `author` → `{"name": "MRDGH2821"}`; `homepage`/`repository` → `https://github.com/MRDGH2821/ai-job-search-plugin`.
- `.claude/settings.json`: marketplace key → `ai-job-search-plugin`; `enabledPlugins` keys → `ai-job-search-plugin@ai-job-search-plugin` (true), `danish-job-portals@ai-job-search-plugin` (false); allow entry `Skill(ai-job-search-plugin:job-application-assistant)`.
- `tools/security_guards.py`: `ALLOWED_PERMISSIONS` entry, `ALLOWED_MARKETPLACES` key `ai-job-search-plugin`, `ALLOWED_PLUGINS` new ids, `WORKSPACE_GITIGNORE` path, every `plugins/ai-job-search/skills` in globs/constants.
- `tests/paths.py`: `PLUGIN = REPO / "plugins" / "ai-job-search-plugin"`. Run `grep -rn '"ai-job-search"' tests/*.py` and change any `"plugins" / "ai-job-search"` path pieces to `"ai-job-search-plugin"`; update test expectations that name old ids (`test_plugin_layout.py` marketplace test, `test_security_guards.py` fixtures) to the new ids.
- `JT/sync_instructions.py`:

```python
START_RE = re.compile(r"^<!-- ai-job-search-plugin:start(?: v\S+)? -->$")
END = "<!-- ai-job-search-plugin:end -->"
# Workspaces created before the rename carry these; a sync replaces them.
LEGACY_START_RE = re.compile(r"^<!-- ai-job-search:start(?: v\S+)? -->$")
LEGACY_END = "<!-- ai-job-search:end -->"
```

and in `locate()`:

```python
def locate(lines: list[str]) -> tuple[int, int] | None:
    def find(start_re, end):
        return ([i for i, line in enumerate(lines) if start_re.match(line.strip())],
                [i for i, line in enumerate(lines) if line.strip() == end])
    new_s, new_e = find(START_RE, END)
    old_s, old_e = find(LEGACY_START_RE, LEGACY_END)
    if (new_s or new_e) and (old_s or old_e):
        raise MarkerError("AGENTS.md: both old (ai-job-search) and new (ai-job-search-plugin) markers are present. "
                          "Keep one block; nothing was written.")
    starts, ends = (new_s, new_e) if (new_s or new_e) else (old_s, old_e)
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise MarkerError(
            "AGENTS.md: malformed markers "
            f"(start on line(s) {[s + 1 for s in starts]}, end on line(s) {[e + 1 for e in ends]}). "
            "Fix them by hand; nothing was written."
        )
    return starts[0], ends[0]
```

Re-run the root sync so the repo's own `AGENTS.md` block carries the new markers: `python3 plugins/ai-job-search-plugin/skills/job-tools/scripts/sync_instructions.py`.

- [ ] **Step 4: GREEN.** `python3 -m unittest discover -s tests -t . 2>&1 | tail -2`; `python3 tools/lint_skills.py && python3 tools/security_guards.py`; `claude plugin validate .`. Expected: all OK.

- [ ] **Step 5: Commit** `refactor: rename to ai-job-search-plugin` (plus trailers).

---

### Task 2: The repository is plugin source, not a workspace

**Files:** delete root `cv/ cover_letters/ templates/ documents/ job_scraper/ company_research/ upskill/`; rewrite root `.gitignore`, `AGENTS.md`; modify `tools/security_guards.py`, `.github/workflows/ci.yml`, `tests/paths.py`, tests reading root workspace files, `tests/test_workspace_init.py`, `tests/test_sync_instructions.py`.

**Interfaces:** `tests/paths.py` gains `WT = SKILLS / "job-tools" / "workspace-template"`; `security_guards.ROOT_REQUIRED_IGNORE_RULES`.

- [ ] **Step 1: Failing tests** — append to `tests/test_independent.py`:

```python
ROOT_WORKSPACE = ("cv", "cover_letters", "templates", "documents", "job_scraper", "company_research", "upskill")


class TestNotAWorkspace(unittest.TestCase):
    def test_root_has_no_workspace_folders(self):
        self.assertEqual([d for d in ROOT_WORKSPACE if (REPO / d).exists()], [])

    def test_root_gitignore_guards_personal_data(self):
        rules = {l.strip() for l in (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()}
        for rule in ("profile/", "salary_data.json", ".env", ".env.*"):
            self.assertIn(rule, rules)

    def test_ci_compiles_from_an_init_workspace(self):
        ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("init_workspace.py --root", ci)
        self.assertNotIn("cd cv\n", ci)
        self.assertNotIn("github.repository == 'MadsLorentzen", ci)

    def test_agents_md_is_a_contributor_guide(self):
        text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("## Working on this plugin", text)
        self.assertNotIn("<!-- ai-job-search-plugin:start", text)
```

- [ ] **Step 2: RED.** Expected FAIL ×4.

- [ ] **Step 3: Implement**
- `git rm -r -q cv cover_letters templates documents job_scraper company_research upskill`.
- Root `.gitignore`: replace with

```gitignore
# Python
__pycache__/
*.pyc
.venv/
venv/

# Dependencies
node_modules/
bun.lock

# Build output
*.pdf
*.aux
*.log
*.out
build/

# Editors and OS
.vscode/
.idea/
.DS_Store
Thumbs.db

# Claude Code local state
.claude/projects/
.claude/settings.local.json

# Personal data must never land in the plugin repository
profile/
salary_data.json
.env
.env.*

# Brainstorm scratch
.superpowers/
```

- `tools/security_guards.py`: add `ROOT_REQUIRED_IGNORE_RULES = ["profile/", "salary_data.json", ".env", ".env.*"]`; `check_gitignore()` checks the root `.gitignore` against `ROOT_REQUIRED_IGNORE_RULES` (and the negation allowlist), and `gitignore.template` against `REQUIRED_IGNORE_RULES` (unchanged list). Update `tests/test_security_guards.py` gitignore fixtures accordingly (root fixture uses the short list).
- `AGENTS.md`: replace with a contributor guide: title `# ai-job-search-plugin: contributor guide`; `## Working on this plugin` (repo = plugin marketplace; `plugins/ai-job-search-plugin/` core, `plugins/danish-job-portals/`; workspace files live in `job-tools/workspace-template/`, never at the root; open Claude Code here and trust the folder to load the plugins in place; create a test workspace with `/init-workspace` in a separate folder); `## Checks` (`python3 -m unittest discover -s tests -t .`, `python3 tools/lint_skills.py`, `python3 tools/security_guards.py`); `## Conventions` (one concern per PR; bump `plugin.json` `version` when `plugins/` changes; a new `allowed-tools` Bash entry needs an `ALLOWED_SKILL_TOOLS` line; skills that run commands say "as one command, no `cd`, no `&&`"; workspace data is always relative to the current directory); `## Tracking the original project` (`python3 tools/upstream_triage.py --remote upstream`; record ported/rejected SHAs in `.github/upstream-handled.txt`).
- `.github/workflows/ci.yml` LaTeX job: add a step before the compiles:

```yaml
      - name: Create a workspace from the plugin template
        run: python3 plugins/ai-job-search-plugin/skills/job-tools/scripts/init_workspace.py --root "$RUNNER_TEMP/ws"
```

  change `cd cv` → `cd "$RUNNER_TEMP/ws/cv"` and `cd cover_letters` → `cd "$RUNNER_TEMP/ws/cover_letters"`; the verify steps use `"$RUNNER_TEMP/ws/cv/main_example.pdf"` and `"$RUNNER_TEMP/ws/cover_letters/cover_example.pdf"`; drop the `if: github.repository == …` line on "Assert stock PDF structure" and rename the step to "Assert stock PDF structure". In the placeholder-integrity job drop its `if:` and point `check` lines at `plugins/ai-job-search-plugin/skills/job-tools/workspace-template/cv/main_example.tex`, `…/workspace-template/cover_letters/cover_example.tex` and the two profile templates; keep the "`profile/` must not exist" block. Update the header comment ("forks personalize…") to: `# CI for the plugin: LaTeX smoke compiles from a freshly initialized workspace, skill lint, CLI typechecks, placeholder integrity and security guards.`
- Tests: add `WT` to `tests/paths.py`. Run
  `grep -nE '(REPO|REPO_ROOT|ROOT) / "(cv|cover_letters|templates|documents|job_scraper|company_research|upskill)"|git", "ls-files", "documents' tests/*.py`
  and point each at `paths.WT / "<same>"` (a `git ls-files documents/` becomes `git ls-files <WT>/documents/` with the prefix stripped). In `tests/test_workspace_init.py` delete class `TestTemplateSync` and `test_clone_root_gitignore_needs_no_additions`; keep `test_no_template_file_is_ignored`. In `tests/test_sync_instructions.py` delete class `RepoRootTests` except `test_readme_and_changelog_mention_the_command`, and change the branch-1 assertion in `tests/test_profile_separation.py::test_claude_md_holds_no_personal_data` to read the `10-verification.md`/`profile/` facts from `plugins/ai-job-search-plugin/skills/job-tools/scripts/agents-block.md` instead of `AGENTS.md`.

- [ ] **Step 4: GREEN** (suite, lint, guards). **Step 5: Commit** `refactor: the repository is plugin source, not a workspace`.

---

### Task 3: Plugin version replaces framework_version

**Files:** strip `framework_version` frontmatter from `plugins/ai-job-search-plugin/skills/job-application-assistant/**/*.md`; `agents-block.md` frontmatter key → `version:`; `JT/sync_instructions.py` (`load_template` reads `version`); delete `tools/check_framework_version.py`, `tests/test_check_framework_version.py`; CI lint job drops the version-guard step; python-tests job checkout `fetch-depth: 0`; both `plugin.json` `version` → `2.0.0`; create `tests/test_plugin_version.py`.

- [ ] **Step 1: Failing tests** — `tests/test_plugin_version.py`:

```python
"""A change under plugins/<p>/ must bump that plugin's version (Claude Code updates on version)."""
import json
import os
import subprocess
import unittest

from tests import paths


def base_ref():
    ref = os.environ.get("GITHUB_BASE_REF")
    if not ref:
        return None
    for cand in (f"origin/{ref}", ref):
        if subprocess.run(["git", "rev-parse", "--verify", cand], cwd=paths.REPO, capture_output=True).returncode == 0:
            return cand
    return None


class TestPluginVersion(unittest.TestCase):
    def test_versions_are_2_or_later(self):
        for p in ("ai-job-search-plugin", "danish-job-portals"):
            v = json.loads((paths.REPO / "plugins" / p / ".claude-plugin" / "plugin.json").read_text())["version"]
            self.assertGreaterEqual(tuple(int(x) for x in v.split(".")), (2, 0, 0), p)

    def test_changed_plugin_bumps_version(self):
        base = base_ref()
        if not base:
            self.skipTest("no GITHUB_BASE_REF (local run)")
        for p in ("ai-job-search-plugin", "danish-job-portals"):
            changed = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD", "--", f"plugins/{p}/"],
                                     cwd=paths.REPO, capture_output=True, text=True).stdout.split()
            if not changed:
                continue
            old = subprocess.run(["git", "show", f"{base}:plugins/{p}/.claude-plugin/plugin.json"],
                                 cwd=paths.REPO, capture_output=True, text=True)
            if old.returncode:
                continue  # new plugin at base
            new_v = json.loads((paths.REPO / "plugins" / p / ".claude-plugin" / "plugin.json").read_text())["version"]
            self.assertNotEqual(json.loads(old.stdout)["version"], new_v, f"{p} changed without a version bump")

    def test_no_framework_version_markers_left(self):
        hits = [str(f.relative_to(paths.REPO)) for f in paths.REPO.glob("plugins/**/*.md")
                if "framework_version:" in f.read_text(encoding="utf-8")]
        self.assertEqual(hits, [])
        self.assertFalse((paths.REPO / "tools" / "check_framework_version.py").exists())
```

- [ ] **Step 2: RED.** **Step 3: Implement:**

```bash
python3 - <<'PYEOF'
import re
from pathlib import Path
for f in Path("plugins").glob("**/*.md"):
    s = f.read_text(encoding="utf-8")
    if "framework_version:" not in s:
        continue
    if f.name == "agents-block.md":
        s = s.replace("framework_version:", "version:", 1)
    else:
        s = re.sub(r"^framework_version:[^\n]*\n", "", s, count=1, flags=re.M)
        s = re.sub(r"\A---\n---\n\n?", "", s)  # frontmatter left empty -> drop it
    f.write_text(s, encoding="utf-8")
PYEOF
git rm -q tools/check_framework_version.py tests/test_check_framework_version.py
```
  `JT/sync_instructions.py` `load_template`: `re.search(r"^version:\s*(\S+)", …)`. Both `plugin.json` → `"version": "2.0.0"`. CI: delete the "Framework version guard" step; python-tests checkout gets `with: fetch-depth: 0`. Remove `framework_version` handling from `tests/test_profile_separation.py` (the `frontmatter_version` assertion in `test_every_template_exists_with_framework_version`: keep existence, drop the version check) and any other test asserting it (`grep -rn framework_version tests`).

- [ ] **Step 4: GREEN. Step 5: Commit** `refactor: plugin version replaces per-file framework_version`.

---

### Task 4: Upstream tracking with a path map; drop upstream-only paths

**Files:** create `tools/upstream_paths.py`; modify `tools/upstream_triage.py`, `.github/workflows/upstream-watch.yml`; `git mv .github/upstream-wontport.txt .github/upstream-handled.txt`; delete `tools/check_upstream_updates.py`, `tests/test_check_upstream_updates.py`; remove `/setup`'s legacy migration; rewrite `/setup` Step 0b warning; tests.

**Interfaces:** `upstream_paths.map_upstream_path(path: str) -> list[str]` (list: `.gitignore` maps to two paths); `DANISH = {"jobbank-search","jobdanmark-search","jobindex-search","jobnet-search"}`.

- [ ] **Step 1: Failing tests** — `tests/test_upstream_paths.py`:

```python
import sys
import unittest

from tests import paths

sys.path.insert(0, str(paths.REPO / "tools"))
from upstream_paths import map_upstream_path  # noqa: E402

P = "plugins/ai-job-search-plugin/skills"


class TestMap(unittest.TestCase):
    def test_rows(self):
        cases = {
            ".claude/commands/apply.md": [f"{P}/apply/SKILL.md"],
            ".claude/skills/job-scraper/SKILL.md": [f"{P}/job-scraper/SKILL.md"],
            ".claude/skills/job-application-assistant/01-candidate-profile.md":
                [f"{P}/job-application-assistant/profile-templates/candidate.md"],
            ".claude/skills/job-application-assistant/02-behavioral-profile.md":
                [f"{P}/job-application-assistant/profile-templates/behavioral.md"],
            ".claude/agents/gemini-research-expert.md": ["plugins/ai-job-search-plugin/agents/gemini-research-expert.md"],
            ".agents/skills/jobnet-search/cli/src/cli.ts": ["plugins/danish-job-portals/skills/jobnet-search/cli/src/cli.ts"],
            ".agents/skills/linkedin-search/SKILL.md": [f"{P}/linkedin-search/SKILL.md"],
            "tools/rank_state.py": [f"{P}/job-tools/scripts/rank_state.py"],
            "salary_lookup.py": [f"{P}/job-tools/scripts/salary_lookup.py"],
            "tools/README_SALARY_TOOL.md": [f"{P}/job-tools/scripts/README_SALARY_TOOL.md"],
            "cv/main_example.tex": [f"{P}/job-tools/workspace-template/cv/main_example.tex"],
            "documents/README.md": [f"{P}/job-tools/workspace-template/documents/README.md"],
            ".gitignore": [f"{P}/job-tools/workspace-template/gitignore.template", ".gitignore"],
            "tools/lint_skills.py": ["tools/lint_skills.py"],
            "README.md": ["README.md"],
        }
        for upstream, ours in cases.items():
            self.assertEqual(map_upstream_path(upstream), ours, upstream)
```

Append to `tests/test_upstream_triage.py`:

```python
    def test_command_commit_is_mapped_and_relevant(self):
        # upstream edits a command file at its old path; this repo has it as a plugin skill
        mapped = self.root / "plugins/ai-job-search-plugin/skills/apply/SKILL.md"
        mapped.parent.mkdir(parents=True, exist_ok=True)
        mapped.write_text("ours\n", encoding="utf-8")
        self.commit("fork layout")
        self.set_upstream_to_head()
        git(self.root, "checkout", "-q", "-b", "up", "upstream/master")
        self.write(".claude/commands/apply.md", "upstream change\n")
        sha = self.commit("feat(apply): upstream improvement")
        git(self.root, "update-ref", "refs/remotes/upstream/master", sha)
        git(self.root, "checkout", "-q", "-")
        out = self.run_triage().stdout
        section = out.split("### Worth reviewing", 1)[1].split("### Probably skip", 1)[0]
        self.assertIn("upstream improvement", section)
        self.assertIn("plugins/ai-job-search-plugin/skills/apply/SKILL.md", section)
        self.assertIn(f"git show {sha} -- .claude/commands/apply.md", out)
```

(Adapt to the file's fixture helpers if names differ: the class already defines `write`, `commit`, `set_upstream_to_head`, `run_triage`; the fixture copies `tools/upstream_triage.py` into a temp repo — also copy `tools/upstream_paths.py`.) Change the existing `test_listed_sha_is_excluded` to write `.github/upstream-handled.txt` with `<sha>  # rejected: test`.

Append to `tests/test_setup_command.py` (and delete class `SetupLegacyMigration`):

```python
class NoUpstreamMigration(unittest.TestCase):
    def test_setup_has_no_fork_migration_or_fork_warning(self):
        text = COMMAND.read_text(encoding="utf-8")
        self.assertNotIn("#### Legacy fork migration", text)
        self.assertNotIn("public GitHub fork", text)
        self.assertIn("public repository", text)
```

- [ ] **Step 2: RED.**

- [ ] **Step 3: Implement**

`tools/upstream_paths.py`:

```python
"""Map a path in the original project (MadsLorentzen/ai-job-search) to this repository.

Used by upstream_triage.py so upstream commits are judged, and ported, against
where the same files live here after the plugin conversion.
"""
from __future__ import annotations

CORE = "plugins/ai-job-search-plugin"
SKILLS = f"{CORE}/skills"
DANISH = {"jobbank-search", "jobdanmark-search", "jobindex-search", "jobnet-search"}
RUNTIME = {"rank_state.py", "job_key.py", "verify_pdf.py", "verify_layout.py",
           "robots_check.py", "convert_salary_excel.py", "README_SALARY_TOOL.md"}
WORKSPACE_DIRS = ("cv/", "cover_letters/", "templates/", "documents/", "job_scraper/",
                  "company_research/", "upskill/")
PROFILE_TEMPLATES = {"01-candidate-profile.md": "candidate.md", "02-behavioral-profile.md": "behavioral.md"}


def map_upstream_path(path: str) -> list[str]:
    parts = path.split("/")
    if path.startswith(".claude/commands/") and path.endswith(".md") and len(parts) == 3:
        return [f"{SKILLS}/{parts[2][:-3]}/SKILL.md"]
    if path.startswith(".claude/skills/job-application-assistant/") and parts[-1] in PROFILE_TEMPLATES:
        return [f"{SKILLS}/job-application-assistant/profile-templates/{PROFILE_TEMPLATES[parts[-1]]}"]
    if path.startswith(".claude/skills/"):
        return [f"{SKILLS}/" + "/".join(parts[2:])]
    if path.startswith(".claude/agents/"):
        return [f"{CORE}/agents/" + "/".join(parts[2:])]
    if path.startswith(".agents/skills/") and len(parts) > 2:
        home = "plugins/danish-job-portals/skills" if parts[2] in DANISH else SKILLS
        return [f"{home}/" + "/".join(parts[2:])]
    if (path.startswith("tools/") and parts[-1] in RUNTIME) or path == "salary_lookup.py":
        return [f"{SKILLS}/job-tools/scripts/{parts[-1]}"]
    if path.startswith(WORKSPACE_DIRS):
        return [f"{SKILLS}/job-tools/workspace-template/{path}"]
    if path == ".gitignore":
        return [f"{SKILLS}/job-tools/workspace-template/gitignore.template", ".gitignore"]
    return [path]
```

`tools/upstream_triage.py`:
- `sys.path.insert(0, str(Path(__file__).resolve().parent))` then `from upstream_paths import map_upstream_path`.
- In the loop: `mapped = {f: [m for m in map_upstream_path(f) if path_exists(m)] for f in touched}`; `present = sorted({m for ms in mapped.values() for m in ms})`; keep the skip rules on `present`; append `review.append((short, sha, subj, present, [f for f in touched if mapped[f]]))`.
- Report table column "Files here (mapped)"; replace the cherry-pick details block with "Read each change, then port it by hand to the mapped files:" and one line per commit `git show {sha} -- {' '.join(upstream_paths_touched)}  # {subj}`; after it: "Record each commit you port or reject in `.github/upstream-handled.txt`."
- `--wontport` flag → `--handled`, default `.github/upstream-handled.txt`; `load_wontport` → `load_handled` (same parsing); skip reason "listed in upstream-handled.txt".
- Delete `_print_crossref` and its calls.
- Module docstring: replace the `check_upstream_updates.py` companion paragraph with one sentence about the path map.

`.github/upstream-handled.txt`: header comment explaining `<sha>  # ported|rejected: note`, one entry per line, ships empty.

`.github/workflows/upstream-watch.yml`: any `upstream-wontport` → `upstream-handled`; keep its fork guard.

`git rm -q tools/check_upstream_updates.py tests/test_check_upstream_updates.py`.

`plugins/ai-job-search-plugin/skills/setup/SKILL.md`: delete the whole `#### Legacy fork migration` subsection and, in Step 0a item 3, the sentence `If \`profile/\` did not exist before step 2, run **Legacy fork migration** below first. Then,` → `Then,` (capitalize the next word). Replace Step 0b's public-fork check paragraphs (from "Otherwise, first check where this working copy would publish to" through the quoted heads-up and "Wait for the user's confirmation…" paragraph) with:

```markdown
Otherwise, before anything is written, check whether this workspace folder would publish personal data: run `git remote get-url origin`. If it fails (no remote, or not a git repository), skip this check silently. If there is a GitHub `origin` and `gh` is available, check `gh repo view <owner/repo> --json visibility`. If the repository is public, or its visibility cannot be determined, warn and wait:

> **Heads-up before we start:** your `origin` points at `<owner/repo>`, which is a public repository. This setup writes your personal data (name, contact details, employment history, salary expectations) into files in this folder, and anything you commit and push is visible to anyone. Keep this workspace in a **private** repository, or don't push it. Want to continue?

A private origin or no origin needs no warning; continue silently.
```

  Remove tests pinning the migration (`test_profile_separation.py` legacy-file tests that reference migration behaviour stay only if they check that framework files have no legacy names; delete `strip_setup_migration` usage now that the subsection is gone).

- [ ] **Step 4: GREEN. Step 5: Commit** `feat(upstream): path-mapped triage and handled list; drop upstream-only migration`.

---

### Task 5: Identity and docs

**Files:** `LICENSE`, `.github/FUNDING.yml` (delete), `.github/ISSUE_TEMPLATE/config.yml`, `.github/PULL_REQUEST_TEMPLATE.md`, `SECURITY.md`, `README.md`, `SETUP.md`, `CONTRIBUTING.md`, `CHANGELOG.md`; tests in `tests/test_independent.py`; update `tests/test_plugin_layout.py::TestDocs`, `tests/test_profile_separation.py::TestDocs`.

- [ ] **Step 1: Failing tests** — append to `tests/test_independent.py`:

```python
ALLOWED_MADS = ("LICENSE", "README.md", "SETUP.md", "CHANGELOG.md", "docs/superpowers/",
                "tools/upstream_triage.py", "tools/upstream_paths.py", ".github/workflows/upstream-watch.yml",
                ".github/upstream-handled.txt", "tests/")


class TestIdentityDocs(unittest.TestCase):
    def test_original_author_only_where_allowed(self):
        out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
        offenders = []
        for rel in out.splitlines():
            if rel.startswith(ALLOWED_MADS) or not (REPO / rel).is_file():
                continue
            try:
                if "MadsLorentzen" in (REPO / rel).read_text(encoding="utf-8"):
                    offenders.append(rel)
            except UnicodeDecodeError:
                continue
        self.assertEqual(offenders, [])

    def test_license_keeps_both_copyrights(self):
        text = (REPO / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Copyright (c) 2026 Mads Lorentzen", text)
        self.assertIn("Copyright (c) 2026 MRDGH2821", text)
        self.assertFalse((REPO / ".github" / "FUNDING.yml").exists())

    def test_readme(self):
        text = (REPO / "README.md").read_text(encoding="utf-8")
        for needle in ("/plugin marketplace add MRDGH2821/ai-job-search-plugin",
                       "/plugin install ai-job-search-plugin@ai-job-search-plugin",
                       "/init-workspace", "## Credits", "MadsLorentzen/ai-job-search",
                       "upstream_triage.py", "untested outside Claude Code"):
            self.assertIn(needle, text)

    def test_changelog_top_section(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        first = text.split("\n## [", 2)[1]
        self.assertTrue(first.startswith("2.0.0]"), first[:40])
        self.assertIn("ai-job-search-plugin", first)
```

Update `tests/test_plugin_layout.py::TestDocs`: `test_readme_explains_both_install_routes_and_capa` expects the new install lines and `capa registry add MRDGH2821/ai-job-search-plugin`; delete `test_setup_md_has_the_upgrade_section`; `test_agents_md_and_contributing_point_at_capa` → checks CONTRIBUTING mentions `capa` only. In `tests/test_profile_separation.py` delete the `TestDocs` methods about SETUP §9 and the changelog fork-break check. In `tests/test_changelog_structure.py` nothing changes (it checks `[Unreleased]` structure; the new top is `## [2.0.0] - Unreleased`: if that test requires a literal `## [Unreleased]` heading, keep an empty `## [Unreleased]` above `## [2.0.0] - 2026-09-25` instead, and make `test_changelog_top_section` look at the first version section after it).

- [ ] **Step 2: RED.**

- [ ] **Step 3: Write**
- `LICENSE`: under the existing copyright line add `Copyright (c) 2026 MRDGH2821`.
- `git rm -q .github/FUNDING.yml`.
- `ISSUE_TEMPLATE/config.yml`, `PULL_REQUEST_TEMPLATE.md`, `SECURITY.md`: every `MadsLorentzen/ai-job-search` link → `MRDGH2821/ai-job-search-plugin`; drop fork-index / discussion #78 / "fork" wording.
- `README.md` (rewrite): title `# ai-job-search-plugin`; one-paragraph what-it-is; `## Install` (marketplace add, install, optional Danish plugin); `## First run` (`/init-workspace` in an empty private folder, then `/setup`); `## Commands` (the existing command list, updated names); `## How /apply works` (keep existing section text); `## Other harnesses (capa)` (`capa registry add MRDGH2821/ai-job-search-plugin`, "untested outside Claude Code"); `## Developing the plugin` (clone, trust, checks; point to `AGENTS.md`); `## Tracking the original project` (`upstream` remote, `python3 tools/upstream_triage.py --remote upstream`, `.github/upstream-handled.txt`); `## Credits` ("Forked from [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search) (MIT) by Mads Lorentzen."); `## License`.
- `SETUP.md` (rewrite): prerequisites (Claude Code, Python 3.10+, LaTeX with lualatex/xelatex, Bun for portals), install, first run, salary data (`salary_data.json` in the workspace root; converter usage), optional Danish plugin, troubleshooting (keep the existing troubleshooting items that still apply), and a short "Tracking the original project" note.
- `CONTRIBUTING.md` (rewrite): scope; one concern per PR; required checks (tests, lint, guards, `plugin.json` version bump); permission additions need an `ALLOWED_SKILL_TOOLS` entry; market-specific portals go in their own market plugin; porting from the original project (triage, handled list).
- `CHANGELOG.md`: new top section (below `## [Unreleased]` if that heading must stay): `## [2.0.0] - 2026-09-25` with `### Changed`: "**Independent project: ai-job-search-plugin.** Forked from MadsLorentzen/ai-job-search v1.7.1 and renamed … marketplace/plugin ids, markers (old workspaces upgrade on next sync), repository is plugin source only, plugin version replaces framework_version, upstream triage maps paths; fork-migration tooling removed."

- [ ] **Step 4: GREEN** (suite, lint, guards, validate). **Step 5: Commit** `docs: independent ai-job-search-plugin identity and docs`.

---

### Task 6: Verification, push, repo rename

- [ ] **Step 1:** suite, lint, guards, `claude plugin validate .`, `claude --plugin-dir plugins/ai-job-search-plugin plugin details ai-job-search-plugin` (20 skills, 1 agent).
- [ ] **Step 2:** headless `/ai-job-search-plugin:init-workspace` in an empty folder (`--allowedTools "Skill,AskUserQuestion" --output-format json`): no denials; `AGENTS.md` starts with `<!-- ai-job-search-plugin:start`.
- [ ] **Step 3:** `python3 tools/upstream_triage.py --remote upstream --branch master | head -20` runs (report or "up to date").
- [ ] **Step 4:** push `plugin/5-independent` to `origin`; open PR #5 (`--base plugin/4-workspace-init`) on `MRDGH2821/ai-job-search` with a summary and test plan.
- [ ] **Step 5:** AskUserQuestion: "Rename the GitHub repository MRDGH2821/ai-job-search to ai-job-search-plugin now?" On yes: `gh repo rename ai-job-search-plugin -R MRDGH2821/ai-job-search --yes` and `git remote set-url origin https://github.com/MRDGH2821/ai-job-search-plugin.git`; verify with `gh repo view MRDGH2821/ai-job-search-plugin --json name`. On no: leave it and say so.
