"""Functional acceptance tests for the contract renderer.

Covers Acceptance Criterion the render_primer contract and adjacent
error modes using synthetic in-memory fixtures.

No real graph.json required, no live API calls, no src/ internals accessed.
exercises the public contract of backend.contracts.render_primer only.

Contract reference: render_primer's docstring
and §Acceptance Criteria .
"""

from __future__ import annotations

import pytest

from backend.contracts import (
    FileContract,
    build_contracts,
    render_primer,
)


# ---------------------------------------------------------------------------
# Shared fixture helpers
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


def _two_file_contracts() -> dict[str, FileContract]:
    """a/mod.py imports a/util.py; mod.py defines MyClass."""
    n_util = _make_node("util", "util.py", "a/util.py")
    n_mod = _make_node("mod", "mod.py", "a/mod.py")
    n_cls = _make_node("mod_cls", "MyClass", "a/mod.py")
    edges = [
        _make_edge("mod", "util", "imports"),
        _make_edge("mod", "mod_cls", "contains"),
    ]
    return build_contracts(_graph(n_util, n_mod, n_cls, edges=edges))


def _subtree_fixture() -> dict[str, FileContract]:
    """Three files: x/y/a.py, x/y/b.py, x/z/c.py.  a.py imports c.py (cross-subtree)."""
    n_a = _make_node("a", "a.py", "x/y/a.py")
    n_b = _make_node("b", "b.py", "x/y/b.py")
    n_c = _make_node("c", "c.py", "x/z/c.py")
    edges = [_make_edge("a", "c", "imports")]
    return build_contracts(_graph(n_a, n_b, n_c, edges=edges))


# ---------------------------------------------------------------------------
# Basic API shape
# ---------------------------------------------------------------------------

def test_render_primer_returns_string():
    """render_primer must return a str."""
    result = render_primer(_two_file_contracts())
    assert isinstance(result, str)


def test_render_primer_empty_contracts_no_crash():
    """render_primer({}) must not crash and must return a str."""
    result = render_primer({})
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Section structure
# ---------------------------------------------------------------------------

def test_render_primer_has_main_heading():
    """Output must contain '# Derived contracts —' as the top-level heading."""
    result = render_primer(_two_file_contracts())
    assert "# Derived contracts —" in result


def test_render_primer_has_dependency_map_section():
    """Output must contain '## Dependency map' section header."""
    result = render_primer(_two_file_contracts())
    assert "## Dependency map" in result


def test_render_primer_has_file_contracts_section():
    """Output must contain '## File contracts' section header."""
    result = render_primer(_two_file_contracts())
    assert "## File contracts" in result


def test_render_primer_has_blockquote_preamble():
    """Output must include a blockquote preamble line starting with '>'."""
    result = render_primer(_two_file_contracts())
    lines = result.splitlines()
    assert any(line.startswith(">") for line in lines), (
        "Expected at least one blockquote line (starting with '>') in primer"
    )


# ---------------------------------------------------------------------------
# IN n / OUT m header present in both sections
# ---------------------------------------------------------------------------

def test_ac7_dep_map_contains_in_out_counts():
    """dependency map section includes 'IN <n> / OUT <m>' for each file."""
    result = render_primer(_two_file_contracts())
    assert "IN " in result and "/ OUT " in result


def test_ac7_file_contracts_has_in_out_headings():
    """file contracts section uses '### `<file>` — IN <n> / OUT <m>' headings."""
    result = render_primer(_two_file_contracts())
    lines = result.splitlines()
    h3_with_in_out = [
        l for l in lines
        if l.startswith("###") and "IN " in l and "/ OUT " in l
    ]
    assert h3_with_in_out, (
        "No '### `<file>` — IN n / OUT m' headings found in ## File contracts"
    )


def test_ac7_in_count_value_correct():
    """IN count in the rendered output equals len(referenced_by) for that file."""
    # a.py is imported by b.py and c.py → IN 2
    n_a = _make_node("a", "a.py", "a.py")
    n_b = _make_node("b", "b.py", "b.py")
    n_c = _make_node("c", "c.py", "c.py")
    edges = [_make_edge("b", "a", "imports"), _make_edge("c", "a", "imports")]
    contracts = build_contracts(_graph(n_a, n_b, n_c, edges=edges))
    result = render_primer(contracts)
    assert "IN 2" in result, f"Expected 'IN 2' in output for a.py (IN=2); got output:\n{result}"


def test_ac7_out_count_value_correct():
    """OUT count in the rendered output equals len(references) for that file."""
    # a.py imports b.py and c.py → OUT 2
    n_a = _make_node("a", "a.py", "a.py")
    n_b = _make_node("b", "b.py", "b.py")
    n_c = _make_node("c", "c.py", "c.py")
    edges = [_make_edge("a", "b", "imports"), _make_edge("a", "c", "imports")]
    contracts = build_contracts(_graph(n_a, n_b, n_c, edges=edges))
    result = render_primer(contracts)
    assert "OUT 2" in result, f"Expected 'OUT 2' in output for a.py (OUT=2); got output:\n{result}"


# ---------------------------------------------------------------------------
# byte-identical determinism across two calls
# ---------------------------------------------------------------------------

def test_ac7_byte_identical_no_subtree():
    """render_primer(contracts) is byte-identical on two consecutive calls."""
    contracts = _two_file_contracts()
    assert render_primer(contracts) == render_primer(contracts)


def test_ac7_byte_identical_with_subtree():
    """render_primer(contracts, subtree=...) is byte-identical on two consecutive calls."""
    contracts = _subtree_fixture()
    r1 = render_primer(contracts, subtree="x/y")
    r2 = render_primer(contracts, subtree="x/y")
    assert r1 == r2


