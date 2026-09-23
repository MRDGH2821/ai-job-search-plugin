"""Guards for the profile/ separation (spec: docs/superpowers/specs/
2026-09-24-plugin-profile-separation-design.md, branch 1).

Candidate data lives in a workspace profile/ folder created from the
framework-owned templates in profile-templates/. Framework files hold rules
only and point at profile data with `profile/<file>.md#<anchor>` links.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FW = REPO / ".claude" / "skills" / "job-application-assistant"
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


def frontmatter_version(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None
    v = re.search(r"^framework_version:\s*(\S+)", m.group(1), re.MULTILINE)
    return v.group(1) if v else None


class TestTemplates(unittest.TestCase):
    def test_every_template_exists_with_framework_version(self):
        for name in TEMPLATES:
            path = TPL / name
            self.assertTrue(path.is_file(), f"missing template {path}")
            self.assertIsNotNone(frontmatter_version(path), f"{name}: no framework_version")

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


if __name__ == "__main__":
    unittest.main()
