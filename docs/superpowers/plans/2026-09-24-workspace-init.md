# Workspace Init Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One command (`/init-workspace`, also run by `/setup`) lays out the author's workspace in any folder from a template shipped inside the plugin.

**Architecture:** The template lives in `plugins/ai-job-search/skills/job-tools/workspace-template/`. A test keeps it in sync with the clone's root copy, and the security guard checks its `.gitignore`. A stdlib script (`init_workspace.py`) copies missing files only and appends missing privacy rules to an existing `.gitignore`, refusing to write anything if a target is in the way. A thin user-only skill runs it plus `sync_instructions.py` and offers `git init`; `/setup` Step 0a runs it first.

**Tech Stack:** Python 3 stdlib, markdown skills, stdlib `unittest`, git.

**Spec:** `docs/superpowers/specs/2026-09-24-workspace-init-design.md`.

## Global Constraints

- Branch `plugin/4-workspace-init`, stacked on `plugin/3-instruction-sync`. Tree clean before Task 1 (`stash@{0}` unrelated).
- Template root, exactly: `plugins/ai-job-search/skills/job-tools/workspace-template/` (below `WT/`). Script: `plugins/ai-job-search/skills/job-tools/scripts/init_workspace.py` (below `JT/init_workspace.py`).
- Template `.gitignore` file name: `gitignore.template`; target name in the workspace: `.gitignore`.
- Repo-only `.gitignore` lines removed from the template, exactly: `plugins/**/node_modules/`, `# Brainstorm mockups (superpowers visual companion) - never ship`, `.superpowers/`.
- Append header, exactly: `# Added by /init-workspace: personal data must never be committed`.
- Output lines, exactly: `created: <posix path>`, `updated: .gitignore (+N rules)`, `kept: N existing files`. Exit 0 success, 2 refused (nothing written).
- New permission entries, exactly: `Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py:*)`, `Bash(git init)`.
- Skill bodies that run commands say: run now, without asking for confirmation, as one command, no `cd`, no `&&` (lesson from branches 2-3).
- Tests: `python3 -m unittest tests.<module> -v`; suite `python3 -m unittest discover -s tests -t . -v`. `git log --no-show-signature` in scripts; `claude -p` probes use `--model claude-haiku-4-5-20251001`.
- Commits end with the two trailer lines (`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, `Claude-Session: https://claude.ai/code/session_01C8revGiLzJ6ZYvz6LZMmZa`). Finish: keep the branch as-is.

## Review Focus

1. **Template files silently ignored by the repo's own `.gitignore`** (fonts, `cv/main_example.tex` under the plugin path) → a plugin install from GitHub would lack them. Expected: every template file is tracked. Pinned in Task 1 (`test_no_template_file_is_ignored`).
2. **`/setup` in the clone (a workspace that already has everything)** → nothing created, `.gitignore` untouched. Pinned in Task 2 (`test_clone_root_gitignore_needs_no_additions`) plus the second-run test.
3. **`.gitignore` without a trailing newline, or with CRLF** → rules appended on new lines in the file's style. Pinned in Task 2 (`test_gitignore_append_respects_newlines`).
4. **Something in the way** (`cv` is a file; a directory named `cv/main_example.tex`) → exit 2, nothing written. Pinned in Task 2 (`test_blocked_target_writes_nothing`).
5. **Non-UTF-8 `.gitignore`** → exit 2, nothing written. Pinned in Task 2 (`test_unreadable_gitignore_writes_nothing`).

---

### Task 1: Template, sync test, guard

**Files:**
- Create: `WT/…` (copied from the root), `WT/gitignore.template`, `tests/test_workspace_init.py`
- Modify: `tools/security_guards.py` (`check_gitignore`), `tests/test_security_guards.py`

**Interfaces:**
- Produces: `WT/` tree; `tests/test_workspace_init.py` helpers `WT: Path`, `expected_gitignore_template(root_text: str) -> str`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workspace_init.py`:

```python
"""Workspace init (spec: docs/superpowers/specs/2026-09-24-workspace-init-design.md)."""
import os
import subprocess
import unittest
from pathlib import Path

from tests import paths

UPSTREAM = "MadsLorentzen/ai-job-search"
WT = paths.SKILLS / "job-tools" / "workspace-template"
REPO_ONLY_IGNORE = {"plugins/**/node_modules/",
                    "# Brainstorm mockups (superpowers visual companion) - never ship",
                    ".superpowers/"}
ALWAYS_SYNCED_DIRS = ("cover_letters/OpenFonts",)
ALWAYS_SYNCED_FILES = ("cover_letters/cover.cls", "templates/README.md", "documents/README.md")
UPSTREAM_SYNCED = ("cv/main_example.tex", "cover_letters/cover_example.tex")
GITKEEP_ROOTS = ("documents", "job_scraper", "company_research", "upskill")


def expected_gitignore_template(root_text: str) -> str:
    kept = [line for line in root_text.splitlines() if line.strip() not in REPO_ONLY_IGNORE]
    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept) + "\n"