# ---------------------------------------------------------------------------
# subtree filtering
# ---------------------------------------------------------------------------

def test_ac7_subtree_restricts_file_contract_cards():
    """with subtree='x/y', contract cards exist only for files under x/y."""
    contracts = _subtree_fixture()
    result = render_primer(contracts, subtree="x/y")
    # x/z/c.py must NOT have a card
    assert "### `x/z/c.py`" not in result
    # x/y/a.py and x/y/b.py must each appear
    assert "x/y/a.py" in result
    assert "x/y/b.py" in result


def test_ac7_subtree_cross_subtree_refs_in_card_body():
    """a cross-subtree reference path still appears in the card body text."""
    contracts = _subtree_fixture()
    result = render_primer(contracts, subtree="x/y")
    # x/y/a.py references x/z/c.py; that path must appear in the body even
    # though x/z/c.py has no card of its own under subtree=x/y
    assert "x/z/c.py" in result


def test_ac7_subtree_title_in_heading():
    """the subtree string appears in the # Derived contracts heading."""
    contracts = _subtree_fixture()
    result = render_primer(contracts, subtree="x/y")
    first_line = result.splitlines()[0]
    assert "x/y" in first_line, (
        f"Expected subtree 'x/y' in heading line, got: {first_line!r}"
    )


def test_ac7_no_subtree_all_files_get_cards():
    """when subtree is None, every file in contracts gets a file-contract card."""
    contracts = _subtree_fixture()
    result = render_primer(contracts)
    for file_path in contracts:
        assert file_path in result, f"Expected {file_path!r} in primer output (no subtree)"


def test_ac7_unmatched_subtree_no_file_cards():
    """a subtree matching no files produces no '### `...' card headings."""
    contracts = _subtree_fixture()
    result = render_primer(contracts, subtree="does/not/exist")
    h3_card_lines = [l for l in result.splitlines() if l.startswith("### `")]
    assert h3_card_lines == [], (
        f"Expected no file contract cards for non-matching subtree, found: {h3_card_lines}"
    )


# ---------------------------------------------------------------------------
# field rendering — defines, references, referenced_by, inferred
# ---------------------------------------------------------------------------

def test_ac7_defines_field_lists_signatures():
    """file contract card includes 'defines:' with the file's signatures."""
    n_mod = _make_node("mod", "mod.py", "mod.py")
    n_cls = _make_node("mod_cls", "MyClass", "mod.py")
    contracts = build_contracts(
        _graph(n_mod, n_cls, edges=[_make_edge("mod", "mod_cls", "contains")])
    )
    result = render_primer(contracts)
    assert "defines" in result
    assert "MyClass" in result


def test_ac7_empty_refs_render_as_dash():
    """a file with no references/referenced_by renders '—' (em-dash), not empty."""
    n_lone = _make_node("lone", "lone.py", "lone.py")
    contracts = build_contracts(_graph(n_lone))
    result = render_primer(contracts)
    assert "—" in result, (
        "Expected em-dash '—' for empty reference fields; not found in output"
    )


def test_ac7_inferred_field_label():
    """file contract card uses the 'inferred (verify)' label for low-trust neighbours."""
    n_a = _make_node("a", "a.py", "a.py")
    n_b = _make_node("b", "b.py", "b.py")
    # 'calls' is an INFERRED_RELATIONS member → inferred bucket
    contracts = build_contracts(
        _graph(n_a, n_b, edges=[_make_edge("a", "b", "calls", "EXTRACTED")])
    )
    result = render_primer(contracts)
    assert "inferred (verify)" in result, (
        "Expected 'inferred (verify)' label in file contract card"
    )


# ---------------------------------------------------------------------------
# sorted output
# ---------------------------------------------------------------------------

def test_ac7_dependency_map_files_sorted():
    """files appear in sorted order within the dependency map."""
    n_z = _make_node("z", "z.py", "z.py")
    n_a = _make_node("a", "a.py", "a.py")
    n_m = _make_node("m", "m.py", "m.py")
    contracts = build_contracts(_graph(n_z, n_a, n_m))
    result = render_primer(contracts)
    pos_a = result.find("a.py")
    pos_m = result.find("m.py")
    pos_z = result.find("z.py")
    assert pos_a < pos_m < pos_z, (
        "Files in dependency map must appear in sorted (alphabetical) order"
    )


def test_ac7_file_contracts_headings_sorted():
    """### headings in File contracts appear in sorted file-path order."""
    n_z = _make_node("z", "z.py", "z.py")
    n_a = _make_node("a", "a.py", "a.py")
    n_m = _make_node("m", "m.py", "m.py")
    contracts = build_contracts(_graph(n_z, n_a, n_m))
    result = render_primer(contracts)
    h3_lines = [l for l in result.splitlines() if l.startswith("### `")]
    paths = []
    for line in h3_lines:
        start = line.index("`") + 1
        end = line.index("`", start)
        paths.append(line[start:end])
    assert paths == sorted(paths), (
        f"File contract headings not in sorted order: {paths}"
    )


# ---------------------------------------------------------------------------
# title line
# ---------------------------------------------------------------------------

def test_ac7_title_no_subtree_contains_repo():
    """when subtree is None, heading says 'repo'."""
    result = render_primer(_two_file_contracts())
    first_line = result.splitlines()[0]
    assert "repo" in first_line.lower(), (
        f"Expected 'repo' in heading when subtree=None, got: {first_line!r}"
    )


def test_ac7_title_with_subtree_contains_subtree_value():
    """when subtree is given, heading contains that subtree string."""
    contracts = _subtree_fixture()
    result = render_primer(contracts, subtree="x/y")
    first_line = result.splitlines()[0]
    assert "x/y" in first_line, (
        f"Expected subtree 'x/y' in heading, got: {first_line!r}"
    )
