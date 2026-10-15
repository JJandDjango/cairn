"""Tests for local mode (features 18-21): render.py and pages.py with mode "local".

Focus: the .docs-local/ layout and the root note, that nothing tracked is
ever written, the exclude file (found through git, worktrees included),
reruns, and the `git clean -x` caution. The test numbers in comments are the
Pass 4 test list approved 2026-10-15; 15 is the test_pages parametrization,
20 is test_render's #21.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import pages
import render

TEMPLATES = Path(render.__file__).parent / "templates"
SKILL_DIR = Path(render.__file__).parent
TODAY = "2026-10-15"

LOCAL_SET = {
    ".docs-local/README.md",
    ".docs-local/ARCHITECTURE.md",
    ".docs-local/CONTRIBUTING.md",
    ".docs-local/CHANGELOG.md",
    ".docs-local/decisions/0001-record-architecture-decisions.md",
    ".docs-local/decisions/ADR-template.md",
    ".docs-local/docs/recipe-template.md",
    ".docs-local/docs/feature-template.md",
    ".docs-local/docs/design-template.md",
}
GITIGNORE = ".docs-local/.gitignore"
ROOT_NOTE = "CLAUDE.local.md"
IMPORTS = ["@.docs-local/README.md", "@.docs-local/ARCHITECTURE.md"]
TRACKED_ROOT = ["CLAUDE.md", "README.md", "ARCHITECTURE.md", "CONTRIBUTING.md",
                "CHANGELOG.md", "decisions", "docs"]
NONCODE_TYPES = ["novel", "content-site", "business", "research"]
ALL_TYPES = ["code"] + NONCODE_TYPES
LONG_INTENT = "x" * 200


@pytest.fixture(autouse=True)
def _no_parent_repo(monkeypatch, tmp_path):
    """Keep git from finding a repo above the test's temp folder."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))


def _answers(**overrides):
    answers = {
        "project_name": "demo",
        "intent": "why it exists",
        "project_type": "code",
        "adoption": "greenfield",
        "mode": "local",
    }
    answers.update(overrides)
    return answers


def _cli(root, **overrides):
    root.mkdir(parents=True, exist_ok=True)
    return render.main(["--answers", json.dumps(_answers(**overrides)), "--cwd", str(root)])


def _render(root, **overrides):
    root.mkdir(parents=True, exist_ok=True)
    render.render_all(_answers(**overrides), TEMPLATES, root, TODAY)
    return root


def _write(root, rel, text=""):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _read(root, rel):
    return (root / rel).read_text(encoding="utf-8")


def _files(root, under=""):
    base = root / under if under else root
    return {p.relative_to(root).as_posix() for p in base.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def _snapshot(root):
    return {rel: (root / rel).read_bytes() for rel in _files(root)}


def _strip_code(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`]*`", "", text)


def _git(root, *args):
    result = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
         "-c", "commit.gpgsign=false", *args],
        cwd=root, check=True, capture_output=True, text=True,
    )
    return result.stdout


def _commit_all(root):
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")


def _project(root):
    """A small code tree with docstrings."""
    _write(root, "src/app/main.py", '"""Start the app.\n\nMore detail."""\n')
    _write(root, "src/lib.rs", "//! The library root.\n")
    _write(root, "tests/test_main.py", "def test_x():\n    pass\n")
    return root


def _tracked_repo(root):
    """A committed repo with its own .gitignore, README.md and CLAUDE.md."""
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _write(root, ".gitignore", "build/\n")
    _write(root, "README.md", "# theirs\n")
    _write(root, "CLAUDE.md", "# their rules\n")
    _write(root, "src/app.py", '"""The app."""\n')
    _commit_all(root)
    return root


def _exclude(root):
    return root / ".git" / "info" / "exclude"


# ------------------------------------------------ feature 18, layout (1-7)

def test_local_render_writes_docs_local_and_root_note(tmp_path):  # 1
    root = _render(tmp_path)
    assert _files(root) == LOCAL_SET | {GITIGNORE, ROOT_NOTE}
    for rel in TRACKED_ROOT:
        assert not (root / rel).exists(), rel


def test_root_note_imports_resolve_and_keeps_machine_note(tmp_path):  # 2
    root = _render(tmp_path)
    text = _read(root, ROOT_NOTE)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert lines[:2] == IMPORTS
    for line in IMPORTS:
        assert (root / line[1:]).is_file(), line
    assert "# This machine" in text


@pytest.mark.parametrize("ptype", NONCODE_TYPES)
def test_noncode_types_same_set_without_diagram_and_status_row(tmp_path, ptype):  # 3
    root = _render(tmp_path / ptype, project_type=ptype)
    assert _files(root) == LOCAL_SET | {GITIGNORE, ROOT_NOTE}
    arch = _read(root, ".docs-local/ARCHITECTURE.md")
    assert "```mermaid" not in arch
    assert "status command" not in arch
    code_arch = _read(_render(tmp_path / "code"), ".docs-local/ARCHITECTURE.md")
    assert code_arch.count("```mermaid") == 1
    assert "status command" in code_arch


