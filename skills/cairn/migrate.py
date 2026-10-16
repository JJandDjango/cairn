"""Move a 1.x spine to its 2.0 homes: a dry-run plan, then the mechanical moves.

Report-first: with no flag it prints one line per 1.x file and writes
nothing. With --apply it does only the mechanical moves; Claude then trims
to budget, routes STATE.md and removes it. Zero third-party dependencies.

Run it from a project:
    python migrate.py [--cwd DIR] [--apply]

Behavior:
  - The five 1.x files are THEORY.md, MAP.md, STATE.md, CONVENTIONS.md and
    DOCS-SYSTEM.md, at the root, or in .docs-local/ when the 2.0 spine
    (ARCHITECTURE.md) is there. The 2.0 pages land beside them.
  - Plan lines read `<source> -> <dest> [<op>]`: MAP.md becomes
    ARCHITECTURE.md (rename, or append when that page exists), THEORY.md
    joins ARCHITECTURE.md, CONVENTIONS.md and DOCS-SYSTEM.md join
    CONTRIBUTING.md (append), STATE.md is left to Claude (route). Each
    appended file sits under a `## From <FILE>.md` heading, text verbatim,
    after any text the page already holds.
  - A source is deleted only after its text is found in the destination; a
    failed check keeps the source, prints to stderr and exits 1.
  - STATE.md, decisions/ and docs/ are never touched. A page over its
    size budget is reported (OVERBUDGET) and left as written.
  - Nothing to move prints `nothing to migrate`, exit 0. A second --apply
    finds nothing to do.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import audit
import render


ROUTE_DEST = "(Claude: route its parts, then remove)"

# Plan order: MAP and THEORY into ARCHITECTURE.md, then CONVENTIONS and
# DOCS-SYSTEM into CONTRIBUTING.md.
DESTINATIONS = {
    "MAP.md": "ARCHITECTURE.md",
    "THEORY.md": "ARCHITECTURE.md",
    "CONVENTIONS.md": "CONTRIBUTING.md",
    "DOCS-SYSTEM.md": "CONTRIBUTING.md",
}


@dataclass
class Action:
    source: str
    dest: str
    op: str


# ------------------------------------------------------------------ planning

def top_dir(cwd: Path) -> Path:
    """Where the 1.x files and their 2.0 targets live."""
    if (cwd / render.LOCAL_DIR / "ARCHITECTURE.md").is_file():
        return cwd / render.LOCAL_DIR
    return cwd


def _rel(cwd: Path, p: Path) -> str:
    return p.relative_to(cwd).as_posix()


def plan(cwd: Path) -> list[Action]:
    """The actions apply() would perform. Writes nothing."""
    top = top_dir(cwd)
    actions = []
    for name, target in DESTINATIONS.items():
        if not (top / name).is_file():
            continue
        op = "append"
        if name == "MAP.md" and not (top / target).exists():
            op = "rename"
        actions.append(Action(_rel(cwd, top / name), _rel(cwd, top / target), op))
    if (top / "STATE.md").is_file():
        actions.append(Action(_rel(cwd, top / "STATE.md"), ROUTE_DEST, "route"))
    return actions


def _line(action: Action) -> str:
    return f"{action.source} -> {action.dest} [{action.op}]"


# ------------------------------------------------------------------- applying

def _merge(source: Path, dest: Path, op: str) -> str | None:
    """Move source's text into dest, verify it, then drop source. Returns an
    error message, or None on success. Bytes throughout, so the text is kept
    exactly as written."""
    try:
        text = source.read_bytes()
        if op == "rename":
            merged = text
        else:
            existing = dest.read_bytes() if dest.exists() else b""
            if existing and not existing.endswith(b"\n"):
                existing += b"\n"
            if existing:
                existing += b"\n"
            tail = b"" if text.endswith(b"\n") else b"\n"
            merged = existing + f"## From {source.name}\n\n".encode("utf-8") + text + tail
        dest.write_bytes(merged)
        if text not in dest.read_bytes():
            return f"{source.name} text not found in {dest.name} after the merge; source kept"
        source.unlink()
    except OSError as exc:
        return f"{source.name} -> {dest.name} failed ({exc}); source kept"
    return None


def apply(cwd: Path) -> int:
    """Perform the plan. Exit code: 0 done (or nothing to do), 1 a merge failed."""
    actions = plan(cwd)
    if not actions:
        print("nothing to migrate")
        return 0

    failed: set[str] = set()
    touched: list[str] = []
    status = 0
    for action in actions:
        print(_line(action))
        if action.op == "route" or action.dest in failed:
            continue
        error = _merge(cwd / action.source, cwd / action.dest, action.op)
        if error:
            print(f"ERROR: {error}", file=sys.stderr)
            failed.add(action.dest)
            status = 1
        elif action.dest not in touched:
            touched.append(action.dest)

    for rel in touched:
        limit = audit.TOP_BUDGETS.get(Path(rel).name)
        size = (cwd / rel).stat().st_size
        if limit is not None and size > limit:
            print(f"OVERBUDGET {rel} {size} > {limit}")
    return status


# -------------------------------------------------------------------- driver

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Move a 1.x spine to its 2.0 homes (dry run unless --apply)."
    )
    parser.add_argument("--cwd", default=".",
                        help="Project root (default: current directory).")
    parser.add_argument("--apply", action="store_true",
                        help="Perform the mechanical moves; without it, print the plan only.")
    args = parser.parse_args(argv)

    cwd = Path(args.cwd).resolve()
    if not cwd.is_dir():
        print(f"ERROR: not a directory: {cwd}", file=sys.stderr)
        return 2

    if args.apply:
        return apply(cwd)
    actions = plan(cwd)
    if not actions:
        print("nothing to migrate")
        return 0
    for action in actions:
        print(_line(action))
    return 0


if __name__ == "__main__":
    sys.exit(main())