def tracked(prefix):
    out = subprocess.run(["git", "ls-files", prefix], cwd=paths.REPO, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


class TestTemplateSync(unittest.TestCase):
    def test_always_synced_files_match(self):
        rels = list(ALWAYS_SYNCED_FILES)
        for d in ALWAYS_SYNCED_DIRS:
            rels += tracked(d)
        for root in GITKEEP_ROOTS:
            rels += [p for p in tracked(root) if p.endswith(".gitkeep")]
        self.assertGreater(len(rels), 25)
        for rel in rels:
            self.assertEqual((WT / rel).read_bytes(), (paths.REPO / rel).read_bytes(), rel)

    @unittest.skipIf(os.environ.get("GITHUB_REPOSITORY", UPSTREAM) != UPSTREAM,
                     "forks personalize these files")
    def test_upstream_examples_match(self):
        for rel in UPSTREAM_SYNCED:
            self.assertEqual((WT / rel).read_bytes(), (paths.REPO / rel).read_bytes(), rel)

    def test_template_has_nothing_the_root_lacks(self):
        extra = [str(p.relative_to(WT)) for p in WT.rglob("*")
                 if p.is_file() and p.name != "gitignore.template" and not (paths.REPO / p.relative_to(WT)).exists()]
        self.assertEqual(extra, [])

    def test_gitignore_template_is_the_root_minus_repo_only_lines(self):
        root = (paths.REPO / ".gitignore").read_text(encoding="utf-8")
        self.assertEqual((WT / "gitignore.template").read_text(encoding="utf-8"), expected_gitignore_template(root))

    def test_no_template_file_is_ignored(self):
        files = [str(p.relative_to(paths.REPO)) for p in WT.rglob("*") if p.is_file()]
        proc = subprocess.run(["git", "check-ignore", "--no-index", *files], cwd=paths.REPO, capture_output=True, text=True)
        self.assertEqual(proc.stdout.strip(), "", "template files ignored by the repo's .gitignore")
```

Append to `tests/test_security_guards.py`:

```python
class TestTemplateGitignoreGuard(unittest.TestCase):
    def test_template_missing_a_required_rule_fails(self):
        import importlib
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        full = "\n".join(security_guards.REQUIRED_IGNORE_RULES) + "\n"
        (tmp / ".gitignore").write_text(full, encoding="utf-8")
        wt = tmp / "plugins" / "ai-job-search" / "skills" / "job-tools" / "workspace-template"
        wt.mkdir(parents=True)
        (wt / "gitignore.template").write_text(full.replace("salary_data.json\n", ""), encoding="utf-8")
        mod = importlib.reload(security_guards)
        mod.ROOT = tmp
        mod.errors.clear()
        mod.check_gitignore()
        found = list(mod.errors)
        importlib.reload(security_guards)
        self.assertTrue(any("gitignore.template" in e and "salary_data.json" in e for e in found), found)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_workspace_init tests.test_security_guards.TestTemplateGitignoreGuard -v 2>&1 | tail -3`
Expected: FAIL/ERROR (template files missing; guard reads only the root `.gitignore`).

- [ ] **Step 3: Build the template**

```bash
WT=plugins/ai-job-search/skills/job-tools/workspace-template
for f in cv/main_example.tex cover_letters/cover.cls cover_letters/cover_example.tex templates/README.md documents/README.md \
         $(git ls-files cover_letters/OpenFonts) \
         $(git ls-files documents job_scraper company_research upskill | grep '\.gitkeep$'); do
  mkdir -p "$WT/$(dirname "$f")" && cp -p "$f" "$WT/$f"
done
python3 - <<'PYEOF'
from pathlib import Path
from tests.test_workspace_init import expected_gitignore_template
root = Path(".gitignore").read_text(encoding="utf-8")
Path("plugins/ai-job-search/skills/job-tools/workspace-template/gitignore.template").write_text(
    expected_gitignore_template(root), encoding="utf-8")
PYEOF
git add -A plugins/ai-job-search/skills/job-tools/workspace-template && git status --short | grep -c workspace-template
```
Expected: the count equals 5 + 19 fonts + the tracked `.gitkeep` count + 1 (`gitignore.template`). If `git add` reports a file as ignored, stop: Review Focus 1 has fired; fix the root `.gitignore` rule (anchor it) rather than force-adding.

- [ ] **Step 4: Extend the guard**

In `tools/security_guards.py`, turn `check_gitignore` into a loop over two files. Replace its first lines:

```python
def check_gitignore() -> None:
    path = ROOT / ".gitignore"
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    except OSError as exc:
        errors.append(f".gitignore: unreadable: {exc}")
        return
```

with:

```python
WORKSPACE_GITIGNORE = "plugins/ai-job-search/skills/job-tools/workspace-template/gitignore.template"


def check_gitignore() -> None:
    _check_gitignore_file(ROOT / ".gitignore", ".gitignore")
    template = ROOT / WORKSPACE_GITIGNORE
    if template.exists():
        # /init-workspace copies this into every new workspace: it must carry the same rules.
        _check_gitignore_file(template, WORKSPACE_GITIGNORE)


def _check_gitignore_file(path, label: str) -> None:
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    except OSError as exc:
        errors.append(f"{label}: unreadable: {exc}")
        return
```

and in the two error messages below, replace the leading `.gitignore:` with `{label}:` (both are f-strings already; make the first one an f-string if it is not).

- [ ] **Step 5: Run to verify it passes**

Run: `python3 -m unittest tests.test_workspace_init tests.test_security_guards -v 2>&1 | tail -2`; `python3 tools/security_guards.py`
Expected: OK; guards OK.

- [ ] **Step 6: Commit**

```bash
git add plugins/ai-job-search/skills/job-tools/workspace-template tools/security_guards.py tests/test_workspace_init.py tests/test_security_guards.py
git commit -m "feat(job-tools): workspace template kept in sync with the clone"   # plus trailers
```

---

### Task 2: init_workspace.py

**Files:**
- Create: `JT/init_workspace.py`
- Test: `tests/test_workspace_init.py`

**Interfaces:**
- Consumes: `WT/` (Task 1).
- Produces: CLI `python3 JT/init_workspace.py [--root DIR]`, output/exit codes per Global Constraints.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_workspace_init.py`:

```python
import sys  # noqa: E402
import tempfile  # noqa: E402

SCRIPT = paths.JOB_TOOLS / "init_workspace.py"
HEADER = "# Added by /init-workspace: personal data must never be committed"


def run(root, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True,
                          encoding="utf-8")


def template_targets():
    out = []
    for p in WT.rglob("*"):
        if p.is_file():
            rel = p.relative_to(WT)
            out.append(Path(".gitignore") if rel.name == "gitignore.template" else rel)
    return sorted(out)


class TestInitScript(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def snapshot(self):
        return {str(p.relative_to(self.root)): (p.read_bytes() if p.is_file() else None)
                for p in self.root.rglob("*")}

    def test_empty_folder_gets_the_whole_tree(self):
        proc = run(self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for rel in template_targets():
            self.assertTrue((self.root / rel).is_file(), rel)
        font = next((WT / "cover_letters" / "OpenFonts").rglob("*.ttf"))
        self.assertEqual((self.root / font.relative_to(WT)).read_bytes(), font.read_bytes())
        self.assertIn("created: cv/main_example.tex", proc.stdout)
        self.assertNotIn("profile", proc.stdout)
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_second_run_is_unchanged(self):
        run(self.root)
        before = self.snapshot()
        proc = run(self.root)
        self.assertNotIn("created:", proc.stdout)
        self.assertIn(f"kept: {len(template_targets())} existing files", proc.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_existing_files_are_never_overwritten(self):
        (self.root / "cv").mkdir()
        (self.root / "cv" / "main_example.tex").write_text("mine", encoding="utf-8")
        run(self.root)
        self.assertEqual((self.root / "cv" / "main_example.tex").read_text(encoding="utf-8"), "mine")

    def test_existing_gitignore_gains_only_missing_rules(self):
        (self.root / ".gitignore").write_text("my-secret-dir/\nsalary_data.json\n", encoding="utf-8")
        proc = run(self.root)
        text = (self.root / ".gitignore").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("my-secret-dir/\nsalary_data.json\n"))
        self.assertEqual(text.count("salary_data.json"), 1)
        self.assertIn(HEADER, text)
        self.assertIn("job_search_tracker.csv", text)
        self.assertRegex(proc.stdout, r"updated: \.gitignore \(\+\d+ rules\)")
        before = text
        run(self.root)
        self.assertEqual((self.root / ".gitignore").read_text(encoding="utf-8"), before)

    def test_gitignore_append_respects_newlines(self):
        (self.root / ".gitignore").write_bytes(b"a/\r\nb/")
        run(self.root)
        data = (self.root / ".gitignore").read_bytes()
        self.assertTrue(data.startswith(b"a/\r\nb/\r\n"))
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))

    def test_clone_root_gitignore_needs_no_additions(self):
        (self.root / ".gitignore").write_bytes((paths.REPO / ".gitignore").read_bytes())
        proc = run(self.root)
        self.assertNotIn("updated: .gitignore", proc.stdout)

    def test_blocked_target_writes_nothing(self):
        for make in (lambda r: (r / "cv").write_text("a file", encoding="utf-8"),
                     lambda r: (r / "cv" / "main_example.tex").mkdir(parents=True)):
            with tempfile.TemporaryDirectory() as t:
                r = Path(t)
                make(r)
                before = {str(p.relative_to(r)) for p in r.rglob("*")}
                proc = run(r)
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn("cv", proc.stderr)
                self.assertEqual({str(p.relative_to(r)) for p in r.rglob("*")}, before)

    def test_unreadable_gitignore_writes_nothing(self):
        (self.root / ".gitignore").write_bytes(b"\xff\xfe\x81")
        proc = run(self.root)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual({p.name for p in self.root.iterdir()}, {".gitignore"})

    def test_root_flag(self):
        other = self.root / "ws"
        other.mkdir()
        self.assertEqual(run(self.root, "--root", str(other)).returncode, 0)
        self.assertTrue((other / "cv" / "main_example.tex").exists())
        self.assertFalse((self.root / "cv").exists())
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_workspace_init.TestInitScript -v 2>&1 | tail -3`
Expected: FAIL/ERROR ×9 (script missing).

- [ ] **Step 3: Write the script**

`JT/init_workspace.py`:

```python
#!/usr/bin/env python3
"""Lay out an ai-job-search workspace in the current folder.

Usage: python3 init_workspace.py [--root DIR]

Copies every file of the workspace template (next to this script) that the
workspace does not have yet - CV and cover-letter sources, fonts, the documents/
tree, state folders - and never overwrites anything. The template's
gitignore.template becomes .gitignore; an existing .gitignore only gains the
privacy rules it lacks. --root defaults to the current directory: the workspace
root, never this script's folder.

Exit codes: 0 done, 2 refused (something is in the way or unreadable; nothing
was written).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "workspace-template"
GITIGNORE_SOURCE = "gitignore.template"
HEADER = "# Added by /init-workspace: personal data must never be committed"


class InitError(Exception):
    """A state the script refuses to guess about. Nothing has been written."""


def template_files() -> list[Path]:
    return sorted(p.relative_to(TEMPLATE) for p in TEMPLATE.rglob("*") if p.is_file())


def target_of(rel: Path) -> Path:
    return Path(".gitignore") if rel.name == GITIGNORE_SOURCE and rel.parent == Path(".") else rel


def rule_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def check_path(root: Path, rel: Path) -> None:
    for parent in reversed(rel.parents[:-1]):
        p = root / parent
        if p.exists() and not p.is_dir():
            raise InitError(f"{parent.as_posix()}: a file is in the way of a folder the workspace needs. Nothing was written.")
    if (root / rel).is_dir():
        raise InitError(f"{rel.as_posix()}: a folder is in the way of a file the workspace needs. Nothing was written.")


def plan(root: Path) -> tuple[list[tuple[Path, Path]], tuple[str, list[str], bytes] | None, int]:
    """(files to copy [(source, target rel)], .gitignore append plan, kept count)."""
    copies: list[tuple[Path, Path]] = []
    gitignore_plan = None
    kept = 0
    for rel in template_files():
        target = target_of(rel)
        check_path(root, target)
        dest = root / target
        if target == Path(".gitignore") and dest.exists():
            raw = dest.read_bytes()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise InitError(".gitignore: not UTF-8 text. Convert it to UTF-8 first; nothing was written.") from exc
            have = {line.strip() for line in text.splitlines()}
            missing = [r for r in rule_lines((TEMPLATE / rel).read_text(encoding="utf-8")) if r not in have]
            kept += 1
            if missing:
                gitignore_plan = (text, missing, raw)
            continue
        if dest.exists():
            kept += 1
        else:
            copies.append((TEMPLATE / rel, target))
    return copies, gitignore_plan, kept


def run(root: Path) -> list[str]:
    copies, gitignore_plan, kept = plan(root)
    out = []
    for source, target in copies:
        dest = root / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        out.append(f"created: {target.as_posix()}")
    if gitignore_plan:
        text, missing, _ = gitignore_plan
        newline = "\r\n" if "\r\n" in text else "\n"
        body = text if text.endswith(("\n", "\r\n")) or not text else text + newline
        body += newline + newline.join([HEADER, *missing]) + newline
        (root / ".gitignore").write_bytes(body.encode("utf-8"))
        out.append(f"updated: .gitignore (+{len(missing)} rules)")
    out.append(f"kept: {kept} existing files")
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)  # absent on a StringIO under test
        if reconfigure:
            reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="workspace root (default: current directory)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        for line in run(root):
            print(line)
        return 0
    except InitError as exc:
        print(exc, file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"cannot write: {exc}. Check the folder's permissions and run again.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_workspace_init -v 2>&1 | tail -2`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add plugins/ai-job-search/skills/job-tools/scripts/init_workspace.py tests/test_workspace_init.py
git commit -m "feat(job-tools): init_workspace lays out a workspace without overwriting anything"   # plus trailers
```

---

### Task 3: /init-workspace skill, /setup reuse, permissions, docs

**Files:**
- Create: `plugins/ai-job-search/skills/init-workspace/SKILL.md`
- Modify: `plugins/ai-job-search/skills/setup/SKILL.md`, `plugins/ai-job-search/skills/job-tools/SKILL.md`, `tools/security_guards.py`, `README.md`, `SETUP.md`, `CHANGELOG.md`
- Test: `tests/test_workspace_init.py`

**Interfaces:**
- Consumes: `JT/init_workspace.py` CLI (Task 2), `JT/sync_instructions.py` (branch 3).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_workspace_init.py`:

```python
import re  # noqa: E402

INIT_ENTRY = "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py:*)"
SYNC_ENTRY = "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py:*)"


def frontmatter(path):
    m = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.DOTALL)
    return m.group(1) if m else ""


class TestWiring(unittest.TestCase):
    def test_skill(self):
        skill = paths.skill_file("init-workspace")
        fm = frontmatter(skill)
        self.assertIn("name: init-workspace", fm)
        self.assertIn("disable-model-invocation: true", fm)
        for entry in (INIT_ENTRY, SYNC_ENTRY, "Bash(git init)"):
            self.assertIn(entry, fm)
        body = skill.read_text(encoding="utf-8").split("\n---\n", 1)[1]
        self.assertTrue(body.lstrip().startswith("# /init-workspace "))
        self.assertIn("without asking for confirmation", body)
        self.assertIn("no `cd`, no `&&`", body)
        self.assertIn("private repository", body)
        self.assertIn("/setup", body)

    def test_setup_runs_init_first(self):
        setup = paths.command_file("setup")
        self.assertIn(INIT_ENTRY, frontmatter(setup))
        step0a = setup.read_text(encoding="utf-8").split("### Step 0a:", 1)[1].split("#### Legacy fork migration", 1)[0]
        self.assertIn("init_workspace.py", step0a)
        self.assertLess(step0a.index("init_workspace.py"), step0a.index("Create `profile/`"))

    def test_guard_and_docs(self):
        guards = (paths.REPO / "tools" / "security_guards.py").read_text(encoding="utf-8")
        self.assertIn(INIT_ENTRY, guards)
        self.assertIn('"Bash(git init)"', guards)
        readme = (paths.REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("/init-workspace", readme)
        self.assertNotIn("arrives in a later release", readme)
        self.assertIn("/init-workspace", (paths.REPO / "SETUP.md").read_text(encoding="utf-8"))
        changelog = (paths.REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("/init-workspace", changelog.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0])
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_workspace_init.TestWiring -v 2>&1 | tail -3`
Expected: FAIL/ERROR ×3.

- [ ] **Step 3: The skill**

`plugins/ai-job-search/skills/init-workspace/SKILL.md`:

````markdown
---
name: init-workspace
description: "Lay out a job-search workspace in the current folder (CV and cover-letter sources, fonts, documents tree, privacy .gitignore). Use when the user runs /init-workspace."
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py:*), Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py:*), Bash(git init)
---
# /init-workspace - Lay Out a Job-Search Workspace

