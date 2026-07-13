"""Deterministic per-file dependency-contract renderer.

``build_contracts`` derives per-file dependency contracts from a graphify graph
dict (the 0-token static-analysis output). Pure Python, LLM-free: the trustable
EXTRACTED import/inherit edges become ``references``/``referenced_by``; lower-trust
``INFERRED``/calls/uses edges become ``inferred``.

graphify extracts repo structure deterministically (``cairn derive``, 0 tokens);
this module turns the raw symbol graph into per-file dependency contracts —
reusing the ``reconcile.py`` rollup pattern — so the map is *derived and
verifiable*, never hand-fudged.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import graphify_adapter

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Cross-file dependency relations graphify EXTRACTS with high confidence: a real
# module-level import/inherit/re-export. The trustable dependency signal,
# asserted in references/referenced_by.
DEP_RELATIONS: frozenset[str] = frozenset(
    {"imports", "imports_from", "re_exports", "inherits"}
)

# Symbol-level "this name is used here" relations. Lower-trust heuristics;
# surfaced separately, confidence-flagged, NEVER asserted as a dependency.
INFERRED_RELATIONS: frozenset[str] = frozenset({"calls", "uses"})

# Extensions that count as "code" (mirrors reconcile.CODE_EXTS).
_CODE_EXTS: frozenset[str] = frozenset(
    {
        ".py", ".ps1", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs",
        ".java", ".rb", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs",
    }
)


# ---------------------------------------------------------------------------
# FileContract dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileContract:
    """The derived contract for one source file.

    All list fields are sorted, de-duplicated tuples of repo-relative
    forward-slash paths (deterministic).
    """

    file: str                       # repo-relative, forward-slash, e.g. "src/core.py"
    signatures: tuple[str, ...]     # top-level symbols this file DEFINES (contains targets), sorted
    references: tuple[str, ...]     # OUT: files this file imports/inherits (EXTRACTED + DEP_RELATIONS), sorted
    referenced_by: tuple[str, ...]  # IN:  files that import/inherit this file (EXTRACTED + DEP_RELATIONS), sorted
    inferred: tuple[str, ...]       # low-trust neighbours (INFERRED_RELATIONS or confidence==INFERRED), sorted

    @property
    def in_count(self) -> int:
        """Number of files that import/inherit this file."""
        return len(self.referenced_by)

    @property
    def out_count(self) -> int:
        """Number of files this file imports/inherits."""
        return len(self.references)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_code_node(n: dict[str, Any]) -> bool:
    """True if the node belongs to a code source file.

    Primary signal: ``file_type == "code"``.
    Fallback (absent file_type): check ``source_file`` extension against
    ``_CODE_EXTS`` — mirrors the reconcile.py CODE_EXTS convention.
    """
    ft = n.get("file_type")
    if ft == "code":
        return True
    if ft is None:
        sf = n.get("source_file") or ""
        return Path(sf).suffix.lower() in _CODE_EXTS
    return False


def _norm_sf(sf: str) -> str:
    """Normalize source_file path to forward-slash form."""
    return sf.replace("\\", "/")


def _clean_label(label: str) -> bool:
    """Label-noise filter (mirrors reconcile.py §10 calibration).

    Accepts labels that are non-empty, single-line, and shorter than 40 chars.
    Rejects docstring-fragment labels and other long multi-line artefacts.
    """
    lab = (label or "").strip()
    return bool(lab) and "\n" not in lab and len(lab) < 40


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------


def build_contracts(graph: dict[str, Any]) -> dict[str, FileContract]:
    """Derive per-file contracts from a loaded graphify graph (the dict returned
    by ``graphify_adapter.load_graph`` — keys ``"nodes"``, ``"edges"``).

    Pure and deterministic: same graph in → identical dict out.

    Algorithm (spec current.md Output A §5-step):
      1. ``node_file``: map each node id → normalized ``source_file``, for nodes
         with ``file_type == "code"`` (or code extension if absent).  Nodes
         without a qualifying source_file are ignored.
      2. For each file, find its *file node* (``label == basename(file)``) and
         collect ``signatures`` from its ``contains``-edge targets with the
         reconcile label-noise filter (non-empty, no newline, len < 40).
      3. Roll all edges to file pairs: skip dangling and intra-file pairs,
         then route by confidence + relation:
           - EXTRACTED + DEP_RELATIONS → ``references`` / ``referenced_by``
           - INFERRED_RELATIONS OR confidence=="INFERRED" → ``inferred`` (both directions)
      4. Remove pairs already asserted in references/referenced_by from inferred
         (a trustable edge is never also flagged low-trust).
      5. Emit one ``FileContract`` per distinct code file; sort + dedup all
         tuples.  Test files are included so a base module's ``referenced_by``
         lists its test consumers.

    Returns ``{file: FileContract}`` (empty dict for an empty/invalid graph).
    """
    nodes: list[dict] = list(graph.get("nodes") or [])
    edges: list[dict] = list(graph.get("edges") or [])

    # --- Step 1: build node lookup and node_file map -------------------------
    node_lookup: dict[str, dict] = {}
    node_file: dict[str, str] = {}         # node_id → normalized source_file
    file_nodes_map: dict[str, list[dict]] = {}  # source_file → all nodes in that file

    for n in nodes:
        nid = n.get("id")
        if nid:
            node_lookup[nid] = n
        sf = n.get("source_file")
        if sf and _is_code_node(n) and nid:
            sf_norm = _norm_sf(sf)
            node_file[nid] = sf_norm
            file_nodes_map.setdefault(sf_norm, []).append(n)

    if not node_file:
        return {}  # no code nodes at all

    all_files: set[str] = set(node_file.values())

    # --- Step 2: file node → source_file map; collect signatures -------------
    # A "file node" is the node within a file whose label == basename(file).
    file_node_to_sf: dict[str, str] = {}   # node_id → source_file (file-level nodes only)
    for sf in all_files:
        basename = Path(sf).name
        for n in file_nodes_map.get(sf, []):
            if n.get("label") == basename:
                nid = n.get("id")
                if nid:
                    file_node_to_sf[nid] = sf
                break

    file_sigs: dict[str, set[str]] = {sf: set() for sf in all_files}
    for e in edges:
        if e.get("relation") != "contains":
            continue
        src_id = e.get("source")
        tgt_id = e.get("target")
        if src_id not in file_node_to_sf or not tgt_id:
            continue
        tgt_node = node_lookup.get(tgt_id)
        if tgt_node:
            lab = (tgt_node.get("label") or "").strip()
            if _clean_label(lab):
                file_sigs[file_node_to_sf[src_id]].add(lab)

    # --- Step 3: roll edges up to file pairs ---------------------------------
    refs: dict[str, set[str]] = {sf: set() for sf in all_files}
    ref_by: dict[str, set[str]] = {sf: set() for sf in all_files}
    inferred_raw: dict[str, set[str]] = {sf: set() for sf in all_files}

    for e in edges:
        src_id = e.get("source")
        tgt_id = e.get("target")
        if not src_id or not tgt_id:
            continue
        fs = node_file.get(src_id)
        ft = node_file.get(tgt_id)
        if not fs or not ft:
            continue  # endpoint has no known code file — skip
        if fs == ft:
            continue  # intra-file — skip

        relation = e.get("relation") or ""
        confidence = (e.get("confidence") or "").upper()

        if confidence == "EXTRACTED" and relation in DEP_RELATIONS:
            refs[fs].add(ft)
            ref_by[ft].add(fs)
        elif relation in INFERRED_RELATIONS or confidence == "INFERRED":
            inferred_raw[fs].add(ft)
            inferred_raw[ft].add(fs)

    # --- Steps 4 + 5: exclude trustable pairs; emit FileContracts ------------
    result: dict[str, FileContract] = {}
    for sf in all_files:
        trustable = refs[sf] | ref_by[sf]
        result[sf] = FileContract(
            file=sf,
            signatures=tuple(sorted(file_sigs[sf])),
            references=tuple(sorted(refs[sf])),
            referenced_by=tuple(sorted(ref_by[sf])),
            inferred=tuple(sorted(inferred_raw[sf] - trustable)),
        )

    return result


def build_contracts_from_graph_json(
    graph_json: str | Path,
) -> dict[str, FileContract]:
    """Convenience wrapper: ``graphify_adapter.load_graph(graph_json)`` then
    ``build_contracts(...)``.

    ``graph_json`` is the path to graphify's output ``graph.json``.
    Raises ``FileNotFoundError`` / ``json.JSONDecodeError`` on I/O or parse
    failures (callers that want graceful degradation should guard with
    ``try/except``).
    """
    graph = graphify_adapter.load_graph(graph_json)
    return build_contracts(graph)


# ---------------------------------------------------------------------------
# render_primer
# ---------------------------------------------------------------------------


def _fmt_paths(paths: tuple[str, ...]) -> str:
    """Format a sorted tuple of paths as inline backtick list, or '—' if empty."""
    if not paths:
        return "—"  # em-dash
    return ", ".join(f"`{p}`" for p in paths)


def render_primer(
    contracts: dict[str, "FileContract"], subtree: str | None = None
) -> str:
    """Render the deterministic, LLM-free per-file dependency-contract markdown.

    When *subtree* is given (e.g. ``"src/pkg"``), emit contract cards only
    for files under that path; cross-references to files OUTSIDE the subtree are
    still listed (as paths). Output is stable across runs (files sorted, refs
    sorted). Sections:

      # Derived contracts — <subtree or "repo">
      > 0-token, derived from graphify graph.json. EXTRACTED import/inherit refs are the
      > trustable dependency signal; INFERRED (calls/uses) are flagged — verify before trusting.

      ## Dependency map (blast radius)
      - `<file>` — IN <in_count> / OUT <out_count>
        - referenced_by: <paths | —>
        - references: <paths | —>

      ## File contracts
      ### `<file>` — IN <n> / OUT <m>
      - defines: <signatures | —>
      - references: <paths | —>
      - referenced_by: <paths | —>
      - inferred (verify): <paths | —>
    """
    # Select and sort files for the subtree (or all files)
    if subtree is not None:
        prefix = subtree.rstrip("/") + "/"
        selected: list[str] = sorted(
            k for k in contracts if k == subtree or k.startswith(prefix)
        )
    else:
        selected = sorted(contracts.keys())

    title = subtree if subtree is not None else "repo"

    out: list[str] = []

    # ---------- header ----------
    out.append(f"# Derived contracts — {title}")
    out.append(
        "> 0-token, derived from graphify graph.json. EXTRACTED import/inherit refs are the\n"
        "> trustable dependency signal; INFERRED (calls/uses) are flagged — verify before trusting."
    )
    out.append("")

    # ---------- dependency map ----------
    out.append("## Dependency map (blast radius)")
    for f in selected:
        fc = contracts[f]
        out.append(f"- `{f}` — IN {fc.in_count} / OUT {fc.out_count}")
        out.append(f"  - referenced_by: {_fmt_paths(fc.referenced_by)}")
        out.append(f"  - references: {_fmt_paths(fc.references)}")
    out.append("")

    # ---------- file contracts ----------
    out.append("## File contracts")
    for f in selected:
        fc = contracts[f]
        out.append(f"### `{f}` — IN {fc.in_count} / OUT {fc.out_count}")
        sig_str = ", ".join(fc.signatures) if fc.signatures else "—"
        out.append(f"- defines: {sig_str}")
        out.append(f"- references: {_fmt_paths(fc.references)}")
        out.append(f"- referenced_by: {_fmt_paths(fc.referenced_by)}")
        out.append(f"- inferred (verify): {_fmt_paths(fc.inferred)}")
        out.append("")

    return "\n".join(out)
