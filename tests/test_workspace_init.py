"""Workspace init (spec: docs/superpowers/specs/2026-09-24-workspace-init-design.md)."""
import os
import subprocess
import unittest
from pathlib import Path

from tests import paths

UPSTREAM = "MadsLorentzen/ai-job-search"
WT = paths.SKILLS / "job-tools" / "workspace-template"
REPO_ONLY_IGNORE = {"plugins/**/node_modules/",
                    "# Brainstorm mockups (superpowers visual companion) - never ship",
                    ".superpowers/"}
ALWAYS_SYNCED_DIRS = ("cover_letters/OpenFonts",)
ALWAYS_SYNCED_FILES = ("cover_letters/cover.cls", "templates/README.md", "documents/README.md")
UPSTREAM_SYNCED = ("cv/main_example.tex", "cover_letters/cover_example.tex")
GITKEEP_ROOTS = ("documents", "job_scraper", "company_research", "upskill")


def expected_gitignore_template(root_text: str) -> str:
    kept = [line for line in root_text.splitlines() if line.strip() not in REPO_ONLY_IGNORE]
    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept) + "\n"


def tracked(prefix):
    out = subprocess.run(["git", "ls-files", prefix], cwd=paths.REPO, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


class TestTemplateSync(unittest.TestCase):
    def test_always_synced_files_match(self):
        rels = list(ALWAYS_SYNCED_FILES)
        for d in ALWAYS_SYNCED_DIRS:
            rels += tracked(d)
        for root in GITKEEP_ROOTS:
            rels += [p for p in tracked(root) if p.endswith(".gitkeep")]
        self.assertGreater(len(rels), 25)
        for rel in rels:
            self.assertEqual((WT / rel).read_bytes(), (paths.REPO / rel).read_bytes(), rel)

    @unittest.skipIf(os.environ.get("GITHUB_REPOSITORY", UPSTREAM) != UPSTREAM,
                     "forks personalize these files")
    def test_upstream_examples_match(self):
        for rel in UPSTREAM_SYNCED:
            self.assertEqual((WT / rel).read_bytes(), (paths.REPO / rel).read_bytes(), rel)

    def test_template_has_nothing_the_root_lacks(self):
        extra = [str(p.relative_to(WT)) for p in WT.rglob("*")
                 if p.is_file() and p.name != "gitignore.template" and not (paths.REPO / p.relative_to(WT)).exists()]
        self.assertEqual(extra, [])

    def test_gitignore_template_is_the_root_minus_repo_only_lines(self):
        root = (paths.REPO / ".gitignore").read_text(encoding="utf-8")
        self.assertEqual((WT / "gitignore.template").read_text(encoding="utf-8"), expected_gitignore_template(root))

    def test_no_template_file_is_ignored(self):
        files = [str(p.relative_to(paths.REPO)) for p in WT.rglob("*") if p.is_file()]
        proc = subprocess.run(["git", "check-ignore", "--no-index", *files], cwd=paths.REPO, capture_output=True, text=True)
        self.assertEqual(proc.stdout.strip(), "", "template files ignored by the repo's .gitignore")
