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


RUNTIME = ("rank_state", "job_key", "verify_pdf", "verify_layout", "robots_check",
           "convert_salary_excel")
FALLBACK = ("`${CLAUDE_SKILL_DIR}` is this skill's folder. If your tool does not expand it, "
            "read paths as relative to the folder containing this SKILL.md.")
SKILL_DIR_REF = re.compile(r"\$\{CLAUDE_SKILL_DIR\}(/[^\s`'\")|*>]+)")


def strip_setup_migration(text):
    """/setup's Legacy fork migration reads old paths from git history; they stay literal."""
    marker = "#### Legacy fork migration"
    if marker not in text:
        return text
    head, tail = text.split(marker, 1)
    rest = tail.split("\n### ", 1)
    return head + ("\n### " + rest[1] if len(rest) > 1 else "")


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

    def test_skill_bodies_call_scripts_with_python3(self):
        offenders = [str(p.relative_to(REPO)) for p in paths.all_skill_files()
                     if re.search(r"(^|[^3])python \$\{CLAUDE_SKILL_DIR\}", p.read_text(encoding="utf-8"), re.M)]
        self.assertEqual(offenders, [])
