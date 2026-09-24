#!/usr/bin/env python3
"""Keep this workspace's AGENTS.md block and CLAUDE.md import in sync.

Usage: python3 sync_instructions.py [--check] [--root DIR]

Writes the ai-job-search-plugin managed block (from agents-block.md next to this script)
between <!-- ai-job-search-plugin:start vX --> and <!-- ai-job-search-plugin:end --> in
AGENTS.md, and makes sure CLAUDE.md contains an `@AGENTS.md` line. Text outside
the markers, in either file, is never changed. --root defaults to the current
directory: the workspace root, never this script's folder.

Exit codes: 0 done / in sync, 1 --check found drift, 2 cannot proceed safely
(malformed markers, unreadable file, broken symlink); nothing is written.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "agents-block.md"
START_RE = re.compile(r"^<!-- ai-job-search-plugin:start(?: v\S+)? -->$")
END = "<!-- ai-job-search-plugin:end -->"
# Workspaces created before the rename carry these; a sync replaces them.
LEGACY_START_RE = re.compile(r"^<!-- ai-job-search:start(?: v\S+)? -->$")
LEGACY_END = "<!-- ai-job-search:end -->"
IMPORT = "@AGENTS.md"
BOM = b"\xef\xbb\xbf"


class SyncError(Exception):
    """A state the script refuses to guess about. Nothing has been written."""


MarkerError = SyncError


def load_template() -> tuple[str, str]:
    """(version, body) from agents-block.md."""
    text = TEMPLATE.read_text(encoding="utf-8")
    version, body = "0.0.0", text
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if m:
        v = re.search(r"^framework_version:\s*(\S+)", m.group(1), re.MULTILINE)
        if v:
            version = v.group(1)
        body = text[m.end():]
    return version, body.strip("\n")


def managed_block() -> list[str]:
    version, body = load_template()
    return [f"<!-- ai-job-search-plugin:start v{version} -->", *body.split("\n"), END]


def read(path: Path) -> tuple[str, bool, str]:
    """(text with \\n newlines, had BOM, the file's newline)."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SyncError(f"{path.name}: cannot read it ({exc.strerror}). Nothing was written.") from exc
    try:
        (raw[len(BOM):] if raw.startswith(BOM) else raw).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SyncError(f"{path.name}: not UTF-8 text. Convert it to UTF-8 first; nothing was written.") from exc
    bom = raw.startswith(BOM)
    text = (raw[len(BOM):] if bom else raw).decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.replace("\r\n", "\n"), bom, newline


def write(path: Path, text: str, bom: bool, newline: str) -> None:
    """Replace the file atomically; a symlink keeps pointing at its (updated) target."""
    target = path.resolve() if path.is_symlink() else path
    data = (BOM if bom else b"") + text.replace("\n", newline).encode("utf-8")
    tmp = target.with_name(target.name + ".sync-tmp")
    tmp.write_bytes(data)
    if target.exists():
        shutil.copymode(target, tmp)
    os.replace(tmp, target)


def locate(lines: list[str]) -> tuple[int, int] | None:
    def find(start_re, end):
        return ([i for i, line in enumerate(lines) if start_re.match(line.strip())],
                [i for i, line in enumerate(lines) if line.strip() == end])

    new_s, new_e = find(START_RE, END)
    old_s, old_e = find(LEGACY_START_RE, LEGACY_END)
    if (new_s or new_e) and (old_s or old_e):
        raise MarkerError("AGENTS.md: both old (ai-job-search) and new (ai-job-search-plugin) markers are present. "
                          "Keep one block; nothing was written.")
    starts, ends = (new_s, new_e) if (new_s or new_e) else (old_s, old_e)
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise MarkerError(
            "AGENTS.md: malformed ai-job-search-plugin markers "
            f"(start on line(s) {[s + 1 for s in starts]}, end on line(s) {[e + 1 for e in ends]}). "
            "Fix them by hand; nothing was written."
        )
    return starts[0], ends[0]


def desired_agents(current: str | None, block: list[str]) -> str:
    if current is None:
        return "\n".join(block) + "\n"
    lines = current.split("\n")
    span = locate(lines)
    if span is None:
        base = current.rstrip("\n")
        return (base + "\n\n" if base else "") + "\n".join(block) + "\n"
    start, end = span
    return "\n".join(lines[:start] + block + lines[end + 1:])


def has_import(text: str) -> bool:
    return any(line.strip() == IMPORT for line in text.split("\n"))


def claude_mode(root: Path) -> str:
    """How CLAUDE.md relates to AGENTS.md: "file", "missing", "symlink-to-agents",
    "same-file" (AGENTS.md is a link to it), or "symlink-elsewhere"."""
    agents, claude = root / "AGENTS.md", root / "CLAUDE.md"
    for path in (agents, claude):
        if path.is_symlink() and not path.exists():
            raise SyncError(f"{path.name}: broken symlink. Fix or remove it; nothing was written.")
        if path.is_dir():
            raise SyncError(f"{path.name}: is a directory. Nothing was written.")
    same = agents.exists() and claude.exists() and agents.resolve() == claude.resolve()
    if claude.is_symlink():
        return "symlink-to-agents" if same else "symlink-elsewhere"
    if same:
        return "same-file"
    return "file" if claude.exists() else "missing"


def plan(root: Path) -> dict:
    """What sync would write. Raises MarkerError before anything is written."""
    agents, claude = root / "AGENTS.md", root / "CLAUDE.md"
    block = managed_block()
    if agents.exists():
        text, bom, nl = read(agents)
        agents_plan = (desired_agents(text, block), text, bom, nl)
    else:
        agents_plan = (desired_agents(None, block), None, False, "\n")
    mode = claude_mode(root)
    if mode != "file" and mode != "missing":
        claude_plan = mode
    elif claude.exists():
        text, bom, nl = read(claude)
        new = text if has_import(text) else IMPORT + "\n\n" + text
        claude_plan = (new, text, bom, nl)
    else:
        claude_plan = (IMPORT + "\n", None, False, "\n")
    return {"agents": agents_plan, "claude": claude_plan}


def status(new: str, old: str | None) -> str:
    if old is None:
        return "created"
    return "unchanged" if new == old else "updated"


def sync(root: Path) -> list[str]:
    p = plan(root)
    out = []
    new, old, bom, nl = p["agents"]
    if new != old:
        write(root / "AGENTS.md", new, bom, nl)
    out.append(f"AGENTS.md: {status(new, old)}")
    notes = {
        "symlink-to-agents": "CLAUDE.md: unchanged (symlink to AGENTS.md)",
        "same-file": "CLAUDE.md: unchanged (same file as AGENTS.md)",
        "symlink-elsewhere": "CLAUDE.md: unchanged (symlink to a file outside this workspace; add @AGENTS.md there yourself if you want it)",
    }
    if isinstance(p["claude"], str):
        out.append(notes[p["claude"]])
    else:
        new, old, bom, nl = p["claude"]
        if new != old:
            write(root / "CLAUDE.md", new, bom, nl)
        out.append(f"CLAUDE.md: {status(new, old)}")
    return out


def check(root: Path) -> list[str]:
    problems = []
    agents = root / "AGENTS.md"
    if not agents.exists():
        return ["AGENTS.md: missing - run /sync-instructions"]
    p = plan(root)
    new, old, _, _ = p["agents"]
    if locate(old.split("\n")) is None:
        problems.append("AGENTS.md: no ai-job-search-plugin block - run /sync-instructions")
    elif new != old:
        problems.append("AGENTS.md: the ai-job-search-plugin block is out of date - run /sync-instructions")
    if not isinstance(p["claude"], str):
        new, old, _, _ = p["claude"]
        if new != old:
            problems.append("CLAUDE.md: missing the @AGENTS.md import - run /sync-instructions")
    return problems


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)  # absent on a StringIO under test
        if reconfigure:
            reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="report drift, write nothing")
    ap.add_argument("--root", default=".", help="workspace root (default: current directory)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.check:
            problems = check(root)
            for line in problems:
                print(line)
            return 1 if problems else 0
        for line in sync(root):
            print(line)
        return 0
    except SyncError as exc:
        print(exc, file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"cannot write: {exc}. Check the file permissions and run again.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
