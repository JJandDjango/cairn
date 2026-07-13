"""Functional acceptance tests for the contract renderer.

Covers the disk-path surface of the public contract that earlier tests did not exercise:

  * build_contracts_from_graph_json with a synthetic NetworkX node-link JSON
    temp file — the "convenience wrapper" contract path.
  * Error mode: file does not exist → exception raised (not a silent empty dict).
  * Integration: render_primer over contracts loaded from a JSON file.

All other criteria and error modes are
covered by test_contracts_v0.py and test_contracts_render_v0.py;
this file adds only what was missing.

No live API calls, no real graphify-out/graph.json required, no src/
internals read.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from backend.contracts import (
    FileContract,
    build_contracts_from_graph_json,
    render_primer,
)


# ---------------------------------------------------------------------------
# Helpers — NetworkX node-link raw format (what graphify writes to disk)
# Spec: "Edges live under the top-level `links` key (NetworkX node-link);
#        `load_graph` already normalizes them to `edges`."
# ---------------------------------------------------------------------------

def _code_node(node_id: str, label: str, source_file: str) -> dict:
    return {
        "id": node_id,
        "label": label,
        "file_type": "code",
        "source_file": source_file,
        "source_location": "L1",
    }


def _link(source: str, target: str, relation: str,
          confidence: str = "EXTRACTED", score: float = 1.0) -> dict:
    return {
        "source": source,
        "target": target,
        "relation": relation,
        "confidence": confidence,
        "confidence_score": score,
    }


def _nx_graph(*nodes, links=()) -> dict:
    """Minimal NetworkX node-link JSON dict (on-disk graphify format)."""
    return {
        "directed": True,
        "multigraph": False,
        "graph": {},
        "nodes": list(nodes),
        "links": list(links),
    }


def _write_graph(tmp_path: Path, graph_dict: dict) -> Path:
    p = tmp_path / "synthetic_graph.json"
    p.write_text(json.dumps(graph_dict), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# build_contracts_from_graph_json — happy-path (disk wrapper)
# ---------------------------------------------------------------------------

def test_from_graph_json_returns_dict(tmp_path):
    """build_contracts_from_graph_json on a valid JSON file returns a dict."""
    g = _nx_graph(_code_node("a", "a.py", "a.py"))
    p = _write_graph(tmp_path, g)
    result = build_contracts_from_graph_json(p)
    assert isinstance(result, dict)


def test_from_graph_json_imports_edge_sets_referenced_by(tmp_path):
    """Convenience wrapper: EXTRACTED imports edge b→a gives a.py referenced_by=('b.py',)."""
    n_a = _code_node("a", "a.py", "a.py")
    n_b = _code_node("b", "b.py", "b.py")
    lnk = _link("b", "a", "imports")
    g = _nx_graph(n_a, n_b, links=[lnk])
    p = _write_graph(tmp_path, g)

    contracts = build_contracts_from_graph_json(p)
    assert "a.py" in contracts
    assert "b.py" in contracts["a.py"].referenced_by


def test_from_graph_json_accepts_string_path(tmp_path):
    """build_contracts_from_graph_json accepts a plain str path (not only Path)."""
    g = _nx_graph(_code_node("x", "x.py", "x.py"))
    p = _write_graph(tmp_path, g)
    result = build_contracts_from_graph_json(str(p))
    assert isinstance(result, dict)


def test_from_graph_json_returns_file_contract_instances(tmp_path):
    """Values in the returned dict are FileContract instances."""
    n_a = _code_node("a", "a.py", "a.py")
    g = _nx_graph(n_a)
    p = _write_graph(tmp_path, g)
    contracts = build_contracts_from_graph_json(p)
    for val in contracts.values():
        assert isinstance(val, FileContract), f"Expected FileContract, got {type(val)}"


def test_from_graph_json_empty_graph_empty_dict(tmp_path):
    """Convenience wrapper on an empty-node JSON returns an empty dict (AC-1 via disk)."""
    g = _nx_graph(links=())
    p = _write_graph(tmp_path, g)
    result = build_contracts_from_graph_json(p)
    assert result == {}


def test_from_graph_json_dep_relation_inherits(tmp_path):
    """EXTRACTED 'inherits' (DEP_RELATIONS member) routes to references/referenced_by via disk path."""
    n_base = _code_node("base", "base.py", "base.py")
    n_child = _code_node("child", "child.py", "child.py")
    lnk = _link("child", "base", "inherits")
    g = _nx_graph(n_base, n_child, links=[lnk])
    p = _write_graph(tmp_path, g)
    contracts = build_contracts_from_graph_json(p)
    assert "base.py" in contracts["child.py"].references
    assert "child.py" in contracts["base.py"].referenced_by


def test_from_graph_json_inferred_relation_calls(tmp_path):
    """INFERRED_RELATIONS member 'calls' routes to inferred (not dep buckets) via disk path."""
    n_caller = _code_node("caller", "caller.py", "caller.py")
    n_callee = _code_node("callee", "callee.py", "callee.py")
    lnk = _link("caller", "callee", "calls")
    g = _nx_graph(n_caller, n_callee, links=[lnk])
    p = _write_graph(tmp_path, g)
    contracts = build_contracts_from_graph_json(p)
    caller_fc = contracts["caller.py"]
    assert "callee.py" not in caller_fc.references
    # 'callee.py' may appear in caller's inferred or vice-versa
    assert "callee.py" in caller_fc.inferred or "caller.py" in contracts["callee.py"].inferred


def test_from_graph_json_determinism(tmp_path):
    """Two calls on the same file return equal dicts (AC-5 / determinism via disk path)."""
    n_a = _code_node("a", "a.py", "a.py")
    n_b = _code_node("b", "b.py", "b.py")
    lnk = _link("b", "a", "imports")
    g = _nx_graph(n_a, n_b, links=[lnk])
    p = _write_graph(tmp_path, g)
    assert build_contracts_from_graph_json(p) == build_contracts_from_graph_json(p)


# ---------------------------------------------------------------------------
# Error mode: missing file (missing-graph — a missing graph.json raises, not a silent {})
# ---------------------------------------------------------------------------

def test_from_graph_json_missing_file_raises(tmp_path):
    """missing-graph: a missing JSON file raises an exception, not a silent {}."""
    missing = tmp_path / "does_not_exist.json"
    assert not missing.exists()
    with pytest.raises(Exception):
        build_contracts_from_graph_json(missing)


# ---------------------------------------------------------------------------
# Integration: render_primer over file-loaded contracts
# ---------------------------------------------------------------------------

def test_render_primer_over_file_loaded_contracts_returns_string(tmp_path):
    """render_primer works on contracts loaded from a JSON file and returns str."""
    n_a = _code_node("a", "a.py", "pkg/a.py")
    n_b = _code_node("b", "b.py", "pkg/b.py")
    n_cls = {
        "id": "cls", "label": "MyClass", "file_type": "code",
        "source_file": "pkg/a.py", "source_location": "L5",
    }
    links = [
        _link("b", "a", "imports"),
        _link("a", "cls", "contains"),
    ]
    g = _nx_graph(n_a, n_b, n_cls, links=links)
    p = _write_graph(tmp_path, g)
    contracts = build_contracts_from_graph_json(p)
    result = render_primer(contracts)
    assert isinstance(result, str)
    assert "# Derived contracts —" in result


def test_render_primer_over_file_loaded_contracts_in_out_counts(tmp_path):
    """render_primer over file-loaded contracts includes correct IN/OUT counts."""
    n_a = _code_node("a", "a.py", "a.py")
    n_b = _code_node("b", "b.py", "b.py")
    n_c = _code_node("c", "c.py", "c.py")
    links = [
        _link("b", "a", "imports"),
        _link("c", "a", "imports"),
    ]
    g = _nx_graph(n_a, n_b, n_c, links=links)
    p = _write_graph(tmp_path, g)
    contracts = build_contracts_from_graph_json(p)
    result = render_primer(contracts)
    # a.py is imported by 2 files → IN 2
    assert "IN 2" in result


def test_render_primer_subtree_over_file_loaded_contracts(tmp_path):
    """render_primer(subtree=...) over file-loaded contracts restricts cards correctly."""
    n_x = _code_node("x", "x.py", "sub/x.py")
    n_y = _code_node("y", "y.py", "sub/y.py")
    n_other = _code_node("o", "other.py", "other/other.py")
    links = [_link("x", "o", "imports")]
    g = _nx_graph(n_x, n_y, n_other, links=links)
    p = _write_graph(tmp_path, g)
    contracts = build_contracts_from_graph_json(p)
    result = render_primer(contracts, subtree="sub")
    # Cards only for sub/x.py and sub/y.py
    assert "### `other/other.py`" not in result
    assert "sub/x.py" in result
    assert "sub/y.py" in result
    # Cross-subtree ref path still appears in body
    assert "other/other.py" in result
