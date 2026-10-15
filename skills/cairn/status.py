"""Print what is in flight: last done, next, and what waits on you.

There is no STATE.md; this command derives the same facts on demand from
git and GitHub, and writes nothing. Zero third-party dependencies.

Run it from a project:
    python status.py [--cwd DIR]

Behavior:
  - Last done: the 5 newest non-merge commits (git log) and the 5 newest
    merged PRs (gh).
  - Next: the 5 oldest open issues that are not labelled needs-ruling. If
    `git config cairn.plan <path>` names a markdown file (path from the repo
    root), Next is that file's first unfinished step instead, and issues are
    never used. A step is a top-level numbered item (`1.` or `1)`); it is done
    when its text starts with `~~` or `[x]`.
  - Waiting on you: up to 10 open issues labelled needs-ruling.
  - Every section always prints, `(none)` when empty. A section that cannot
    be read (gh missing, gh not signed in, no plan file) says why.
  - Exit 0 whenever output printed. Exit 1 only when --cwd is not a
    directory or not a git repo.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


COMMIT_LIMIT = 5
PR_LIMIT = 5
ISSUE_LIMIT = 5
WAITING_LIMIT = 10
FETCH_LIMIT = "1000"
RULING_LABEL = "needs-ruling"
PLAN_SETTING = "cairn.plan"

STEP = re.compile(r"(\d+)[.)]\s+(.*)")
LIST_ITEM = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")
DONE_CHECK = re.compile(r"\[[xX]\]")
FENCE = re.compile(r"\s*(```|~~~)")


class GhUnavailable(Exception):
    """gh could not answer; the message is the reason shown to the reader."""


# ------------------------------------------------------------------ git

def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess | None:
    """Run git; None when git itself cannot start."""
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True,
            encoding="utf-8", errors="replace",
        )
    except OSError:
        return None


def _repo_root(cwd: Path) -> Path | None:
    result = _git(["rev-parse", "--show-toplevel"], cwd)
    if result is None or result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip())


def _recent_commits(root: Path) -> list[str] | None:
    """`<sha> <subject>` lines, newest first; None when there are no commits."""
    head = _git(["rev-parse", "--verify", "--quiet", "HEAD"], root)
    if head is None or head.returncode != 0:
        return None
    log = _git(
        ["log", "--no-merges", "-n", str(COMMIT_LIMIT), "--format=%h %s"], root,
    )
    if log is None or log.returncode != 0:
        return None
    return [line for line in log.stdout.splitlines() if line.strip()]


def _plan_setting(root: Path) -> str | None:
    result = _git(["config", "--get", PLAN_SETTING], root)
    if result is None or result.returncode != 0:
        return None
    return result.stdout.strip() or None


# ------------------------------------------------------------------ gh

def _gh(args: list[str], cwd: Path):
    """Run gh and return its parsed JSON, or raise GhUnavailable(reason)."""
    try:
        result = subprocess.run(
            ["gh", *args], cwd=cwd, capture_output=True,
            encoding="utf-8", errors="replace",
        )
    except OSError:
        raise GhUnavailable("gh is not installed")
    if result.returncode != 0:
        lines = [line.strip() for line in result.stderr.splitlines() if line.strip()]
        raise GhUnavailable(lines[0] if lines else f"gh exited {result.returncode}")
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise GhUnavailable("gh returned output that is not JSON")


def _titled(item) -> str:
    return f"#{item['number']} {' '.join(str(item['title']).split())}"


def _merged_prs(root: Path) -> list[str]:
    data = _gh(["pr", "list", "--state", "merged", "--limit", str(PR_LIMIT * 4),
                "--json", "number,title,mergedAt"], root)
    try:
        data = sorted(data, key=lambda i: str(i.get("mergedAt") or ""), reverse=True)
        return [_titled(item) for item in data[:PR_LIMIT]]
    except (KeyError, TypeError, AttributeError):
        raise GhUnavailable("gh returned an unexpected shape")


def _open_issues(root: Path) -> tuple[list[dict], list[dict]]:
    """(plain issues, needs-ruling issues), each oldest first."""
    data = _gh(["issue", "list", "--state", "open", "--limit", FETCH_LIMIT,
                "--json", "number,title,labels,createdAt"], root)
    try:
        data = sorted(data, key=lambda i: (str(i.get("createdAt") or ""), i["number"]))
        plain, waiting = [], []
        for item in data:
            labels = {(l.get("name") if isinstance(l, dict) else l)
                      for l in item.get("labels") or []}
            (waiting if RULING_LABEL in labels else plain).append(item)
        return plain, waiting
    except (KeyError, TypeError, AttributeError):
        raise GhUnavailable("gh returned an unexpected shape")


# ------------------------------------------------------------------ plan file

def _steps(text: str) -> list[tuple[str, bool]]:
    """(text, done) for each top-level numbered step, in file order."""
    lines = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    steps: list[list] = []
    fence = None
    current = None
    for line in lines:
        fenced = FENCE.match(line)
        if fence is not None:
            if fenced and fenced.group(1) == fence:
                fence = None
            continue
        if fenced:
            fence = fenced.group(1)
            current = None
            continue
        step = STEP.match(line)
        if step:
            current = [step.group(2).strip()]
            steps.append(current)
        elif not line.strip() or line.lstrip().startswith("#") or LIST_ITEM.match(line):
            current = None
        elif current is not None:
            current.append(line.strip())
    out = []
    for parts in steps:
        joined = " ".join(part for part in parts if part)
        out.append((joined, joined.startswith("~~") or bool(DONE_CHECK.match(joined))))
    return out


def next_step(text: str) -> str | None:
    """The first unfinished step's text, or None when there is none."""
    for step, done in _steps(text):
        if not done:
            return step
    return None


