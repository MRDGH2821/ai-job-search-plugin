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
