---
name: init-workspace
description: "Lay out a job-search workspace in the current folder (CV and cover-letter sources, fonts, documents tree, privacy .gitignore). Use when the user runs /init-workspace."
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py:*), Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py:*), Bash(git init)
---
# /init-workspace - Lay Out a Job-Search Workspace

`${CLAUDE_SKILL_DIR}` is this skill's folder. If your tool does not expand it, read paths as relative to the folder containing this SKILL.md.

The user typing `/init-workspace` is the request. Run each command below now, without asking for confirmation, from the current directory, exactly as written and as one command: no `cd`, no `&&`. Any other form does not match this skill's permissions.

1. Lay out the workspace (copies only what is missing, never overwrites):

   ```bash
   python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/init_workspace.py
   ```

   Report its `created:`/`updated:`/`kept:` lines in short. If it exits 2, show its message and stop.

2. Write the workspace instructions (`AGENTS.md` block, `CLAUDE.md` import):

   ```bash
   python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py
   ```

   Report its lines. If it exits 2, show its message and stop.

3. If this folder is not inside a git repository (no `.git` here or in any parent folder), ask once with AskUserQuestion: "Make this folder a git repository? This folder will hold your personal data. If you push it anywhere, use a private repository." Options: "Yes, run git init" / "No". On yes, run `git init`.

4. Tell the user the next step: run `/setup` to fill in `profile/` with their details.
