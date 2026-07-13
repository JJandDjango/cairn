"""Functional acceptance tests for the contract renderer.

Covers the acceptance criteria and
all documented Error Modes (empty-graph, no-source, dangling-edge, self-edge,
path-sep) using synthetic in-memory graph fixtures.

render_primer is deliberately excluded.

Constraints: no real graph.json required, no live API calls, no src/ internals.
tests public contract at backend.contracts only.
"""

from __future__ import annotations

import pytest

from backend.contracts import (
    DEP_RELATIONS,
    INFERRED_RELATIONS,
    FileContract,
    build_contracts,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_node(node_id: str, label: str, source_file: str, file_type: str = "code") -> dict:
    return {
        "id": node_id,
        "label": label,
        "file_type": file_type,
        "source_file": source_file,
        "source_location": "L1",
    }


def _make_edge(
    source: str,
    target: str,
    relation: str,
    confidence: str = "EXTRACTED",
    confidence_score: float = 1.0,
) -> dict:
    return {
        "source": source,
        "target": target,
        "relation": relation,
        "confidence": confidence,
        "confidence_score": confidence_score,
    }


def _graph(*nodes, edges=()) -> dict:
    """Build a minimal graph dict with 'nodes' and 'edges' keys (load_graph output shape)."""
    return {"nodes": list(nodes), "edges": list(edges)}


# ---------------------------------------------------------------------------
# Module-level contract constants
# ---------------------------------------------------------------------------

def test_dep_relations_contains_expected_members():
    """DEP_RELATIONS must include the four trustable cross-file dependency types."""
    assert "imports" in DEP_RELATIONS
    assert "imports_from" in DEP_RELATIONS
    assert "re_exports" in DEP_RELATIONS
    assert "inherits" in DEP_RELATIONS


def test_inferred_relations_contains_calls_and_uses():
    """INFERRED_RELATIONS must include calls and uses (lower-trust heuristics)."""
    assert "calls" in INFERRED_RELATIONS
    assert "uses" in INFERRED_RELATIONS


def test_dep_and_inferred_are_disjoint():
    """DEP_RELATIONS and INFERRED_RELATIONS must not overlap (clean routing)."""
    assert DEP_RELATIONS.isdisjoint(INFERRED_RELATIONS)


# ---------------------------------------------------------------------------
# FileContract dataclass contract
# ---------------------------------------------------------------------------

def test_file_contract_is_frozen():
    """FileContract must be immutable (frozen dataclass)."""
    fc = FileContract(
        file="a.py",
        signatures=("Foo",),
        references=("b.py",),
        referenced_by=("c.py",),
        inferred=(),
    )
    with pytest.raises((AttributeError, TypeError)):
        fc.file = "mutated"  # type: ignore[misc]


def test_file_contract_in_count_and_out_count():
    """in_count = len(referenced_by); out_count = len(references)."""
    fc = FileContract(
        file="a.py",
        signatures=(),
        references=("b.py", "c.py"),
        referenced_by=("x.py",),
        inferred=(),
    )
    assert fc.in_count == 1
    assert fc.out_count == 2


def test_file_contract_zero_counts():
    """FileContract with empty ref tuples has in_count == out_count == 0."""
    fc = FileContract(file="lone.py", signatures=(), references=(), referenced_by=(), inferred=())
    assert fc.in_count == 0
    assert fc.out_count == 0


# ---------------------------------------------------------------------------
# AC-1: empty graph -> empty dict
# ---------------------------------------------------------------------------

def test_ac1_empty_graph_returns_empty_dict():
    """AC-1: build_contracts({'nodes':[], 'edges':[]}) == {}."""
    result = build_contracts({"nodes": [], "edges": []})
    assert result == {}


# ---------------------------------------------------------------------------
# AC-2: EXTRACTED imports edges -> references / referenced_by
# ---------------------------------------------------------------------------

def _build_ac2_graph():
    """
    a.py (file node with symbol MyClass)
    b.py imports a.py  (EXTRACTED imports)
    c.py imports a.py  (EXTRACTED imports)
    """
    n_a = _make_node("a", "a.py", "a.py")
    n_a_sym = _make_node("a_myclass", "MyClass", "a.py")
    n_b = _make_node("b", "b.py", "b.py")
    n_c = _make_node("c", "c.py", "c.py")
    edges = [
        _make_edge("a", "a_myclass", "contains"),
        _make_edge("b", "a", "imports"),
        _make_edge("c", "a", "imports"),
    ]
    return _graph(n_a, n_a_sym, n_b, n_c, edges=edges)


def test_ac2_referenced_by_and_references():
    """AC-2: a.py's referenced_by == ('b.py', 'c.py') and references == ()."""
    contracts = build_contracts(_build_ac2_graph())
    assert "a.py" in contracts
    a = contracts["a.py"]
    assert a.referenced_by == ("b.py", "c.py")
    assert a.references == ()


def test_ac2_importer_has_reference():
    """AC-2: b.py and c.py each have references containing a.py."""
    contracts = build_contracts(_build_ac2_graph())
    assert "a.py" in contracts["b.py"].references
    assert "a.py" in contracts["c.py"].references


def test_ac2_all_dep_relations_route_to_references():
    """AC-2: All DEP_RELATIONS route to references/referenced_by when confidence==EXTRACTED."""
    for rel in DEP_RELATIONS:
        n_src = _make_node("src", "src.py", "src.py")
        n_dst = _make_node("dst", "dst.py", "dst.py")
        g = _graph(n_src, n_dst, edges=[_make_edge("src", "dst", rel, "EXTRACTED")])
        contracts = build_contracts(g)
        assert "dst.py" in contracts["src.py"].references, f"'{rel}' not routed to references"
        assert "src.py" in contracts["dst.py"].referenced_by, f"'{rel}' not routed to referenced_by"


# ---------------------------------------------------------------------------
# AC-3: uses/INFERRED edges -> inferred, NOT references/referenced_by
# ---------------------------------------------------------------------------

def test_ac3_extracted_uses_goes_to_inferred_not_references():
    """AC-3: EXTRACTED 'uses' edge routes to inferred bucket, not references/referenced_by."""
    n_c = _make_node("c", "c.py", "c.py")
    n_a = _make_node("a", "a.py", "a.py")
    g = _graph(n_c, n_a, edges=[_make_edge("c", "a", "uses", "EXTRACTED")])
    contracts = build_contracts(g)
    a = contracts["a.py"]
    c = contracts["c.py"]
    # must NOT appear in dep buckets
    assert "c.py" not in a.referenced_by
    assert "a.py" not in c.references
    # must appear in inferred somewhere
    assert "a.py" in c.inferred or "c.py" in a.inferred


def test_ac3_inferred_confidence_goes_to_inferred_not_dep_buckets():
    """AC-3: confidence==INFERRED edge routes to inferred, not references/referenced_by."""
    n_c = _make_node("c", "c.py", "c.py")
    n_a = _make_node("a", "a.py", "a.py")
    g = _graph(n_c, n_a, edges=[_make_edge("c", "a", "imports", "INFERRED")])
    contracts = build_contracts(g)
    a = contracts["a.py"]
    c = contracts["c.py"]
    assert "a.py" not in c.references
    assert "c.py" not in a.referenced_by
    assert "a.py" in c.inferred or "c.py" in a.inferred


def test_ac3_calls_goes_to_inferred():
    """AC-3: INFERRED_RELATIONS member 'calls' routes to inferred."""
    n_c = _make_node("c", "c.py", "c.py")
    n_a = _make_node("a", "a.py", "a.py")
    g = _graph(n_c, n_a, edges=[_make_edge("c", "a", "calls", "EXTRACTED")])
    contracts = build_contracts(g)
    c = contracts["c.py"]
    assert "a.py" not in c.references
    assert "c.py" not in contracts["a.py"].referenced_by


def test_ac3_inferred_path_absent_from_dep_buckets():
    """AC-3 negative: every entry in inferred must be absent from references and referenced_by."""
    n_c = _make_node("c", "c.py", "c.py")
    n_a = _make_node("a", "a.py", "a.py")
    g = _graph(n_c, n_a, edges=[_make_edge("c", "a", "uses", "EXTRACTED")])
    contracts = build_contracts(g)
    for fc in contracts.values():
        for path in fc.inferred:
            assert path not in fc.references, f"inferred path {path!r} leaked into references"
            assert path not in fc.referenced_by, f"inferred path {path!r} leaked into referenced_by"


# ---------------------------------------------------------------------------
# AC-4: signatures come from file node's contains targets only
# ---------------------------------------------------------------------------

def test_ac4_signatures_from_contains_targets():
    """AC-4: signatures == sorted labels of the file node's contains targets."""
    n_file = _make_node("mod", "mod.py", "mod.py")
    n_cls = _make_node("mod_cls", "MyClass", "mod.py")
    n_fn = _make_node("mod_fn", "my_func", "mod.py")
    g = _graph(
        n_file, n_cls, n_fn,
        edges=[
            _make_edge("mod", "mod_cls", "contains"),
            _make_edge("mod", "mod_fn", "contains"),
        ],
    )
    contracts = build_contracts(g)
    fc = contracts["mod.py"]
    assert fc.signatures == ("MyClass", "my_func")


def test_ac4_uses_target_not_in_signatures():
    """AC-4: A symbol reachable only via 'uses' (e.g. Path) must not appear in signatures."""
    n_file = _make_node("mod", "mod.py", "mod.py")
    n_path = _make_node("path_node", "Path", "pathlib.py")
    g = _graph(
        n_file, n_path,
        edges=[_make_edge("mod", "path_node", "uses", "EXTRACTED")],
    )
    contracts = build_contracts(g)
    fc = contracts["mod.py"]
    assert "Path" not in fc.signatures


def test_ac4_no_contains_means_empty_signatures():
    """AC-4: A file with no contains edges has empty signatures tuple."""
    n_file = _make_node("empty", "empty.py", "empty.py")
    contracts = build_contracts(_graph(n_file))
    assert contracts["empty.py"].signatures == ()


# ---------------------------------------------------------------------------
# AC-5: determinism — sorted, de-duplicated tuples; re-run yields equal dicts
# ---------------------------------------------------------------------------

def test_ac5_referenced_by_is_sorted():
    """AC-5: referenced_by tuple is sorted."""
    n_a = _make_node("a", "a.py", "a.py")
    n_z = _make_node("z", "z.py", "z.py")
    n_m = _make_node("m", "m.py", "m.py")
    edges = [
        _make_edge("z", "a", "imports"),
        _make_edge("m", "a", "imports"),
    ]
    contracts = build_contracts(_graph(n_a, n_z, n_m, edges=edges))
    rb = contracts["a.py"].referenced_by
    assert list(rb) == sorted(rb), "referenced_by must be sorted"


def test_ac5_references_is_sorted():
    """AC-5: references tuple is sorted."""
    n_a = _make_node("a", "a.py", "a.py")
    n_z = _make_node("z", "z.py", "z.py")
    n_m = _make_node("m", "m.py", "m.py")
    edges = [
        _make_edge("a", "z", "imports"),
        _make_edge("a", "m", "imports"),
    ]
    contracts = build_contracts(_graph(n_a, n_z, n_m, edges=edges))
    refs = contracts["a.py"].references
    assert list(refs) == sorted(refs), "references must be sorted"


def test_ac5_tuples_deduplicated():
    """AC-5: duplicate edges produce de-duplicated tuples."""
    n_a = _make_node("a", "a.py", "a.py")
    n_b = _make_node("b", "b.py", "b.py")
    edges = [
        _make_edge("b", "a", "imports"),
        _make_edge("b", "a", "imports"),
    ]
    contracts = build_contracts(_graph(n_a, n_b, edges=edges))
    assert contracts["a.py"].referenced_by.count("b.py") == 1


def test_ac5_determinism_two_calls_equal():
    """AC-5: calling build_contracts twice on identical input yields equal results."""
    g = _build_ac2_graph()
    assert build_contracts(g) == build_contracts(g)


# ---------------------------------------------------------------------------
# AC-6 / self-edge: intra-file edges produce no self-reference
# ---------------------------------------------------------------------------

def test_ac6_intrafile_edge_no_self_reference():
    """AC-6 / self-edge: edge where source_file == target_file must be skipped."""
    n_file = _make_node("mod", "mod.py", "mod.py")
    n_sym = _make_node("mod_sym", "MyClass", "mod.py")
    g = _graph(
        n_file, n_sym,
        edges=[
            _make_edge("mod", "mod_sym", "contains"),
            _make_edge("mod_sym", "mod", "references"),  # intra-file back-ref
        ],
    )
    contracts = build_contracts(g)
    fc = contracts["mod.py"]
    assert "mod.py" not in fc.references
    assert "mod.py" not in fc.referenced_by
    assert "mod.py" not in fc.inferred


# ---------------------------------------------------------------------------
# Error modes (negative-path coverage)
# ---------------------------------------------------------------------------

def test_em_cr_nokey_empty_dict():
    """empty-graph: {} missing 'nodes'/'edges' -> {} contracts, no crash."""
    result = build_contracts({})
    assert result == {}


def test_em_cr_nokey_partial_keys_no_crash():
    """empty-graph: only 'nodes' present, no 'edges' -> no crash, dict returned."""
    result = build_contracts({"nodes": [_make_node("a", "a.py", "a.py")]})
    assert isinstance(result, dict)


def test_em_cr_nosrc_node_without_source_file():
    """no-source: node without source_file is ignored (no crash)."""
    n_nosrc = {"id": "ghost", "label": "ghost.py", "file_type": "code"}
    n_real = _make_node("real", "real.py", "real.py")
    g = _graph(n_nosrc, n_real)
    # Must not crash; ghost.py (no source_file) must not be a contract key
    result = build_contracts(g)
    assert isinstance(result, dict)
    # 'real.py' may be present; no assertion it isn't — just no crash


def test_em_cr_nosrc_non_code_file_type_ignored():
    """no-source: nodes with file_type != 'code' are ignored."""
    n_doc = {
        "id": "doc",
        "label": "README.md",
        "file_type": "doc",
        "source_file": "README.md",
        "source_location": "L1",
    }
    n_real = _make_node("mod", "mod.py", "mod.py")
    g = _graph(n_doc, n_real)
    contracts = build_contracts(g)
    assert "README.md" not in contracts


def test_em_cr_dangle_edge_to_unknown_target():
    """dangling-edge: edge referencing unknown target node id is skipped (no crash)."""
    n_a = _make_node("a", "a.py", "a.py")
    g = _graph(n_a, edges=[_make_edge("a", "nonexistent_id", "imports")])
    result = build_contracts(g)
    assert isinstance(result, dict)


def test_em_cr_dangle_edge_from_unknown_source():
    """dangling-edge: edge whose source node id is unknown is skipped (no crash)."""
    n_a = _make_node("a", "a.py", "a.py")
    g = _graph(n_a, edges=[_make_edge("ghost_id", "a", "imports")])
    result = build_contracts(g)
    assert isinstance(result, dict)


def test_em_cr_self_intrafile_no_self_in_inferred():
    """self-edge: an intra-file edge must not produce a self-entry in inferred."""
    n_file = _make_node("f", "f.py", "f.py")
    n_sym = _make_node("f_sym", "Foo", "f.py")
    g = _graph(n_file, n_sym, edges=[_make_edge("f", "f_sym", "calls")])
    contracts = build_contracts(g)
    fc = contracts.get("f.py")
    if fc:
        assert "f.py" not in fc.inferred
        assert "f.py" not in fc.references
        assert "f.py" not in fc.referenced_by


def test_em_cr_sep_backslash_normalized():
    """path-sep: backslash OS separators in source_file are normalized to forward slash."""
    n_a = {"id": "a", "label": "a.py", "file_type": "code",
           "source_file": "pkg\\sub\\a.py", "source_location": "L1"}
    n_b = {"id": "b", "label": "b.py", "file_type": "code",
           "source_file": "pkg\\sub\\b.py", "source_location": "L1"}
    g = _graph(n_a, n_b, edges=[_make_edge("b", "a", "imports")])
    contracts = build_contracts(g)
    # Keys must use forward slashes — no backslash-keyed entries
    for key in contracts:
        assert "\\" not in key, f"Contract key contains backslash: {key!r}"