def _next_from_plan(root: Path, setting: str) -> list[str]:
    path = root / setting
    if not path.is_file():
        return [f"(plan file {setting} not found)"]
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return [f"(plan file {setting} could not be read)"]
    step = next_step(text)
    if step is not None:
        return [step]
    if _steps(text):
        return [f"(every step in {setting} is done)"]
    return [f"(no numbered steps in {setting})"]


# ------------------------------------------------------------------ output

def _section(title: str, lines: list[str]) -> list[str]:
    return [title, *[f"  {line}" for line in lines], ""]


def build(root: Path) -> str:
    commits = _recent_commits(root)
    last = list(commits) if commits else ["(no commits yet)"]

    try:
        last += _merged_prs(root) or ["(no merged PRs)"]
    except GhUnavailable as exc:
        last.append(f"(merged PRs: {exc})")

    setting = _plan_setting(root)
    try:
        plain, waiting = _open_issues(root)
        issue_error = None
    except GhUnavailable as exc:
        plain, waiting, issue_error = [], [], str(exc)

    if setting:
        nxt = _next_from_plan(root, setting)
    elif issue_error:
        nxt = [f"({issue_error})"]
    else:
        nxt = [_titled(i) for i in plain[:ISSUE_LIMIT]] or ["(none)"]

    if issue_error:
        wait = [f"({issue_error})"]
    else:
        wait = [_titled(i) for i in waiting[:WAITING_LIMIT]] or ["(none)"]

    out = (_section("Last done", last) + _section("Next", nxt)
           + _section("Waiting on you", wait))
    return "\n".join(out).rstrip("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print last done, next, and what waits on you."
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Target project root (default: current directory).",
    )
    args = parser.parse_args(argv)

    cwd = Path(args.cwd).resolve()
    if not cwd.is_dir():
        print(f"ERROR: not a directory: {cwd}", file=sys.stderr)
        return 1
    root = _repo_root(cwd)
    if root is None:
        print(f"ERROR: not a git repository: {cwd}", file=sys.stderr)
        return 1

    text = build(root)
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(errors="replace")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
