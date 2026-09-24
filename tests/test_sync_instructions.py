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
START = "<!-- ai-job-search:start v"
END = "<!-- ai-job-search:end -->"


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

    def test_setup_runs_the_sync_in_step_0a(self):
        setup = paths.command_file("setup")
        self.assertIn(ENTRY, _frontmatter(setup))
        text = setup.read_text(encoding="utf-8")
        step0a = text.split("### Step 0a:", 1)[1].split("#### Legacy fork migration", 1)[0]
        self.assertIn("python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py", step0a)

    def test_guard_reviews_the_entry(self):
        guards = (paths.REPO / "tools" / "security_guards.py").read_text(encoding="utf-8")
        self.assertIn(ENTRY, guards)
