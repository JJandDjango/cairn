"""Tests for the 2.0 checks (features 22-28): audit.py, the CI template, SKILL.md.

Focus: detection and exit codes, each finding code in tracked and local mode,
that a fresh render passes its own audit, that the audit writes nothing, the
workflow render.py writes, and the maintain and audit sections of SKILL.md.
The test numbers in comments are the Pass 5 test list approved 2026-10-15;
16 (plan equals run) is in test_pages.py.
"""
import json
import re
import subprocess
from datetime import date
from pathlib import Path

import pytest

import audit
import pages
import render
import spine_1x

SKILL_DIR = Path(render.__file__).parent
TEMPLATES = SKILL_DIR / "templates"
WORKFLOW = ".github/workflows/cairn-audit.yml"

NONCODE_TYPES = ["novel", "content-site", "business", "research"]
ALL_TYPES = ["code"] + NONCODE_TYPES
MODES = ["tracked", "local"]
CODES = ["SIZE-BUDGET", "AT-IMPORT", "LINK-BROKEN", "GEN-STALE", "COVER-PAGE", "COVER-FILE"]


@pytest.fixture(autouse=True)
def _no_parent_repo(monkeypatch, tmp_path):
    """Keep git from finding a repo above the test's temp folder."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))


def _write(root, rel, text=""):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _read(root, rel):
    return (root / rel).read_text(encoding="utf-8")


def _append(root, rel, text):
    _write(root, rel, _read(root, rel) + text)


def _project(root):
    """A small code tree: one documented file, one not, and a Rust file."""
    _write(root, "src/app/main.py", '"""Start the app.\n\nMore detail."""\n')
    _write(root, "src/app/util.js", "export const x = 1;\n")
    _write(root, "src/lib.rs", "//! The library root.\n")
    _write(root, "tests/test_main.py", "def test_x():\n    pass\n")


def _answers(mode, **overrides):
    answers = {
        "project_name": "demo",
        "intent": "why it exists",
        "project_type": "code",
        "adoption": "greenfield",
        "mode": mode,
    }
    answers.update(overrides)
    return answers


def _build(root, mode="tracked", tree=True, **overrides):
    """Render through the CLI, as a user would: spine, then folder pages."""
    root.mkdir(parents=True, exist_ok=True)
    if tree:
        _project(root)
    assert render.main(["--answers", json.dumps(_answers(mode, **overrides)),
                        "--cwd", str(root)]) == 0
    return root


def _top(mode):
    return ".docs-local/" if mode == "local" else ""


def _page(mode):
    return pages.LOCAL_PAGE if mode == "local" else pages.PAGE


def _find(root, code=None):
    findings = audit.run_checks(root, audit.spine_mode(root))
    return [f for f in findings if code is None or f.code == code]


def _actionable(findings):
    return [(f.code, f.path) for f in findings if f.severity in ("ERROR", "WARN")]


def _snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _pad_to(root, rel, size):
    """Append an HTML comment so the file is exactly size bytes (a pad from an
    earlier call is replaced)."""
    path = root / rel
    raw = re.sub(rb"<!--x+-->$", b"", path.read_bytes())
    assert len(raw) + 7 <= size
    path.write_bytes(raw + b"<!--" + b"x" * (size - len(raw) - 7) + b"-->")


# ----------------------------------------------- detection and exit (27: 1-4)

@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("ptype", ALL_TYPES)
def test_fresh_render_audits_clean(tmp_path, ptype, mode):  # 1 (tracked), 2 (local)
    root = _build(tmp_path, mode, project_type=ptype)
    assert audit.spine_mode(root) == mode
    assert _actionable(_find(root)) == []
    assert audit.main(["--cwd", str(root)]) == 0
    # Code projects have pages for the audit to check; the others have none.
    assert (root / "src" / _page(mode)).exists() == (ptype == "code")


def test_no_spine_exits_2(tmp_path, capsys):  # 3
    assert audit.main(["--cwd", str(tmp_path)]) == 2
    _write(tmp_path, "README.md", "# just a readme\n")
    assert audit.main(["--cwd", str(tmp_path)]) == 2
    assert "ARCHITECTURE.md" in capsys.readouterr().err


def test_1x_only_spine_behaves_as_before(tmp_path):  # 3
    spine_1x.render_1x({"project_name": "demo", "intent": "why", "project_type": "code",
                        "adoption": "greenfield"}, tmp_path, date.today().isoformat())
    assert audit.spine_mode(tmp_path) is None
    assert audit.main(["--cwd", str(tmp_path)]) == 0

    (tmp_path / "STATE.md").unlink()
    assert audit.main(["--cwd", str(tmp_path)]) == 1


def test_both_spines_run_both_check_sets(tmp_path):  # 3
    root = _build(tmp_path, project_type="novel", tree=False)
    spine_1x.render_1x({"project_name": "demo", "intent": "why", "project_type": "novel",
                        "adoption": "brownfield"}, root, date.today().isoformat())
    _pad_to(root, "README.md", 2049)
    findings = audit.run_audit(root) + audit.run_checks(root, "tracked")
    codes = {f.code for f in findings if f.severity in ("ERROR", "WARN")}
    assert {"INFERRED-TAG", "SIZE-BUDGET"} <= codes
    assert audit.main(["--cwd", str(root)]) == 1


BREAKERS = {
    "SIZE-BUDGET": lambda root, mode: _pad_to(root, _top(mode) + "README.md", 2049),
    "AT-IMPORT": lambda root, mode: _append(root, _top(mode) + "README.md", "\n@docs/x.md\n"),
    "LINK-BROKEN": lambda root, mode: _append(root, _top(mode) + "ARCHITECTURE.md",
                                              "\n[gone](missing.md)\n"),
    "GEN-STALE": lambda root, mode: _write(root, "src/app/main.py", '"""Boot the app."""\n'),
    "COVER-PAGE": lambda root, mode: _write(root, "lib/helper.py", ""),
    "COVER-FILE": lambda root, mode: _write(root, "src/app/extra.txt", "notes\n"),
}


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("code", CODES)
def test_each_failing_check_exits_1(tmp_path, code, mode):  # 4
    root = _build(tmp_path, mode)
    assert audit.main(["--cwd", str(root)]) == 0
    BREAKERS[code](root, mode)
    errors = [f.code for f in _find(root) if f.severity == "ERROR"]
    assert code in errors
    assert audit.main(["--cwd", str(root)]) == 1


# ------------------------------------------------------ size budgets (22: 5-7)

@pytest.mark.parametrize("rel,limit", [
    ("README.md", 2048),
    ("ARCHITECTURE.md", 3072),
    ("CONTRIBUTING.md", 3072),
    ("src/app/CLAUDE.md", 2048),
])
def test_budget_over_fails_exactly_at_limit_passes(tmp_path, rel, limit):  # 5
    root = _build(tmp_path)
    _pad_to(root, rel, limit)
    assert (root / rel).stat().st_size == limit
    assert _find(root, "SIZE-BUDGET") == []

    _pad_to(root, rel, limit + 1)
    found = _find(root, "SIZE-BUDGET")
    assert [(f.severity, f.path) for f in found] == [("ERROR", rel)]
    assert str(limit) in found[0].message


def test_root_claude_md_over_10_lines_fails(tmp_path):  # 6
    root = _build(tmp_path)
    _write(root, "CLAUDE.md", "@README.md\n@ARCHITECTURE.md\n" + "a line\n" * 8)
    assert len(_read(root, "CLAUDE.md").splitlines()) == 10
    assert _find(root, "SIZE-BUDGET") == []

    _append(root, "CLAUDE.md", "one more\n")
    found = _find(root, "SIZE-BUDGET")
    assert [f.path for f in found] == ["CLAUDE.md"]


@pytest.mark.parametrize("rel,limit", [
    (".docs-local/README.md", 2048),
    (".docs-local/ARCHITECTURE.md", 3072),
    (".docs-local/CONTRIBUTING.md", 3072),
    ("src/app/CLAUDE.local.md", 2048),
])
def test_local_files_held_to_same_budgets(tmp_path, rel, limit):  # 7
    root = _build(tmp_path, "local")
    _pad_to(root, rel, limit)
    assert _find(root, "SIZE-BUDGET") == []
    _pad_to(root, rel, limit + 1)
    assert [f.path for f in _find(root, "SIZE-BUDGET")] == [rel]


def test_local_root_note_has_no_line_budget(tmp_path):  # 7
    root = _build(tmp_path, "local")
    _append(root, "CLAUDE.local.md", "a machine note\n" * 40)
    assert _find(root) == []


# --------------------------------------------------- @ outside code (23: 8-10)

@pytest.mark.parametrize("rel", ["README.md", "ARCHITECTURE.md", "src/app/CLAUDE.md"])
def test_at_import_outside_code_fails_with_line(tmp_path, rel):  # 8
    root = _build(tmp_path)
    expected = len(_read(root, rel).splitlines()) + 2
    _append(root, rel, "\nSee @docs/guide.md for more.\n")
    found = _find(root, "AT-IMPORT")
    assert [(f.severity, f.path) for f in found] == [("ERROR", rel)]
    assert f"line {expected}" in found[0].message
    assert "@docs/guide.md" in found[0].message


@pytest.mark.parametrize("rel", ["README.md", "ARCHITECTURE.md", "src/app/CLAUDE.md"])
def test_at_in_fence_or_inline_code_passes(tmp_path, rel):  # 8
    root = _build(tmp_path)
    _append(root, rel, "\nUse `@docs/guide.md` here.\n\n```\n@docs/guide.md\n```\n"
                       "\n~~~\n@other.md\n~~~\n")
    assert _find(root, "AT-IMPORT") == []


def test_email_passes_and_contributing_and_root_importer_exempt(tmp_path):  # 9
    root = _build(tmp_path)
    _append(root, "README.md", "\nWrite to a@b.c or first.last@example.com.\n")
    _append(root, "CONTRIBUTING.md", "\nImport @docs/recipe-template.md here.\n")
    assert "@README.md" in _read(root, "CLAUDE.md")
    assert _find(root, "AT-IMPORT") == []


@pytest.mark.parametrize("rel", [".docs-local/README.md", ".docs-local/ARCHITECTURE.md",
                                 "src/app/CLAUDE.local.md"])
def test_local_mode_checks_local_pages_not_root_note(tmp_path, rel):  # 10
    root = _build(tmp_path, "local")
    assert "@.docs-local/README.md" in _read(root, "CLAUDE.local.md")
    _append(root, "CLAUDE.local.md", "\n@elsewhere.md\n")
    assert _find(root, "AT-IMPORT") == []

    _append(root, rel, "\n@docs/guide.md\n")
    assert [f.path for f in _find(root, "AT-IMPORT")] == [rel]


# ------------------------------------------------------- links (24: 11-12)

def test_broken_link_names_source_and_target(tmp_path):  # 11
    root = _build(tmp_path)
    _append(root, "README.md", "\n[gone](missing.md#top) and [also](docs/nope.md)\n")
    found = _find(root, "LINK-BROKEN")
    assert sorted((f.path, f.message) for f in found) == [
        ("README.md", "link 'docs/nope.md' does not resolve"),
        ("README.md", "link 'missing.md#top' does not resolve"),
    ]
    _append(root, "src/app/CLAUDE.md", "\n[gone](../../nope.md)\n")
    paths = sorted(f.path for f in _find(root, "LINK-BROKEN"))
    assert paths == ["README.md", "README.md", "src/app/CLAUDE.md"]


def test_anchor_stripped_and_skipped_links_pass(tmp_path):  # 11
    root = _build(tmp_path)
    _append(root, "README.md",
            "\n[a](ARCHITECTURE.md#invariants) [b](https://example.com/x.md)\n"
            "[c](http://example.com/y) [d](mailto:a@b.c) [e](#section)\n"
            "[f](ARCHITECTURE.md \"a title\") [g](<ARCHITECTURE.md>)\n"
            "`[h](nope.md)`\n\n```\n[i](nope.md)\n```\n"
            "<!-- [j](nope.md) -->\n")
    assert _find(root, "LINK-BROKEN") == []


def test_links_resolve_from_the_files_own_folder(tmp_path):  # 12
    root = _build(tmp_path)
    _append(root, "src/app/CLAUDE.md",
            "\n[recipe](../../docs/recipe-template.md)\n[folder](../../docs/)\n"
            "[up](..)\n[root](/docs/recipe-template.md)\n")
    assert _find(root, "LINK-BROKEN") == []

    _append(root, "src/app/CLAUDE.md", "\n[wrong](docs/recipe-template.md)\n")
    found = _find(root, "LINK-BROKEN")
    assert [(f.path, f.message) for f in found] == [
        ("src/app/CLAUDE.md", "link 'docs/recipe-template.md' does not resolve")]


def test_local_links_resolve_from_docs_local(tmp_path):  # 12
    root = _build(tmp_path, "local")
    _append(root, ".docs-local/README.md", "\n[recipe](docs/recipe-template.md)\n")
    _append(root, "src/app/CLAUDE.local.md",
            "\n[recipe](../../.docs-local/docs/recipe-template.md)\n")
    assert _find(root, "LINK-BROKEN") == []
    _append(root, ".docs-local/README.md", "\n[bad](../docs/recipe-template.md)\n")
    assert [f.path for f in _find(root, "LINK-BROKEN")] == [".docs-local/README.md"]


# ------------------------------------------------ generated lines (25: 13-17)

def test_edited_docstring_is_stale_and_audit_writes_nothing(tmp_path):  # 13
    root = _build(tmp_path)
    _write(root, "src/app/main.py", '"""Boot the app."""\n')
    before = _snapshot(root)
    found = _find(root, "GEN-STALE")
    assert [(f.severity, f.path) for f in found] == [("ERROR", "src/app/CLAUDE.md")]
    assert audit.main(["--cwd", str(root)]) == 1
    assert audit.main(["--cwd", str(root), "--format", "json"]) == 1
    assert _snapshot(root) == before


def test_new_documented_file_without_block_line_is_stale(tmp_path):  # 14
    root = _build(tmp_path)
    _write(root, "src/app/extra.py", '"""Extra helper."""\n')
    found = _find(root, "GEN-STALE")
    assert [f.path for f in found] == ["src/app/CLAUDE.md"]


def test_typed_lines_never_stale_and_page_without_markers_is_one_info(tmp_path):  # 15
    root = _build(tmp_path)
    page = _read(root, "src/app/CLAUDE.md")
    typed = page.replace(pages.TYPED_FILE_HINT, "Helpers, edited by a person.")
    assert typed != page
    _write(root, "src/app/CLAUDE.md", typed)
    assert _find(root, "GEN-STALE") == []
    assert _actionable(_find(root)) == []

    _write(root, "src/app/CLAUDE.md",
           "# Hand-written\n\n- `main.py`: starts it\n- `util.js`: helpers\n")
    found = _find(root, "GEN-STALE")
    assert [(f.severity, f.path) for f in found] == [("INFO", "src/app/CLAUDE.md")]
    assert audit.main(["--cwd", str(root)]) == 0


@pytest.mark.parametrize("mode", MODES)
def test_running_pages_clears_every_gen_stale(tmp_path, mode):  # 17
    root = _build(tmp_path, mode)
    _write(root, "src/app/main.py", '"""Boot the app."""\n')
    _write(root, "src/app/extra.py", '"""Extra helper."""\n')
    _write(root, "src/lib.rs", "//! A new root.\n")
    assert len(_find(root, "GEN-STALE")) == 2
    pages.run(root, _page(mode))
    assert _find(root, "GEN-STALE") == []
    assert _find(root, "COVER-FILE") == []


# ------------------------------------------------------- coverage (26: 18-21)

def test_working_folder_without_page_fails_excluded_never(tmp_path):  # 18
    _git(tmp_path, "init", "-q")
    _write(tmp_path, ".gitignore", "ignored/\n")
    root = _build(tmp_path)
    for rel in ["venv/pyvenv.cfg", "venv/lib/x.py", "tests/fixtures/a.json", "vendor/v.py",
                "build/b.py", ".hidden/h.py", "ignored/i.py", "node_modules/n.js",
                "src/app/__pycache__/m.pyc"]:
        _write(root, rel, "x\n")
    assert _find(root, "COVER-PAGE") == []
    assert _actionable(_find(root)) == []

    _write(root, "lib/helper.py", '"""Help."""\n')
    found = _find(root, "COVER-PAGE")
    assert [f.path for f in found] == ["lib"]
    assert "lib/CLAUDE.md" in found[0].message
    pages.run(root)
    assert _find(root, "COVER-PAGE") == []


def test_file_without_line_fails_dotfiles_count_page_name_does_not(tmp_path):  # 19
    root = _build(tmp_path)
    _write(root, "src/app/extra.txt", "notes\n")
    _write(root, "src/app/.env.example", "KEY=\n")
    _write(root, "src/app/CLAUDE.local.md", "my note\n")
    found = _find(root, "COVER-FILE")
    assert sorted((f.path, f.message) for f in found) == [
        ("src/app/CLAUDE.md", "'.env.example' has no line in the page"),
        ("src/app/CLAUDE.md", "'extra.txt' has no line in the page"),
    ]
    # A typed line, anywhere in the page, covers the file.
    _append(root, "src/app/CLAUDE.md", "- `extra.txt`: notes\n- `.env.example`: key\n")
    assert _find(root, "COVER-FILE") == []


def test_name_inside_a_longer_name_is_not_a_line(tmp_path):  # 19
    root = _build(tmp_path)
    _write(root, "src/app/til.js", "x\n")
    _write(root, "src/app/util.js.bak", "x\n")
    _append(root, "src/app/CLAUDE.md", "- `util.js.bak`: a backup\n")
    found = _find(root, "COVER-FILE")
    assert [f.message for f in found] == ["'til.js' has no line in the page"]


def test_hand_written_page_still_checked_tracked_claude_md_ignored_in_local(tmp_path):  # 20
    root = _build(tmp_path)
    _write(root, "src/app/CLAUDE.md", "# Hand-written\n\nKeep me.\n")
    found = _find(root, "COVER-FILE")
    assert sorted(f.message for f in found) == ["'main.py' has no line in the page",
                                                "'util.js' has no line in the page"]

    local = _build(tmp_path / "local", "local")
    _write(local, "src/app/CLAUDE.md", "# Theirs\n@elsewhere.md\n[x](nope.md)\n" + "pad\n" * 900)
    assert _actionable(_find(local)) == []
    (local / "src/app/CLAUDE.local.md").unlink()
    found = _find(local, "COVER-PAGE")
    assert [f.path for f in found] == ["src/app"]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("ptype", NONCODE_TYPES)
def test_noncode_project_gets_no_folder_checks(tmp_path, ptype, mode):  # 21
    root = _build(tmp_path, mode, project_type=ptype)
    _write(root, "chapters/one.md", "Once upon a time.\n")
    assert not [p for p in root.rglob(_page(mode)) if p.parent != root]
    assert _actionable(_find(root)) == []
    assert audit.main(["--cwd", str(root)]) == 0


# --------------------------------------------------------- CI template (27: 22-23)

@pytest.mark.parametrize("ptype", ALL_TYPES)
def test_tracked_render_writes_audit_workflow_no_clobber(tmp_path, capsys, ptype):  # 22
    root = _build(tmp_path, project_type=ptype, tree=False)
    text = _read(root, WORKFLOW)
    assert re.search(r"^on:\s*\n\s+pull_request:", text, re.M)
    assert "audit.py --cwd ." in text
    assert "{{" not in text
    assert "https://github.com/JJandDjango/cairn" in text
    assert text.count("CAIRN_REF: main") == 1

    _write(root, WORKFLOW, "mine\n")
    capsys.readouterr()
    assert render.main(["--answers", json.dumps(_answers("tracked", project_type=ptype)),
                        "--cwd", str(root)]) == 0
    assert _read(root, WORKFLOW) == "mine\n"
    assert f"skipped  {Path(WORKFLOW)}  (exists)" in capsys.readouterr().out


def test_workflow_template_has_no_github_expressions():  # 22
    text = (TEMPLATES / "cairn-audit.yml.template").read_text(encoding="utf-8")
    assert "${{" not in text and "{{" not in text


@pytest.mark.parametrize("ptype", ALL_TYPES)
def test_local_render_writes_no_github_file(tmp_path, ptype):  # 23
    root = _build(tmp_path, "local", project_type=ptype)
    assert not (root / ".github").exists()
    assert not (root / ".docs-local/.github").exists()


# ------------------------------------------------------------ SKILL.md (28: 24-25)

def _skill():
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def _section(tag):
    return re.search(rf"<{tag}>(.*?)</{tag}>", _skill(), re.S).group(1)


def test_maintain_section_for_2_0_spine_keeps_1x_branch():  # 24
    maintain = _section("maintain-subcommand")
    two, one_x = maintain.split("1.x steps (until")
    for needle in ["audit.py", "pages.py", "uncommitted", "Do NOT commit",
                   "TOUCH the pages", "never create or regenerate"]:
        assert needle in two, needle
    assert "REGENERATE STATE.md" not in two
    assert "REGENERATE STATE.md" in one_x
    assert "TOUCH MAP.md" in one_x


def test_audit_section_states_exit_1_in_both_modes_and_no_no_spine_note():  # 25
    audit_section = _section("audit-subcommand")
    assert "exit 1" in audit_section.lower()
    assert "both modes" in audit_section
    assert "audit reports no spine" not in _skill()
    assert "2.0 spine" in _section("context")


# ------------------------------------- code-ness from ARCHITECTURE.md (amendment)

STATUS_ROW = render.CODE_STATUS_ROW


def _delete_pages(root, mode):
    for p in list(root.rglob(_page(mode))):
        if p.parent != root:
            p.unlink()


def _drop_status_row(root, mode):
    rel = _top(mode) + "ARCHITECTURE.md"
    text = _read(root, rel)
    assert STATUS_ROW in text
    _write(root, rel, text.replace(STATUS_ROW, ""))


@pytest.mark.parametrize("mode", MODES)
def test_code_project_with_pages_deleted_fails_cover_page(tmp_path, mode):  # Pass 5 amendment, A1
    root = _build(tmp_path, mode)
    assert STATUS_ROW in _read(root, _top(mode) + "ARCHITECTURE.md")
    _delete_pages(root, mode)
    assert not [p for p in root.rglob(_page(mode)) if p.parent != root]
    found = _find(root, "COVER-PAGE")
    assert found and all(f.severity == "ERROR" for f in found)
    assert "src/app" in [f.path for f in found]
    assert audit.main(["--cwd", str(root)]) == 1


@pytest.mark.parametrize("mode", MODES)
def test_noncode_render_with_no_pages_stays_clean(tmp_path, mode):  # Pass 5 amendment, A2
    root = _build(tmp_path, mode, project_type="novel")
    assert STATUS_ROW not in _read(root, _top(mode) + "ARCHITECTURE.md")
    assert not [p for p in root.rglob(_page(mode)) if p.parent != root]
    assert _actionable(_find(root)) == []
    assert audit.main(["--cwd", str(root)]) == 0


@pytest.mark.parametrize("mode", MODES)
def test_status_row_removed_with_pages_present_still_checks_folders(tmp_path, mode):  # Pass 5 amendment, A3
    root = _build(tmp_path, mode)
    _drop_status_row(root, mode)
    assert _actionable(_find(root)) == []
    _write(root, "src/app/extra.txt", "notes\n")
    found = _find(root, "COVER-FILE")
    assert [f.message for f in found] == ["'extra.txt' has no line in the page"]
    assert audit.main(["--cwd", str(root)]) == 1


@pytest.mark.parametrize("mode", MODES)
def test_status_row_removed_and_no_pages_has_no_folder_checks(tmp_path, mode):  # Pass 5 amendment, A4
    root = _build(tmp_path, mode)
    _drop_status_row(root, mode)
    _delete_pages(root, mode)
    assert _find(root, "COVER-PAGE") == []
    assert _actionable(_find(root)) == []
    assert audit.main(["--cwd", str(root)]) == 0


@pytest.mark.parametrize("mode", MODES)
def test_prose_or_inline_code_mention_is_not_the_status_row(tmp_path, mode):  # Pass 5 amendment, A5
    root = _build(tmp_path, mode, project_type="novel")
    rel = _top(mode) + "ARCHITECTURE.md"
    _append(root, rel, "\nTo see progress, run `/cairn status` in this folder.\n\n"
                       "`/cairn status`\n\nThe /cairn status command reports it.\n\n"
                       "```\n| Status | `/cairn status` |\n```\n")
    assert _find(root, "COVER-PAGE") == []
    assert _actionable(_find(root)) == []
    assert audit.main(["--cwd", str(root)]) == 0
