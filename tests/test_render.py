"""Tests for the zero-dep 2.0 renderer (skills/cairn/render.py).

Focus: the 2.0 file set for every project type, each template's required
sections, the budgets and link rules a fresh render must already meet,
no-clobber, the interview answers (mode, the removed backend key), and the
absence of any graphify trace. The test numbers in comments are the Pass 1
test list approved 2026-10-14.
"""
import json
import re
from pathlib import Path

import pytest

import render

TEMPLATES = Path(render.__file__).parent / "templates"
SKILL_DIR = Path(render.__file__).parent
REPO_ROOT = SKILL_DIR.parent.parent
TODAY = "2026-10-14"

SPINE_2_0 = {
    "CLAUDE.md",
    "README.md",
    "ARCHITECTURE.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "CLAUDE.local.md",
    "decisions/0001-record-architecture-decisions.md",
    "decisions/ADR-template.md",
    "docs/recipe-template.md",
    "docs/feature-template.md",
    "docs/design-template.md",
    ".github/workflows/cairn-audit.yml",
}
STRATA_1X = {"THEORY.md", "MAP.md", "STATE.md", "CONVENTIONS.md", "DOCS-SYSTEM.md"}
NONCODE_TYPES = ["novel", "content-site", "business", "research"]
ALL_TYPES = ["code"] + NONCODE_TYPES
LONG_INTENT = "x" * 200


def _answers(**overrides):
    answers = {
        "project_name": "demo",
        "intent": "why it exists",
        "project_type": "code",
        "adoption": "greenfield",
        "mode": "tracked",
    }
    answers.update(overrides)
    return answers


def _render(root, **overrides):
    root.mkdir(parents=True, exist_ok=True)
    render.render_all(_answers(**overrides), TEMPLATES, root, TODAY)
    return root


def _read(root, rel):
    return (root / rel).read_text(encoding="utf-8")


