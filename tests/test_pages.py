"""Tests for the folder-page script (skills/cairn/pages.py).

Focus: which folders get a page, what a new page holds, the docstring lines
in its marked block, reruns that touch only that block, and the CLI. The
test numbers in comments are the Pass 2 test list approved 2026-10-14.
Tests 10, 11, 12 and 14 run once per page name, CLAUDE.md and (local mode)
CLAUDE.local.md; the rest of local mode is in test_local.py.
"""
import json
import re
import subprocess
from pathlib import Path

import pytest

import pages
import render

TEMPLATES = Path(render.__file__).parent / "templates"
NONCODE_TYPES = ["novel", "content-site", "business", "research"]
PAGE_NAMES = [pages.PAGE, pages.LOCAL_PAGE]


def _write(root, rel, text=""):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _read(root, rel):
    return (root / rel).read_text(encoding="utf-8")


def _bytes(root, rel):
    return (root / rel).read_bytes()


def _block(text):
    start = text.index(pages.BLOCK_START) + len(pages.BLOCK_START)
    return text[start:text.index(pages.BLOCK_END)].strip("\n").splitlines()


def _outside_block(text):
    start = text.index(pages.BLOCK_START)
    end = text.index(pages.BLOCK_END) + len(pages.BLOCK_END)
    return text[:start] + text[end:]


def _git_init(root):
    subprocess.run(["git", "init", "-q", str(root)], check=True)


def _answers(ptype):
    return {"project_name": "demo", "intent": "why it exists", "project_type": ptype,
            "adoption": "brownfield", "mode": "tracked"}


