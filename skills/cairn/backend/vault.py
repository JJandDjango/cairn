"""Atlas vault management: the portfolio overlay at ``~/.claude/atlas/``
(ATLAS.md sections 5 & 7).

Each project's authored ``ATLAS.md`` is symlinked into the vault as ``<name>.md``
so ``[[name]]`` resolves in Obsidian's graph view. A generated ``index.md`` is
the portfolio dashboard. Symlinks need Windows Developer Mode (a Pass 1
prerequisite); we fall back to a copy + marker if symlinks are unavailable.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from . import schema

VAULT = Path.home() / ".claude" / "atlas"


def ensure_vault() -> Path:
    """Create the vault scaffold if missing. Returns the vault path."""
    VAULT.mkdir(parents=True, exist_ok=True)
    (VAULT / "canvas").mkdir(exist_ok=True)
    index = VAULT / "index.md"
    if not index.exists():
        index.write_text(
            "# Atlas Portfolio\n\n_No projects yet. Run `/atlas init <path>`._\n",
            encoding="utf-8")
    return VAULT


def add_project(atlas_md: str | Path) -> Path:
    """Link a project's ATLAS.md into the vault as ``<name>.md`` (name from
    frontmatter), then regenerate ``index.md``. Falls back to a copy if symlinks
    are unavailable. Returns the vault entry path."""
    atlas_md = Path(atlas_md).resolve()
    fm, _ = schema.parse(atlas_md)
    name = fm.get("name")
    if not name:
        raise ValueError(f"{atlas_md} has no 'name' in frontmatter")
    ensure_vault()
    link = VAULT / f"{name}.md"
    if link.exists() or link.is_symlink():
        link.unlink()
    copy_marker = VAULT / f".{name}.copy"
    try:
        os.symlink(atlas_md, link)
        if copy_marker.exists():
            copy_marker.unlink()
    except (OSError, NotImplementedError):
        # Windows without Developer Mode / insufficient privilege: copy + mark.
        link.write_text(atlas_md.read_text(encoding="utf-8"), encoding="utf-8")
        copy_marker.write_text(str(atlas_md), encoding="utf-8")
    write_index()
    return link


def list_projects() -> list[dict[str, Any]]:
    """Parse every ``<name>.md`` in the vault into a summary list."""
    ensure_vault()
    out: list[dict[str, Any]] = []
    for md in sorted(VAULT.glob("*.md")):
        if md.name == "index.md":
            continue
        try:
            fm, _ = schema.split_frontmatter(md.read_text(encoding="utf-8"))
            out.append(schema.summary(fm))
        except Exception as exc:  # malformed entry shouldn't crash the roll-up
            out.append({"name": md.stem, "status": "?",
                        "purpose": f"(parse error: {exc})",
                        "components": 0, "flows": 0})
    return out


def render_index() -> str:
    """Generate ``index.md`` content from the current vault projects."""
    projects = list_projects()
    lines = ["# Atlas Portfolio", ""]
    if not projects:
        lines.append("_No projects yet. Run `/atlas init <path>`._")
        return "\n".join(lines) + "\n"
    lines += ["## Projects", "",
              "| Project | Status | Purpose | Components | Flows |",
              "|---|---|---|---|---|"]
    for p in projects:
        lines.append(
            f"| [[{p['name']}]] | {p['status']} | {p['purpose']} | "
            f"{p['components']} | {p['flows']} |")
    return "\n".join(lines) + "\n"


def write_index() -> Path:
    """Write the generated portfolio dashboard to ``index.md``."""
    ensure_vault()
    idx = VAULT / "index.md"
    idx.write_text(render_index(), encoding="utf-8")
    return idx
