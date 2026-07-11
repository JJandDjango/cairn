"""Thin adapter over graphify, the derived backend (ATLAS.md section 6).

Depends on the *data* (the `graph.json` node-link schema), not graphify's churny
CLI. Pinned at `graphifyy==0.8.31`; upgrades are deliberate. All graphify CLI
contact is isolated to this one file, so upstream churn is a one-file fix. MIT
upstream means a vendored fork is the escape hatch if it paywalls/pivots.

Pass 1 exposes only the no-LLM path (`graphify update`, 0 tokens). LLM-on
semantic extraction (`graphify extract`, which gates on a backend key) arrives
with the reconciliation loop in Pass 2.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

PINNED_VERSION = "0.8.31"


class GraphifyError(Exception):
    pass


def _graphify() -> str:
    exe = shutil.which("graphify")
    if not exe:
        raise GraphifyError(
            "graphify not found on PATH. Install: uv tool install graphifyy==0.8.31"
        )
    return exe


def version() -> str:
    # Decode subprocess output UTF-8/replace: graphify output is not guaranteed
    # ASCII and the OS locale codec (cp1252 on Windows) crashes on bytes
    # undefined there. Harness-wide policy; see cli_runner.py. (#133)
    out = subprocess.run([_graphify(), "--version"], capture_output=True,
                         text=True, encoding="utf-8", errors="replace", timeout=30)
    return (out.stdout or out.stderr).strip()


def check_version() -> tuple[bool, str]:
    """Return (matches_pin, reported_version)."""
    v = version()
    return (PINNED_VERSION in v, v)


def update(path: str | Path, timeout: int = 900) -> Path:
    """Run the no-LLM `graphify update` (0 tokens, local CPU) over `path`.

    Returns the path to `graphify-out/graph.json`. This is the `--fast` /
    pointer-only path; `graphify extract` (LLM-on) is intentionally not wrapped
    in Pass 1.
    """
    target = Path(path).resolve()
    # graphify's `update <path>` is cwd-relative by design ("cd <repo> && update .").
    # Run from target, scan "." — honors that contract and sidesteps cross-shell
    # absolute-path mangling. Output -> <target>/graphify-out.
    proc = subprocess.run([_graphify(), "update", "."], cwd=str(target),
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    if proc.returncode != 0:
        raise GraphifyError(
            f"graphify update failed ({proc.returncode}): {proc.stderr.strip()}"
        )
    graph = target / "graphify-out" / "graph.json"
    if not graph.exists():
        raise GraphifyError(f"graphify update produced no graph.json at {graph}")
    return graph


def load_graph(graph_json: str | Path) -> dict[str, Any]:
    """Load graphify's NetworkX node-link `graph.json`.

    Stable contract (the thing Atlas actually depends on):
      nodes[].id / .label / .source_file
      edges[].source / .target / .relation / .confidence / .confidence_score
    NetworkX writes the edge list under "links"; some versions use "edges".
    """
    data = json.loads(Path(graph_json).read_text(encoding="utf-8"))
    return {
        "nodes": data.get("nodes", []),
        "edges": data.get("edges", data.get("links", [])),
        "raw": data,
    }


def node_by_symbol(graph: dict[str, Any], symbol: str) -> dict[str, Any] | None:
    """Look a node up by label or id. (graphify's reliable `explain` primitive;
    its NL `query`/`affected` are fragile and deliberately not used.)"""
    for n in graph.get("nodes", []):
        if symbol in (n.get("label"), n.get("id")):
            return n
    return None
