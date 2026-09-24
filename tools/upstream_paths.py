"""Map a path in the original project (MadsLorentzen/ai-job-search) to this repository.

Used by upstream_triage.py so upstream commits are judged, and ported, against
where the same files live here after the plugin conversion.
"""
from __future__ import annotations

CORE = "plugins/ai-job-search-plugin"
SKILLS = f"{CORE}/skills"
DANISH = {"jobbank-search", "jobdanmark-search", "jobindex-search", "jobnet-search"}
RUNTIME = {"rank_state.py", "job_key.py", "verify_pdf.py", "verify_layout.py",
           "robots_check.py", "convert_salary_excel.py", "README_SALARY_TOOL.md"}
WORKSPACE_DIRS = ("cv/", "cover_letters/", "templates/", "documents/", "job_scraper/",
                  "company_research/", "upskill/")
PROFILE_TEMPLATES = {"01-candidate-profile.md": "candidate.md", "02-behavioral-profile.md": "behavioral.md"}


def map_upstream_path(path: str) -> list[str]:
    parts = path.split("/")
    if path.startswith(".claude/commands/") and path.endswith(".md") and len(parts) == 3:
        return [f"{SKILLS}/{parts[2][:-3]}/SKILL.md"]
    if path.startswith(".claude/skills/job-application-assistant/") and parts[-1] in PROFILE_TEMPLATES:
        return [f"{SKILLS}/job-application-assistant/profile-templates/{PROFILE_TEMPLATES[parts[-1]]}"]
    if path.startswith(".claude/skills/"):
        return [f"{SKILLS}/" + "/".join(parts[2:])]
    if path.startswith(".claude/agents/"):
        return [f"{CORE}/agents/" + "/".join(parts[2:])]
    if path.startswith(".agents/skills/") and len(parts) > 2:
        home = "plugins/danish-job-portals/skills" if parts[2] in DANISH else SKILLS
        return [f"{home}/" + "/".join(parts[2:])]
    if (path.startswith("tools/") and parts[-1] in RUNTIME) or path == "salary_lookup.py":
        return [f"{SKILLS}/job-tools/scripts/{parts[-1]}"]
    if path.startswith(WORKSPACE_DIRS):
        return [f"{SKILLS}/job-tools/workspace-template/{path}"]
    if path == ".gitignore":
        return [f"{SKILLS}/job-tools/workspace-template/gitignore.template", ".gitignore"]
    return [path]
