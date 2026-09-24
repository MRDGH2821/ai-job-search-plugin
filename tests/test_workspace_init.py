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


import sys  # noqa: E402
import tempfile  # noqa: E402

SCRIPT = paths.JOB_TOOLS / "init_workspace.py"
HEADER = "# Added by /init-workspace: personal data must never be committed"


def run(root, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True,
                          encoding="utf-8")


def template_targets():
    out = []
    for p in WT.rglob("*"):
        if p.is_file():
            rel = p.relative_to(WT)
            out.append(Path(".gitignore") if rel.name == "gitignore.template" else rel)
    return sorted(out)


class TestInitScript(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def snapshot(self):
        return {str(p.relative_to(self.root)): (p.read_bytes() if p.is_file() else None)
                for p in self.root.rglob("*")}

    def test_empty_folder_gets_the_whole_tree(self):
        proc = run(self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for rel in template_targets():
            self.assertTrue((self.root / rel).is_file(), rel)
        font = next((WT / "cover_letters" / "OpenFonts").rglob("*.ttf"))
        self.assertEqual((self.root / font.relative_to(WT)).read_bytes(), font.read_bytes())
        self.assertIn("created: cv/main_example.tex", proc.stdout)
        self.assertNotIn("profile", proc.stdout)
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_second_run_is_unchanged(self):
        run(self.root)
        before = self.snapshot()
        proc = run(self.root)
        self.assertNotIn("created:", proc.stdout)
        self.assertIn(f"kept: {len(template_targets())} existing files", proc.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_existing_files_are_never_overwritten(self):
        (self.root / "cv").mkdir()
        (self.root / "cv" / "main_example.tex").write_text("mine", encoding="utf-8")
        run(self.root)
        self.assertEqual((self.root / "cv" / "main_example.tex").read_text(encoding="utf-8"), "mine")

    def test_existing_gitignore_gains_only_missing_rules(self):
        (self.root / ".gitignore").write_text("my-secret-dir/\nsalary_data.json\n", encoding="utf-8")
        proc = run(self.root)
        text = (self.root / ".gitignore").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("my-secret-dir/\nsalary_data.json\n"))
        self.assertEqual(text.count("salary_data.json"), 1)
        self.assertIn(HEADER, text)
        self.assertIn("job_search_tracker.csv", text)
        self.assertRegex(proc.stdout, r"updated: \.gitignore \(\+\d+ rules\)")
        before = text
        run(self.root)
        self.assertEqual((self.root / ".gitignore").read_text(encoding="utf-8"), before)

    def test_gitignore_append_respects_newlines(self):
        (self.root / ".gitignore").write_bytes(b"a/\r\nb/")
        run(self.root)
        data = (self.root / ".gitignore").read_bytes()
        self.assertTrue(data.startswith(b"a/\r\nb/\r\n"))
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))

    def test_clone_root_gitignore_needs_no_additions(self):
        (self.root / ".gitignore").write_bytes((paths.REPO / ".gitignore").read_bytes())
        proc = run(self.root)
        self.assertNotIn("updated: .gitignore", proc.stdout)

    def test_blocked_target_writes_nothing(self):
        for make in (lambda r: (r / "cv").write_text("a file", encoding="utf-8"),
                     lambda r: (r / "cv" / "main_example.tex").mkdir(parents=True)):
            with tempfile.TemporaryDirectory() as t:
                r = Path(t)
                make(r)
                before = {str(p.relative_to(r)) for p in r.rglob("*")}
                proc = run(r)
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn("cv", proc.stderr)
                self.assertEqual({str(p.relative_to(r)) for p in r.rglob("*")}, before)

    def test_unreadable_gitignore_writes_nothing(self):
        (self.root / ".gitignore").write_bytes(b"\xff\xfe\x81")
        proc = run(self.root)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual({p.name for p in self.root.iterdir()}, {".gitignore"})

    def test_root_flag(self):
        other = self.root / "ws"
        other.mkdir()
        self.assertEqual(run(self.root, "--root", str(other)).returncode, 0)
        self.assertTrue((other / "cv" / "main_example.tex").exists())
        self.assertFalse((self.root / "cv").exists())


import re  # noqa: E402

INIT_ENTRY = "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py:*)"
SYNC_ENTRY = "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py:*)"


def frontmatter(path):
    m = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.DOTALL)
    return m.group(1) if m else ""


class TestWiring(unittest.TestCase):
    def test_skill(self):
        skill = paths.skill_file("init-workspace")
        fm = frontmatter(skill)
        self.assertIn("name: init-workspace", fm)
        self.assertIn("disable-model-invocation: true", fm)
        for entry in (INIT_ENTRY, SYNC_ENTRY, "Bash(git init)"):
            self.assertIn(entry, fm)
        body = skill.read_text(encoding="utf-8").split("\n---\n", 1)[1]
        self.assertTrue(body.lstrip().startswith("# /init-workspace "))
        self.assertIn("without asking for confirmation", body)
        self.assertIn("no `cd`, no `&&`", body)
        self.assertIn("private repository", body)
        self.assertIn("/setup", body)

    def test_setup_runs_init_first(self):
        setup = paths.command_file("setup")
        self.assertIn(INIT_ENTRY, frontmatter(setup))
        step0a = setup.read_text(encoding="utf-8").split("### Step 0a:", 1)[1].split("#### Legacy fork migration", 1)[0]
        self.assertIn("init_workspace.py", step0a)
        self.assertLess(step0a.index("init_workspace.py"), step0a.index("Create `profile/`"))

    def test_guard_and_docs(self):
        guards = (paths.REPO / "tools" / "security_guards.py").read_text(encoding="utf-8")
        self.assertIn(INIT_ENTRY, guards)
        self.assertIn('"Bash(git init)"', guards)
        readme = (paths.REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("/init-workspace", readme)
        self.assertNotIn("arrives in a later release", readme)
        self.assertIn("/init-workspace", (paths.REPO / "SETUP.md").read_text(encoding="utf-8"))
        changelog = (paths.REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("/init-workspace", changelog.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0])
