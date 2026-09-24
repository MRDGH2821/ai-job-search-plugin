"""Where framework files live. Tests import paths from here and nowhere else,
so moving the framework means editing this one file."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FW = REPO / ".claude" / "skills" / "job-application-assistant"
TPL = FW / "profile-templates"
JOB_TOOLS = REPO / "tools"
SETTINGS = REPO / ".claude" / "settings.json"
_COMMANDS = REPO / ".claude" / "commands"
_SKILLS = REPO / ".claude" / "skills"
_PORTALS = REPO / ".agents" / "skills"
SALARY_LOOKUP = REPO / "salary_lookup.py"  # Task 2: moves under JOB_TOOLS


def command_file(name: str) -> Path:
    return _COMMANDS / f"{name}.md"


def skill_file(name: str) -> Path:
    return _SKILLS / name / "SKILL.md"


def portal_dirs() -> list[Path]:
    return sorted(p for p in _PORTALS.glob("*-search") if (p / "SKILL.md").is_file())


def framework_markdown() -> list[Path]:
    return sorted(_COMMANDS.glob("*.md")) + sorted(_SKILLS.rglob("*.md"))


def add_job_tools_to_sys_path() -> None:
    for folder in (JOB_TOOLS, SALARY_LOOKUP.parent):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