def _strip_code(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`]*`", "", text)


def _project(root):
    """A small brownfield code tree."""
    _write(root, "src/app/main.py", '"""Start the app.\n\nMore detail."""\n')
    _write(root, "src/app/util.js", "export const x = 1;\n")
    _write(root, "src/lib.rs", "//! The library root.\n")
    _write(root, "tests/test_main.py", "def test_x():\n    pass\n")
    return root


# ---------------------------------------------------- which folders (1-4)

def test_code_render_creates_pages_noncode_none(tmp_path):  # 1
    code = _project(tmp_path / "code")
    assert render.main(["--answers", json.dumps(_answers("code")), "--cwd", str(code)]) == 0
    for rel in ["src/CLAUDE.md", "src/app/CLAUDE.md", "tests/CLAUDE.md"]:
        assert (code / rel).is_file()
    for ptype in NONCODE_TYPES:
        other = _project(tmp_path / ptype)
        render.main(["--answers", json.dumps(_answers(ptype)), "--cwd", str(other)])
        assert not list(other.glob("*/**/CLAUDE.md"))


def test_root_spine_page_untouched(tmp_path):  # 2
    _project(tmp_path)
    render.render_all(_answers("code"), TEMPLATES, tmp_path, "2026-10-14")
    before = _bytes(tmp_path, "CLAUDE.md")
    pages.run(tmp_path)
    pages.run(tmp_path)
    assert _bytes(tmp_path, "CLAUDE.md") == before
    assert (tmp_path / "docs/CLAUDE.md").is_file()
    assert not (tmp_path / "decisions/CLAUDE.md").exists()


@pytest.mark.parametrize("folder", sorted(pages.EXCLUDED_NAMES) + [".github", "ignored"])
def test_excluded_folders_and_descendants_get_no_page(tmp_path, folder):  # 3
    _git_init(tmp_path)
    _write(tmp_path, ".gitignore", "ignored/\n")
    _write(tmp_path, "src/keep.py", "")
    _write(tmp_path, f"src/{folder}/a.py", "")
    _write(tmp_path, f"src/{folder}/deep/b.py", "")
    pages.run(tmp_path)
    assert (tmp_path / "src/CLAUDE.md").is_file()
    assert not (tmp_path / f"src/{folder}/CLAUDE.md").exists()
    assert not (tmp_path / f"src/{folder}/deep/CLAUDE.md").exists()


@pytest.mark.parametrize("git", [False, True])
def test_virtualenv_under_any_name_gets_no_page(tmp_path, git):  # 3
    if git:
        _git_init(tmp_path)
    _write(tmp_path, "src/keep.py", "")
    _write(tmp_path, "src/myenv/pyvenv.cfg", "home = /usr/bin\n")
    _write(tmp_path, "src/myenv/Lib/site-packages/pkg/__init__.py", "")
    pages.run(tmp_path)
    assert [p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("CLAUDE.md")] == ["src/CLAUDE.md"]
    assert "myenv" not in _read(tmp_path, "src/CLAUDE.md")


def test_excluded_names_match_any_case(tmp_path):  # 3, 4
    _write(tmp_path, "src/keep.py", "")
    _write(tmp_path, "src/Vendor/v.py", "")
    _write(tmp_path, "src/Fixtures/f.json", "{}")
    pages.run(tmp_path)
    assert not (tmp_path / "src/Vendor/CLAUDE.md").exists()
    assert not (tmp_path / "src/Fixtures/CLAUDE.md").exists()
    assert "`Fixtures/`" in _read(tmp_path, "src/CLAUDE.md")


def test_fixture_folder_gets_one_line_in_parent(tmp_path):  # 4
    _write(tmp_path, "tests/test_a.py", "")
    _write(tmp_path, "tests/fixtures/sample.json", "{}")
    _write(tmp_path, "tests/fixtures/more/other.json", "{}")
    pages.run(tmp_path)
    page = _read(tmp_path, "tests/CLAUDE.md")
    assert sum("`fixtures/`" in line for line in page.splitlines()) == 1


# ------------------------------------------------- a new page's content (5-6)

def test_new_page_has_sections(tmp_path):  # 5
    _project(tmp_path)
    pages.run(tmp_path)
    page = _read(tmp_path, "src/app/CLAUDE.md")
    headings = [ln for ln in page.splitlines() if ln.startswith("## ")]
    assert headings == ["## Purpose", "## Files", "## Rules", "## Links"]
    assert page.count(pages.BLOCK_START) == page.count(pages.BLOCK_END) == 1


def test_parent_page_one_line_per_subfolder(tmp_path):  # 6
    _write(tmp_path, "src/a/x.py", "")
    _write(tmp_path, "src/b/y.py", "")
    _write(tmp_path, "src/b/c/z.py", "")
    pages.run(tmp_path)
    page = _read(tmp_path, "src/CLAUDE.md")
    for sub in ["a", "b"]:
        assert sum(f"`{sub}/`" in line for line in page.splitlines()) == 1
    assert "`c/`" not in page
    assert "`c/`" in _read(tmp_path, "src/b/CLAUDE.md")


# --------------------------------------------------- docstring lines (7-9)

def test_python_docstring_first_line_in_block(tmp_path):  # 7
    _project(tmp_path)
    pages.run(tmp_path)
    assert _block(_read(tmp_path, "src/app/CLAUDE.md")) == ["- `main.py`: Start the app."]


@pytest.mark.parametrize("name,source,line", [
    ("a.ts", "/**\n * Parse the config.\n * @module cfg\n */\nexport {};\n", "Parse the config."),
    ("b.js", "#!/usr/bin/env node\n/** Run the CLI. */\n", "Run the CLI."),
    ("c.rs", "//!\n//! Hold the state.\n//! More.\n", "Hold the state."),
])
def test_doc_comment_first_line_in_block(tmp_path, name, source, line):  # 8
    _write(tmp_path, f"src/{name}", source)
    pages.run(tmp_path)
    assert _block(_read(tmp_path, "src/CLAUDE.md")) == [f"- `{name}`: {line}"]


def test_bom_does_not_hide_docstring(tmp_path):  # 7, 8
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.py").write_bytes(b'\xef\xbb\xbf"""Python doc."""\n')
    (tmp_path / "src/b.js").write_bytes(b"\xef\xbb\xbf/** JS doc. */\n")
    pages.run(tmp_path)
    assert _block(_read(tmp_path, "src/CLAUDE.md")) == ["- `a.py`: Python doc.", "- `b.js`: JS doc."]


def test_dotfile_gets_a_line(tmp_path):  # 9
    _write(tmp_path, "src/.env.example", "KEY=\n")
    pages.run(tmp_path)
    assert f"- `.env.example`: {pages.TYPED_FILE_HINT}" in _read(tmp_path, "src/CLAUDE.md")


@pytest.mark.parametrize("name,source", [
    ("plain.js", "/* a license header */\nexport const x = 1;\n"),
    ("late.js", "import x from 'y';\n/** Too late. */\n"),
    ("nodoc.py", "x = 1\n"),
    ("notes.txt", "Some notes.\n"),
])
def test_undocumented_file_starter_line_outside_block(tmp_path, name, source):  # 9
    _write(tmp_path, f"src/{name}", source)
    pages.run(tmp_path)
    page = _read(tmp_path, "src/CLAUDE.md")
    assert _block(page) == []
    assert f"- `{name}`: {pages.TYPED_FILE_HINT}" in _outside_block(page)
    _write(tmp_path, "src/new.py", "")
    pages.run(tmp_path)
    assert _block(_read(tmp_path, "src/CLAUDE.md")) == []


# ---------------------------------------------------------- reruns (10-14)

@pytest.mark.parametrize("page", PAGE_NAMES)
def test_rerun_unchanged_is_byte_identical(tmp_path, page):  # 10
    _project(tmp_path)
    pages.run(tmp_path, page)
    before = {p: p.read_bytes() for p in tmp_path.rglob(page)}
    assert before
    assert pages.run(tmp_path, page) == []
    assert {p: p.read_bytes() for p in tmp_path.rglob(page)} == before


def _type_into(root, rel):
    """Replace every hint with typed text, as a person would."""
    page = _read(root, rel)
    page = re.sub(r"<!--[^>]*-->", "typed by hand", page.replace(pages.BLOCK_START, "@@S")
                  .replace(pages.BLOCK_END, "@@E"))
    page = page.replace("@@S", pages.BLOCK_START).replace("@@E", pages.BLOCK_END)
    (root / rel).write_text(page, encoding="utf-8")
    return page


@pytest.mark.parametrize("page_name", PAGE_NAMES)
def test_docstring_edit_changes_only_block_line(tmp_path, page_name):  # 11
    _project(tmp_path)
    pages.run(tmp_path, page_name)
    typed = _type_into(tmp_path, f"src/app/{page_name}")
    _write(tmp_path, "src/app/main.py", '"""Boot the app."""\n')
    assert pages.run(tmp_path, page_name) == [("updated", f"src/app/{page_name}")]
    page = _read(tmp_path, f"src/app/{page_name}")
    assert _block(page) == ["- `main.py`: Boot the app."]
    assert _outside_block(page) == _outside_block(typed)


@pytest.mark.parametrize("page_name", PAGE_NAMES)
def test_rerun_keeps_crlf_typed_bytes(tmp_path, page_name):  # 11
    _project(tmp_path)
    pages.run(tmp_path, page_name)
    page = tmp_path / "src/app" / page_name
    page.write_bytes(page.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    _write(tmp_path, "src/app/main.py", '"""Boot the app."""\n')
    pages.run(tmp_path, page_name)
    raw = page.read_bytes()
    assert b"Boot the app." in raw
    assert raw.count(b"\n") == raw.count(b"\r\n")


@pytest.mark.parametrize("page_name", PAGE_NAMES)
def test_rerun_keeps_mixed_line_endings_outside_block(tmp_path, page_name):  # 11
    _project(tmp_path)
    pages.run(tmp_path, page_name)
    page = tmp_path / "src/app" / page_name
    raw = page.read_bytes().replace(b"## Purpose\n", b"## Purpose\r\n")
    page.write_bytes(raw)
    _write(tmp_path, "src/app/main.py", '"""Boot the app."""\n')
    pages.run(tmp_path, page_name)
    after = page.read_bytes()
    assert after.replace(b"Boot", b"Start") == raw


@pytest.mark.parametrize("page_name", PAGE_NAMES)
def test_deleted_file_leaves_block(tmp_path, page_name):  # 12
    _project(tmp_path)
    _write(tmp_path, "src/app/extra.py", '"""Extra helper."""\n')
    pages.run(tmp_path, page_name)
    assert len(_block(_read(tmp_path, f"src/app/{page_name}"))) == 2
    (tmp_path / "src/app/extra.py").unlink()
    pages.run(tmp_path, page_name)
    assert _block(_read(tmp_path, f"src/app/{page_name}")) == ["- `main.py`: Start the app."]


def test_block_sorted_and_stable(tmp_path):  # 13
    for name in ["zeta.py", "Alpha.py", "mid.py", "beta.py"]:
        _write(tmp_path, f"src/{name}", f'"""Doc for {name}."""\n')
    pages.run(tmp_path)
    block = _block(_read(tmp_path, "src/CLAUDE.md"))
    names = [line.split("`")[1] for line in block]
    assert names == sorted(names)
    (tmp_path / "src/CLAUDE.md").unlink()
    pages.run(tmp_path)
    assert _block(_read(tmp_path, "src/CLAUDE.md")) == block


@pytest.mark.parametrize("page_name", PAGE_NAMES)
def test_page_without_markers_skipped_untouched(tmp_path, capsys, page_name):  # 14
    _project(tmp_path)
    _write(tmp_path, f"src/app/{page_name}", "# Hand-written\n\nKeep me.\n")
    before = _bytes(tmp_path, f"src/app/{page_name}")
    assert ("skipped", f"src/app/{page_name}") in pages.run(tmp_path, page_name)
    assert _bytes(tmp_path, f"src/app/{page_name}") == before


# ------------------------------------------------ rules a page meets (15-16)

def test_links_resolve_and_no_at_outside_code(tmp_path):  # 15
    _project(tmp_path)
    _write(tmp_path, "src/app/cfg.py", '"""Load @config/settings.json."""\n')
    _write(tmp_path, "src/app/odd.py", '"""Ends <!-- /cairn:files --> here."""\n')
    _write(tmp_path, "ARCHITECTURE.md", "# arch\n")
    pages.run(tmp_path)
    page = tmp_path / "src/app/CLAUDE.md"
    page.write_text(_read(tmp_path, "src/app/CLAUDE.md")
                    + "[architecture](../../ARCHITECTURE.md)\n", encoding="utf-8")
    pages.run(tmp_path)
    before = page.read_bytes()
    assert pages.run(tmp_path) == []
    assert page.read_bytes() == before
    linked = 0
    for page in tmp_path.rglob("CLAUDE.md"):
        text = page.read_text(encoding="utf-8")
        assert "@" not in _strip_code(re.sub(r"<!--.*?-->", "", text, flags=re.S))
        for target in re.findall(r"\]\(([^)#]+)\)", text):
            assert (page.parent / target).exists()
            linked += 1
    assert linked == 1


def test_fresh_page_under_budget(tmp_path):  # 16
    for i in range(12):
        _write(tmp_path, f"src/module_{i:02}.py", f'"""Handle the part number {i} of the work."""\n')
    for i in range(3):
        _write(tmp_path, f"src/sub_{i}/x.py", "")
    pages.run(tmp_path)
    assert len(_bytes(tmp_path, "src/CLAUDE.md")) < 2048


# ------------------------------------------------------- robustness (17-18)

def test_unparseable_python_counts_as_undocumented(tmp_path):  # 17
    _write(tmp_path, "src/broken.py", '"""Looks fine."""\ndef (:\n')
    (tmp_path / "src/binary.py").write_bytes(b"\xff\xfe\x00")
    pages.run(tmp_path)
    page = _read(tmp_path, "src/CLAUDE.md")
    assert _block(page) == []
    assert f"- `broken.py`: {pages.TYPED_FILE_HINT}" in page


def test_git_and_non_git_give_same_pages(tmp_path):  # 18
    plain = _project(tmp_path / "plain")
    _write(plain, ".hidden/x.py", "")
    _write(plain, "src/vendor/v.py", "")
    repo = _project(tmp_path / "repo")
    _write(repo, ".hidden/x.py", "")
    _write(repo, "src/vendor/v.py", "")
    _git_init(repo)
    pages.run(plain)
    pages.run(repo)
    pages_of = lambda root: {p.relative_to(root).as_posix(): p.read_bytes()
                             for p in root.rglob("CLAUDE.md")}
    assert pages_of(plain) == pages_of(repo)
    assert set(pages_of(plain)) == {"src/CLAUDE.md", "src/app/CLAUDE.md", "tests/CLAUDE.md"}


# ----------------------------------------------------------------- CLI (19)

def test_cli_output_and_exit_codes(tmp_path, capsys):  # 19
    _project(tmp_path)
    _write(tmp_path, "tests/CLAUDE.md", "# mine\n")
    assert pages.main(["--cwd", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "created  src/CLAUDE.md" in out
    assert "skipped  tests/CLAUDE.md" in out

    _write(tmp_path, "src/app/main.py", '"""Boot the app."""\n')
    assert pages.main(["--cwd", str(tmp_path)]) == 0
    assert "updated  src/app/CLAUDE.md" in capsys.readouterr().out

    (tmp_path / "tests/CLAUDE.md").unlink()
    pages.run(tmp_path)
    assert pages.main(["--cwd", str(tmp_path)]) == 0
    assert "Every folder page is fresh." in capsys.readouterr().out

    assert pages.main(["--cwd", str(tmp_path / "missing")]) == 1
    assert "not a directory" in capsys.readouterr().err
