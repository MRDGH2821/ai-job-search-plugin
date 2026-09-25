---
name: sync-instructions
description: "Write the framework's standing instructions into this workspace's AGENTS.md and make CLAUDE.md import it. Use when the user runs /sync-instructions."
argument-hint: "[--check]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py:*)
---
# /sync-instructions - Sync Workspace Instructions

`${CLAUDE_SKILL_DIR}` is this skill's folder. If your tool does not expand it, read paths as relative to the folder containing this SKILL.md.

The user typing `/sync-instructions` is the request. Run it now, without asking for confirmation, from the current directory (the workspace root), exactly as written and as one command: no `cd`, no `&&`. Any other form does not match this skill's permission and may write to the wrong folder.

```bash
python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py $ARGUMENTS
```

It keeps one managed block between `<!-- ai-job-search-plugin:start … -->` and `<!-- ai-job-search-plugin:end -->` in `AGENTS.md` and one `@AGENTS.md` line in `CLAUDE.md`. Everything else in both files is left alone.

Report the script's output lines to the user. Then:
- Exit 0: done. If `AGENTS.md` or `CLAUDE.md` says `created` or `updated`, tell the user the new instructions apply from their next Claude Code session.
- Exit 1 (only with `--check`): list the problems it printed and offer to run `/sync-instructions` without `--check`.
- Exit 2: it refused to write anything: broken markers in `AGENTS.md` (usually a hand edit), an unreadable file or broken symlink. Show its message (it names the file and, for markers, the line numbers) and ask the user to fix that; do not edit `AGENTS.md` or `CLAUDE.md` yourself.
