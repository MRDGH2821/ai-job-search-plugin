"""sync_instructions.py keeps AGENTS.md's managed block and CLAUDE.md's import in sync
(spec: docs/superpowers/specs/2026-09-24-instruction-sync-design.md)."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import paths

SCRIPT = paths.JOB_TOOLS / "sync_instructions.py"
START = "<!-- ai-job-search-plugin:start v"
END = "<!-- ai-job-search-plugin:end -->"


def run(root, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True,
                          encoding="utf-8")


class SyncTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.agents = self.root / "AGENTS.md"
        self.claude = self.root / "CLAUDE.md"

    def test_creates_both_files(self):
        proc = run(self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("AGENTS.md: created", proc.stdout)
        self.assertIn("CLAUDE.md: created", proc.stdout)
        text = self.agents.read_text(encoding="utf-8")
        self.assertTrue(text.startswith(START))
        self.assertIn(END, text)
        self.assertIn("profile/", text)
        self.assertNotIn("plugins/", text)
        self.assertEqual(self.claude.read_text(encoding="utf-8"), "@AGENTS.md\n")

    def test_second_run_is_unchanged(self):
        run(self.root)
        before = (self.agents.read_bytes(), self.claude.read_bytes())
        proc = run(self.root)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("AGENTS.md: unchanged", proc.stdout)
        self.assertIn("CLAUDE.md: unchanged", proc.stdout)
        self.assertEqual((self.agents.read_bytes(), self.claude.read_bytes()), before)

    def test_existing_claude_md_keeps_every_line(self):
        self.claude.write_text("# My notes\n\nKeep this.\n", encoding="utf-8")
        run(self.root)
        self.assertEqual(self.claude.read_text(encoding="utf-8"), "@AGENTS.md\n\n# My notes\n\nKeep this.\n")

    def test_import_already_present_is_left_alone(self):
        self.claude.write_text("# Notes\n  @AGENTS.md  \n", encoding="utf-8")
        proc = run(self.root)
        self.assertIn("CLAUDE.md: unchanged", proc.stdout)
        self.assertEqual(self.claude.read_text(encoding="utf-8"), "# Notes\n  @AGENTS.md  \n")

    def test_foreign_text_and_capa_blocks_survive(self):
        foreign = "# Codex notes\n\n<!-- capa:start:x -->\ncapa text\n<!-- capa:end:x -->\n\nTail ünïcödé.\n"
        self.agents.write_text(foreign, encoding="utf-8")
        run(self.root)
        text = self.agents.read_text(encoding="utf-8")
        self.assertTrue(text.startswith(foreign.rstrip("\n") + "\n\n" + START))
        self.assertEqual(text.count(START), 1)

    def test_stale_block_replaced_in_place(self):
        self.agents.write_text(f"head\n{START}0.0.1 -->\nold body\n{END}\ntail\n", encoding="utf-8")
        run(self.root)
        text = self.agents.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("head\n" + START))
        self.assertTrue(text.endswith(END + "\ntail\n"))
        self.assertNotIn("old body", text)

    def test_malformed_markers_write_nothing(self):
        cases = [f"{START}1 -->\nno end\n", f"no start\n{END}\n", f"{END}\n{START}1 -->\n",
                 f"{START}1 -->\n{END}\n{START}1 -->\n{END}\n"]
        for case in cases:
            self.agents.write_text(case, encoding="utf-8")
            self.claude.write_text("mine\n", encoding="utf-8")
            proc = run(self.root)
            self.assertEqual(proc.returncode, 2, case)
            self.assertIn("line", proc.stderr)
            self.assertEqual(self.agents.read_text(encoding="utf-8"), case)
            self.assertEqual(self.claude.read_text(encoding="utf-8"), "mine\n")

    def test_symlinked_claude_md_gets_no_import(self):
        self.agents.write_text("x\n", encoding="utf-8")
        try:
            os.symlink("AGENTS.md", self.claude)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        proc = run(self.root)
        self.assertIn("CLAUDE.md: unchanged (symlink to AGENTS.md)", proc.stdout)
        self.assertNotIn("@AGENTS.md", self.agents.read_text(encoding="utf-8"))

    def test_crlf_and_bom_are_kept(self):
        self.agents.write_bytes(b"\xef\xbb\xbfhead\r\ntail\r\n")
        self.claude.write_bytes(b"notes\r\n")
        run(self.root)
        a, c = self.agents.read_bytes(), self.claude.read_bytes()
        self.assertTrue(a.startswith(b"\xef\xbb\xbfhead\r\n"))
        self.assertNotIn(b"\n", a.replace(b"\r\n", b""))
        self.assertEqual(c, b"@AGENTS.md\r\n\r\nnotes\r\n")

    def test_root_flag(self):
        other = self.root / "ws"
        other.mkdir()
        proc = run(self.root, "--root", str(other))
        self.assertEqual(proc.returncode, 0)
        self.assertTrue((other / "AGENTS.md").exists())
        self.assertFalse(self.agents.exists())


class CheckTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_in_sync(self):
        run(self.root)
        self.assertEqual(run(self.root, "--check").returncode, 0)

    def test_drift_cases_exit_1_and_write_nothing(self):
        run(self.root)
        agents = self.root / "AGENTS.md"
        good = agents.read_text(encoding="utf-8")
        for mutate in (lambda: agents.unlink(),
                       lambda: agents.write_text("no block\n", encoding="utf-8"),
                       lambda: agents.write_text(good.replace("profile/", "PROFILE/", 1), encoding="utf-8"),
                       lambda: (self.root / "CLAUDE.md").write_text("nothing\n", encoding="utf-8")):
            run(self.root)
            mutate()
            snapshot = {p.name: p.read_bytes() for p in self.root.iterdir()}
            proc = run(self.root, "--check")
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, snapshot)


import re as _re  # noqa: E402

ENTRY = "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py:*)"


def _frontmatter(path):
    m = _re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), _re.DOTALL)
    return m.group(1) if m else ""


class WiringTests(unittest.TestCase):
    def test_skill_is_user_only_and_preapproved(self):
        skill = paths.skill_file("sync-instructions")
        fm = _frontmatter(skill)
        self.assertIn("name: sync-instructions", fm)
        self.assertIn("disable-model-invocation: true", fm)
        self.assertIn(ENTRY, fm)
        body = skill.read_text(encoding="utf-8").split("\n---\n", 1)[1]
        self.assertTrue(body.lstrip().startswith("# /sync-instructions "))
        self.assertIn("python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py", body)

    def test_skill_runs_without_asking_again(self):
        # Task 4 probe: the model asked "Would you like me to proceed?" and wrote nothing.
        body = paths.skill_file("sync-instructions").read_text(encoding="utf-8")
        self.assertIn("Run it now, without asking for confirmation", body)
        # A `cd … &&` prefix does not match the permission and can target the wrong folder.
        self.assertIn("as one command: no `cd`, no `&&`", body)

    def test_setup_runs_the_sync_in_step_0a(self):
        setup = paths.command_file("setup")
        self.assertIn(ENTRY, _frontmatter(setup))
        text = setup.read_text(encoding="utf-8")
        step0a = text.split("### Step 0a:", 1)[1].split("\n### ", 1)[0]
        self.assertIn("python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py", step0a)
        self.assertIn("no `cd`, no `&&`", step0a)

    def test_guard_reviews_the_entry(self):
        guards = (paths.REPO / "tools" / "security_guards.py").read_text(encoding="utf-8")
        self.assertIn(ENTRY, guards)


class RepoRootTests(unittest.TestCase):
    def test_claude_md_is_just_the_import(self):
        self.assertEqual((paths.REPO / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")

    def test_readme_and_changelog_mention_the_command(self):
        self.assertIn("/sync-instructions", (paths.REPO / "README.md").read_text(encoding="utf-8"))
        changelog = (paths.REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = changelog.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0]
        self.assertIn("/sync-instructions", unreleased)


class ReviewFixTests(unittest.TestCase):
    """Final review, branch 3: symlinks, unreadable files, and writes outside the workspace."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.agents = self.root / "AGENTS.md"
        self.claude = self.root / "CLAUDE.md"

    def _symlink(self, target, link):
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")

    def test_agents_symlink_to_claude_gets_the_block_in_one_run(self):
        self.claude.write_text("notes\n", encoding="utf-8")
        self._symlink("CLAUDE.md", self.agents)
        proc = run(self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = self.claude.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("notes\n"))
        self.assertIn(START, text)
        self.assertNotIn("\n@AGENTS.md", "\n" + text)  # no self-import line
        self.assertIn("CLAUDE.md: unchanged (same file as AGENTS.md)", proc.stdout)
        self.assertIn("unchanged", run(self.root).stdout)

    def test_unreadable_file_exits_2_and_writes_nothing(self):
        self.agents.write_bytes(b"\xff\xfe not utf-8 \x81")
        proc = run(self.root)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("AGENTS.md", proc.stderr)
        self.assertEqual(self.agents.read_bytes(), b"\xff\xfe not utf-8 \x81")
        self.assertFalse(self.claude.exists())
        self.assertEqual(run(self.root, "--check").returncode, 2)

    def test_dangling_claude_symlink_exits_2_before_writing(self):
        self._symlink("missing-target.md", self.claude)
        proc = run(self.root)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertFalse(self.agents.exists(), "AGENTS.md must not be written when CLAUDE.md cannot be")

    def test_claude_symlink_outside_the_workspace_is_left_alone(self):
        shared_dir = tempfile.TemporaryDirectory()
        self.addCleanup(shared_dir.cleanup)
        shared = Path(shared_dir.name) / "SHARED.md"
        shared.write_text("shared rules\n", encoding="utf-8")
        self._symlink(str(shared), self.claude)
        proc = run(self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(shared.read_text(encoding="utf-8"), "shared rules\n")
        self.assertIn("CLAUDE.md: unchanged (symlink", proc.stdout)

    def test_symlinked_agents_md_stays_a_symlink(self):
        (self.root / "docs").mkdir()
        target = self.root / "docs" / "AGENTS.md"
        target.write_text("team notes\n", encoding="utf-8")
        self._symlink("docs/AGENTS.md", self.agents)
        run(self.root)
        self.assertTrue(self.agents.is_symlink())
        self.assertIn(START, target.read_text(encoding="utf-8"))
        self.assertEqual([p.name for p in (self.root / "docs").iterdir()], ["AGENTS.md"], "no temp files left behind")

    def test_callers_describe_every_exit_2_cause(self):
        for text in (paths.skill_file("sync-instructions").read_text(encoding="utf-8"),
                     paths.command_file("setup").read_text(encoding="utf-8")):
            self.assertIn("unreadable file or broken symlink", text)


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
