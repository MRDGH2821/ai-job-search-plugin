import sys
import unittest

from tests import paths

sys.path.insert(0, str(paths.REPO / "tools"))
from upstream_paths import map_upstream_path  # noqa: E402

P = "plugins/ai-job-search-plugin/skills"


class TestMap(unittest.TestCase):
    def test_rows(self):
        cases = {
            ".claude/commands/apply.md": [f"{P}/apply/SKILL.md"],
            ".claude/skills/job-scraper/SKILL.md": [f"{P}/job-scraper/SKILL.md"],
            ".claude/skills/job-application-assistant/01-candidate-profile.md":
                [f"{P}/job-application-assistant/profile-templates/candidate.md"],
            ".claude/skills/job-application-assistant/02-behavioral-profile.md":
                [f"{P}/job-application-assistant/profile-templates/behavioral.md"],
            ".claude/agents/gemini-research-expert.md": ["plugins/ai-job-search-plugin/agents/gemini-research-expert.md"],
            ".agents/skills/jobnet-search/cli/src/cli.ts": ["plugins/danish-job-portals/skills/jobnet-search/cli/src/cli.ts"],
            ".agents/skills/linkedin-search/SKILL.md": [f"{P}/linkedin-search/SKILL.md"],
            "tools/rank_state.py": [f"{P}/job-tools/scripts/rank_state.py"],
            "salary_lookup.py": [f"{P}/job-tools/scripts/salary_lookup.py"],
            "tools/README_SALARY_TOOL.md": [f"{P}/job-tools/scripts/README_SALARY_TOOL.md"],
            "cv/main_example.tex": [f"{P}/job-tools/workspace-template/cv/main_example.tex"],
            "documents/README.md": [f"{P}/job-tools/workspace-template/documents/README.md"],
            ".gitignore": [f"{P}/job-tools/workspace-template/gitignore.template", ".gitignore"],
            ".claude/skills/job-scraper/search-queries.md":
                [f"{P}/job-application-assistant/profile-templates/search-queries.md"],
            "tools/lint_skills.py": ["tools/lint_skills.py"],
            "README.md": ["README.md"],
        }
        for upstream, ours in cases.items():
            self.assertEqual(map_upstream_path(upstream), ours, upstream)
