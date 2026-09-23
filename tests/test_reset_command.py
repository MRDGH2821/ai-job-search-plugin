"""Guards for /reset's two scopes: documents and profile.

Both scopes have the same failure mode - /reset promises a clean slate it
does not deliver, because something that writes personal data is missing
from the Step 1 preview the user confirms and from the Step 3 execution.

Documents scope: /reset ends its documents pass by telling the user "The
`documents/` folder is now empty." That statement is only true if every
personal-data drop folder is actually covered by both the Step 1 preview
and the Step 3 delete block. `documents/postings/` was missing from both
while being documented in documents/README.md and protected as personal
data by tools/security_guards.py (review finding F26, 2026-08-19), so a
reset silently kept the user's hand-pasted job postings.

Profile scope: the same class of gap, one scope over. /setup Step 3
populates six skill files, and /reset profile cleared four of them -
`04-job-evaluation.md` (the user's match areas, career goals, financial
situation and schedule constraints) was listed by name as containing
"framework rules, not candidate data", and `job-scraper/search-queries.md`
(their role titles, city and commute tiers) appeared nowhere in reset.md.
Both are tracked and unignored, and CI's placeholder-integrity job guards
04-job-evaluation.md under "personal data may have been committed", so a
"blank" profile left /rank scoring against the old skills and /scrape
running the old city.

Both file lists are derived - the documents folders from the repository
tree, the profile files from /setup Step 3's own headings - so a new drop
folder or a new /setup target fails this test until /reset covers it.
"""
import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESET = REPO / ".claude" / "commands" / "reset.md"
SETUP = REPO / ".claude" / "commands" / "setup.md"


def tracked_document_subfolders():
    """Names of documents/ subfolders tracked in git (ignores local noise)."""
    out = subprocess.run(
        ["git", "ls-files", "documents/"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    folders = set()
    for line in out.splitlines():
        parts = line.split("/")
        if len(parts) >= 3:  # documents/<subfolder>/<file...>
            folders.add(parts[1])
    return folders


class TestResetCoversEveryDocumentsSubfolder(unittest.TestCase):
    def setUp(self):
        self.text = RESET.read_text(encoding="utf-8")
        self.folders = tracked_document_subfolders()
        # The tree must actually contain the folders this test is about,
        # or the assertions below would pass vacuously.
        self.assertGreaterEqual(len(self.folders), 5, self.folders)

    def test_preview_lists_every_subfolder(self):
        missing = [
            f for f in sorted(self.folders) if f"documents/{f}/" not in self.text
        ]
        self.assertEqual(
            missing,
            [],
            "reset.md's preview never mentions these documents/ subfolders, "
            f"so the user confirms a deletion list that omits them: {missing}",
        )

    def test_delete_block_removes_every_subfolder(self):
        deleted = set(re.findall(r"rm -r?f documents/(\w+)/", self.text))
        missing = sorted(self.folders - deleted)
        self.assertEqual(
            missing,
            [],
            "reset.md's delete block has no rm line for these documents/ "
            'subfolders, yet the command then claims "The `documents/` '
            f'folder is now empty.": {missing}',
        )


def section(text: str, start: str, end: str) -> str:
    """The slice of text from the start marker up to the end marker."""
    begin = text.index(start)
    return text[begin : text.index(end, begin)]


TPL = REPO / ".claude" / "skills" / "job-application-assistant" / "profile-templates"


def setup_step3_profile_files():
    """profile/ files /setup Step 3 populates, derived from its own headings."""
    step3 = section(SETUP.read_text(encoding="utf-8"), "## Step 3:", "## Step 4:")
    targets = re.findall(r"^###\s+\d+\.\s+\w+\s+`([^`]+)`", step3, re.MULTILINE)
    return {t.split("/", 1)[1] for t in targets if t.startswith("profile/")}


class TestResetRestoresProfileFromTemplates(unittest.TestCase):
    def setUp(self):
        self.text = RESET.read_text(encoding="utf-8")
        self.files = setup_step3_profile_files()
        self.assertGreaterEqual(len(self.files), 7, self.files)

    def test_preview_lists_every_profile_file(self):
        preview = section(self.text, "### If scope includes `profile`:", "### If scope includes `documents`:")
        missing = sorted(f for f in self.files if f"profile/{f}" not in preview)
        self.assertEqual(missing, [], f"reset preview omits profile files /setup writes: {missing}")

    def test_execution_copies_templates(self):
        execution = section(self.text, "### Profile reset", "### Documents reset")
        self.assertIn("profile-templates/", execution)
        self.assertNotIn("| Line to restore | Token |", execution, "token-restore tables must be gone")

    def test_reset_preserves_active_template(self):
        execution = section(self.text, "### Profile reset", "### Documents reset")
        self.assertIn("Active Template", execution)
        self.assertIn("keep", execution.lower())

    def test_every_template_is_a_setup_target(self):
        templates = {p.name for p in TPL.glob("*.md")}
        self.assertEqual(sorted(templates - self.files), [], "a template /setup never fills")


if __name__ == "__main__":
    unittest.main()
