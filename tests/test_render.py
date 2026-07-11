"""Tests for the zero-dep core renderer (skills/cairn/render.py).

Focus: the layered-backend seam added in Slice 2. The structured MAP stub and the
DOCS-SYSTEM backend note appear ONLY for a graphify-backend code project; the
novel / non-backend path renders with no frontmatter (the load-bearing
invariant). render.py is stdlib-only, so this imports without the backend deps.
"""
from pathlib import Path

import render

TEMPLATES = Path(render.__file__).parent / "templates"
TODAY = "2026-07-11"


def _render(root, **overrides):
    answers = {
        "project_name": "demo",
        "intent": "why it exists",
        "project_type": "novel",
        "backend": "none",
        "material": "greenfield",
    }
    answers.update(overrides)
    render.render_all(answers, TEMPLATES, root, TODAY)
    return root


def test_novel_map_has_no_structured_stub(tmp_path):
    mapmd = (_render(tmp_path) / "MAP.md").read_text(encoding="utf-8")
    assert mapmd.startswith("# Map - demo")
    assert "atlas_schema" not in mapmd
    assert "OPTIONAL structured model" not in mapmd


def test_code_graphify_map_has_structured_stub(tmp_path):
    mapmd = (_render(tmp_path, project_type="code", backend="graphify")
             / "MAP.md").read_text(encoding="utf-8")
    assert mapmd.startswith("<!-- OPTIONAL structured model")
    assert "atlas_schema: 1" in mapmd
    assert "name: demo" in mapmd
    assert "purpose: why it exists" in mapmd
    # the plain authored table still follows the stub
    assert "# Map - demo" in mapmd


def test_code_none_map_has_no_stub(tmp_path):
    mapmd = (_render(tmp_path, project_type="code", backend="none")
             / "MAP.md").read_text(encoding="utf-8")
    assert mapmd.startswith("# Map - demo")
    assert "atlas_schema" not in mapmd


def test_graphify_off_noncode_coerced_to_none(tmp_path):
    # backend=graphify on a non-code type must coerce to none -> no stub.
    mapmd = (_render(tmp_path, project_type="business", backend="graphify")
             / "MAP.md").read_text(encoding="utf-8")
    assert "atlas_schema" not in mapmd


def test_map_mode_points_at_cairn_for_graphify(tmp_path):
    mapmd = (_render(tmp_path, project_type="code", backend="graphify")
             / "MAP.md").read_text(encoding="utf-8")
    assert "/cairn derive" in mapmd
    assert "/atlas init" not in mapmd


def test_docs_system_backend_note_gated(tmp_path):
    novel_docs = (_render(tmp_path / "n") / "DOCS-SYSTEM.md").read_text(encoding="utf-8")
    assert "Optional structured MAP" not in novel_docs

    code_docs = (_render(tmp_path / "c", project_type="code", backend="graphify")
                 / "DOCS-SYSTEM.md").read_text(encoding="utf-8")
    assert "Optional structured MAP" in code_docs
    assert "/cairn view" in code_docs


def test_invalid_backend_value_rejected(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        _render(tmp_path, project_type="code", backend="atlas")
