#!/usr/bin/env python3
"""Supply-chain guards for the template's riskiest surfaces.

Run from anywhere: python tools/security_guards.py

This repo ships pre-approved Claude Code permissions and CLI code that every
fork user executes. These guards make the dangerous changes LOUD, not
impossible: a PR that intentionally needs one of them must update the
allowlists in this file in the same diff, so the change is explicit and
reviewable rather than buried.

Checks:
1. .claude/settings.json — every permissions.allow entry must be in the exact
   allowlist below. Catches permission widening (e.g. Bash(*), Bash(curl:*)),
   which would auto-approve commands on every fork. The same file's `hooks`
   key is held to an allowlist too: a hook runs automatically when its event
   fires, with no prompt, so it is strictly more dangerous than a pre-approved
   permission.
2. .gitignore — the personal-data ignore rules must all still be present,
   and no un-allowlisted negation (!pattern) may re-include them. Catches
   weakening that would make future users silently commit their tracker,
   profile exports, or application archives.
3. .agents/**/package.json — no npm/bun lifecycle scripts (preinstall,
   install, postinstall, prepare, prepack) and no trustedDependencies.
   Catches code execution smuggled into `bun install`.

Stdlib only. Exit 0 on success, 1 with a failure list otherwise.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []

# The exact permission entries the template ships in .claude/settings.json.
# A PR that adds or changes an entry must add it here too - that is the point:
# the diff shows both. Script and portal permissions moved into each plugin
# skill's allowed-tools in the plugin layout change; ALLOWED_SKILL_TOOLS below
# reviews those.
ALLOWED_PERMISSIONS = {
    "Skill(ai-job-search-plugin:job-application-assistant)",
    "Bash(pdftotext:*)",
}

# Bash entries a plugin skill may pre-approve in its allowed-tools. Permissions
# moved out of settings.json into the skills in the plugin layout change, so the
# review moved with them: a new entry needs a line here in the same PR.
ALLOWED_SKILL_TOOLS = {
    "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/rank_state.py:*)",
    "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/job_key.py:*)",
    "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/verify_pdf.py:*)",
    "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/verify_layout.py:*)",
    "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/salary_lookup.py:*)",
    "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py:*)",
    "Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py:*)",
    "Bash(git init)",
    "Bash(pdftotext:*)",
    "Bash(bun --version)",
    # The user's own portals from /add-portal (workspace .agents/skills/).
    "Bash(bun run .agents/skills/*/cli/src/cli.ts *)",
    # Shipped portals run their own CLI from their own folder.
    "Bash(bun run ${CLAUDE_SKILL_DIR}/cli/src/cli.ts *)",
    "Bash(bun install --cwd ${CLAUDE_SKILL_DIR}/cli)",
}

# Skills allowed a bare `Bash` (every command pre-approved). Reviewed: the core
# application skill has shipped it since before the plugin layout.
ALLOWED_BARE_BASH = {"job-application-assistant"}

# The clone's settings.json loads exactly these marketplaces and plugins. A PR
# that points the clone at another marketplace or plugin makes every fork load
# code nobody reviewed here, so it must change these values in the same PR.
ALLOWED_MARKETPLACES = {
    "ai-job-search-plugin": {"source": {"source": "directory", "path": "./"}},
}
ALLOWED_PLUGINS = {"ai-job-search-plugin@ai-job-search-plugin", "danish-job-portals@ai-job-search-plugin"}

# Plugin components that run code without a model decision or a prompt. The
# template ships none; like ALLOWED_HOOKS, adding one needs a guard change.
FORBIDDEN_PLUGIN_KEYS = {"hooks", "mcpServers", "lspServers"}
FORBIDDEN_PLUGIN_FILES = ("hooks", ".mcp.json", ".lsp.json")

# Personal-data ignore rules that must never disappear from .gitignore.
REQUIRED_IGNORE_RULES = [
    "salary_data.json",
    # Depth-independent: the job-scraper skill resolves `job_scraper/` relative
    # to its own directory, so the state file lands under .claude/skills/... and
    # a repo-rooted rule silently fails to match it.
    "**/job_scraper/seen_jobs.json",
    "**/job_scraper/notion_sync.json",
    "**/job_scraper/*.md",
    "*_BehavioralReport.pdf",
    "linkedin_Profile.pdf",
    "cv/main_*.*",
    "!cv/main_example.tex",
    # ATS text extractions (/apply step 5d) carry the CV's full text.
    "cv/*.txt",
    "cover_letters/cover_*.*",
    # /apply also recognizes the uppercase Cover_* naming variant.
    "cover_letters/Cover_*.*",
    "documents/cv/**",
    "documents/linkedin/**",
    "documents/diplomas/**",
    "documents/references/**",
    "documents/projects/**",
    "documents/applications/**",
    "documents/postings/**",
    # Belt-and-braces, not the primary guard: nothing writes here.
    # /interview's prep packs land under documents/applications/**, above.
    "documents/interview/**",
    "job_search_tracker.csv",
    "gmail_sync/",
    "reports/",
    "upskill/*.md",
    # Depth-independent twin of the rule above. The upskill *skill* resolves
    # `upskill/` relative to its own directory - the same observed behavior
    # the **/job_scraper rules exist for - so reports can land at
    # .claude/skills/upskill/upskill/*.md where the rooted rule cannot see
    # them. `**/upskill/*.md` would also ignore the skill's own SKILL.md
    # (the directory shares the name), so the report-file prefix is pinned.
    "**/upskill/report-*.md",
    # Not personal data but the same failure mode: /add-portal can generate a
    # skill for a portal that only returns usable content through a paid
    # fetching service, and that skill reads an API token from the environment.
    ".env",
    ".env.*",
    # Company research cache (/apply Step 3, /interview Step 2). Referenced
    # from commands, not a skill, so a plain rooted rule is correct here -
    # unlike the **/-prefixed job_scraper/upskill rules above.
    "company_research/*.json",
]

# Negation (re-include) rules the template legitimately ships. .gitignore is
# order-sensitive: a later `!pattern` re-includes a path an earlier rule
# excluded, so a rule can be physically present in REQUIRED_IGNORE_RULES yet
# no longer ignored (e.g. adding `!salary_data.json`). Set membership on the
# required rules cannot see that. Any negation outside this allowlist is a
# failure - add an intentional one here in the same PR, exactly as with
# ALLOWED_PERMISSIONS, so the widening is explicit and reviewable.
ALLOWED_IGNORE_NEGATIONS = {
    "!cover_letters/OpenFonts/fonts/**",
    "!cv/main_example.tex",
    "!cover_letters/cover_example.tex",
    "!documents/**/.gitkeep",
}

# Hook commands the template legitimately ships, as "<Event>:<command>" strings.
# Empty by design - the template ships no hooks at all.
#
# A hook is strictly more dangerous than a permissions.allow entry. A permission
# pre-approves something Claude may choose to do; a hook runs unconditionally when
# its event fires, with no prompt and no model decision in between. Cloning a repo
# and opening it is enough. This is the vector the Shai-Hulud worm used in its
# August 2026 wave, planting a SessionStart hook in .claude/settings.json that
# executed on session start:
# https://research.jfrog.com/post/shai-hulud-is-back-august/
ALLOWED_HOOKS: set[str] = set()

FORBIDDEN_SCRIPTS = {"preinstall", "install", "postinstall", "prepare", "prepack"}


def _hook_commands(event: str, entries: object):
    """Yield "<Event>:<command>" for every command a hook event would run.

    Fails closed: any shape this does not recognise yields a marker that cannot
    be in the allowlist, so an unfamiliar hook layout is rejected rather than
    silently skipped.
    """
    unrecognised = f"{event}:<unrecognised hook shape>"
    if not isinstance(entries, list):
        yield unrecognised
        return
    for entry in entries:
        if not isinstance(entry, dict):
            yield unrecognised
            continue
        inner = entry.get("hooks")
        if not isinstance(inner, list):
            yield unrecognised
            continue
        for hook in inner:
            command = hook.get("command") if isinstance(hook, dict) else None
            yield f"{event}:{command}" if isinstance(command, str) else unrecognised


def check_permissions() -> None:
    path = ROOT / ".claude" / "settings.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f".claude/settings.json: unreadable or invalid JSON: {exc}")
        return
    if not isinstance(data, dict):
        errors.append(".claude/settings.json: top-level JSON value must be an object")
        return

    # Checked before the permissions shape guards below, so a file that pairs a
    # malformed permissions block with a hook cannot return early and skip this.
    hooks = data.get("hooks", {})
    if hooks:
        if not isinstance(hooks, dict):
            errors.append(".claude/settings.json: hooks must be an object")
        else:
            for event, entries in hooks.items():
                for command in _hook_commands(str(event), entries):
                    if command not in ALLOWED_HOOKS:
                        errors.append(
                            f".claude/settings.json: hook not in the reviewed allowlist: "
                            f"{command!r}. A hook runs automatically when its event fires - it "
                            "is never gated by the permissions prompt, so it executes on every "
                            "fork without the user agreeing to anything. If this hook is "
                            "intentional, add it to ALLOWED_HOOKS in tools/security_guards.py "
                            "in the same PR so the addition is explicit and reviewable."
                        )

    marketplaces = data.get("extraKnownMarketplaces", {})
    if marketplaces != ALLOWED_MARKETPLACES and marketplaces:
        errors.append(
            ".claude/settings.json: extraKnownMarketplaces differs from the reviewed value "
            f"{ALLOWED_MARKETPLACES!r}. Update ALLOWED_MARKETPLACES in tools/security_guards.py "
            "in the same PR if this is intentional."
        )
    enabled = data.get("enabledPlugins", {})
    if not isinstance(enabled, dict) or set(enabled) - ALLOWED_PLUGINS:
        errors.append(
            ".claude/settings.json: enabledPlugins names a plugin outside the reviewed set "
            f"{sorted(ALLOWED_PLUGINS)}. Update ALLOWED_PLUGINS in tools/security_guards.py "
            "in the same PR if this is intentional."
        )

    permissions = data.get("permissions", {})
    if not isinstance(permissions, dict):
        errors.append(".claude/settings.json: permissions must be an object")
        return
    allow = permissions.get("allow", [])
    if not isinstance(allow, list) or not all(isinstance(entry, str) for entry in allow):
        errors.append(".claude/settings.json: permissions.allow must be a list of strings")
        return
    for entry in allow:
        if entry not in ALLOWED_PERMISSIONS:
            errors.append(
                f".claude/settings.json: permission not in the reviewed allowlist: {entry!r}. "
                "Pre-approved permissions run without prompting on every fork. If this entry is "
                "intentional, add it to ALLOWED_PERMISSIONS in tools/security_guards.py in the "
                "same PR so the widening is explicit and reviewable."
            )
    for entry in ALLOWED_PERMISSIONS - set(allow):
        # Not an error: settings may legitimately drop an entry. But an
        # allowlist entry that no longer exists should be pruned.
        print(f"note: allowlisted permission not present in settings.json: {entry!r}")


WORKSPACE_GITIGNORE = "plugins/ai-job-search-plugin/skills/job-tools/workspace-template/gitignore.template"


def check_gitignore() -> None:
    _check_gitignore_file(ROOT / ".gitignore", ".gitignore")
    template = ROOT / WORKSPACE_GITIGNORE
    if template.exists():
        # /init-workspace copies this into every new workspace: it must carry the same rules.
        _check_gitignore_file(template, WORKSPACE_GITIGNORE)


def _check_gitignore_file(path, label: str) -> None:
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    except OSError as exc:
        errors.append(f"{label}: unreadable: {exc}")
        return
    rules = set(lines)
    for rule in REQUIRED_IGNORE_RULES:
        if rule not in rules:
            errors.append(
                f"{label}: required personal-data rule missing: {rule!r}. "
                "These rules keep fork users from committing personal data. If the rule moved "
                "or was renamed intentionally, update REQUIRED_IGNORE_RULES in "
                "tools/security_guards.py in the same PR."
            )
    for line in lines:
        if line.startswith("!") and line not in ALLOWED_IGNORE_NEGATIONS:
            errors.append(
                f"{label}: negation rule not in the reviewed allowlist: {line!r}. "
                "A negation re-includes a path an earlier rule excluded and can silently "
                "re-expose personal data (a required ignore rule stays present but stops "
                "taking effect). If this negation is intentional, add it to "
                "ALLOWED_IGNORE_NEGATIONS in tools/security_guards.py in the same PR."
            )


def check_package_manifests() -> None:
    manifests = [
        p for p in list(ROOT.glob("plugins/**/package.json")) + list(ROOT.glob(".agents/**/package.json"))
        if "node_modules" not in p.parts
    ]
    if not manifests:
        errors.append("no package.json files found under plugins/ or .agents/ - glob roots are wrong or the tree moved")
    for manifest in manifests:
        relpath = manifest.relative_to(ROOT)
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{relpath}: unreadable or invalid JSON: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{relpath}: top-level JSON value must be an object")
            continue
        scripts = data.get("scripts", {})
        if not isinstance(scripts, dict):
            errors.append(f"{relpath}: scripts must be an object")
            continue
        bad = FORBIDDEN_SCRIPTS & set(scripts)
        if bad:
            errors.append(
                f"{relpath}: lifecycle script(s) {sorted(bad)} are forbidden - they execute "
                "arbitrary code during `bun install` on every fork user's machine."
            )
        if "trustedDependencies" in data:
            errors.append(
                f"{relpath}: trustedDependencies is forbidden - it re-enables dependency "
                "lifecycle scripts that bun blocks by default."
            )



def _allowed_tools_value(frontmatter: str) -> str:
    """The allowed-tools value, in inline or YAML-list form, as one string."""
    lines = frontmatter.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("allowed-tools:"):
            parts = [line.split(":", 1)[1]]
            for follow in lines[i + 1:]:
                if follow.startswith((" ", "\t", "-")):
                    parts.append(follow.strip().lstrip("-").strip())
                else:
                    break
            return ", ".join(p for p in parts if p.strip())
    return ""


def check_skill_tools() -> None:
    for skill in sorted(ROOT.glob("plugins/*/skills/*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        if not m:
            continue
        value = _allowed_tools_value(m.group(1))
        for entry in re.findall(r"Bash\([^)]*\)", value):
            if entry not in ALLOWED_SKILL_TOOLS:
                errors.append(
                    f"{skill.relative_to(ROOT)}: allowed-tools entry not in the reviewed allowlist: "
                    f"{entry!r}. Add it to ALLOWED_SKILL_TOOLS in tools/security_guards.py in the same PR."
                )
        if re.search(r"(^|[,\s])Bash\s*(,|$)", value) and skill.parent.name not in ALLOWED_BARE_BASH:
            errors.append(
                f"{skill.relative_to(ROOT)}: allowed-tools grants bare Bash (every command). "
                "Name the exact commands, or add the skill to ALLOWED_BARE_BASH in "
                "tools/security_guards.py in the same PR."
            )


def check_plugin_surface() -> None:
    for plugin in sorted(p for p in ROOT.glob("plugins/*") if p.is_dir()):
        for name in FORBIDDEN_PLUGIN_FILES:
            if (plugin / name).exists():
                errors.append(
                    f"{(plugin / name).relative_to(ROOT)}: plugins in this template ship no hooks, "
                    "MCP or LSP servers - they run code with no prompt. Extend the guard in the same PR "
                    "if this is intentional."
                )
        manifest = plugin / ".claude-plugin" / "plugin.json"
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{manifest.relative_to(ROOT)}: unreadable or invalid JSON: {exc}")
            continue
        for key in FORBIDDEN_PLUGIN_KEYS & set(data if isinstance(data, dict) else {}):
            errors.append(f"{manifest.relative_to(ROOT)}: '{key}' is not allowed in a template plugin manifest.")


def main() -> int:
    check_permissions()
    check_skill_tools()
    check_plugin_surface()
    check_gitignore()
    check_package_manifests()
    if errors:
        print(f"security_guards: {len(errors)} failure(s)")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(
        "security_guards: OK (permissions allowlist, skill allowed-tools, plugin surface, hooks "
        "allowlist, gitignore rules, package manifests)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
