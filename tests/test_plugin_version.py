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