def _files(root):
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def _strip_code(text):
    """Text outside fenced code blocks and inline code spans."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`]*`", "", text)


def _cli(root, answers):
    return render.main(["--answers", json.dumps(answers), "--cwd", str(root)])


# ------------------------------------------------ the 2.0 file set (1, 2)

def test_code_render_creates_2_0_file_set(tmp_path):  # 1
    files = _files(_render(tmp_path))
    assert files == SPINE_2_0
    assert not files & STRATA_1X


@pytest.mark.parametrize("ptype", NONCODE_TYPES)
def test_noncode_render_gets_same_file_set(tmp_path, ptype):  # 2
    assert _files(_render(tmp_path, project_type=ptype)) == SPINE_2_0


# ---------------------------------------------- each template's content (3-8)

def test_root_claude_md_imports_readme_and_architecture(tmp_path):  # 3
    lines = [ln for ln in _read(_render(tmp_path), "CLAUDE.md").splitlines() if ln.strip()]
    assert lines[:2] == ["@README.md", "@ARCHITECTURE.md"]
    assert len(lines) == 3
    assert lines[2].startswith("Read deeper only as the task needs")


def test_readme_has_user_sections(tmp_path):  # 4
    readme = _read(_render(tmp_path), "README.md")
    assert readme.startswith("# demo\n\nwhy it exists\n")
    for heading in ["## What it does", "## Install", "## Usage",
                    "## Help and contributing", "## License"]:
        assert heading in readme


def test_architecture_has_required_sections(tmp_path):  # 5
    arch = _read(_render(tmp_path), "ARCHITECTURE.md")
    for heading in ["## Intent", "## Invariants", "## Folder map", "## Where things live"]:
        assert heading in arch
    assert "why it exists" in arch


@pytest.mark.parametrize("ptype", ALL_TYPES)
def test_architecture_diagram_code_only(tmp_path, ptype):  # 6
    arch = _read(_render(tmp_path, project_type=ptype), "ARCHITECTURE.md")
    assert arch.count("```mermaid") == (1 if ptype == "code" else 0)


@pytest.mark.parametrize("ptype", ALL_TYPES)
def test_architecture_status_command_row_code_only(tmp_path, ptype):  # 7
    arch = _read(_render(tmp_path, project_type=ptype), "ARCHITECTURE.md")
    assert ("status command" in arch) == (ptype == "code")


def test_contributing_sections_and_recipe_link(tmp_path):  # 8
    contrib = _read(_render(tmp_path), "CONTRIBUTING.md")
    for heading in ["## Set up and test", "## Workflow", "## House rules", "## Recipes"]:
        assert heading in contrib
    assert "(docs/recipe-template.md)" in contrib


# ------------------------------------- rules a fresh render already meets (9-11)

@pytest.mark.parametrize("ptype", ALL_TYPES)
@pytest.mark.parametrize("adoption", ["greenfield", "brownfield"])
def test_budgets_hold_on_fresh_render(tmp_path, ptype, adoption):  # 9
    root = _render(tmp_path, project_type=ptype, adoption=adoption, intent=LONG_INTENT)
    for rel, budget in [("README.md", 2048), ("ARCHITECTURE.md", 3072),
                        ("CONTRIBUTING.md", 3072)]:
        assert len((root / rel).read_bytes()) <= budget, rel


@pytest.mark.parametrize("ptype", ALL_TYPES)
def test_no_at_outside_code_in_readme_and_architecture(tmp_path, ptype):  # 10
    root = _render(tmp_path, project_type=ptype)
    for rel in ["README.md", "ARCHITECTURE.md"]:
        assert "@" not in _strip_code(_read(root, rel)), rel


@pytest.mark.parametrize("ptype", ALL_TYPES)
def test_every_relative_link_resolves(tmp_path, ptype):  # 11
    root = _render(tmp_path, project_type=ptype)
    link = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
    checked = 0
    for rel in _files(root):
        for target in link.findall(_strip_code(_read(root, rel))):
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue
            path = (root / rel).parent / target.split("#")[0]
            assert path.exists(), f"{rel} -> {target}"
            checked += 1
    assert checked > 0


# ------------------------------------------------------ other templates (12-16)

def test_adr_seed_and_template_unchanged_from_1x(tmp_path):  # 12
    root = _render(tmp_path)
    seed = _read(root, "decisions/0001-record-architecture-decisions.md")
    assert seed.startswith("# 1. Record architecture decisions")
    assert f"Date: {TODAY}" in seed
    assert "demo needs a durable record" in seed
    assert _read(root, "decisions/ADR-template.md") == \
        (TEMPLATES / "decisions/ADR-template.md.template").read_text(encoding="utf-8")


def test_changelog_has_unreleased_section(tmp_path):  # 13
    changelog = _read(_render(tmp_path), "CHANGELOG.md")
    assert changelog.startswith("# Changelog")
    assert "## Unreleased" in changelog


def test_brownfield_intent_tagged_in_readme_and_architecture(tmp_path):  # 14
    root = _render(tmp_path, adoption="brownfield")
    for rel in ["README.md", "ARCHITECTURE.md"]:
        assert "why it exists _(inferred - confirm)_" in _read(root, rel), rel
    green = _render(tmp_path / "g")
    assert "inferred - confirm" not in _read(green, "README.md")


@pytest.mark.parametrize("ptype", ALL_TYPES)
def test_no_placeholder_left(tmp_path, ptype):  # 15
    root = _render(tmp_path, project_type=ptype, adoption="brownfield")
    for rel in _files(root):
        assert "{{" not in _read(root, rel), rel


def test_gitignore_gains_local_note_once_and_keeps_content(tmp_path):  # 16
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    assert render.update_gitignore(fresh) is True
    assert "CLAUDE.local.md" in _read(fresh, ".gitignore").splitlines()

    kept = tmp_path / "kept"
    kept.mkdir()
    (kept / ".gitignore").write_text("node_modules/", encoding="utf-8")
    assert _cli(kept, _answers()) == 0
    assert _cli(kept, _answers()) == 0
    text = _read(kept, ".gitignore")
    assert text.startswith("node_modules/\n")
    assert text.splitlines().count("CLAUDE.local.md") == 1


# --------------------------------------------------------- no-clobber (17, 18)

def test_no_clobber_every_target(tmp_path):  # 17
    for rel in SPINE_2_0:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("mine\n", encoding="utf-8")
    created, skipped = render.render_all(_answers(), TEMPLATES, tmp_path, TODAY)
    assert created == []
    assert {p.relative_to(tmp_path).as_posix() for p in skipped} == SPINE_2_0
    for rel in SPINE_2_0:
        assert _read(tmp_path, rel) == "mine\n", rel


def test_rerun_creates_nothing(tmp_path):  # 18
    _render(tmp_path)
    created, skipped = render.render_all(_answers(), TEMPLATES, tmp_path, TODAY)
    assert created == []
    assert len(skipped) == len(SPINE_2_0)


# ------------------------------------------------- interview answers (19-24)

def test_mode_required(tmp_path, capsys):  # 19
    answers = _answers()
    del answers["mode"]
    assert _cli(tmp_path, answers) == 1
    assert "mode" in capsys.readouterr().err
    with pytest.raises(ValueError):
        render.render_all(answers, TEMPLATES, tmp_path, TODAY)
    assert _files(tmp_path) == set()


def test_invalid_mode_rejected(tmp_path):  # 20
    with pytest.raises(ValueError, match="mode"):
        _render(tmp_path, mode="shared")


def test_local_mode_accepted_and_invalid_mode_fails_before_write(tmp_path, capsys):  # 21 (Pass 4, 20)
    ok = tmp_path / "ok"
    ok.mkdir()
    assert _cli(ok, _answers(mode="local")) == 0
    assert (ok / ".docs-local/README.md").is_file()
    assert "not built yet" not in capsys.readouterr().err

    bad = tmp_path / "bad"
    bad.mkdir()
    assert _cli(bad, _answers(mode="shared")) == 1
    assert "mode" in capsys.readouterr().err
    assert _files(bad) == set()


def test_backend_key_rejected(tmp_path, capsys):  # 22
    assert _cli(tmp_path, _answers(backend="none")) == 1
    assert "'backend' answer was removed" in capsys.readouterr().err
    assert _files(tmp_path) == set()


@pytest.mark.parametrize("key,value", [("project_type", "poem"), ("adoption", "bluefield")])
def test_bad_project_type_or_adoption_rejected(tmp_path, key, value):  # 23
    with pytest.raises(ValueError, match=key):
        _render(tmp_path, **{key: value})


def test_cli_output_and_exit_codes(tmp_path, capsys):  # 24
    assert _cli(tmp_path, _answers()) == 0
    out = capsys.readouterr().out
    assert "created  README.md" in out
    assert "updated  .gitignore" in out

    assert _cli(tmp_path, _answers()) == 0
    out = capsys.readouterr().out
    assert "skipped  README.md  (exists)" in out
    assert "updated  .gitignore" not in out

    assert render.main(["--answers", "{not json", "--cwd", str(tmp_path)]) == 1
    answers = _answers()
    del answers["intent"]
    assert _cli(tmp_path, answers) == 1


# ---------------------------------------------- the handoff rule (Pass 2, 20)

@pytest.mark.parametrize("ptype", ALL_TYPES)
def test_contributing_states_handoff_rule(tmp_path, ptype):  # Pass 2, 20
    contrib = " ".join(_read(_render(tmp_path, project_type=ptype), "CONTRIBUTING.md").split())
    assert ("A handoff in the middle of a piece of work stays in that work's "
            "own folder, never in a top-level file.") in contrib


# ------------------------------------------------------ graphify removed (25)

def test_no_graphify_traces():  # 25
    for gone in ["backend", "backend_cli.py", "detect.py"]:
        assert not (SKILL_DIR / gone).exists(), gone
    scanned = [p for p in SKILL_DIR.rglob("*") if p.is_file() and p.suffix != ".pyc"]
    scanned.append(REPO_ROOT / "pyproject.toml")
    for path in scanned:
        assert "graphify" not in path.read_text(encoding="utf-8").lower(), path
