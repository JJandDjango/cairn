"""Unit tests for backend.contracts — contract renderer.

All tests use synthetic in-memory graph dicts; no real ``graph.json``, no
graphify subprocess, no live API. A single ``@pytest.mark.slow`` real-graph
regression test lives at the bottom and is skipped when the graph is
absent.

Acceptance criteria covered:
  AC-1  empty / missing-key graph → {}
  AC-2  EXTRACTED DEP_RELATIONS → references / referenced_by
  AC-3  EXTRACTED uses + INFERRED edges → inferred, absent from trustable refs
  AC-4  signatures from contains targets; externals NOT in signatures
  AC-5  determinism — sorted, deduped tuples; two calls yield equal dicts
  AC-6  intra-file edges → no self-reference
"""
from __future__ import annotations

import json

import pytest

from backend.contracts import (
    DEP_RELATIONS,
    INFERRED_RELATIONS,
    FileContract,
    build_contracts,
    build_contracts_from_graph_json,
    render_primer,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _node(nid: str, label: str, sf: str, file_type: str | None = "code") -> dict:
    """Minimal code node."""
    n: dict = {
        "id": nid,
        "label": label,
        "source_file": sf,
        "source_location": "L1",
    }
    if file_type is not None:
        n["file_type"] = file_type
    return n


def _edge(
    src: str,
    tgt: str,
    relation: str,
    confidence: str = "EXTRACTED",
    score: float | None = None,
) -> dict:
    return {
        "source": src,
        "target": tgt,
        "relation": relation,
        "confidence": confidence,
        "confidence_score": (
            score if score is not None else (1.0 if confidence == "EXTRACTED" else 0.5)
        ),
    }


def _graph(nodes: list[dict], edges: list[dict] | None = None) -> dict:
    return {"nodes": nodes, "edges": list(edges or [])}


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_dep_relations_contents(self):
        assert DEP_RELATIONS == frozenset(
            {"imports", "imports_from", "re_exports", "inherits"}
        )

    def test_inferred_relations_contents(self):
        assert INFERRED_RELATIONS == frozenset({"calls", "uses"})

    def test_dep_and_inferred_disjoint(self):
        assert not (DEP_RELATIONS & INFERRED_RELATIONS)


# ---------------------------------------------------------------------------
# AC-1: empty / missing-key graph → {}
# ---------------------------------------------------------------------------


class TestEmptyGraph:
    def test_empty_nodes_and_edges(self):
        """AC-1: build_contracts({"nodes": [], "edges": []}) returns {}."""
        assert build_contracts({"nodes": [], "edges": []}) == {}

    def test_missing_nodes_key(self):
        """empty-graph: missing 'nodes' key — treat as empty, no crash."""
        assert build_contracts({"edges": []}) == {}

    def test_missing_both_keys(self):
        """empty-graph: empty dict — treat as empty, no crash."""
        assert build_contracts({}) == {}

    def test_none_values(self):
        """None nodes/edges — treat as empty, no crash."""
        assert build_contracts({"nodes": None, "edges": None}) == {}

    def test_no_code_nodes(self):
        """Nodes with non-code file extension and absent file_type → {}."""
        nodes = [_node("a", "README", "README.md", file_type=None)]
        assert build_contracts(_graph(nodes)) == {}

    def test_non_code_file_type_ignored(self):
        """Nodes with file_type != 'code' (e.g. 'doc') are ignored."""
        nodes = [_node("a", "MAP", "MAP.md", file_type="doc")]
        assert build_contracts(_graph(nodes)) == {}


# ---------------------------------------------------------------------------
# AC-2: EXTRACTED DEP_RELATIONS → references / referenced_by
# ---------------------------------------------------------------------------


class TestExtractedImports:
    def test_simple_import(self):
        """AC-2: b.py imports a.py → a.py.referenced_by==(b.py,), b.py.references==(a.py,)."""
        nodes = [_node("a", "a", "a.py"), _node("b", "b", "b.py")]
        contracts = build_contracts(_graph(nodes, [_edge("b", "a", "imports")]))
        assert contracts["a.py"].referenced_by == ("b.py",)
        assert contracts["a.py"].references == ()
        assert contracts["b.py"].references == ("a.py",)
        assert contracts["b.py"].referenced_by == ()

    def test_two_importers_sorted(self):
        """AC-2: b.py and c.py both import a.py → a.py.referenced_by == ('b.py', 'c.py')."""
        nodes = [
            _node("a", "a", "a.py"),
            _node("b", "b", "b.py"),
            _node("c", "c", "c.py"),
        ]
        edges = [_edge("b", "a", "imports"), _edge("c", "a", "imports")]
        contracts = build_contracts(_graph(nodes, edges))
        assert contracts["a.py"].referenced_by == ("b.py", "c.py")
        assert contracts["a.py"].references == ()

    def test_imports_from_is_dep(self):
        """imports_from is in DEP_RELATIONS — produces references/referenced_by."""
        nodes = [_node("a", "a", "a.py"), _node("b", "b", "b.py")]
        contracts = build_contracts(_graph(nodes, [_edge("b", "a", "imports_from")]))
        assert contracts["a.py"].referenced_by == ("b.py",)

    def test_inherits_is_dep(self):
        """inherits is in DEP_RELATIONS — produces references/referenced_by."""
        nodes = [_node("a", "a", "a.py"), _node("b", "b", "b.py")]
        contracts = build_contracts(_graph(nodes, [_edge("b", "a", "inherits")]))
        assert contracts["a.py"].referenced_by == ("b.py",)

    def test_re_exports_is_dep(self):
        """re_exports is in DEP_RELATIONS — produces references/referenced_by."""
        nodes = [_node("a", "a", "a.py"), _node("b", "b", "b.py")]
        contracts = build_contracts(_graph(nodes, [_edge("b", "a", "re_exports")]))
        assert contracts["a.py"].referenced_by == ("b.py",)

    def test_inferred_import_not_in_references(self):
        """INFERRED confidence on 'imports' → goes to inferred, NOT references."""
        nodes = [_node("a", "a", "a.py"), _node("b", "b", "b.py")]
        contracts = build_contracts(
            _graph(nodes, [_edge("b", "a", "imports", confidence="INFERRED")])
        )
        assert contracts["a.py"].referenced_by == ()
        assert "b.py" in contracts["a.py"].inferred

    def test_inferred_not_in_references(self):
        """An edge with confidence INFERRED never lands in references regardless of relation."""
        nodes = [_node("x", "x", "x.py"), _node("y", "y", "y.py")]
        contracts = build_contracts(
            _graph(nodes, [_edge("x", "y", "inherits", confidence="INFERRED")])
        )
        assert contracts["y.py"].referenced_by == ()
        assert "y.py" in contracts["x.py"].inferred


# ---------------------------------------------------------------------------
# AC-3: uses / INFERRED edges → inferred, absent from trustable refs
# ---------------------------------------------------------------------------


class TestInferredEdges:
    def test_extracted_uses_goes_to_inferred(self):
        """AC-3: EXTRACTED 'uses' → inferred (not references/referenced_by)."""
        nodes = [_node("a", "a", "a.py"), _node("c", "c", "c.py")]
        contracts = build_contracts(
            _graph(nodes, [_edge("c", "a", "uses", confidence="EXTRACTED")])
        )
        assert "c.py" in contracts["a.py"].inferred
        assert contracts["a.py"].referenced_by == ()
        assert "a.py" in contracts["c.py"].inferred
        assert contracts["c.py"].references == ()

    def test_calls_goes_to_inferred(self):
        """'calls' is in INFERRED_RELATIONS → inferred (both directions)."""
        nodes = [_node("a", "a", "a.py"), _node("c", "c", "c.py")]
        contracts = build_contracts(
            _graph(nodes, [_edge("c", "a", "calls", confidence="EXTRACTED")])
        )
        assert "a.py" in contracts["c.py"].inferred
        assert "c.py" in contracts["a.py"].inferred

    def test_inferred_confidence_edge_goes_to_inferred(self):
        """AC-3: confidence=='INFERRED' on any relation → inferred."""
        nodes = [_node("a", "a", "a.py"), _node("c", "c", "c.py")]
        contracts = build_contracts(
            _graph(nodes, [_edge("c", "a", "imports", confidence="INFERRED")])
        )
        assert "c.py" in contracts["a.py"].inferred
        assert contracts["a.py"].referenced_by == ()

    def test_trustable_pair_excluded_from_inferred(self):
        """AC-3 + step 4: trustable edge means the pair never also appears in inferred."""
        nodes = [_node("a", "a", "a.py"), _node("c", "c", "c.py")]
        edges = [
            _edge("c", "a", "imports", confidence="EXTRACTED"),   # trustable
            _edge("c", "a", "uses", confidence="EXTRACTED"),      # would go to inferred → excluded
        ]
        contracts = build_contracts(_graph(nodes, edges))
        assert contracts["a.py"].referenced_by == ("c.py",)
        # 'a.py' is already trustable for c.py → NOT in c.py.inferred
        assert "a.py" not in contracts["c.py"].inferred
        # 'c.py' is already trustable for a.py → NOT in a.py.inferred
        assert "c.py" not in contracts["a.py"].inferred

    def test_inferred_not_in_referenced_by(self):
        """AC-3: inferred edge doesn't leak into referenced_by."""
        nodes = [_node("a", "a", "a.py"), _node("b", "b", "b.py")]
        contracts = build_contracts(
            _graph(nodes, [_edge("b", "a", "calls", confidence="EXTRACTED")])
        )
        assert contracts["a.py"].referenced_by == ()

    def test_inferred_symmetric(self):
        """Inferred is symmetric: both a and b appear in each other's inferred."""
        nodes = [_node("a", "a", "a.py"), _node("b", "b", "b.py")]
        contracts = build_contracts(
            _graph(nodes, [_edge("a", "b", "uses", confidence="EXTRACTED")])
        )
        assert "b.py" in contracts["a.py"].inferred
        assert "a.py" in contracts["b.py"].inferred


# ---------------------------------------------------------------------------
# AC-4: signatures from contains targets; externals absent
# ---------------------------------------------------------------------------


class TestSignatures:
    def test_signatures_from_contains_targets(self):
        """AC-4: signatures = sorted labels of the file node's contains targets."""
        file_node = _node("fn_a", "a.py", "a.py")   # label == basename
        sym_linter = _node("sym_Linter", "Linter", "a.py")
        sym_check = _node("sym_LintCheck", "LintCheck", "a.py")
        nodes = [file_node, sym_linter, sym_check]
        edges = [
            _edge("fn_a", "sym_Linter", "contains"),
            _edge("fn_a", "sym_LintCheck", "contains"),
        ]
        contracts = build_contracts(_graph(nodes, edges))
        assert contracts["a.py"].signatures == ("LintCheck", "Linter")  # sorted

    def test_external_via_uses_not_in_signatures(self):
        """AC-4: a symbol reachable only via uses/references edge is absent from signatures."""
        file_node = _node("fn_a", "a.py", "a.py")
        path_node = _node("path_node", "Path", "pathlib.py")
        nodes = [file_node, path_node]
        edges = [_edge("fn_a", "path_node", "uses")]  # uses, not contains
        contracts = build_contracts(_graph(nodes, edges))
        assert "Path" not in contracts["a.py"].signatures

    def test_signatures_empty_when_no_contains(self):
        """File with no contains edges has empty signatures tuple."""
        nodes = [_node("a", "a", "a.py")]
        contracts = build_contracts(_graph(nodes))
        assert contracts["a.py"].signatures == ()

    def test_signatures_deduplicated(self):
        """Duplicate labels in contains targets appear exactly once."""
        file_node = _node("fn_a", "a.py", "a.py")
        sym1 = _node("sym1", "MyClass", "a.py")
        sym2 = _node("sym2", "MyClass", "a.py")  # same label
        nodes = [file_node, sym1, sym2]
        edges = [
            _edge("fn_a", "sym1", "contains"),
            _edge("fn_a", "sym2", "contains"),
        ]
        contracts = build_contracts(_graph(nodes, edges))
        assert contracts["a.py"].signatures.count("MyClass") == 1

    def test_noise_label_long_excluded(self):
        """Labels with len >= 40 are filtered out (noise filter)."""
        file_node = _node("fn_a", "a.py", "a.py")
        sym_long = _node("sym_long", "A" * 40, "a.py")  # 40 chars — excluded (< 40 is False)
        sym_ok = _node("sym_ok", "GoodSymbol", "a.py")
        nodes = [file_node, sym_long, sym_ok]
        edges = [
            _edge("fn_a", "sym_long", "contains"),
            _edge("fn_a", "sym_ok", "contains"),
        ]
        contracts = build_contracts(_graph(nodes, edges))
        assert "A" * 40 not in contracts["a.py"].signatures
        assert "GoodSymbol" in contracts["a.py"].signatures

    def test_noise_label_newline_excluded(self):
        """Labels with a newline are filtered out (noise filter)."""
        file_node = _node("fn_a", "a.py", "a.py")
        sym_nl = _node("sym_nl", "foo\nbar", "a.py")
        sym_ok = _node("sym_ok", "FooBar", "a.py")
        nodes = [file_node, sym_nl, sym_ok]
        edges = [
            _edge("fn_a", "sym_nl", "contains"),
            _edge("fn_a", "sym_ok", "contains"),
        ]
        contracts = build_contracts(_graph(nodes, edges))
        assert "foo\nbar" not in contracts["a.py"].signatures
        assert "FooBar" in contracts["a.py"].signatures

    def test_signatures_sorted(self):
        """Signatures are sorted alphabetically (deterministic order)."""
        file_node = _node("fn_a", "a.py", "a.py")
        syms = [_node(f"s{i}", name, "a.py") for i, name in enumerate(["Zebra", "Apple", "Mango"])]
        nodes = [file_node] + syms
        edges = [_edge("fn_a", f"s{i}", "contains") for i in range(3)]
        contracts = build_contracts(_graph(nodes, edges))
        assert list(contracts["a.py"].signatures) == sorted(["Zebra", "Apple", "Mango"])

    def test_contains_target_in_other_file_not_in_signatures(self):
        """contains edge pointing to a node in a different file: that target's
        label is only added to the file that owns the file node."""
        fn_a = _node("fn_a", "a.py", "a.py")
        sym_b = _node("sym_b", "BSymbol", "b.py")
        nodes = [fn_a, sym_b]
        # fn_a (in a.py) has a contains edge to sym_b (in b.py)
        # Since sym_b is the target and is a cross-file symbol, the target node
        # label goes into a.py's signatures (it is a contains target of fn_a)
        edges = [_edge("fn_a", "sym_b", "contains")]
        contracts = build_contracts(_graph(nodes, edges))
        # The label "BSymbol" was added to a.py's signatures because fn_a is a.py's file node
        assert "BSymbol" in contracts["a.py"].signatures


# ---------------------------------------------------------------------------
# AC-5: determinism — sorted, deduped tuples; two calls equal
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_two_calls_same_input_equal(self):
        """AC-5: build_contracts is pure — two calls on the same graph yield equal dicts."""
        nodes = [
            _node("a", "a", "a.py"),
            _node("b", "b", "b.py"),
            _node("c", "c", "c.py"),
        ]
        edges = [
            _edge("b", "a", "imports"),
            _edge("c", "a", "uses", confidence="EXTRACTED"),
        ]
        g = _graph(nodes, edges)
        assert build_contracts(g) == build_contracts(g)

    def test_referenced_by_is_sorted(self):
        """AC-5: referenced_by sorted ascending even if edges arrived in reverse order."""
        nodes = [
            _node("a", "a", "a.py"),
            _node("z", "z", "z.py"),
            _node("b", "b", "b.py"),
        ]
        # Insert z first, then b — referenced_by should still be ('b.py', 'z.py')
        edges = [_edge("z", "a", "imports"), _edge("b", "a", "imports")]
        contracts = build_contracts(_graph(nodes, edges))
        assert contracts["a.py"].referenced_by == ("b.py", "z.py")

    def test_duplicate_edges_deduped(self):
        """AC-5: duplicate edges produce deduplicated tuples."""
        nodes = [_node("a", "a", "a.py"), _node("b", "b", "b.py")]
        # Same edge twice — should still appear once
        edges = [_edge("b", "a", "imports"), _edge("b", "a", "imports")]
        contracts = build_contracts(_graph(nodes, edges))
        assert contracts["a.py"].referenced_by.count("b.py") == 1


# ---------------------------------------------------------------------------
# AC-6: intra-file edges → no self-reference
# ---------------------------------------------------------------------------


class TestIntraFile:
    def test_intra_file_calls_no_self_ref(self):
        """AC-6: calls edge between nodes in the same file → no self-ref in any field."""
        fn_a = _node("fn_a", "a.py", "a.py")
        sym1 = _node("sym1", "FuncA", "a.py")
        sym2 = _node("sym2", "FuncB", "a.py")
        nodes = [fn_a, sym1, sym2]
        # sym1 calls sym2, both in a.py → intra-file
        edges = [_edge("sym1", "sym2", "calls")]
        contracts = build_contracts(_graph(nodes, edges))
        fc = contracts["a.py"]
        assert fc.references == ()
        assert fc.referenced_by == ()
        assert fc.inferred == ()  # no self-ref in inferred either

    def test_intra_file_imports_no_self_ref(self):
        """AC-6: EXTRACTED imports edge within same file → skipped."""
        fn_a = _node("fn_a", "a.py", "a.py")
        sym1 = _node("sym1", "A", "a.py")
        sym2 = _node("sym2", "B", "a.py")
        nodes = [fn_a, sym1, sym2]
        edges = [_edge("sym1", "sym2", "imports", confidence="EXTRACTED")]
        contracts = build_contracts(_graph(nodes, edges))
        fc = contracts["a.py"]
        assert fc.references == ()
        assert fc.referenced_by == ()

    def test_cross_file_edge_with_intra_file_present(self):
        """AC-6: mixed intra + cross-file — only cross-file edges produce refs."""
        fn_a = _node("fn_a", "a.py", "a.py")
        sym_a = _node("sym_a", "A", "a.py")
        sym_a2 = _node("sym_a2", "A2", "a.py")
        fn_b = _node("fn_b", "b.py", "b.py")
        nodes = [fn_a, sym_a, sym_a2, fn_b]
        edges = [
            _edge("sym_a", "sym_a2", "calls"),   # intra-file — skip
            _edge("fn_b", "fn_a", "imports"),     # cross-file — keep
        ]
        contracts = build_contracts(_graph(nodes, edges))
        assert contracts["a.py"].referenced_by == ("b.py",)
        assert contracts["a.py"].inferred == ()   # intra-file calls skipped


# ---------------------------------------------------------------------------
# dangling-edge: dangling edges (unknown node id) → skipped
# ---------------------------------------------------------------------------


class TestDanglingEdges:
    def test_unknown_source_id_skipped(self):
        """dangling-edge: edge with source id not in nodes → skipped, no crash."""
        nodes = [_node("a", "a", "a.py")]
        edges = [_edge("GHOST", "a", "imports")]
        contracts = build_contracts(_graph(nodes, edges))
        assert contracts["a.py"].referenced_by == ()

    def test_unknown_target_id_skipped(self):
        """dangling-edge: edge with target id not in nodes → skipped."""
        nodes = [_node("a", "a", "a.py")]
        edges = [_edge("a", "GHOST", "imports")]
        contracts = build_contracts(_graph(nodes, edges))
        assert contracts["a.py"].references == ()

    def test_non_code_node_acts_as_dangling(self):
        """no-source: node with non-code extension absent from node_file → edge skipped."""
        n_doc = _node("doc1", "README", "README.md", file_type=None)
        n_code = _node("code1", "x", "x.py")
        nodes = [n_doc, n_code]
        # edge from doc node to code node → doc node not in node_file → dangling
        edges = [_edge("doc1", "code1", "imports")]
        contracts = build_contracts(_graph(nodes, edges))
        assert "README.md" not in contracts
        assert "x.py" in contracts
        assert contracts["x.py"].referenced_by == ()


# ---------------------------------------------------------------------------
# path-sep: OS-native path separators normalized
# ---------------------------------------------------------------------------


class TestOSSeparators:
    def test_backslash_normalized_to_forward_slash(self):
        """path-sep: source_file with backslashes is normalized to forward slashes."""
        nodes = [
            _node("a", "a.py", "src\\lint\\a.py"),
            _node("b", "b.py", "src\\lint\\b.py"),
        ]
        edges = [_edge("b", "a", "imports")]
        contracts = build_contracts(_graph(nodes, edges))
        assert "src/lint/a.py" in contracts
        assert "src/lint/b.py" in contracts
        assert contracts["src/lint/a.py"].referenced_by == ("src/lint/b.py",)


# ---------------------------------------------------------------------------
# FileContract dataclass
# ---------------------------------------------------------------------------


class TestFileContract:
    def test_in_count_property(self):
        fc = FileContract(
            file="a.py",
            signatures=(),
            references=("b.py", "c.py"),
            referenced_by=("d.py",),
            inferred=(),
        )
        assert fc.in_count == 1

    def test_out_count_property(self):
        fc = FileContract(
            file="a.py",
            signatures=(),
            references=("b.py", "c.py"),
            referenced_by=("d.py",),
            inferred=(),
        )
        assert fc.out_count == 2

    def test_frozen_raises_on_mutation(self):
        """FileContract is frozen (immutable after creation)."""
        fc = FileContract(
            file="a.py", signatures=(), references=(), referenced_by=(), inferred=()
        )
        with pytest.raises((AttributeError, TypeError)):
            fc.file = "b.py"  # type: ignore[misc]

    def test_in_out_zero_for_empty(self):
        fc = FileContract(
            file="a.py", signatures=(), references=(), referenced_by=(), inferred=()
        )
        assert fc.in_count == 0 and fc.out_count == 0


# ---------------------------------------------------------------------------
# build_contracts_from_graph_json — convenience wrapper
# ---------------------------------------------------------------------------


class TestBuildContractsFromGraphJson:
    def test_loads_and_builds(self, tmp_path):
        """Writes a minimal graph.json and checks the result matches build_contracts."""
        nodes = [_node("a", "a", "a.py"), _node("b", "b", "b.py")]
        edges = [_edge("b", "a", "imports")]
        graph_data = {"nodes": nodes, "edges": edges}
        p = tmp_path / "graph.json"
        p.write_text(json.dumps(graph_data), encoding="utf-8")
        contracts = build_contracts_from_graph_json(p)
        assert "a.py" in contracts
        assert contracts["a.py"].referenced_by == ("b.py",)

    def test_links_key_accepted(self, tmp_path):
        """graphify_adapter normalizes 'links' → 'edges' (NetworkX compat)."""
        nodes = [_node("a", "a", "a.py"), _node("b", "b", "b.py")]
        edges = [_edge("b", "a", "imports")]
        # Write with 'links' key (NetworkX node-link format)
        graph_data = {"nodes": nodes, "links": edges}
        p = tmp_path / "graph.json"
        p.write_text(json.dumps(graph_data), encoding="utf-8")
        contracts = build_contracts_from_graph_json(p)
        assert contracts["a.py"].referenced_by == ("b.py",)


# ---------------------------------------------------------------------------
# render_primer — deterministic markdown output
# ---------------------------------------------------------------------------


class TestRenderPrimer:
    """render_primer emits IN/OUT headers, lists refs, honours subtree, is byte-stable."""

    # ---- fixture helpers ----

    def _two_file_contracts(self) -> dict[str, FileContract]:
        """Minimal contracts: a.py (imported by b.py), b.py (imports a.py)."""
        nodes = [
            _node("fn_a", "a.py", "a.py"),
            _node("sym_Foo", "Foo", "a.py"),
            _node("fn_b", "b.py", "b.py"),
        ]
        edges = [
            _edge("fn_a", "sym_Foo", "contains"),
            _edge("fn_b", "fn_a", "imports"),
        ]
        return build_contracts(_graph(nodes, edges))

    def _subtree_contracts(self) -> dict[str, FileContract]:
        """Three files: x/y/alpha.py, x/y/beta.py, x/z/gamma.py."""
        nodes = [
            _node("alpha", "alpha.py", "x/y/alpha.py"),
            _node("beta", "beta.py", "x/y/beta.py"),
            _node("gamma", "gamma.py", "x/z/gamma.py"),
        ]
        edges = [
            _edge("beta", "alpha", "imports"),  # beta → alpha
            _edge("gamma", "beta", "imports"),  # gamma → beta (cross-subtree)
        ]
        return build_contracts(_graph(nodes, edges))

    # ---- IN n / OUT m header ----

    def test_in_out_header_present_no_subtree(self):
        """output contains 'IN n / OUT m' line for each file."""
        contracts = self._two_file_contracts()
        text = render_primer(contracts)
        # a.py is imported by b.py → IN 1 / OUT 0
        assert "IN 1 / OUT 0" in text
        # b.py imports a.py → IN 0 / OUT 1
        assert "IN 0 / OUT 1" in text

    def test_in_out_header_in_dep_map_line(self):
        """dependency map lines have '- `<file>` — IN n / OUT m' format."""
        contracts = self._two_file_contracts()
        text = render_primer(contracts)
        assert "- `a.py` — IN 1 / OUT 0" in text
        assert "- `b.py` — IN 0 / OUT 1" in text

    def test_in_out_header_in_file_contract_section(self):
        """file contract section has '### `<file>` — IN n / OUT m' format."""
        contracts = self._two_file_contracts()
        text = render_primer(contracts)
        assert "### `a.py` — IN 1 / OUT 0" in text
        assert "### `b.py` — IN 0 / OUT 1" in text

    # ---- refs listed ----

    def test_referenced_by_listed(self):
        """referenced_by paths appear in the output for a.py."""
        contracts = self._two_file_contracts()
        text = render_primer(contracts)
        # a.py is referenced_by b.py
        assert "`b.py`" in text

    def test_references_listed(self):
        """references paths appear in the output for b.py."""
        contracts = self._two_file_contracts()
        text = render_primer(contracts)
        # b.py references a.py
        assert "`a.py`" in text

    def test_defines_signature_listed(self):
        """signatures from the file node's contains targets appear under 'defines'."""
        contracts = self._two_file_contracts()
        text = render_primer(contracts)
        assert "Foo" in text  # a.py defines Foo

    def test_empty_refs_show_dash(self):
        """empty references/referenced_by/inferred shows '—'."""
        contracts = self._two_file_contracts()
        text = render_primer(contracts)
        # a.py has no references (OUT 0)
        assert "- references: —" in text

    # ---- subtree filtering ----

    def test_subtree_filters_cards(self):
        """subtree=x/y restricts file contract cards to files under x/y."""
        contracts = self._subtree_contracts()
        text = render_primer(contracts, subtree="x/y")
        # x/y files should appear
        assert "x/y/alpha.py" in text
        assert "x/y/beta.py" in text
        # x/z/gamma.py should NOT appear as a card
        assert "### `x/z/gamma.py`" not in text

    def test_subtree_cross_refs_still_listed(self):
        """cross-refs from outside the subtree are still listed as paths."""
        contracts = self._subtree_contracts()
        text = render_primer(contracts, subtree="x/y")
        # beta.py is referenced_by gamma.py (outside x/y); path should still appear
        assert "x/z/gamma.py" in text

    def test_subtree_title_in_header(self):
        """the subtree name appears in the '# Derived contracts —' heading."""
        contracts = self._subtree_contracts()
        text = render_primer(contracts, subtree="x/y")
        assert "# Derived contracts — x/y" in text

    def test_no_subtree_title_is_repo(self):
        """without subtree, the heading says 'repo'."""
        contracts = self._two_file_contracts()
        text = render_primer(contracts)
        assert "# Derived contracts — repo" in text

    def test_subtree_no_match_empty_body(self):
        """subtree that matches no files → empty dependency map + file contracts."""
        contracts = self._two_file_contracts()
        text = render_primer(contracts, subtree="nonexistent/")
        # Should still produce a valid (minimal) header
        assert "# Derived contracts — nonexistent/" in text
        # No file cards
        assert "###" not in text

    # ---- byte-stability (determinism) ----

    def test_byte_identical_two_calls(self):
        """two calls on the same contracts dict yield byte-identical strings."""
        contracts = self._two_file_contracts()
        assert render_primer(contracts) == render_primer(contracts)

    def test_byte_identical_with_subtree(self):
        """two calls with the same subtree yield byte-identical strings."""
        contracts = self._subtree_contracts()
        r1 = render_primer(contracts, subtree="x/y")
        r2 = render_primer(contracts, subtree="x/y")
        assert r1 == r2

    def test_files_sorted_in_output(self):
        """files appear sorted in the output (deterministic order)."""
        nodes = [
            _node("z", "z.py", "z.py"),
            _node("a", "a.py", "a.py"),
            _node("m", "m.py", "m.py"),
        ]
        contracts = build_contracts(_graph(nodes))
        text = render_primer(contracts)
        idx_a = text.index("a.py")
        idx_m = text.index("m.py")
        idx_z = text.index("z.py")
        assert idx_a < idx_m < idx_z

    # ---- section structure ----

    def test_required_sections_present(self):
        """output has 'Dependency map' and 'File contracts' sections."""
        contracts = self._two_file_contracts()
        text = render_primer(contracts)
        assert "## Dependency map (blast radius)" in text
        assert "## File contracts" in text

    def test_header_blockquote_present(self):
        """the standard preamble blockquote is present."""
        contracts = self._two_file_contracts()
        text = render_primer(contracts)
        assert "> 0-token, derived from graphify graph.json" in text

    def test_inferred_listed_with_verify_label(self):
        """inferred paths appear under 'inferred (verify)' label."""
        nodes = [_node("a", "a.py", "a.py"), _node("b", "b.py", "b.py")]
        edges = [_edge("b", "a", "calls", confidence="EXTRACTED")]
        contracts = build_contracts(_graph(nodes, edges))
        text = render_primer(contracts)
        assert "inferred (verify):" in text
