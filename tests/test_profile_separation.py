"""Guards for the profile/ separation (spec: docs/superpowers/specs/
2026-09-24-plugin-profile-separation-design.md, branch 1).

Candidate data lives in a workspace profile/ folder created from the
framework-owned templates in profile-templates/. Framework files hold rules
only and point at profile data with `profile/<file>.md#<anchor>` links.
"""
import re
import unittest
from pathlib import Path
from tests import paths

REPO = Path(__file__).resolve().parent.parent
FW = paths.FW
TPL = FW / "profile-templates"
TEMPLATES = (
    "candidate.md",
    "behavioral.md",
    "evaluation.md",
    "cv.md",
    "cover-letter.md",
    "writing-patterns.md",
    "star.md",
    "search-queries.md",
)
# A token /setup fills. Each template must still carry its sentinel.
SENTINELS = {
    "candidate.md": "[YOUR_EMAIL]",
    "behavioral.md": "[PROFILE_TYPE]",
    "evaluation.md": "[YOUR_PRIMARY_SKILLS]",
    "cv.md": "[YOUR_PROFILE_STATEMENT_TEMPLATE_1]",
    "cover-letter.md": "## Patterns From Past Letters",
    "writing-patterns.md": "## Patterns Observed in Past Applications",
    "star.md": "[PROJECT_NAME]",
    "search-queries.md": "[YOUR_JOB_BOARD]",
}
REQUIRED_HEADINGS = {
    "candidate.md": ["Identity", "Languages", "Education", "Professional Experience",
                     "Independent Projects", "Technical Skills", "Certifications",
                     "Publications", "Awards", "References"],
    "evaluation.md": ["Skill Match Areas", "Experience Areas", "Career Goals",
                      "What Excites You", "Target Sectors", "Deal-breakers",
                      "Motivation", "Life Situation", "Eligibility Constraints",
                      "Calibration"],
    "cv.md": ["Active Template", "Profile Statements"],
    "cover-letter.md": ["Active Template", "Patterns From Past Letters"],
    "writing-patterns.md": ["Patterns Observed in Past Applications"],
    "star.md": ["Ready-Made STAR Examples", "STAR Candidates (Complete Manually)"],
}


def slug(heading: str) -> str:
    """GitHub-style anchor for a markdown heading."""
    text = heading.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def headings(path: Path) -> set[str]:
    """Slugs of every ATX heading in a markdown file."""
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
        if m:
            found.add(slug(m.group(1)))
    return found


class TestTemplates(unittest.TestCase):
    def test_every_template_exists(self):
        for name in TEMPLATES:
            path = TPL / name
            self.assertTrue(path.is_file(), f"missing template {path}")

    def test_templates_carry_their_setup_sentinel(self):
        for name, sentinel in SENTINELS.items():
            self.assertIn(sentinel, (TPL / name).read_text(encoding="utf-8"), name)

    def test_templates_have_required_headings(self):
        for name, wanted in REQUIRED_HEADINGS.items():
            have = headings(TPL / name)
            missing = [h for h in wanted if slug(h) not in have]
            self.assertEqual(missing, [], f"{name} lacks headings {missing}")

    def test_candidate_template_holds_fields_that_lived_in_claude_md(self):
        text = (TPL / "candidate.md").read_text(encoding="utf-8")
        self.assertIn("**CV language:**", text)
        self.assertIn("**LinkedIn headline:**", text)


SETUP_TOKEN = re.compile(r"\[(?:YOUR_[A-Z0-9_]+|FIRST_NAME|LAST_NAME)\]")
FRAMEWORK_FILES = [
    "03-writing-style.md", "04-job-evaluation.md", "05-cv-templates.md",
    "06-cover-letter-templates.md", "07-interview-prep.md",
    "08-application-forms.md", "09-web-research.md", "10-verification.md", "SKILL.md",
]
POINTER = re.compile(r"`profile/([\w-]+\.md)(?:#([\w-]+))?`")