`${CLAUDE_SKILL_DIR}` is this skill's folder. If your tool does not expand it, read paths as relative to the folder containing this SKILL.md.

The user typing `/init-workspace` is the request. Run each command below now, without asking for confirmation, from the current directory, exactly as written and as one command: no `cd`, no `&&`. Any other form does not match this skill's permissions.

1. Lay out the workspace (copies only what is missing, never overwrites):

   ```bash
   python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py
   ```

   Report its `created:`/`updated:`/`kept:` lines in short. If it exits 2, show its message and stop.

2. Write the workspace instructions (`AGENTS.md` block, `CLAUDE.md` import):

   ```bash
   python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py
   ```

   Report its lines. If it exits 2, show its message and stop.

3. If this folder is not inside a git repository (no `.git` here or in any parent folder), ask once with AskUserQuestion: "Make this folder a git repository? This folder will hold your personal data. If you push it anywhere, use a private repository." Options: "Yes, run git init" / "No". On yes, run `git init`.

4. Tell the user the next step: run `/setup` to fill in `profile/` with their details.
````

- [ ] **Step 4: /setup, job-tools table, guard**

`plugins/ai-job-search/skills/setup/SKILL.md`:
- Frontmatter `allowed-tools:` line: append `, Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py:*)`.
- Step 0a: insert a new first item and renumber the existing four items 2-5; in the old item 2 (now 3), change `before step 1` to `before step 2`:
  ```markdown
  1. Lay out the workspace: run `python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py` exactly as written, as one command from the current directory (no `cd`, no `&&`). It copies only what is missing (CV and cover-letter sources, fonts, the `documents/` tree, a privacy `.gitignore`) and never overwrites anything. Mention in one line what it created, if anything. If it exits 2, show its message and continue.
  ```

