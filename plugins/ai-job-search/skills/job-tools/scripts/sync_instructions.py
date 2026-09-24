#!/usr/bin/env python3
"""Keep this workspace's AGENTS.md block and CLAUDE.md import in sync.

Usage: python3 sync_instructions.py [--check] [--root DIR]

Writes the ai-job-search managed block (from agents-block.md next to this script)
between <!-- ai-job-search:start vX --> and <!-- ai-job-search:end --> in
AGENTS.md, and makes sure CLAUDE.md contains an `@AGENTS.md` line. Text outside
the markers, in either file, is never changed. --root defaults to the current
directory: the workspace root, never this script's folder.

Exit codes: 0 done / in sync, 1 --check found drift, 2 malformed markers
(nothing written).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "agents-block.md"
START_RE = re.compile(r"^<!-- ai-job-search:start(?: v\S+)? -->$")
END = "<!-- ai-job-search:end -->"
IMPORT = "@AGENTS.md"
BOM = b"\xef\xbb\xbf"


class MarkerError(Exception):
    pass


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
    return [f"<!-- ai-job-search:start v{version} -->", *body.split("\n"), END]


def read(path: Path) -> tuple[str, bool, str]:
    """(text with \\n newlines, had BOM, the file's newline)."""
    raw = path.read_bytes()
    bom = raw.startswith(BOM)
    text = (raw[len(BOM):] if bom else raw).decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.replace("\r\n", "\n"), bom, newline


def write(path: Path, text: str, bom: bool, newline: str) -> None:
    data = text.replace("\n", newline).encode("utf-8")
    path.write_bytes((BOM if bom else b"") + data)


def locate(lines: list[str]) -> tuple[int, int] | None:
    starts = [i for i, line in enumerate(lines) if START_RE.match(line.strip())]
    ends = [i for i, line in enumerate(lines) if line.strip() == END]
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise MarkerError(
            "AGENTS.md: malformed ai-job-search markers "
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


def claude_is_symlink_to_agents(root: Path) -> bool:
    claude = root / "CLAUDE.md"
    return claude.is_symlink() and claude.resolve() == (root / "AGENTS.md").resolve()


def plan(root: Path) -> dict:
    """What sync would write. Raises MarkerError before anything is written."""
    agents, claude = root / "AGENTS.md", root / "CLAUDE.md"
    block = managed_block()
    if agents.exists():
        text, bom, nl = read(agents)
        agents_plan = (desired_agents(text, block), text, bom, nl)
    else:
        agents_plan = (desired_agents(None, block), None, False, "\n")
    if claude_is_symlink_to_agents(root):
        claude_plan = "symlink"
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
    if p["claude"] == "symlink":
        out.append("CLAUDE.md: unchanged (symlink to AGENTS.md)")
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
        problems.append("AGENTS.md: no ai-job-search block - run /sync-instructions")
    elif new != old:
        problems.append("AGENTS.md: the ai-job-search block is out of date - run /sync-instructions")
    if p["claude"] != "symlink":
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
    except MarkerError as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
