---
name: sync-instructions
description: "Write the framework's standing instructions into this workspace's AGENTS.md and make CLAUDE.md import it. Use when the user runs /sync-instructions."
argument-hint: "[--check]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py:*)
---
# /sync-instructions - Sync Workspace Instructions

`${CLAUDE_SKILL_DIR}` is this skill's folder. If your tool does not expand it, read paths as relative to the folder containing this SKILL.md.

Run this from the workspace root (the folder you run Claude in), exactly as written:

```bash
python3 ${CLAUDE_SKILL_DIR}/../job-tools/scripts/sync_instructions.py $ARGUMENTS
```

It keeps one managed block between `<!-- ai-job-search:start … -->` and `<!-- ai-job-search:end -->` in `AGENTS.md` and one `@AGENTS.md` line in `CLAUDE.md`. Everything else in both files is left alone.

Report the script's output lines to the user. Then:
- Exit 0: done. If `AGENTS.md` or `CLAUDE.md` says `created` or `updated`, tell the user the new instructions apply from their next Claude Code session.
- Exit 1 (only with `--check`): list the problems it printed and offer to run `/sync-instructions` without `--check`.
- Exit 2: the markers in `AGENTS.md` are broken (usually a hand edit). Show the line numbers it printed and ask the user to fix or delete the broken marker lines; do not edit `AGENTS.md` yourself.