`plugins/ai-job-search/skills/job-tools/SKILL.md` table: add row
`| \`scripts/init_workspace.py\` | \`/init-workspace\`, \`/setup\` | \`python3 ${CLAUDE_SKILL_DIR}/scripts/init_workspace.py\` (copies missing files from \`workspace-template/\` into the workspace root; never overwrites) |`

`tools/security_guards.py` `ALLOWED_SKILL_TOOLS`: add after the `sync_instructions.py` entry:
```python
    "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py:*)",
    "Bash(git init)",
```

- [ ] **Step 5: Docs**

README.md "Install as a plugin (without cloning)": replace the paragraph starting `Then run Claude in an empty folder and run \`/setup\`` with:

```markdown
Then, in an empty folder, run `/init-workspace` (it lays out the CV and cover-letter sources, fonts, the `documents/` tree and a privacy `.gitignore`, and offers `git init`), then `/setup` to fill in your details.
```

and add to "Other commands":

```markdown
- **`/init-workspace`** lays out a job-search workspace in the current folder from the plugin's template: CV and cover-letter sources, fonts, the `documents/` tree, state folders and a privacy `.gitignore`. It copies only what is missing and never overwrites. `/setup` runs it for you too.
```

SETUP.md: at the end of section `## 2. Fork and clone`, add:

```markdown
**Starting from the plugin instead of a clone?** Install it (`/plugin marketplace add MadsLorentzen/ai-job-search`, then `/plugin install ai-job-search@ai-job-search`), open Claude Code in an empty folder and run `/init-workspace`. It lays out the same folders this repository has, then points you to `/setup`.
```

CHANGELOG.md `## [Unreleased]` → `### Added` (top):

```markdown
- **`/init-workspace`: lay out a workspace from the plugin** (`plugins/ai-job-search/skills/init-workspace/`,
  `job-tools/scripts/init_workspace.py`, `job-tools/workspace-template/`) - a plugin install
  has no repository folders, so this copies the author's layout (CV and cover-letter
  sources, fonts, `documents/` tree, state folders, privacy `.gitignore`) into any folder,
  never overwriting, then writes the workspace instructions and offers `git init`. `/setup`
  runs it first. A test keeps the template identical to this repository's own files.
```

- [ ] **Step 6: Run to verify it passes**

Run: `python3 -m unittest discover -s tests -t . 2>&1 | tail -2`; `python3 tools/lint_skills.py && python3 tools/security_guards.py`
Expected: OK; `lint_skills: OK (24 skills, settings.json)`; guards OK.

- [ ] **Step 7: Commit**

```bash
git add plugins tools/security_guards.py README.md SETUP.md CHANGELOG.md tests/test_workspace_init.py
git commit -m "feat: /init-workspace skill; /setup lays out the workspace first"   # plus trailers
```