def test_code_project_gets_local_pages_same_as_tracked(tmp_path):  # 4
    local = _project(tmp_path / "local")
    assert _cli(local) == 0
    tracked = _project(tmp_path / "tracked")
    assert _cli(tracked, mode="tracked") == 0
    for rel in ["src", "src/app", "tests"]:
        page = _read(local, f"{rel}/CLAUDE.local.md")
        assert page == _read(tracked, f"{rel}/CLAUDE.md"), rel
    assert [ln for ln in page.splitlines() if ln.startswith("## ")] == \
        ["## Purpose", "## Files", "## Rules", "## Links"]
    assert page.count(pages.BLOCK_START) == page.count(pages.BLOCK_END) == 1
    assert not list(local.rglob("CLAUDE.md"))


def test_tracked_folder_claude_md_untouched_and_not_listed(tmp_path):  # 5
    root = _project(tmp_path)
    _git(root, "init", "-q")
    _write(root, "src/app/CLAUDE.md", "# Theirs\n\nKeep me.\n")
    _commit_all(root)
    before = (root / "src/app/CLAUDE.md").read_bytes()

    assert _cli(root) == 0
    assert (root / "src/app/CLAUDE.md").read_bytes() == before
    page = _read(root, "src/app/CLAUDE.local.md")
    assert "`CLAUDE.md`" not in page
    assert "`main.py`" in page

    _write(root, "src/app/main.py", '"""Boot the app."""\n')
    assert _cli(root) == 0
    assert (root / "src/app/CLAUDE.md").read_bytes() == before
    assert "- `main.py`: Boot the app." in _read(root, "src/app/CLAUDE.local.md")


@pytest.mark.parametrize("ptype", ALL_TYPES)
def test_links_resolve_no_at_outside_code_no_placeholder(tmp_path, ptype):  # 6
    root = _render(tmp_path, project_type=ptype, adoption="brownfield")
    link = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
    checked = 0
    for rel in _files(root, ".docs-local"):
        text = _read(root, rel)
        assert "{{" not in text, rel
        for target in link.findall(_strip_code(text)):
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue
            assert ((root / rel).parent / target.split("#")[0]).exists(), f"{rel} -> {target}"
            checked += 1
    assert checked > 0
    for rel in [".docs-local/README.md", ".docs-local/ARCHITECTURE.md"]:
        assert "@" not in _strip_code(_read(root, rel)), rel


@pytest.mark.parametrize("ptype", ALL_TYPES)
@pytest.mark.parametrize("adoption", ["greenfield", "brownfield"])
def test_budgets_hold_on_fresh_local_render(tmp_path, ptype, adoption):  # 7
    root = _render(tmp_path, project_type=ptype, adoption=adoption, intent=LONG_INTENT)
    for rel, budget in [(".docs-local/README.md", 2048), (".docs-local/ARCHITECTURE.md", 3072),
                        (".docs-local/CONTRIBUTING.md", 3072)]:
        assert len((root / rel).read_bytes()) <= budget, rel


# ------------------------------------- feature 19, nothing tracked is written (8-13)

def test_tracked_files_byte_identical_and_status_clean(tmp_path):  # 8
    root = _tracked_repo(tmp_path)
    before = {rel: (root / rel).read_bytes()
              for rel in [".gitignore", "README.md", "CLAUDE.md", "src/app.py"]}
    assert _cli(root) == 0
    for rel, data in before.items():
        assert (root / rel).read_bytes() == data, rel
    assert (root / ".docs-local/README.md").is_file()
    assert (root / "src/CLAUDE.local.md").is_file()
    assert _git(root, "status", "--porcelain").strip() == ""


def test_docs_local_gitignore_is_star_and_newline(tmp_path):  # 9
    assert _cli(tmp_path) == 0
    assert (tmp_path / GITIGNORE).read_bytes() == b"*\n"


def test_exclude_gains_note_once_keeps_content_creates_info(tmp_path):  # 10
    kept = tmp_path / "kept"
    kept.mkdir()
    _git(kept, "init", "-q")
    _exclude(kept).write_bytes(b"*.log")        # no trailing newline
    assert _cli(kept) == 0
    assert _cli(kept) == 0
    raw = _exclude(kept).read_bytes()
    assert raw.startswith(b"*.log\n")
    assert raw.decode("utf-8").splitlines().count(ROOT_NOTE) == 1

    fresh = tmp_path / "fresh"
    fresh.mkdir()
    _git(fresh, "init", "-q")
    shutil.rmtree(fresh / ".git" / "info")
    assert _cli(fresh) == 0
    assert _read(fresh, ".git/info/exclude").splitlines().count(ROOT_NOTE) == 1


