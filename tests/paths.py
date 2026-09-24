"""Where framework files live. Tests import paths from here and nowhere else,
so moving the framework means editing this one file."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugins" / "ai-job-search-plugin"
MARKET = REPO / "plugins" / "danish-job-portals"
SKILLS = PLUGIN / "skills"
FW = SKILLS / "job-application-assistant"
TPL = FW / "profile-templates"
JOB_TOOLS = SKILLS / "job-tools" / "scripts"
WT = SKILLS / "job-tools" / "workspace-template"
SETTINGS = REPO / ".claude" / "settings.json"
SALARY_LOOKUP = JOB_TOOLS / "salary_lookup.py"


def command_file(name: str) -> Path:
    return SKILLS / name / "SKILL.md"


def skill_file(name: str) -> Path:
    return SKILLS / name / "SKILL.md"


def portal_dirs() -> list[Path]:
    found = list(SKILLS.glob("*-search")) + list((MARKET / "skills").glob("*-search"))
    return sorted((p for p in found if (p / "SKILL.md").is_file()), key=lambda p: p.name)


def all_skill_files() -> list[Path]:
    return sorted(REPO.glob("plugins/*/skills/*/SKILL.md"))


def framework_markdown() -> list[Path]:
    return sorted(p for p in REPO.glob("plugins/*/skills/**/*.md") if "node_modules" not in p.parts)


def add_job_tools_to_sys_path() -> None:
    if str(JOB_TOOLS) not in sys.path:
        sys.path.insert(0, str(JOB_TOOLS))