---

### Task 4: Verification

**Files:** none unless a check fails.

- [ ] **Step 1: CI-equivalent checks**

```bash
python3 -m unittest discover -s tests -t . 2>&1 | tail -2
python3 tools/lint_skills.py && python3 tools/security_guards.py
GITHUB_BASE_REF=plugin/3-instruction-sync python3 tools/check_framework_version.py
claude plugin validate . 2>&1 | grep -E '✔|✘'
claude --plugin-dir plugins/ai-job-search plugin details ai-job-search 2>&1 | grep Skills
```
Expected: all pass; 20 skills including `init-workspace`.

- [ ] **Step 2: /init-workspace end-to-end from a plugin install**

```bash
S=$(mktemp -d) && cd $S && timeout 240 claude -p "/ai-job-search:init-workspace" \
  --plugin-dir /home/mr-fw16/Projects/Source-Codes/ai-job-search/plugins/ai-job-search \
  --model claude-haiku-4-5-20251001 --allowedTools "Skill,AskUserQuestion" --output-format json 2>/dev/null \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('DENIALS:', d.get('permission_denials')); print(str(d.get('result'))[:300])"
ls -a; head -1 AGENTS.md; cat CLAUDE.md; ls cover_letters/OpenFonts/fonts/*/ | head -3; cd -
```
Expected: `DENIALS: []` (or only a `git init` denial if the headless run could not ask; record it); the tree (`cv/`, `cover_letters/`, `documents/`, `templates/`, `job_scraper/`, `company_research/`, `upskill/`, `.gitignore`), `AGENTS.md` starting with the start marker, `CLAUDE.md` = `@AGENTS.md`.

- [ ] **Step 3: Record and fix**

Record results in the ledger; any failure: fix test-first and commit `fix: address workspace init verification findings` (plus trailers).