def test_exclude_found_through_git_in_a_worktree(tmp_path):  # 11
    main_repo = _tracked_repo(tmp_path / "main")
    wt = tmp_path / "wt"
    _git(main_repo, "worktree", "add", "-q", str(wt))
    assert (wt / ".git").is_file()

    assert _cli(wt) == 0
    assert ROOT_NOTE in _read(main_repo, ".git/info/exclude").splitlines()
    assert _git(wt, "status", "--porcelain").strip() == ""
    assert _git(main_repo, "status", "--porcelain").strip() == ""


def test_outside_git_writes_files_skips_exclude_says_why(tmp_path, capsys):  # 12
    assert _cli(tmp_path) == 0
    out = capsys.readouterr().out
    assert _files(tmp_path) >= LOCAL_SET | {GITIGNORE, ROOT_NOTE}
    assert not (tmp_path / ".git").exists()
    assert sum("not a git repository" in line for line in out.splitlines()) == 1
    assert render.exclude_path(tmp_path) is None


@pytest.mark.parametrize("git", [False, True])
def test_root_gitignore_never_created_or_edited(tmp_path, git):  # 13
    root = tmp_path / "root"
    root.mkdir()
    if git:
        _git(root, "init", "-q")
    assert _cli(root) == 0
    assert not (root / ".gitignore").exists()

    other = tmp_path / "other"
    other.mkdir()
    (other / ".gitignore").write_bytes(b"node_modules/")
    if git:
        _git(other, "init", "-q")
    assert _cli(other) == 0
    assert (other / ".gitignore").read_bytes() == b"node_modules/"


# ------------------------------------------------------ feature 20, reruns (14-18)
# 15 (typed lines survive, a docstring edit changes only the block line) is the
# CLAUDE.local.md parametrization in test_pages.py.

def test_second_run_byte_identical_and_prints_no_created(tmp_path, capsys):  # 14
    root = _project(tmp_path)
    _git(root, "init", "-q")
    assert _cli(root) == 0
    first = _snapshot(root)
    exclude = _exclude(root).read_bytes()
    capsys.readouterr()

    assert _cli(root) == 0
    out = capsys.readouterr().out
    assert "created" not in out
    assert _snapshot(root) == first
    assert _exclude(root).read_bytes() == exclude


def test_edited_architecture_survives_rerun(tmp_path):  # 16
    root = _render(tmp_path)
    target = root / ".docs-local/ARCHITECTURE.md"
    target.write_bytes(b"mine\n")
    assert _cli(root) == 0
    assert target.read_bytes() == b"mine\n"


def test_gitignore_recreated_when_missing_never_overwritten(tmp_path):  # 17
    root = _render(tmp_path)
    (root / GITIGNORE).unlink()
    assert _cli(root) == 0
    assert (root / GITIGNORE).read_bytes() == b"*\n"

    (root / GITIGNORE).write_bytes(b"*\n!keep.md\n")
    assert _cli(root) == 0
    assert (root / GITIGNORE).read_bytes() == b"*\n!keep.md\n"


def test_existing_root_note_kept_and_imports_printed(tmp_path, capsys):  # 18
    (tmp_path / ROOT_NOTE).write_bytes(b"mine\n")
    assert _cli(tmp_path) == 0
    out = capsys.readouterr().out
    assert (tmp_path / ROOT_NOTE).read_bytes() == b"mine\n"
    assert f"skipped  {ROOT_NOTE}" in out
    for line in IMPORTS:
        assert line in out

    own = tmp_path / "own"
    assert _cli(own) == 0
    capsys.readouterr()
    assert _cli(own) == 0
    assert "add to" not in capsys.readouterr().out


# ---------------------------------------------------- feature 21, caution (19)

def test_every_local_run_names_git_clean_tracked_does_not(tmp_path, capsys):  # 19
    root = tmp_path / "local"
    assert _cli(root) == 0
    assert "git clean -x" in capsys.readouterr().out
    assert _cli(root) == 0
    assert "git clean -x" in capsys.readouterr().out

    assert _cli(tmp_path / "tracked", mode="tracked") == 0
    assert "git clean -x" not in capsys.readouterr().out


# ------------------------------------------------- mode handling and docs (21-22)

def test_cli_exit_0_on_success_1_when_exclude_unwritable(tmp_path, capsys):  # 21
    ok = tmp_path / "ok"
    ok.mkdir()
    _git(ok, "init", "-q")
    assert _cli(ok) == 0

    bad = tmp_path / "bad"
    bad.mkdir()
    _git(bad, "init", "-q")
    shutil.rmtree(bad / ".git" / "info")
    (bad / ".git" / "info").write_text("a file, not a folder\n", encoding="utf-8")
    capsys.readouterr()
    assert _cli(bad) == 1
    assert "ERROR" in capsys.readouterr().err
    assert _files(bad) == set()


def test_skill_md_no_longer_says_not_built_yet():  # 22
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "not built yet" not in text.lower()
    assert ".docs-local" in text
