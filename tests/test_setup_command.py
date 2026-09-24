"""Guards for the /setup command spec.

The command is a markdown spec (the spec IS the implementation). These tests pin
one invariant that broke silently: Step 3 must personalise every contact block
that `/apply` later compiles into a document. `cv/main_example.tex` was covered;
the LaTeX blocks embedded in `05-cv-templates.md` and `06-cover-letter-templates.md`
were not, so a full Path B/C run left `[YOUR_NAME]`, `[YOUR_EMAIL]` and
`[YOUR_PHONE]` in both, and whether they reached a compiled cover letter depended
on the drafter noticing. A real user (#420) ran `/setup` and then hand-edited both
files to close the gap.
"""
import unittest
from pathlib import Path
from tests import paths


REPO = Path(__file__).resolve().parent.parent
COMMAND = paths.command_file("setup")
SKILL_DIR = paths.FW
CV_TEMPLATES = SKILL_DIR / "05-cv-templates.md"
COVER_TEMPLATES = SKILL_DIR / "06-cover-letter-templates.md"
TPL = SKILL_DIR / "profile-templates"


def _sections(text: str) -> dict[str, str]:
    """Split a command spec into {heading: body} by '## ' headers."""
    parts = text.split("\n## ")
    result = {}
    for part in parts[1:]:
        heading, _, body = part.partition("\n")
        result[heading.strip()] = body
    return result


def _substeps(step_body: str) -> dict[str, str]:
    """Split a step body into {'### N. ...' heading: body}."""
    parts = step_body.split("\n### ")
    result = {}
    for part in parts[1:]:
        heading, _, body = part.partition("\n")
        result[heading.strip()] = body
    return result


class SetupWritesOnlyToProfile(unittest.TestCase):
    def setUp(self):
        self.text = COMMAND.read_text(encoding="utf-8")
        self.sections = _sections(self.text)
        self.step3 = self.sections["Step 3: Generate Profile Files"]

    def test_step3_targets_are_profile_files_with_templates(self):
        import re
        targets = re.findall(r"^###\s+\d+\.\s+\w+\s+`([^`]+)`", self.step3, re.MULTILINE)
        profile_targets = [t for t in targets if t.startswith("profile/")]
        self.assertGreaterEqual(len(profile_targets), 7, targets)
        for t in profile_targets:
            self.assertTrue((TPL / t.split("/", 1)[1]).exists(), f"no template for {t}")
        for t in targets:
            self.assertFalse(t.startswith(".claude/"), f"Step 3 still writes framework file {t}")

    def test_step3_never_edits_framework_latex_blocks(self):
        self.assertNotIn("05-cv-templates.md", self.step3)
        self.assertNotIn("06-cover-letter-templates.md", self.step3)

    def test_step0a_copies_only_missing_templates(self):
        step0 = self.sections["Step 0: Welcome & Choose Path"]
        self.assertIn("### Step 0a: Prepare the profile folder", step0)
        block = step0.split("### Step 0a: Prepare the profile folder", 1)[1]
        self.assertIn("profile-templates/", block)
        self.assertIn("only the missing", block.lower())
        self.assertIn("never overwrite", block.lower())

    def test_step0a_runs_before_section_shortcut(self):
        step0 = self.sections["Step 0: Welcome & Choose Path"]
        self.assertLess(step0.index("Step 0a"), step0.index("--section <name>"))

    def test_completion_summary_lists_profile_files(self):
        summary = self.sections["Step 4: Confirm & Next Steps"].split("**Privacy note:**")[0]
        for name in ("profile/candidate.md", "profile/evaluation.md", "profile/search-queries.md"):
            self.assertIn(name, summary)
        self.assertNotIn(".claude/skills/", summary)


class TemplatesStillCarryThePlaceholders(unittest.TestCase):
    """The instructions above target real tokens; if a template renames them,
    the instruction and this test must move together."""

    def test_cv_templates_contact_block_tokens(self):
        text = CV_TEMPLATES.read_text(encoding="utf-8")
        for token in ("[CANDIDATE_FIRST_NAME]", "[CANDIDATE_LAST_NAME]", "[CANDIDATE_EMAIL]", "[CANDIDATE_PHONE]"):
            self.assertIn(token, text)

    def test_cover_letter_templates_contact_and_signature_tokens(self):
        text = COVER_TEMPLATES.read_text(encoding="utf-8")
        for token in ("[CANDIDATE_NAME]", "[CANDIDATE_EMAIL]", "[CANDIDATE_PHONE]", "[CANDIDATE_LINKEDIN_URL]"):
            self.assertIn(token, text)
        self.assertIn("\\signature{[CANDIDATE_NAME]}", text)


