"""Test-side builder for a 1.x spine: the five files /cairn migrate moves.

The 1.x templates and checks are retired, so this writes small fixed texts of
its own. Each text carries a unique marker line, so a test can tell where it
landed. MAP.md opens with a frontmatter block, so a test can check the first
bytes survive a rename.
"""
from __future__ import annotations

from pathlib import Path

NAMES = ("MAP.md", "THEORY.md", "STATE.md", "CONVENTIONS.md", "DOCS-SYSTEM.md")

TEXTS = {
    "MAP.md": (
        "---\nmode: hand-edited\n---\n"
        "# Map - demo\n\nMAP-BODY-1a2b\n\n"
        "| Component | Responsibility | Status | Deep doc |\n"
        "|---|---|---|---|\n"
        "| core | does the work | stable | no doc yet |\n"
    ),
    "THEORY.md": (
        "# Theory - demo\n\nTHEORY-BODY-3c4d\n\n"
        "Why it exists: a café menu that never lies.\n"
    ),
    "STATE.md": (
        "# State - demo\n\n_Generated 2020-01-01._\n\nSTATE-BODY-5e6f\n\n"
        "## Now\nFinish the thing.\n"
    ),
    "CONVENTIONS.md": (
        "# Conventions - demo\n\nCONVENTIONS-BODY-7a8b\n\n"
        "- **Match the idiom.** New code follows the touched layer.\n"
    ),
    "DOCS-SYSTEM.md": (
        "# Docs system - demo\n\nDOCSSYSTEM-BODY-9c0d\n\n"
        "Six strata, one job each.\n"
    ),
}


def write_1x(root: Path, names=NAMES, top: str = "", texts: dict | None = None) -> dict:
    """Write the named 1.x files into root/top as UTF-8 bytes and return
    {name: bytes}. top is "" (tracked) or ".docs-local" (local mode). texts
    replaces the default text of a name (str or bytes)."""
    folder = root / top if top else root
    folder.mkdir(parents=True, exist_ok=True)
    written = {}
    for name in names:
        text = (texts or {}).get(name, TEXTS[name])
        data = text if isinstance(text, bytes) else text.encode("utf-8")
        (folder / name).write_bytes(data)
        written[name] = data
    return written


def write_history(root: Path, top: str = "") -> None:
    """The folders migrate must never touch: an ADR and a docs/ page."""
    folder = root / top if top else root
    (folder / "decisions").mkdir(parents=True, exist_ok=True)
    (folder / "docs").mkdir(parents=True, exist_ok=True)
    (folder / "decisions" / "0001-record-architecture-decisions.md").write_text(
        "# 1. Record architecture decisions\n\nStatus: accepted\n", encoding="utf-8")
    (folder / "docs" / "guide.md").write_text(
        "<!-- covers: src/ -->\n# Guide\n\nA deep doc the MAP row names.\n", encoding="utf-8")
