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
        self.assertEqual(data["name"], "ai-job-search-plugin")
        entries = {p["name"]: p["source"] for p in data["plugins"]}
        self.assertEqual(entries, {"ai-job-search-plugin": "./plugins/ai-job-search-plugin",
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


class TestSkillPaths(unittest.TestCase):
    def test_no_legacy_paths_in_framework_text(self):
        bad = re.compile(r"\.claude/(commands|skills|agents)/|(?<![\w/.])tools/(%s)\.py|python3? salary_lookup\.py"
                         % "|".join(RUNTIME))
        offenders = []
        for md in paths.framework_markdown() + [REPO / "CLAUDE.md"]:
            text = md.read_text(encoding="utf-8")
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
        self.assertEqual(data["extraKnownMarketplaces"]["ai-job-search-plugin"]["source"],
                         {"source": "directory", "path": "./"})
        self.assertIs(data["enabledPlugins"]["ai-job-search-plugin@ai-job-search-plugin"], True)
        self.assertIn("danish-job-portals@ai-job-search-plugin", data["enabledPlugins"])
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


class TestPortals(unittest.TestCase):
    def test_portals_run_their_cli_from_their_own_folder(self):
        for d in paths.portal_dirs():
            text = (d / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn(".agents/skills/", text, d.name)
            self.assertIn("bun run ${CLAUDE_SKILL_DIR}/cli/src/cli.ts", text, d.name)
            self.assertIn("Bash(bun run ${CLAUDE_SKILL_DIR}/cli/src/cli.ts *)",
                          frontmatter(d / "SKILL.md").get("allowed-tools", ""), d.name)

    def test_danish_portals_self_install(self):
        for d in paths.portal_dirs():
            deps = json.loads((d / "cli" / "package.json").read_text(encoding="utf-8")).get("dependencies", {})
            text = (d / "SKILL.md").read_text(encoding="utf-8")
            if deps:
                self.assertIn("bun install --cwd ${CLAUDE_SKILL_DIR}/cli", text, d.name)
                self.assertIn("Bash(bun install --cwd ${CLAUDE_SKILL_DIR}/cli)",
                              frontmatter(d / "SKILL.md").get("allowed-tools", ""), d.name)

    def test_scrape_discovers_plugin_and_workspace_portals(self):
        text = paths.skill_file("job-scraper").read_text(encoding="utf-8")
        self.assertIn("ends in `-search`", text)
        self.assertIn("Skill tool", text)
        self.assertIn(".agents/skills/*/SKILL.md", text)

    def test_scrape_subagents_load_portal_skill(self):
        text = paths.skill_file("job-scraper").read_text(encoding="utf-8")
        self.assertIn("each subagent must first load its portal skill with the Skill tool", text)


class TestDocs(unittest.TestCase):
    def test_readme_explains_both_install_routes_and_capa(self):
        text = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("/plugin marketplace add MadsLorentzen/ai-job-search", text)
        self.assertIn("/plugin install ai-job-search-plugin@ai-job-search-plugin", text)
        self.assertIn("capa registry add MadsLorentzen/ai-job-search", text)
        self.assertIn("untested outside Claude Code", text)
        self.assertNotIn(".claude/commands/", text)

    def test_setup_md_has_the_upgrade_section(self):
        text = (REPO / "SETUP.md").read_text(encoding="utf-8")
        section = text.split("## 10. Upgrading across the plugin layout change", 1)[1].split("\n## ", 1)[0]
        for needle in ("trust", "plugins/ai-job-search-plugin/skills/", "settings.local.json", "danish-job-portals"):
            self.assertIn(needle, section)

    def test_agents_md_and_contributing_point_at_capa(self):
        for name in ("CONTRIBUTING.md",):
            text = (REPO / name).read_text(encoding="utf-8")
            self.assertIn("capa", text, name)
            self.assertNotIn("auto-discovered", text, name)

    def test_changelog_flags_the_layout_break(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = text.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0]
        self.assertIn("BREAKING (forks): the framework moves into plugins", unreleased)


class TestProfileGuardReachable(unittest.TestCase):
    def test_guard_references_resolve_from_a_plugin_install(self):
        # A bare `job-application-assistant/SKILL.md` resolves in a clone but not from a
        # plugin cache: the model cannot find the guard and improvises (Task 8 probe).
        offenders = []
        for p in paths.all_skill_files():
            if p.parent.name == "job-application-assistant":
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                if "Profile Guard" in line and ("${CLAUDE_SKILL_DIR}/../job-application-assistant/SKILL.md" not in line
                                                or "/setup" not in line):
                    offenders.append(f"{p.relative_to(REPO)}: {line.strip()[:80]}")
        self.assertEqual(offenders, [])


class TestReviewFixes(unittest.TestCase):
    def test_framework_files_do_not_use_cwd_relative_script_paths(self):
        for md in sorted(paths.FW.glob("*.md")):
            text = md.read_text(encoding="utf-8")
            self.assertNotIn("../job-tools/", text, md.name)
            if "<job-tools>" in text and md.name != "SKILL.md":  # SKILL.md defines it
                self.assertIn("<job-tools>/scripts/", text, md.name)
        for skill in ("job-application-assistant", "apply"):
            text = paths.skill_file(skill).read_text(encoding="utf-8")
            self.assertIn("`<job-tools>` means `${CLAUDE_SKILL_DIR}/../job-tools`", text, skill)

    def test_shipped_portals_are_not_forked(self):
        for d in paths.portal_dirs():
            self.assertNotIn("context", frontmatter(d / "SKILL.md"), d.name)

    def test_danish_portals_are_gated_by_the_plugin_not_the_file(self):
        for d in paths.portal_dirs():
            self.assertTrue(str(frontmatter(d / "SKILL.md").get("enabled")).lower().startswith("true"), d.name)
        data = json.loads(paths.SETTINGS.read_text(encoding="utf-8"))
        self.assertIs(data["enabledPlugins"]["danish-job-portals@ai-job-search-plugin"], False)
        setup = paths.command_file("setup").read_text(encoding="utf-8")
        self.assertNotIn("edit each of the four Danish `SKILL.md` files", setup)
        self.assertIn("danish-job-portals@ai-job-search-plugin", setup)

    def test_portal_opt_outs_live_in_the_workspace(self):
        self.assertIn("disabled-portals", {h for h in __import__("tests.test_profile_separation", fromlist=["headings"]).headings(paths.TPL / "search-queries.md")})
        scrape = paths.skill_file("job-scraper").read_text(encoding="utf-8")
        self.assertIn("`profile/search-queries.md#disabled-portals`", scrape)
        self.assertNotIn("offer to set that portal's `enabled: false`", scrape)
        tpl = (paths.TPL / "search-queries.md").read_text(encoding="utf-8")
        self.assertNotIn("under `.agents/skills/*/SKILL.md` and runs its CLI first", tpl)
