#!/usr/bin/env python3
"""Lay out an ai-job-search workspace in the current folder.

Usage: python3 init_workspace.py [--root DIR]

Copies every file of the workspace template (next to this script) that the
workspace does not have yet - CV and cover-letter sources, fonts, the documents/
tree, state folders - and never overwrites anything. The template's
gitignore.template becomes .gitignore; an existing .gitignore only gains the
privacy rules it lacks. --root defaults to the current directory: the workspace
root, never this script's folder.

Exit codes: 0 done, 2 refused (something is in the way or unreadable; nothing
was written).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "workspace-template"
GITIGNORE_SOURCE = "gitignore.template"
HEADER = "# Added by /init-workspace: personal data must never be committed"


class InitError(Exception):
    """A state the script refuses to guess about. Nothing has been written."""


def template_files() -> list[Path]:
    return sorted(p.relative_to(TEMPLATE) for p in TEMPLATE.rglob("*") if p.is_file())


def target_of(rel: Path) -> Path:
    return Path(".gitignore") if rel.name == GITIGNORE_SOURCE and rel.parent == Path(".") else rel


def rule_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def check_path(root: Path, rel: Path) -> None:
    for parent in reversed(rel.parents[:-1]):
        p = root / parent
        if p.exists() and not p.is_dir():
            raise InitError(f"{parent.as_posix()}: a file is in the way of a folder the workspace needs. Nothing was written.")
    if (root / rel).is_dir():
        raise InitError(f"{rel.as_posix()}: a folder is in the way of a file the workspace needs. Nothing was written.")


def plan(root: Path) -> tuple[list[tuple[Path, Path]], tuple[str, list[str], bytes] | None, int]:
    """(files to copy [(source, target rel)], .gitignore append plan, kept count)."""
    copies: list[tuple[Path, Path]] = []
    gitignore_plan = None
    kept = 0
    for rel in template_files():
        target = target_of(rel)
        check_path(root, target)
        dest = root / target
        if target == Path(".gitignore") and dest.exists():
            raw = dest.read_bytes()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise InitError(".gitignore: not UTF-8 text. Convert it to UTF-8 first; nothing was written.") from exc
            have = {line.strip() for line in text.splitlines()}
            missing = [r for r in rule_lines((TEMPLATE / rel).read_text(encoding="utf-8")) if r not in have]
            kept += 1
            if missing:
                gitignore_plan = (text, missing, raw)
            continue
        if dest.exists():
            kept += 1
        else:
            copies.append((TEMPLATE / rel, target))
    return copies, gitignore_plan, kept


def run(root: Path) -> list[str]:
    copies, gitignore_plan, kept = plan(root)
    out = []
    for source, target in copies:
        dest = root / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        out.append(f"created: {target.as_posix()}")
    if gitignore_plan:
        text, missing, _ = gitignore_plan
        newline = "\r\n" if "\r\n" in text else "\n"
        body = text if text.endswith(("\n", "\r\n")) or not text else text + newline
        body += newline + newline.join([HEADER, *missing]) + newline
        (root / ".gitignore").write_bytes(body.encode("utf-8"))
        out.append(f"updated: .gitignore (+{len(missing)} rules)")
    out.append(f"kept: {kept} existing files")
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)  # absent on a StringIO under test
        if reconfigure:
            reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="workspace root (default: current directory)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        for line in run(root):
            print(line)
        return 0
    except InitError as exc:
        print(exc, file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"cannot write: {exc}. Check the folder's permissions and run again.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
