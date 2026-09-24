"""Guards for the onboarding privacy warnings (issue #345 in the original project).

/setup writes personal data into files in the workspace, some tracked by git.
These tests pin that the warning lives at the point of decision (where the
user creates the workspace folder) and that /setup checks the origin's
visibility BEFORE writing anything, not in its closing notes.
"""
import re
import unittest
from pathlib import Path
from tests import paths

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
SETUP_GUIDE = REPO / "SETUP.md"
SETUP_COMMAND = paths.command_file("setup")


def section(text: str, heading: str) -> str:
    """Body of a markdown section up to the next heading of the same level."""
    level = heading.split(" ")[0]
    pattern = re.compile(
        rf"^{re.escape(heading)}\n(.*?)(?=^{level} |\Z)", re.MULTILINE | re.DOTALL
    )
    match = pattern.search(text)
    return match.group(1) if match else ""


class TestWorkspaceWarningsAtTheDecisionPoint(unittest.TestCase):
    def assert_warns(self, body: str, where: str):
        self.assertIn("personal data", body, f"{where} must say /setup writes personal data here")
        self.assertRegex(body, re.compile(r"\bprivate\b", re.IGNORECASE),
                         f"{where} must tell the user to keep the workspace private")

    def test_readme_first_run_warns_where_the_folder_is_created(self):
        body = section(README.read_text(encoding="utf-8"), "## First run")
        self.assertIn("/init-workspace", body, "sanity: the workspace is created in this section")
        self.assert_warns(body, "README")

    def test_setup_guide_warns_where_the_folder_is_created(self):
        body = section(SETUP_GUIDE.read_text(encoding="utf-8"), "## 3. Create your workspace")
        self.assertIn("/init-workspace", body, "sanity: the workspace is created in this section")
        self.assert_warns(body, "SETUP.md")


class TestSetupChecksOriginBeforeWriting(unittest.TestCase):
    def test_preflight_exists_and_precedes_profile_generation(self):
        text = SETUP_COMMAND.read_text(encoding="utf-8")
        self.assertIn(
            "git remote get-url origin",
            text,
            "/setup must check where the working copy would publish to",
        )
        preflight_at = text.index("git remote get-url origin")
        writes_at = text.index("## Step 3: Generate Profile Files")
        self.assertLess(
            preflight_at,
            writes_at,
            "the origin check must run before any profile file is written - the "
            "existing Step 4 note fires after everything is already on disk",
        )
        self.assertIn(
            "public",
            text[max(0, preflight_at - 2000) : preflight_at + 2000].lower(),
            "the preflight must be about public visibility, not just remote presence",
        )


if __name__ == "__main__":
    unittest.main()
