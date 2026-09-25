"""The job-tools scripts run from the workspace root (the current directory).

After the plugin move the scripts live in plugins/ai-job-search/skills/job-tools/scripts/,
and in a plugin install inside the plugin cache. A default path derived from
__file__ points there instead of at the user's workspace (final review, branch 2).
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import paths


def run(script, *args, cwd):
    return subprocess.run([sys.executable, str(paths.JOB_TOOLS / script), *args],
                          cwd=cwd, capture_output=True, text=True)


class TestScriptsUseTheWorkspace(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ws = Path(tmp.name)
        (self.ws / "job_scraper").mkdir()
        (self.ws / "job_scraper" / "seen_jobs.json").write_text(
            json.dumps({"version": 1, "seen": {}}), encoding="utf-8")

    def test_rank_state_reads_the_workspace_state(self):
        proc = run("rank_state.py", "candidates", cwd=self.ws)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("job-tools", proc.stdout + proc.stderr)

    def test_job_key_audits_the_workspace_state(self):
        proc = run("job_key.py", "--audit", cwd=self.ws)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("job-tools", proc.stdout + proc.stderr)
