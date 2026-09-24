"""Workspace init (spec: docs/superpowers/specs/2026-09-24-workspace-init-design.md)."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import paths

WT = paths.WT

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


class TestReviewFixes(unittest.TestCase):
    """Final review, branch 4: the privacy .gitignore must never be weakened or skipped."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_no_negation_is_appended_to_an_existing_gitignore(self):
        (self.root / ".gitignore").write_text("cv/*\n*.tex\n", encoding="utf-8")
        run(self.root)
        appended = (self.root / ".gitignore").read_text(encoding="utf-8").split(HEADER, 1)[1]
        self.assertFalse([l for l in appended.splitlines() if l.strip().startswith("!")], appended)

    def test_gitignore_is_written_before_a_mid_copy_failure(self):
        if os.name == "nt" or os.geteuid() == 0:
            self.skipTest("needs POSIX permissions and a non-root user")
        (self.root / "documents").mkdir()
        (self.root / "documents").chmod(0o500)
        self.addCleanup((self.root / "documents").chmod, 0o700)
        proc = run(self.root)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertTrue((self.root / ".gitignore").is_file(), "privacy rules must land first")

    def test_dangling_gitignore_symlink_is_refused(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        leak = Path(outside.name) / "leak"
        try:
            os.symlink(str(leak), self.root / ".gitignore")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        proc = run(self.root)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertFalse(leak.exists(), "wrote outside the workspace")

    def test_callers_stop_on_exit_2(self):
        setup = paths.command_file("setup").read_text(encoding="utf-8")
        step0a = setup.split("### Step 0a:", 1)[1].split("#### Legacy fork migration", 1)[0]
        item1 = step0a.split("\n2. ", 1)[0]
        self.assertIn("stop", item1.lower())
        self.assertNotIn("show its message and continue", item1)
