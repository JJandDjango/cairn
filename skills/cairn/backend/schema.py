"""MAP authored-model schema: parse, validate, serialize MAP.md frontmatter.

The frontmatter (YAML between `---` fences) is the machine-readable contract for
the *authored* model. The derived graph in `graphify-out/` is a separate
artifact, never merged here except by human acceptance. Keys are snake_case
(Dataview-safe); component/flow *names* are kebab-case values. Frontmatter is
versioned (`cairn_schema`) for migration.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CAIRN_SCHEMA_VERSION = 1

STATUS_VALUES = {"greenfield", "active", "maintenance", "archived"}
LEVEL_VALUES = {"system", "module", "implementation"}


class MapParseError(Exception):
    """Raised when MAP.md cannot be split into frontmatter + body."""


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a MAP.md document into (frontmatter dict, body markdown).

    Expects a leading YAML block delimited by lines that are exactly `---`.
    """
    if not text.startswith("---"):
        raise MapParseError("MAP.md must begin with a '---' frontmatter fence")
    lines = text.splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise MapParseError("unterminated frontmatter: no closing '---'")
    data = yaml.safe_load("\n".join(lines[1:end])) or {}
    if not isinstance(data, dict):
        raise MapParseError("frontmatter is not a YAML mapping")
    body = "\n".join(lines[end + 1:]).lstrip("\n")
    return data, body


def parse(path: str | Path) -> tuple[dict[str, Any], str]:
    """Parse a MAP.md file -> (frontmatter, body)."""
    return split_frontmatter(Path(path).read_text(encoding="utf-8"))


def validate(fm: dict[str, Any]) -> list[str]:
    """Validate authored frontmatter. Returns human-readable error strings
    (empty list == valid)."""
    errors: list[str] = []

    def req(cond: bool, msg: str) -> None:
        if not cond:
            errors.append(msg)

    req(fm.get("cairn_schema") == CAIRN_SCHEMA_VERSION,
        f"cairn_schema must be {CAIRN_SCHEMA_VERSION} (got {fm.get('cairn_schema')!r})")

    # Identity
    req(bool(fm.get("name")), "identity: 'name' is required")
    req(bool(fm.get("purpose")), "identity: 'purpose' is required")
    status = fm.get("status")
    req(status in STATUS_VALUES,
        f"identity: 'status' must be one of {sorted(STATUS_VALUES)} (got {status!r})")

    # Components (>= 1)
    comps = fm.get("components") or []
    req(isinstance(comps, list) and len(comps) >= 1,
        "components: at least one component is required")
    comp_names: set[str] = set()
    for i, c in enumerate(comps if isinstance(comps, list) else []):
        where = f"components[{i}]"
        if not isinstance(c, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        req(bool(c.get("name")), f"{where}: 'name' is required")
        req(bool(c.get("role")), f"{where}: 'role' is required")
        req(bool(c.get("location")), f"{where}: 'location' is required")
        lvl = c.get("level", "module")
        req(lvl in LEVEL_VALUES,
            f"{where}: 'level' must be one of {sorted(LEVEL_VALUES)} (got {lvl!r})")
        if c.get("name"):
            comp_names.add(c["name"])

    # Flows (optional): entry + >= 2 stages, all referencing known components
    for i, fl in enumerate(fm.get("flows") or []):
        where = f"flows[{i}]"
        if not isinstance(fl, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        req(bool(fl.get("name")), f"{where}: 'name' is required")
        entry = fl.get("entry")
        req(bool(entry), f"{where}: 'entry' is required")
        if entry and comp_names and entry not in comp_names:
            errors.append(f"{where}: entry '{entry}' is not a known component")
        stages = fl.get("stages") or []
        req(isinstance(stages, list) and len(stages) >= 2,
            f"{where}: 'stages' must list at least 2 stages")
        for j, st in enumerate(stages if isinstance(stages, list) else []):
            sw = f"{where}.stages[{j}]"
            if not isinstance(st, dict):
                errors.append(f"{sw}: must be a mapping")
                continue
            comp = st.get("component")
            req(bool(comp), f"{sw}: 'component' is required")
            if comp and comp_names and comp not in comp_names:
                errors.append(f"{sw}: component '{comp}' is not a known component")

    # External (optional)
    for i, ex in enumerate(fm.get("external") or []):
        where = f"external[{i}]"
        if not isinstance(ex, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        for key in ("service", "type", "purpose"):
            req(bool(ex.get(key)), f"{where}: '{key}' is required")

    # Cross-project (optional)
    for i, cp in enumerate(fm.get("cross_project") or []):
        where = f"cross_project[{i}]"
        if not isinstance(cp, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        for key in ("project", "type"):
            req(bool(cp.get(key)), f"{where}: '{key}' is required")

    return errors


class _IndentDumper(yaml.SafeDumper):
    """Indent block sequences under their key (`  - x`, not `- x`) to match the
    authored MAP.md style — keeps apply/serialize diffs minimal so the write
    boundary only shows what actually changed."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def serialize(fm: dict[str, Any], body: str = "") -> str:
    """Render frontmatter + body back to MAP.md text. Used for derive-first
    staging and normalization."""
    dumped = yaml.dump(fm, Dumper=_IndentDumper, sort_keys=False,
                       default_flow_style=False, allow_unicode=True,
                       width=4096).rstrip("\n")
    body = (body or "").strip("\n")
    return f"---\n{dumped}\n---\n\n{body}\n" if body else f"---\n{dumped}\n---\n"


def summary(fm: dict[str, Any]) -> dict[str, Any]:
    """Compact per-project summary for `/cairn view` roll-ups."""
    return {
        "name": fm.get("name", "?"),
        "status": fm.get("status", "?"),
        "purpose": fm.get("purpose", ""),
        "components": len(fm.get("components") or []),
        "flows": len(fm.get("flows") or []),
    }