def pointer_sources():
    """Every markdown file that may point into profile/."""
    files = paths.framework_markdown()
    files = [f for f in files if TPL not in f.parents]
    for extra in ("CLAUDE.md", "AGENTS.md"):
        if (REPO / extra).exists():
            files.append(REPO / extra)
    return files


class TestFrameworkFilesHoldRulesOnly(unittest.TestCase):
    def test_framework_files_have_no_setup_tokens(self):
        offenders = {}
        for name in FRAMEWORK_FILES:
            path = FW / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            if name == "SKILL.md" and "## Profile Guard" in text:
                # The guard names the [YOUR_EMAIL] sentinel it checks for.
                head, tail = text.split("## Profile Guard", 1)
                text = head + ("\n## " + tail.split("\n## ", 1)[1] if "\n## " in tail else "")
            hits = sorted(set(SETUP_TOKEN.findall(text)))
            if hits:
                offenders[name] = hits
        self.assertEqual(offenders, {}, "framework files must not carry /setup slots")

    def test_draft_time_tokens_use_candidate_prefix(self):
        cv = (FW / "05-cv-templates.md").read_text(encoding="utf-8")
        cover = (FW / "06-cover-letter-templates.md").read_text(encoding="utf-8")
        for token in ("[CANDIDATE_FIRST_NAME]", "[CANDIDATE_LAST_NAME]",
                      "[CANDIDATE_EMAIL]", "[CANDIDATE_PHONE]"):
            self.assertIn(token, cv)
        self.assertIn("\\signature{[CANDIDATE_NAME]}", cover)
        self.assertIn("profile/candidate.md#identity", cv)
        self.assertIn("profile/candidate.md#identity", cover)

    def test_every_profile_pointer_resolves(self):
        broken = []
        for path in pointer_sources():
            for name, anchor in POINTER.findall(path.read_text(encoding="utf-8")):
                tpl = TPL / name
                if name not in TEMPLATES or not tpl.exists():
                    broken.append(f"{path.relative_to(REPO)}: profile/{name}")
                elif anchor and anchor not in headings(tpl):
                    broken.append(f"{path.relative_to(REPO)}: profile/{name}#{anchor}")
        self.assertEqual(broken, [], "pointers into profile/ must hit a real template heading")

    def test_skill_defines_profile_guard(self):
        text = (FW / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Profile Guard", text)
        guard = text.split("## Profile Guard", 1)[1].split("\n## ", 1)[0]
        self.assertIn("profile/candidate.md", guard)
        self.assertIn("[YOUR_EMAIL]", guard)
        self.assertIn("/setup", guard)


APPLY = paths.command_file("apply")


class TestClaudeMdAndApply(unittest.TestCase):
    def test_verification_file_holds_workflow_and_checklist(self):
        text = (FW / "10-verification.md").read_text(encoding="utf-8")
        self.assertIn("## Workflow for New Job Applications", text)
        self.assertIn("## Verification Checklist", text)
        self.assertIn("### Compiled PDF verification (MANDATORY - never skip)", text)

    def test_claude_md_holds_no_personal_data(self):
        text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIsNone(SETUP_TOKEN.search(text), "CLAUDE.md must hold no /setup slots")
        self.assertNotIn("## Candidate Profile", text)
        self.assertNotIn("## Verification Checklist", text)
        agents = (paths.JOB_TOOLS / "agents-block.md").read_text(encoding="utf-8")
        self.assertIn("10-verification.md", agents)
        self.assertIn("profile/", agents)

    def test_apply_runs_profile_guard_first(self):
        text = APPLY.read_text(encoding="utf-8")
        step1 = text.split("## Step 1", 1)[1].split("\n## ", 1)[0]
        self.assertIn("Profile Guard", step1)

    def test_apply_no_longer_reads_claude_md_for_facts(self):
        text = APPLY.read_text(encoding="utf-8")
        self.assertNotIn("Candidate Profile section", text)
        self.assertNotIn("checklist from `CLAUDE.md`", text)
        self.assertIn("10-verification.md", text)
        self.assertIn("`profile/candidate.md#identity`", text)


LEGACY_NAMES = ("01-candidate-profile.md", "02-behavioral-profile.md", "job-scraper/search-queries.md")


def strip_setup_migration(text: str) -> str:
    """Remove /setup's Legacy fork migration subsection, the one allowed mention."""
    marker = "#### Legacy fork migration"
    if marker not in text:
        return text
    head, tail = text.split(marker, 1)
    rest = tail.split("\n### ", 1)
    return head + ("\n### " + rest[1] if len(rest) > 1 else "")


class TestNoLegacyReferences(unittest.TestCase):
    def test_claude_tree_names_no_legacy_profile_files(self):
        offenders = []
        files = paths.framework_markdown() + [REPO / "CLAUDE.md", paths.WT / "documents" / "README.md"]
        for path in files:
            text = strip_setup_migration(path.read_text(encoding="utf-8"))
            for name in LEGACY_NAMES:
                if name in text:
                    offenders.append(f"{path.relative_to(REPO)}: {name}")
        self.assertEqual(offenders, [], "legacy profile paths still referenced")

    def test_search_queries_read_from_profile(self):
        scraper = (paths.skill_file("job-scraper")).read_text(encoding="utf-8")
        self.assertIn("profile/search-queries.md", scraper)
        self.assertNotIn("`search-queries.md` (this directory)", scraper)


class TestTemplatesPointAtProfile(unittest.TestCase):
    def test_no_template_sends_readers_to_claude_md(self):
        offenders = [n for n in TEMPLATES if "CLAUDE.md" in (TPL / n).read_text(encoding="utf-8")]
        self.assertEqual(offenders, [], "templates must point at profile/, not CLAUDE.md")


class TestLegacyFilesRemoved(unittest.TestCase):
    def test_legacy_profile_files_are_gone(self):
        for path in (FW / "01-candidate-profile.md", FW / "02-behavioral-profile.md",
                     REPO / ".claude" / "skills" / "job-scraper" / "search-queries.md"):
            self.assertFalse(path.exists(), f"{path.relative_to(REPO)} should be deleted")


class TestDocs(unittest.TestCase):
    def test_docs_name_no_legacy_profile_files_outside_migration(self):
        setup_md = (REPO / "SETUP.md").read_text(encoding="utf-8")
        migration = "## 9. Merging the profile-separation change into a personalized fork"
        self.assertIn(migration, setup_md)
        before, after = setup_md.split(migration, 1)
        rest = after.split("\n## ", 1)
        outside = before + (rest[1] if len(rest) > 1 else "")
        for text, where in ((outside, "SETUP.md"), ((REPO / "README.md").read_text(encoding="utf-8"), "README.md"),
                            ((REPO / "AGENTS.md").read_text(encoding="utf-8"), "AGENTS.md")):
            for name in ("01-candidate-profile.md", "02-behavioral-profile.md"):
                self.assertNotIn(name, text, f"{where} still names {name}")

    def test_setup_md_restores_templates_before_committing_the_merge(self):
        setup_md = (REPO / "SETUP.md").read_text(encoding="utf-8")
        section9 = setup_md.split("## 9. Merging the profile-separation change", 1)[1].split("\n## ", 1)[0]
        self.assertIn("git checkout MERGE_HEAD -- plugins/ai-job-search-plugin/skills/job-application-assistant/profile-templates/", section9)
        self.assertLess(section9.index("MERGE_HEAD"), section9.index("Commit the merge"))

    def test_setup_md_covers_claude_md_and_deleted_file_conflicts(self):
        setup_md = (REPO / "SETUP.md").read_text(encoding="utf-8")
        section9 = setup_md.split("## 9. Merging the profile-separation change", 1)[1].split("\n## ", 1)[0]
        self.assertIn("CLAUDE.md", section9)
        self.assertIn("git rm", section9)

    def test_changelog_flags_the_fork_break(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = text.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0]
        self.assertIn("BREAKING (personalized forks)", unreleased)
        self.assertIn("profile/", unreleased)


if __name__ == "__main__":
    unittest.main()
