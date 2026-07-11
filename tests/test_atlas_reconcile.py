"""Pass 2 reconciliation-loop tests (atlas.reconcile): rollup/diff, ranking,
noise filtering, render<->parse round-trip, and the gated apply write-boundary."""
import json

from backend import reconcile, schema


def _node(nid, label, sf):
    return {"id": nid, "label": label, "source_file": sf, "file_type": "code",
            "norm_label": label, "community": "0", "source_location": "L1"}


def _write_graph(path, nodes, edges=()):
    data = {"nodes": nodes, "edges": [
        {"source": s, "target": t, "relation": "uses", "confidence": c,
         "confidence_score": 1.0 if c == "EXTRACTED" else 0.5}
        for s, t, c in edges]}
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _write_atlas(path, locations, root=None):
    comps = "".join(
        f"  - name: c{i}\n    role: r\n    level: module\n    location: {loc}\n"
        for i, loc in enumerate(locations))
    path.write_text(
        "---\natlas_schema: 1\nname: demo\npurpose: p\nstatus: active\n"
        f"components:\n{comps}---\n\n# Demo\n", encoding="utf-8")
    if root is not None:  # materialize authored locations so they aren't dangling
        for loc in locations:
            p = root / loc.rstrip("/")
            if p.suffix:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("x", encoding="utf-8")
            else:
                p.mkdir(parents=True, exist_ok=True)
    return path


def test_reconcile_proposes_uncovered_code_dir(tmp_path):
    atlas = _write_atlas(tmp_path / "ATLAS.md", ["src/core/"], root=tmp_path)
    graph = _write_graph(tmp_path / "graph.json", [
        _node("a", "core_fn()", "src/core/a.py"),
        *[_node(f"w{i}", f"Widget{i}", "src/widget/w.py") for i in range(5)]])
    new = [p for p in reconcile.reconcile(atlas, graph, tmp_path)
           if p.kind == "new_component"]
    assert [p.location for p in new] == ["src/widget/"]
    assert new[0].suggested["name"] == "widget"


def test_reconcile_filters_tests_dotdirs_and_noncode(tmp_path):
    atlas = _write_atlas(tmp_path / "ATLAS.md", ["src/core/"], root=tmp_path)
    graph = _write_graph(tmp_path / "graph.json", [
        *[_node(f"t{i}", f"T{i}", "tests/test_x.py") for i in range(9)],
        *[_node(f"d{i}", f"D{i}", ".claude/skills/s.py") for i in range(9)],
        *[_node(f"m{i}", f"H{i}", "designs/plan.md") for i in range(9)],
        *[_node(f"j{i}", f"K{i}", "agentic/schema/x.json") for i in range(9)]])
    assert [p for p in reconcile.reconcile(atlas, graph, tmp_path)
            if p.kind == "new_component"] == []


def test_reconcile_substance_first_over_confidence(tmp_path):
    atlas = _write_atlas(tmp_path / "ATLAS.md", ["src/core/"], root=tmp_path)
    big = [_node(f"b{i}", f"B{i}", "src/big/b.py") for i in range(10)]
    small = [_node(f"s{i}", f"S{i}", "src/small/s.py") for i in range(4)]
    graph = _write_graph(tmp_path / "graph.json", big + small,
                         edges=[("b0", "b1", "INFERRED"), ("s0", "s1", "EXTRACTED")])
    new = [p for p in reconcile.reconcile(atlas, graph, tmp_path)
           if p.kind == "new_component"]
    assert new[0].location == "src/big/" and new[0].confidence == "INFERRED"
    assert new[1].location == "src/small/" and new[1].confidence == "EXTRACTED"


def test_reconcile_min_nodes_threshold(tmp_path):
    atlas = _write_atlas(tmp_path / "ATLAS.md", ["src/core/"], root=tmp_path)
    graph = _write_graph(tmp_path / "graph.json", [
        _node("a", "core", "src/core/a.py"),
        _node("x", "X", "src/thin/x.py"), _node("y", "Y", "src/thin/x.py")])
    assert [p for p in reconcile.reconcile(atlas, graph, tmp_path)
            if p.kind == "new_component"] == []


def test_reconcile_flags_dangling(tmp_path):
    atlas = _write_atlas(tmp_path / "ATLAS.md", ["src/gone/"])  # not on disk
    graph = _write_graph(tmp_path / "graph.json", [])
    dangling = [p for p in reconcile.reconcile(atlas, graph, tmp_path)
                if p.kind == "dangling_component"]
    assert len(dangling) == 1 and "src/gone" in dangling[0].location


def test_render_unchecked_parses_empty(tmp_path):
    p = reconcile.Proposal(kind="new_component", location="src/widget/",
                           node_count=5, confidence="EXTRACTED",
                           suggested={"name": "widget", "role": "r", "level": "module"})
    md = reconcile.render([p], tmp_path / "proposals.md", name="demo")
    assert reconcile.parse(md) == []


