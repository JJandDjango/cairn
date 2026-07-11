"""Pass 1 skeleton tests for the `atlas` package (schema + vault)."""
from backend import schema, vault

SAMPLE = """---
atlas_schema: 1
name: demo
purpose: A demo project
status: active
versioning: semver (v0.1.0)
components:
  - name: core
    role: does the thing
    level: module
    location: src/core.py
flows:
  - name: main-flow
    entry: core
    stages:
      - {component: core, role: start, stage: entry}
      - {component: core, role: end, stage: storage}
external:
  - {service: github.com/x/y, type: api-consumed, purpose: data}
cross_project:
  - {project: other, type: consumer-of, notes: uses core}
---

# Demo

Body text.
"""


def test_split_frontmatter():
    fm, body = schema.split_frontmatter(SAMPLE)
    assert fm["name"] == "demo"
    assert body.startswith("# Demo")


def test_validate_ok():
    fm, _ = schema.split_frontmatter(SAMPLE)
    assert schema.validate(fm) == []


def test_validate_missing_required():
    fm, _ = schema.split_frontmatter(SAMPLE)
    del fm["name"]
    fm["status"] = "bogus"
    errors = schema.validate(fm)
    assert any("name" in e for e in errors)
    assert any("status" in e for e in errors)


def test_validate_primitive_tag():
    fm, _ = schema.split_frontmatter(SAMPLE)
    fm["components"][0]["primitive"] = "tools"
    assert schema.validate(fm) == []
    for value in schema.PRIMITIVE_VALUES:
        fm["components"][0]["primitive"] = value
        assert schema.validate(fm) == []


def test_validate_primitive_tag_invalid():
    fm, _ = schema.split_frontmatter(SAMPLE)
    fm["components"][0]["primitive"] = "tols"
    assert any("primitive" in e for e in schema.validate(fm))


def test_validate_primitive_tag_optional():
    fm, _ = schema.split_frontmatter(SAMPLE)
    assert "primitive" not in fm["components"][0]
    assert schema.validate(fm) == []


def test_primitive_tag_round_trip():
    fm, body = schema.split_frontmatter(SAMPLE)
    fm["components"][0]["primitive"] = "runtime"
    fm2, _ = schema.split_frontmatter(schema.serialize(fm, body))
    assert fm2["components"][0]["primitive"] == "runtime"
    assert schema.validate(fm2) == []


def test_validate_dangling_flow_reference():
    fm, _ = schema.split_frontmatter(SAMPLE)
    fm["flows"][0]["entry"] = "ghost"
    assert any("ghost" in e for e in schema.validate(fm))


def test_validate_wrong_schema_version():
    fm, _ = schema.split_frontmatter(SAMPLE)
    fm["atlas_schema"] = 99
    assert any("atlas_schema" in e for e in schema.validate(fm))


def test_round_trip():
    fm, body = schema.split_frontmatter(SAMPLE)
    fm2, _ = schema.split_frontmatter(schema.serialize(fm, body))
    assert fm2 == fm
    assert schema.validate(fm2) == []


def test_summary():
    fm, _ = schema.split_frontmatter(SAMPLE)
    s = schema.summary(fm)
    assert s == {"name": "demo", "status": "active", "purpose": "A demo project",
                 "components": 1, "flows": 1}


def test_vault_add_and_index(tmp_path, monkeypatch):
    monkeypatch.setattr(vault, "VAULT", tmp_path / "atlas")
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "ATLAS.md").write_text(SAMPLE, encoding="utf-8")

    link = vault.add_project(proj / "ATLAS.md")
    assert link.exists()
    assert any(p["name"] == "demo" for p in vault.list_projects())

    index = (tmp_path / "atlas" / "index.md").read_text(encoding="utf-8")
    assert "[[demo]]" in index
    assert "| demo |" not in index  # name is wiki-linked, not bare


def test_validate_cli_singular_counts(tmp_path, capsys):
    from backend.__main__ import main
    atlas_md = tmp_path / "ATLAS.md"
    atlas_md.write_text(SAMPLE, encoding="utf-8")
    assert main(["validate", str(atlas_md)]) == 0
    out = capsys.readouterr().out
    assert "(1 component, 1 flow)" in out  # singular — no "1 flows" (#123 nit)
