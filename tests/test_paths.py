"""tests/paths.py is the single place tests learn where framework files live."""
import unittest

from tests import paths


class TestPaths(unittest.TestCase):
    def test_constants_exist(self):
        for p in (paths.REPO, paths.FW, paths.TPL, paths.JOB_TOOLS, paths.SETTINGS):
            self.assertTrue(p.exists(), p)

    def test_every_command_resolves(self):
        for name in ("add-portal", "add-template", "apply", "expand", "gmail-sync", "html-report",
                     "interview", "notion-sync", "outcome", "rank", "reset", "setup"):
            self.assertTrue(paths.command_file(name).is_file(), name)

    def test_skills_and_portals_resolve(self):
        for name in ("job-application-assistant", "job-scraper", "upskill"):
            self.assertTrue(paths.skill_file(name).is_file(), name)
        names = sorted(p.name for p in paths.portal_dirs())
        self.assertEqual(names, ["freehire-search", "jobbank-search", "jobdanmark-search",
                                 "jobindex-search", "jobnet-search", "linkedin-search"])

    def test_job_tools_hold_every_runtime_script(self):
        for script in ("rank_state.py", "job_key.py", "verify_pdf.py", "verify_layout.py",
                       "robots_check.py", "convert_salary_excel.py"):
            self.assertTrue((paths.JOB_TOOLS / script).is_file(), script)
        self.assertTrue(paths.SALARY_LOOKUP.is_file())  # Task 2 moves it into JOB_TOOLS

    def test_framework_markdown_covers_commands_and_skills(self):
        md = paths.framework_markdown()
        self.assertIn(paths.command_file("apply"), md)
        self.assertIn(paths.FW / "04-job-evaluation.md", md)
