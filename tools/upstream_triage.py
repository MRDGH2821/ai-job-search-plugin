#!/usr/bin/env python3
"""Triage upstream commits this fork has not picked up yet.

Emits a Markdown report that sorts the behind-list into "worth reviewing" vs
"probably skip", so a human decides what to merge/port. It never merges,
pushes, or edits anything - it only reads git history and prints. This is the
deliberate report/act boundary: this project moved the original's files into
plugins (see upstream_paths.py), so upstream commits rarely apply as-is. The
report stops at `git show` lines to read each change; a human ports it by hand
to the mapped files and records the SHA in .github/upstream-handled.txt.

Two signals drive the sort:

1. Already applied? A cherry-pick lands with a NEW sha but the same patch, so a
   raw sha comparison misreports it as missing. We compute git patch-ids for the
   fork-only commits and treat any upstream commit whose patch-id (or exact
   subject) matches as already applied.

2. Relevant to this fork? Each touched upstream path is mapped to where the
   same file lives here (upstream_paths.map_upstream_path). A commit whose
   mapped paths all no longer exist here is almost certainly N/A.

3. Handled? Ported or rejected SHAs listed in .github/upstream-handled.txt are
   skipped: after the path move, patch-ids of ported commits no longer match.

Usage: python tools/upstream_triage.py [--remote upstream] [--branch master]
Exits 0 always (a report, not a gate). Prints a note to stderr and exits 0 if
the upstream ref is unavailable, so a scheduled job degrades gracefully.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from upstream_paths import map_upstream_path  # noqa: E402


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def rev_list(range_spec: str) -> list[str]:
    out = git("rev-list", "--no-merges", range_spec).strip()
    return out.splitlines() if out else []


def patch_id(sha: str) -> str | None:
    """Stable patch-id for a commit, or None if it has no diff."""
    show = subprocess.run(
        ["git", "show", sha], capture_output=True, text=True, check=True
    ).stdout
    r = subprocess.run(
        ["git", "patch-id", "--stable"], input=show, capture_output=True, text=True
    )
    line = r.stdout.strip()
    return line.split()[0] if line else None


def subject(sha: str) -> str:
    return git("show", "-s", "--format=%s", sha).strip()


def files_touched(sha: str) -> list[str]:
    out = git("show", "--name-only", "--format=", sha).strip()
    return [f for f in out.splitlines() if f]


def path_exists(path: str) -> bool:
    # ls-tree against HEAD is authoritative for "does this fork still ship it".
    r = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{path}"], capture_output=True
    )
    return r.returncode == 0


def remote_slug(remote: str) -> str | None:
    """owner/repo for a GitHub remote, or None if it can't be parsed."""
    try:
        url = git("remote", "get-url", remote).strip()
    except subprocess.CalledProcessError:
        return None
    for sep in ("github.com/", "github.com:"):
        if sep in url:
            path = url.split(sep, 1)[1]
            return path[:-4] if path.endswith(".git") else path
    return None


def load_handled(path: str) -> list[str]:
    """SHA prefixes already ported or rejected; missing file -> []."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return []
    entries = []
    for line in raw.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


def commit_cell(short: str, sha: str, slug: str | None) -> str:
    if slug:
        return f"[`{short}`](https://github.com/{slug}/commit/{sha})"
    return f"`{short}`"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote", default="upstream")
    ap.add_argument("--branch", default="master")
    ap.add_argument("--handled", default=".github/upstream-handled.txt")
    args = ap.parse_args()
    ref = f"{args.remote}/{args.branch}"
    slug = remote_slug(args.remote)
    handled = load_handled(args.handled)

    try:
        git("rev-parse", "--verify", ref)
    except subprocess.CalledProcessError:
        print(
            f"note: {ref} not available (add the remote and fetch it first); "
            "nothing to triage.",
            file=sys.stderr,
        )
        print(f"_Upstream ref `{ref}` was not available when this ran._")
        return 0

    behind = rev_list(f"HEAD..{ref}")
    if not behind:
        print(f"Up to date with `{ref}`. Nothing to review. :white_check_mark:")
        return 0

    fork_only = rev_list(f"{ref}..HEAD")
    fork_patch_ids = {p for p in (patch_id(s) for s in fork_only) if p}
    fork_subjects = {subject(s) for s in fork_only}

    review: list[tuple[str, str, str, list[tuple[str, str]]]] = []
    skip: list[tuple[str, str, str, str]] = []

    for sha in behind:
        subj = subject(sha)
        short = sha[:9]
        if patch_id(sha) in fork_patch_ids or subj in fork_subjects:
            skip.append((short, sha, subj, "already applied (cherry-picked)"))
            continue
        if any(sha.startswith(e) for e in handled):
            skip.append((short, sha, subj, "listed in upstream-handled.txt"))
            continue
        touched = files_touched(sha)
        # (upstream path, path here) for every touched file that still exists here.
        present = [(f, ours) for f in touched for ours in map_upstream_path(f) if path_exists(ours)]
        # A commit whose only surviving footprint is the changelog is one whose
        # real change lives in files this fork removed - the code doesn't apply,
        # only a doc line would. Low signal; demote it.
        substantive = [pair for pair in present if pair[1] != "CHANGELOG.md"]
        if touched and not present:
            skip.append((short, sha, subj, "touches only files not in this fork"))
        elif present and not substantive:
            skip.append((short, sha, subj, "changelog-only footprint in this fork"))
        else:
            review.append((short, sha, subj, substantive))

    lines: list[str] = []
    lines.append(f"Upstream `{ref}` has **{len(behind)}** commit(s) this fork lacks: "
                 f"**{len(review)}** worth reviewing, **{len(skip)}** probably skippable.")
    lines.append("")
    lines.append("_This is a triage report. Nothing was merged - review and port by hand._")
    lines.append("")

    lines.append("### Worth reviewing")
    if review:
        lines.append("")
        lines.append("| Commit | Subject | Files (upstream → here) |")
        lines.append("|---|---|---|")
        for short, sha, subj, pairs in review:
            shown = ", ".join(f"`{up}`" if up == ours else f"`{up}` → `{ours}`" for up, ours in pairs[:4])
            shown = shown or "_(new/shared paths)_"
            if len(pairs) > 4:
                shown += f" +{len(pairs) - 4} more"
            lines.append(f"| {commit_cell(short, sha, slug)} | {subj} | {shown} |")
        # Read-the-change lines - information, not action. Upstream paths differ
        # from ours, so a human ports each change to the mapped files.
        lines.append("")
        lines.append("<details><summary>Read each change, then port it by hand to the mapped files</summary>")
        lines.append("")
        lines.append("```bash")
        for short, sha, subj, pairs in review:
            ups = " ".join(dict.fromkeys(up for up, _ in pairs))
            lines.append(f"git show {sha} -- {ups}  # {subj}")
        lines.append("```")
        lines.append("")
        lines.append("Record each commit you port or reject in `.github/upstream-handled.txt`.")
        lines.append("")
        lines.append("</details>")
    else:
        lines.append("")
        lines.append("_None._")
    lines.append("")

    lines.append("### Probably skip")
    if skip:
        lines.append("")
        lines.append("| Commit | Subject | Why |")
        lines.append("|---|---|---|")
        for short, sha, subj, why in skip:
            lines.append(f"| {commit_cell(short, sha, slug)} | {subj} | {why} |")
    else:
        lines.append("")
        lines.append("_None._")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