class SetupPathAProjectsIngestion(unittest.TestCase):
    """Guards for /setup Path A document ingestion of documents/projects/."""

    def setUp(self):
        self.text = COMMAND.read_text(encoding="utf-8")
        self.sections = _sections(self.text)

    def test_step0_scan_includes_projects(self):
        step0 = self.sections["Step 0: Welcome & Choose Path"]
        self.assertIn("projects/", step0)

    def test_step_a1_inventory_includes_projects(self):
        self.assertIn("**projects/**:", self.text)

    def test_step_a3_parsing_includes_projects_spec(self):
        self.assertIn("`projects/` documents:", self.text)
        self.assertIn("measurable outcomes", self.text)

    def test_step_a5_and_a6_map_to_independent_projects(self):
        self.assertIn("## Independent Projects", self.text)
        self.assertIn("New independent project:", self.text)


class SetupLegacyMigration(unittest.TestCase):
    def setUp(self):
        text = COMMAND.read_text(encoding="utf-8")
        step0 = _sections(text)["Step 0: Welcome & Choose Path"]
        self.assertIn("#### Legacy fork migration", step0)
        self.block = step0.split("#### Legacy fork migration", 1)[1].split("\n### ", 1)[0]

    def test_detection_uses_git_history_and_the_sentinel(self):
        self.assertIn("git show", self.block)
        self.assertIn("ORIG_HEAD", self.block)
        self.assertIn("[YOUR_EMAIL]", self.block)
        self.assertIn("01-candidate-profile.md", self.block)

    def test_mapping_covers_every_legacy_region(self):
        for legacy in ("01-candidate-profile.md", "02-behavioral-profile.md", "03-writing-style.md",
                       "04-job-evaluation.md", "05-cv-templates.md", "06-cover-letter-templates.md",
                       "07-interview-prep.md", "search-queries.md", "CLAUDE.md"):
            self.assertIn(legacy, self.block, f"migration mapping omits {legacy}")

    def test_migration_carries_active_template(self):
        self.assertIn("ACTIVE-TEMPLATE", self.block)
        self.assertIn("profile/cv.md", self.block)
        self.assertIn("profile/cover-letter.md", self.block)

    def test_migration_reports_conflicts(self):
        self.assertIn("conflict", self.block.lower())
        self.assertIn("never silently", self.block.lower())

    def test_migration_repairs_templates_polluted_by_rename_detection(self):
        # git's rename detection merges a fork's personalized 01/02/search-queries
        # INTO the new templates without a conflict (seen in a scratch-fork merge).
        self.assertIn("rename", self.block.lower())
        self.assertIn("profile-templates/", self.block)
        self.assertIn("[PROFILE_TYPE]", self.block)
        self.assertIn("[YOUR_JOB_BOARD]", self.block)

    def test_history_walk_survives_a_merge_without_orig_head(self):
        # Default `git log -- <path>` simplification follows the merge's TREESAME
        # (upstream) parent and never reaches the fork's personalizing commit.
        self.assertIn("--full-history", self.block)
        self.assertIn("no legacy profile", self.block.lower())

    def test_other_files_are_read_from_the_pre_merge_tip(self):
        # 04 calibration, 05/06 ACTIVE-TEMPLATE and 07 STAR may be edited after the
        # last commit that touched 01; read them from the fork's side of the upgrade
        # merge. (--diff-filter=D finds upstream's deleting commit, whose parent is
        # pristine - verified in a scratch fork.)
        self.assertIn("git log --no-show-signature --merges", self.block)
        self.assertIn("^1", self.block)
        self.assertNotIn("--diff-filter=D", self.block)

    def test_git_log_output_is_not_polluted_by_signatures(self):
        # log.showSignature=true prints gpg lines into --format=%H output.
        for line in self.block.splitlines():
            if "git log" in line:
                self.assertIn("--no-show-signature", line, line)

    def test_migration_confirms_and_never_deletes(self):
        low = self.block.lower()
        self.assertIn("confirm", low)
        self.assertIn("deletes nothing", low)
        self.assertIn("git checkout --theirs", self.block)


if __name__ == "__main__":
    unittest.main()
