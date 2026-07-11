"""Pass 2 reconciliation: diff graphify's derived graph against the authored
MAP.md and emit confidence-ranked proposals into an editable proposals.md.

The human-gated write boundary (atlas-design.md §2): `reconcile()` and `render()`
only ever write to graphify-out/proposals.md (derived, regenerable). The single
write into authored truth is `apply()`, which reads back the checklist the human
edited and writes the checked proposals into MAP.md, re-validating first.

Reconciliation runs at file/directory granularity, not node: graphify's
symbol-level graph (8k+ nodes for this repo, ~61% tests/) is rolled up by
source_file -> directory, so a directory with significant uncovered code becomes
ONE proposal — collapsing thousands of noisy nodes to a handful of high-signal
component proposals (the §10 calibration).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import graphify_adapter as gfx
from . import schema

# Extensions that count as "code" for component discovery. graphify also nodes
# .md headings and .json keys; those are dropped here — they're docs/config, not
# components (a .md file can still be an authored `docs:` pointer, just not a
# discovered component).
CODE_EXTS = {".py", ".ps1", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs",
             ".java", ".rb", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs"}

# Directory names never proposed as components: tests. (VCS/tooling dot-dirs are
# filtered structurally below; doc dirs like designs/ fall out via CODE_EXTS.)
HARD_IGNORE = {"tests", "test"}

MIN_NODES = 3  # below this a candidate dir is too thin to be a component


@dataclass
class Proposal:
    kind: str                       # new_component | dangling_component
    location: str                   # stable id: repo-relative dir/file
    node_count: int = 0
    confidence: str = "INFERRED"    # EXTRACTED | INFERRED (graphify rank)
    symbols: list[str] = field(default_factory=list)
    suggested: dict[str, Any] = field(default_factory=dict)  # name/role/level/location


# ---- candidate rollup -------------------------------------------------------

def _candidate_dir(source_file: str) -> str | None:
    """Roll a node's source_file up to a candidate component location: the first
    two path parts — a package subdir ('agentic/l4', 'src/widget'), a loose
    depth-2 module ('agentic/_clock.py'), or a top-level file ('launch.py').
    Returns None for ignored (dot-dir / tests) paths. Two-level grouping matches
    how authored components are scoped (a subdir or a module), not per-file, and
    is repo-agnostic — no hardcoded package name."""
    parts = Path(source_file).parts
    if not parts or parts[0].startswith(".") or parts[0] in HARD_IGNORE:
        return None
    return "/".join(parts[:2])


def _kebab_name(location: str) -> str:
    base = Path(location).name
    base = re.sub(r"\.[A-Za-z0-9]+$", "", base)   # strip extension
    return base.strip("_").replace("_", "-").lower() or base.lower()


# ---- reconcile --------------------------------------------------------------

def _authored_locations(fm: dict) -> list[str]:
    locs = []
    for c in fm.get("components") or []:
        loc = (c.get("location") or "").split("#", 1)[0].strip().rstrip("/")
        if loc:
            locs.append(loc)
    return locs


def _covered(candidate: str, authored: list[str]) -> bool:
    c = candidate.rstrip("/")
    for a in authored:
        if c == a or c.startswith(a + "/") or a.startswith(c + "/"):
            return True
    return False


def reconcile(atlas_md: str | Path | None, graph_json: str | Path,
              root: str | Path) -> list[Proposal]:
    """Diff the derived graph against MAP.md -> ranked proposals. Pure read;
    writes nothing. A missing/None atlas_md means an empty authored model (every
    code dir becomes a proposal) — the derive-first init case."""
    root = Path(root).resolve()
    fm = schema.parse(atlas_md)[0] if atlas_md and Path(atlas_md).exists() else {}
    authored = _authored_locations(fm)
    graph = gfx.load_graph(graph_json)

    # Map each code node -> candidate dir; bucket nodes per dir.
    node_dir: dict[str, str] = {}
    dir_nodes: dict[str, list[dict]] = {}
    for n in graph["nodes"]:
        sf = n.get("source_file")
        if not sf or Path(sf).suffix.lower() not in CODE_EXTS:
            continue
        cand = _candidate_dir(sf)
        if not cand:
            continue
        node_dir[n.get("id")] = cand
        dir_nodes.setdefault(cand, []).append(n)

    # Per-dir edge-confidence (graphify's EXTRACTED/INFERRED rank) + node degree
    # (for picking the most-connected symbols as human-readable evidence).
    dir_ext = {d: 0 for d in dir_nodes}
    dir_tot = {d: 0 for d in dir_nodes}
    degree: dict[str, int] = {}
    for e in graph["edges"]:
        s, t = e.get("source"), e.get("target")
        conf = (e.get("confidence") or "").upper()
        for d in {node_dir.get(s), node_dir.get(t)}:
            if d is not None:
                dir_tot[d] += 1
                if conf == "EXTRACTED":
                    dir_ext[d] += 1
        if s in node_dir:
            degree[s] = degree.get(s, 0) + 1
        if t in node_dir:
            degree[t] = degree.get(t, 0) + 1

    proposals: list[Proposal] = []

    # New-component proposals: uncovered candidate dirs with enough code.
    for d, ns in dir_nodes.items():
        if _covered(d, authored) or len(ns) < MIN_NODES:
            continue
        ext_frac = dir_ext[d] / dir_tot[d] if dir_tot[d] else 0.0
        conf = "EXTRACTED" if ext_frac >= 0.7 else "INFERRED"
        # Top symbols by degree, skipping docstring-fragment labels (long /
        # multi-line) — the noise the §10 calibration flagged.
        syms: list[str] = []
        for n in sorted(ns, key=lambda n: degree.get(n.get("id"), 0), reverse=True):
            lab = (n.get("label") or "").strip()
            if lab and len(lab) < 40 and "\n" not in lab and lab not in syms:
                syms.append(lab)
            if len(syms) >= 4:
                break
        loc = d if Path(d).suffix else d + "/"
        proposals.append(Proposal(
            kind="new_component", location=loc, node_count=len(ns),
            confidence=conf, symbols=syms,
            suggested={
                "name": _kebab_name(d),
                "role": f"Derived stub — {', '.join(syms[:3]) or 'code'}. EDIT ME.",
                "level": "module",
                "location": loc,
            }))

    # Dangling-component proposals: an authored location no longer on disk.
    for c in fm.get("components") or []:
        loc = (c.get("location") or "").split("#", 1)[0].strip().rstrip("/")
        if loc and not (root / loc).exists():
            proposals.append(Proposal(
                kind="dangling_component", location=c.get("location", loc),
                suggested={"name": c.get("name")}))

    # Substance-first: every candidate dir is an AST certainty (node existence is
    # extracted, not inferred), so node_count is the primary signal of how much a
    # missing component matters. graphify's EXTRACTED/INFERRED is an *edge*-
    # confidence tag — kept as a displayed rank + tiebreak, not the primary sort,
    # else a 326-node subsystem (l4) sinks below an 8-node example.
    rank = {"EXTRACTED": 0, "INFERRED": 1}
    proposals.sort(key=lambda p: (p.kind != "new_component",
                                  -p.node_count, rank.get(p.confidence, 2)))
    return proposals


# ---- proposals.md render / parse / apply -----------------------------------

def render(proposals: list[Proposal], out_md: str | Path,
           name: str, path_hint: str = ".") -> Path:
    """Write the editable checklist. All items start UNCHECKED — acceptance is
    the human checking a box, never a default."""
    new = [p for p in proposals if p.kind == "new_component"]
    dangling = [p for p in proposals if p.kind == "dangling_component"]
    lines = [
        f"# Reconciliation proposals — {name}",
        "",
        "<!-- Generated by `cairn reconcile` from graphify-out/graph.json.",
        "     Check [x] the proposals to accept; edit name/role/level inline if you like.",
        f"     Then apply: python -m backend reconcile {path_hint} --apply",
        "     Nothing is written to your MAP.md until you --apply. -->",
        "",
        f"## New components ({len(new)})",
        "",
    ]
    if not new:
        lines.append("_none — every derived code directory maps to a component._\n")
    for p in new:
        s = p.suggested
        lines.append(f"- [ ] **{p.location}** · {p.node_count} nodes · {p.confidence}")
        lines.append(f"  - name: `{s['name']}`")
        lines.append(f"  - role: `{s['role']}`")
        lines.append(f"  - level: `{s['level']}`")
        if p.symbols:
            lines.append(f"  - symbols: {', '.join(p.symbols)}")
        lines.append("")
    lines.append(f"## Dangling components ({len(dangling)})")
    lines.append("")
    if not dangling:
        lines.append("_none — every authored location resolves on disk._\n")
    for p in dangling:
        lines.append(f"- [ ] **{p.location}** — authored component "
                     f"`{p.suggested.get('name')}` no longer on disk (remove?)")
        lines.append("")
    out = Path(out_md)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


_CHECK_RE = re.compile(r"^- \[([ xX])\]\s+\*\*(.+?)\*\*")
_FIELD_RE = re.compile(r"^\s+-\s+(name|role|level):\s+`(.*)`\s*$")


def parse(proposals_md: str | Path) -> list[dict]:
    """Parse proposals.md -> the CHECKED proposals as
    {location, dangling, fields:{name,role,level,location}}."""
    section = None
    checked: list[dict] = []
    cur: dict | None = None
    for line in Path(proposals_md).read_text(encoding="utf-8").splitlines():
        h = re.match(r"^##\s+(New components|Dangling components)", line)
        if h:
            section = h.group(1)
            cur = None
            continue
        m = _CHECK_RE.match(line)
        if m:
            cur = None
            if m.group(1) in ("x", "X"):
                loc = m.group(2).strip()
                cur = {"location": loc,
                       "dangling": section == "Dangling components",
                       "fields": {"location": loc}}
                checked.append(cur)
            continue
        f = _FIELD_RE.match(line)
        if f and cur is not None:
            cur["fields"][f.group(1)] = f.group(2)
    return checked


def apply(atlas_md: str | Path, proposals_md: str | Path) -> dict:
    """The ONLY write into authored truth. Reads the checked proposals and
    writes them into MAP.md; re-validates before writing (no write on error)."""
    checked = parse(proposals_md)
    fm, body = schema.parse(atlas_md)
    comps = list(fm.get("components") or [])
    added, removed = [], []
    for c in checked:
        if c["dangling"]:
            loc = c["location"].split("#", 1)[0].strip().rstrip("/")
            keep = [x for x in comps if (x.get("location") or "").split("#", 1)[0]
                    .strip().rstrip("/") != loc]
            if len(keep) != len(comps):
                removed.append(loc)
                comps = keep
        else:
            f = c["fields"]
            comps.append({
                "name": f.get("name") or _kebab_name(c["location"]),
                "role": f.get("role") or "EDIT ME.",
                "level": f.get("level") or "module",
                "location": f.get("location") or c["location"],
            })
            added.append(f.get("name") or _kebab_name(c["location"]))
    fm["components"] = comps
    errors = schema.validate(fm)
    if errors:
        return {"written": False, "errors": errors, "added": added, "removed": removed}
    Path(atlas_md).write_text(schema.serialize(fm, body), encoding="utf-8")
    return {"written": True, "errors": [], "added": added, "removed": removed}


# ---- derive-first staging (§3) ---------------------------------------------

def stage_draft(graph_json: str | Path, root: str | Path,
                name: str | None = None) -> str:
    """Build a full candidate MAP.md from the derived graph alone — reconcile
    against an empty model (every code dir becomes a component), then wrap with
    identity stubs. Returns the draft text; the caller stages it in graphify-out/
    for the human to curate and `accept`. This is "every proposal pre-checked"
    rendered as a complete file rather than a checklist (§10)."""
    root = Path(root).resolve()
    name = name or _kebab_name(root.name)
    comps = [dict(p.suggested) for p in reconcile(None, graph_json, root)
             if p.kind == "new_component"]
    if not comps:
        comps = [{"name": "main", "role": "EDIT ME.", "level": "module",
                  "location": "."}]
    fm = {
        "atlas_schema": schema.ATLAS_SCHEMA_VERSION,
        "name": name,
        "purpose": "EDIT ME -- one-line purpose.",
        "status": "active",
        "components": comps,
    }
    body = (f"# {name}\n\nEDIT ME -- 2-3 sentence overview.\n\n"
            "## Starting a session\n\nEDIT ME -- what to read first.\n")
    return schema.serialize(fm, body)


def accept_draft(draft_md: str | Path, atlas_md: str | Path) -> dict:
    """Validate a staged draft and write it to MAP.md (no write on error).
    The derive-first counterpart to apply() — the gated write into authored
    truth for a freshly-modeled project."""
    fm, body = schema.parse(draft_md)
    errors = schema.validate(fm)
    if errors:
        return {"written": False, "errors": errors}
    Path(atlas_md).write_text(schema.serialize(fm, body), encoding="utf-8")
    return {"written": True, "errors": []}