def test_render_parse_roundtrip_checked(tmp_path):
    p = reconcile.Proposal(kind="new_component", location="src/widget/",
                           node_count=5, confidence="EXTRACTED", symbols=["Widget"],
                           suggested={"name": "widget", "role": "Does things.",
                                      "level": "module", "location": "src/widget/"})
    md = reconcile.render([p], tmp_path / "proposals.md", name="demo")
    md.write_text(md.read_text(encoding="utf-8").replace(
        "- [ ] **src/widget/**", "- [x] **src/widget/**"), encoding="utf-8")
    checked = reconcile.parse(md)
    assert len(checked) == 1
    assert checked[0]["location"] == "src/widget/"
    assert checked[0]["fields"]["name"] == "widget"
    assert checked[0]["fields"]["role"] == "Does things."
    assert checked[0]["dangling"] is False


def test_apply_adds_checked_component(tmp_path):
    atlas = _write_atlas(tmp_path / "ATLAS.md", ["src/core/"], root=tmp_path)
    proposals = tmp_path / "proposals.md"
    proposals.write_text(
        "## New components (1)\n\n"
        "- [x] **src/widget/** · 5 nodes · EXTRACTED\n"
        "  - name: `widget`\n  - role: `Does widget things.`\n"
        "  - level: `module`\n\n## Dangling components (0)\n\n_none_\n",
        encoding="utf-8")
    res = reconcile.apply(atlas, proposals)
    assert res["written"] and res["added"] == ["widget"]
    fm, _ = schema.parse(atlas)
    assert schema.validate(fm) == []
    w = next(c for c in fm["components"] if c["name"] == "widget")
    assert w["role"] == "Does widget things." and w["location"] == "src/widget/"


def test_apply_no_write_on_invalid(tmp_path):
    atlas = _write_atlas(tmp_path / "ATLAS.md", ["src/gone/"])
    before = atlas.read_text(encoding="utf-8")
    proposals = tmp_path / "proposals.md"
    proposals.write_text(
        "## New components (0)\n\n_none_\n\n## Dangling components (1)\n\n"
        "- [x] **src/gone/** — authored component `c0` no longer on disk\n",
        encoding="utf-8")
    res = reconcile.apply(atlas, proposals)
    assert res["written"] is False and res["errors"]
    assert atlas.read_text(encoding="utf-8") == before  # untouched on invalid


def test_apply_nothing_checked_is_noop(tmp_path):
    atlas = _write_atlas(tmp_path / "ATLAS.md", ["src/core/"], root=tmp_path)
    proposals = tmp_path / "proposals.md"
    proposals.write_text(
        "## New components (1)\n\n"
        "- [ ] **src/widget/** · 5 nodes · EXTRACTED\n"
        "  - name: `widget`\n\n## Dangling components (0)\n\n_none_\n",
        encoding="utf-8")
    res = reconcile.apply(atlas, proposals)
    assert res["written"] and res["added"] == [] and res["removed"] == []
    fm, _ = schema.parse(atlas)
    assert [c["name"] for c in fm["components"]] == ["c0"]


# ---- derive-first staging ---------------------------------------------------

def test_reconcile_empty_model_proposes_all(tmp_path):
    graph = _write_graph(tmp_path / "graph.json",
                         [_node(f"a{i}", f"A{i}", "src/alpha/a.py") for i in range(4)])
    props = reconcile.reconcile(None, graph, tmp_path)
    assert [p.location for p in props if p.kind == "new_component"] == ["src/alpha/"]
    assert [p for p in props if p.kind == "dangling_component"] == []


def test_stage_draft_builds_valid_candidate(tmp_path):
    graph = _write_graph(tmp_path / "graph.json", [
        *[_node(f"a{i}", f"A{i}", "src/alpha/a.py") for i in range(4)],
        *[_node(f"b{i}", f"B{i}", "src/beta/b.py") for i in range(4)]])
    draft = reconcile.stage_draft(graph, tmp_path, name="demo")
    fm, _ = schema.split_frontmatter(draft)
    assert schema.validate(fm) == []
    assert fm["name"] == "demo"
    assert {c["location"] for c in fm["components"]} == {"src/alpha/", "src/beta/"}


def test_accept_draft_writes_atlas(tmp_path):
    graph = _write_graph(tmp_path / "graph.json",
                         [_node(f"a{i}", f"A{i}", "src/alpha/a.py") for i in range(4)])
    draft_md = tmp_path / "ATLAS.draft.md"
    draft_md.write_text(reconcile.stage_draft(graph, tmp_path, name="demo"),
                        encoding="utf-8")
    atlas_md = tmp_path / "ATLAS.md"
    res = reconcile.accept_draft(draft_md, atlas_md)
    assert res["written"]
    fm, _ = schema.parse(atlas_md)
    assert schema.validate(fm) == [] and fm["name"] == "demo"
