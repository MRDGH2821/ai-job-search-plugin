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
