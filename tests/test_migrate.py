"""Tests for /cairn migrate (feature 29): skills/cairn/migrate.py.

Focus: the dry run prints the plan and writes nothing; --apply does only the
mechanical moves (rename or append, nothing overwritten, a source removed only
after its text is found in the destination); STATE.md is never touched;
over-budget results are reported, never trimmed; local mode migrates inside
.docs-local/. The test numbers in comments are the Pass 6 test list approved
2026-10-15 (plan.md, items 1-13). migrate is imported inside _run, so a missing
module fails each test on its own rather than the whole file at collection.
"""
import builtins
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import audit
import render
import spine_1x

SKILL_DIR = Path(render.__file__).parent
MIGRATE = SKILL_DIR / "migrate.py"

NOTHING = "nothing to migrate"
ROUTE_DEST = "(Claude: route its parts, then remove)"
LINE = {
    "MAP.md": "MAP.md -> ARCHITECTURE.md [rename]",
    "THEORY.md": "THEORY.md -> ARCHITECTURE.md [append]",
    "CONVENTIONS.md": "CONVENTIONS.md -> CONTRIBUTING.md [append]",
    "DOCS-SYSTEM.md": "DOCS-SYSTEM.md -> CONTRIBUTING.md [append]",
    "STATE.md": f"STATE.md -> {ROUTE_DEST} [route]",
}
ALL_LINES = list(LINE.values())
LOCAL = ".docs-local"


@pytest.fixture(autouse=True)
def _no_parent_repo(monkeypatch, tmp_path):
    """Keep git from finding a repo above the test's temp folder."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))


def _run(capsys, root, *flags):
    """Run migrate.main in process; return (exit code, stdout, stderr)."""
    import migrate
    capsys.readouterr()
    code = migrate.main(["--cwd", str(root), *flags])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _lines(out):
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _snapshot(root):
    """Every file's bytes and mtime, every folder, so 'writes nothing' is exact."""
    snap = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        snap[rel] = (p.read_bytes(), p.stat().st_mtime_ns) if p.is_file() else None
    return snap


def _under(snap, *prefixes):
    return {k: v for k, v in snap.items() if k.startswith(prefixes)}


def _answers(mode, **overrides):
    answers = {"project_name": "demo", "intent": "why it exists",
               "project_type": "code", "adoption": "greenfield", "mode": mode}
    answers.update(overrides)
    return answers


def _build2(root, mode="tracked", **overrides):
    """Render a 2.0 spine through the CLI, as a user would."""
    root.mkdir(parents=True, exist_ok=True)
    assert render.main(["--answers", json.dumps(_answers(mode, **overrides)),
                        "--cwd", str(root)]) == 0
    return root


def _read(root, rel):
    return (root / rel).read_bytes()


def _heading_then(data, filename, text):
    """True when data holds a '## From <filename>' line followed by text verbatim."""
    pattern = (rb"^## From " + re.escape(filename.encode()) + rb"\r?\n(?:\r?\n)*"
               + re.escape(text))
    return re.search(pattern, data, re.M) is not None


def _count_heading(data, filename):
    return len(re.findall(rb"^## From " + re.escape(filename.encode()) + rb"\r?$", data, re.M))


# ------------------------------------------------------ plan step: dry run (1-3)

def test_dry_run_prints_one_line_per_file_and_writes_nothing(tmp_path, capsys):  # 1
    spine_1x.write_1x(tmp_path)
    spine_1x.write_history(tmp_path)
    before = _snapshot(tmp_path)

    code, out, err = _run(capsys, tmp_path)
    assert code == 0
    assert sorted(_lines(out)) == sorted(ALL_LINES)
    assert _snapshot(tmp_path) == before

    import migrate
    actions = migrate.plan(tmp_path)
    assert sorted(f"{a.source} -> {a.dest} [{a.op}]" for a in actions) == sorted(ALL_LINES)
    assert _snapshot(tmp_path) == before


def test_cli_runs_as_a_script(tmp_path):  # 1
    spine_1x.write_1x(tmp_path)
    before = _snapshot(tmp_path)

    dry = subprocess.run([sys.executable, str(MIGRATE), "--cwd", str(tmp_path)],
                         capture_output=True, text=True)
    assert dry.returncode == 0, dry.stderr
    assert sorted(_lines(dry.stdout)) == sorted(ALL_LINES)
    assert _snapshot(tmp_path) == before

    applied = subprocess.run([sys.executable, str(MIGRATE), "--cwd", str(tmp_path), "--apply"],
                             capture_output=True, text=True)
    assert applied.returncode == 0, applied.stderr
    assert (tmp_path / "ARCHITECTURE.md").is_file()
    assert (tmp_path / "CONTRIBUTING.md").is_file()
    assert not (tmp_path / "MAP.md").exists()


@pytest.mark.parametrize("flags", [[], ["--apply"]])
@pytest.mark.parametrize("case", ["empty", "tracked-2.0", "local-2.0", "history-only"])
def test_nothing_to_migrate(tmp_path, capsys, case, flags):  # 2
    if case == "tracked-2.0":
        _build2(tmp_path)
    elif case == "local-2.0":
        _build2(tmp_path, "local")
    elif case == "history-only":
        spine_1x.write_history(tmp_path)
    before = _snapshot(tmp_path)

    code, out, err = _run(capsys, tmp_path, *flags)
    assert code == 0
    assert out.strip() == NOTHING
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("name", spine_1x.NAMES)
def test_each_file_alone_is_planned_correctly(tmp_path, capsys, name):  # 3
    spine_1x.write_1x(tmp_path, [name])
    before = _snapshot(tmp_path)
    code, out, err = _run(capsys, tmp_path)
    assert code == 0
    assert _lines(out) == [LINE[name]]
    assert _snapshot(tmp_path) == before

    import migrate
    [action] = migrate.plan(tmp_path)
    assert (action.source, action.op) == (name, LINE[name].rsplit("[", 1)[1].rstrip("]"))


def test_map_is_appended_not_renamed_when_architecture_exists(tmp_path, capsys):  # 3
    (tmp_path / "ARCHITECTURE.md").write_text("# Mine\n", encoding="utf-8")
    spine_1x.write_1x(tmp_path, ["MAP.md"])
    before = _snapshot(tmp_path)
    code, out, err = _run(capsys, tmp_path)
    assert code == 0
    assert _lines(out) == ["MAP.md -> ARCHITECTURE.md [append]"]
    assert _snapshot(tmp_path) == before


# ------------------------------------------------- apply step: the moves (4-7)

def test_map_becomes_architecture_with_frontmatter_verbatim(tmp_path, capsys):  # 4
    texts = spine_1x.write_1x(tmp_path, ["MAP.md"])
    assert texts["MAP.md"].startswith(b"---\n")
    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err
    assert _read(tmp_path, "ARCHITECTURE.md") == texts["MAP.md"]
    assert not (tmp_path / "MAP.md").exists()


def test_renamed_map_stays_first_when_theory_follows(tmp_path, capsys):  # 4, 5
    texts = spine_1x.write_1x(tmp_path, ["MAP.md", "THEORY.md"])
    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err
    arch = _read(tmp_path, "ARCHITECTURE.md")
    assert arch.startswith(texts["MAP.md"])
    assert _heading_then(arch[len(texts["MAP.md"]):], "THEORY.md", texts["THEORY.md"])
    assert b"## From MAP.md" not in arch
    assert not (tmp_path / "MAP.md").exists()
    assert not (tmp_path / "THEORY.md").exists()


@pytest.mark.parametrize("existing", [None, b"# Mine\n\nHand-written.\n"],
                         ids=["new-destination", "existing-destination"])
@pytest.mark.parametrize("theory", [
    pytest.param(spine_1x.TEXTS["THEORY.md"].encode("utf-8"), id="plain"),
    pytest.param(b"# Theory\r\n\r\nTHEORY-CRLF\r\nline two\r\n", id="crlf"),
    pytest.param("# Theory\n\nno trailing newline café".encode("utf-8"), id="no-newline"),
])
def test_theory_is_appended_under_a_heading_verbatim(tmp_path, capsys, existing, theory):  # 5
    spine_1x.write_1x(tmp_path, ["THEORY.md"], texts={"THEORY.md": theory})
    if existing is not None:
        (tmp_path / "ARCHITECTURE.md").write_bytes(existing)
    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err
    arch = _read(tmp_path, "ARCHITECTURE.md")
    assert _heading_then(arch, "THEORY.md", theory)
    assert _count_heading(arch, "THEORY.md") == 1
    assert not (tmp_path / "THEORY.md").exists()


def test_conventions_and_docs_system_create_contributing_in_order(tmp_path, capsys):  # 6
    texts = spine_1x.write_1x(tmp_path, ["DOCS-SYSTEM.md", "CONVENTIONS.md"])
    assert not (tmp_path / "CONTRIBUTING.md").exists()
    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err
    contrib = _read(tmp_path, "CONTRIBUTING.md")
    assert _heading_then(contrib, "CONVENTIONS.md", texts["CONVENTIONS.md"])
    assert _heading_then(contrib, "DOCS-SYSTEM.md", texts["DOCS-SYSTEM.md"])
    assert _count_heading(contrib, "CONVENTIONS.md") == 1
    assert _count_heading(contrib, "DOCS-SYSTEM.md") == 1
    assert contrib.index(b"## From CONVENTIONS.md") < contrib.index(b"## From DOCS-SYSTEM.md")
    assert not (tmp_path / "CONVENTIONS.md").exists()
    assert not (tmp_path / "DOCS-SYSTEM.md").exists()
    assert not (tmp_path / "ARCHITECTURE.md").exists()


@pytest.mark.parametrize("old", ["rendered", b"# Mine\n\nHand-written.\n", b"no trailing newline"],
                         ids=["rendered", "hand-written", "no-trailing-newline"])
def test_existing_destinations_are_never_overwritten(tmp_path, capsys, old):  # 7
    if old == "rendered":
        _build2(tmp_path)
        old_arch, old_contrib = _read(tmp_path, "ARCHITECTURE.md"), _read(tmp_path, "CONTRIBUTING.md")
    else:
        old_arch = old_contrib = old
        (tmp_path / "ARCHITECTURE.md").write_bytes(old)
        (tmp_path / "CONTRIBUTING.md").write_bytes(old)
    texts = spine_1x.write_1x(tmp_path, [n for n in spine_1x.NAMES if n != "STATE.md"])
    others = _under(_snapshot(tmp_path), "README.md", "CLAUDE.md", "CHANGELOG.md", "decisions/")

    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err

    arch = _read(tmp_path, "ARCHITECTURE.md")
    assert arch.startswith(old_arch)
    tail = arch[len(old_arch):]
    assert _heading_then(tail, "MAP.md", texts["MAP.md"])
    assert _heading_then(tail, "THEORY.md", texts["THEORY.md"])
    assert tail.index(b"## From MAP.md") < tail.index(b"## From THEORY.md")

    contrib = _read(tmp_path, "CONTRIBUTING.md")
    assert contrib.startswith(old_contrib)
    tail = contrib[len(old_contrib):]
    assert _heading_then(tail, "CONVENTIONS.md", texts["CONVENTIONS.md"])
    assert _heading_then(tail, "DOCS-SYSTEM.md", texts["DOCS-SYSTEM.md"])
    assert tail.index(b"## From CONVENTIONS.md") < tail.index(b"## From DOCS-SYSTEM.md")

    for name in ("MAP.md", "THEORY.md", "CONVENTIONS.md", "DOCS-SYSTEM.md"):
        assert not (tmp_path / name).exists(), name
    assert _under(_snapshot(tmp_path), "README.md", "CLAUDE.md", "CHANGELOG.md",
                  "decisions/") == others


# ----------------------------------------------- verify before delete (8), STATE (9)

class _Chop:
    """A file proxy that drops the last bytes of everything written to it."""

    def __init__(self, f):
        self._f = f

    def write(self, data):
        self._f.write(data[:-4])
        return len(data)

    def __getattr__(self, attr):
        return getattr(self._f, attr)

    def __enter__(self):
        self._f.__enter__()
        return self

    def __exit__(self, *exc):
        return self._f.__exit__(*exc)


def _corrupt_destination_writes(monkeypatch):
    """Every write to an ARCHITECTURE.md* or CONTRIBUTING.md* loses its tail, so
    the merged text can never contain the whole source."""
    real = io.open

    def fake(file, mode="r", *args, **kwargs):
        f = real(file, mode, *args, **kwargs)
        try:
            name = Path(os.fspath(file)).name
        except TypeError:
            return f
        if any(c in mode for c in "wa+") and name.startswith(("ARCHITECTURE.md", "CONTRIBUTING.md")):
            return _Chop(f)
        return f

    monkeypatch.setattr(io, "open", fake)
    monkeypatch.setattr(builtins, "open", fake)


@pytest.mark.parametrize("name,dest", [("THEORY.md", "ARCHITECTURE.md"),
                                       ("CONVENTIONS.md", "CONTRIBUTING.md"),
                                       ("DOCS-SYSTEM.md", "CONTRIBUTING.md")])
def test_source_kept_and_exit_1_when_text_not_found_in_destination(
        tmp_path, capsys, monkeypatch, name, dest):  # 8
    texts = spine_1x.write_1x(tmp_path, [name])
    (tmp_path / dest).write_text("# Mine\n", encoding="utf-8")
    _corrupt_destination_writes(monkeypatch)

    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 1
    assert err.strip() != ""
    assert (tmp_path / name).read_bytes() == texts[name]
    assert texts[name] not in (tmp_path / dest).read_bytes()


# ---------------------------------------------------------------- STATE.md (9)

def test_state_is_never_touched_by_apply(tmp_path, capsys):  # 9
    texts = spine_1x.write_1x(tmp_path)
    state_before = _under(_snapshot(tmp_path), "STATE.md")

    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err
    assert _under(_snapshot(tmp_path), "STATE.md") == state_before
    assert (tmp_path / "STATE.md").read_bytes() == texts["STATE.md"]
    assert LINE["STATE.md"] in _lines(out)
    assert b"STATE-BODY-5e6f" not in _read(tmp_path, "ARCHITECTURE.md")
    assert b"STATE-BODY-5e6f" not in _read(tmp_path, "CONTRIBUTING.md")


def test_state_alone_is_only_listed(tmp_path, capsys):  # 9
    spine_1x.write_1x(tmp_path, ["STATE.md"])
    before = _snapshot(tmp_path)
    for flags in ([], ["--apply"]):
        code, out, err = _run(capsys, tmp_path, *flags)
        assert code == 0
        assert _lines(out) == [LINE["STATE.md"]]
        assert _snapshot(tmp_path) == before


# ------------------------------------------------------------- idempotent (10)

@pytest.mark.parametrize("with_state", [False, True])
def test_second_apply_changes_no_byte(tmp_path, capsys, with_state):  # 10
    names = spine_1x.NAMES if with_state else [n for n in spine_1x.NAMES if n != "STATE.md"]
    spine_1x.write_1x(tmp_path, names)
    spine_1x.write_history(tmp_path)

    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err
    after_first = _snapshot(tmp_path)

    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err
    assert _snapshot(tmp_path) == after_first
    if with_state:
        assert _lines(out) == [LINE["STATE.md"]]
    else:
        assert out.strip() == NOTHING


# ----------------------------------------------------------------- budgets (11)

@pytest.mark.parametrize("name,dest", [("THEORY.md", "ARCHITECTURE.md"),
                                       ("CONVENTIONS.md", "CONTRIBUTING.md"),
                                       ("DOCS-SYSTEM.md", "CONTRIBUTING.md")])
def test_over_budget_destination_is_reported_not_trimmed(tmp_path, capsys, name, dest):  # 11
    _build2(tmp_path)
    big = b"# Big\n\nBIG-BODY\n" + b"x" * 3500 + b"\n"
    spine_1x.write_1x(tmp_path, [name], texts={name: big})

    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err
    merged = _read(tmp_path, dest)
    assert big in merged
    over = [m for m in (re.fullmatch(r"OVERBUDGET (\S*" + re.escape(dest) + r") (\d+) > (\d+)", ln)
                        for ln in _lines(out)) if m]
    assert len(over) == 1
    assert int(over[0].group(2)) == len(merged)
    assert int(over[0].group(3)) == audit.TOP_BUDGETS[dest]
    assert len(merged) > audit.TOP_BUDGETS[dest]
    assert len([ln for ln in _lines(out) if ln.startswith("OVERBUDGET")]) == 1


def test_renamed_map_over_budget_is_reported(tmp_path, capsys):  # 11
    big = b"# Map\n\n" + b"x" * 3500 + b"\n"
    spine_1x.write_1x(tmp_path, ["MAP.md"], texts={"MAP.md": big})
    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err
    assert _read(tmp_path, "ARCHITECTURE.md") == big
    assert re.search(r"^OVERBUDGET \S*ARCHITECTURE\.md %d > %d$" % (len(big), audit.TOP_BUDGETS["ARCHITECTURE.md"]),
                     out, re.M)


def test_within_budget_prints_no_overbudget(tmp_path, capsys):  # 11
    _build2(tmp_path)
    spine_1x.write_1x(tmp_path, [n for n in spine_1x.NAMES if n != "STATE.md"])
    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err
    assert "OVERBUDGET" not in out
    assert audit.main(["--cwd", str(tmp_path)]) == 0


# ----------------------------------------------------- decisions/ and docs/ (12)

def test_decisions_and_docs_untouched_tracked(tmp_path, capsys):  # 12
    _build2(tmp_path)
    spine_1x.write_history(tmp_path)
    spine_1x.write_1x(tmp_path)
    before = _under(_snapshot(tmp_path), "decisions", "docs")
    assert any(k.startswith("decisions/") for k in before)
    assert "docs/guide.md" in before

    for flags in ([], ["--apply"]):
        code, out, err = _run(capsys, tmp_path, *flags)
        assert code == 0, err
        assert _under(_snapshot(tmp_path), "decisions", "docs") == before


# ----------------------------------------------------------------- local (13)

def test_local_mode_migrates_inside_docs_local_only(tmp_path, capsys):  # 13
    _build2(tmp_path, "local")
    assert (tmp_path / LOCAL / "ARCHITECTURE.md").is_file()
    spine_1x.write_history(tmp_path, LOCAL)
    texts = spine_1x.write_1x(tmp_path, top=LOCAL)
    old_arch = _read(tmp_path, f"{LOCAL}/ARCHITECTURE.md")
    old_contrib = _read(tmp_path, f"{LOCAL}/CONTRIBUTING.md")
    snap = _snapshot(tmp_path)
    outside = {k: v for k, v in snap.items() if not k.startswith(LOCAL)}
    kept = _under(snap, f"{LOCAL}/.gitignore", f"{LOCAL}/README.md", f"{LOCAL}/decisions",
                  f"{LOCAL}/docs", f"{LOCAL}/CHANGELOG.md")

    code, out, err = _run(capsys, tmp_path)
    assert code == 0, err
    assert sorted(_lines(out)) == sorted([
        f"{LOCAL}/MAP.md -> {LOCAL}/ARCHITECTURE.md [append]",
        f"{LOCAL}/THEORY.md -> {LOCAL}/ARCHITECTURE.md [append]",
        f"{LOCAL}/CONVENTIONS.md -> {LOCAL}/CONTRIBUTING.md [append]",
        f"{LOCAL}/DOCS-SYSTEM.md -> {LOCAL}/CONTRIBUTING.md [append]",
        f"{LOCAL}/STATE.md -> {ROUTE_DEST} [route]",
    ])
    assert _snapshot(tmp_path) == snap

    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err

    arch = _read(tmp_path, f"{LOCAL}/ARCHITECTURE.md")
    assert arch.startswith(old_arch)
    assert _heading_then(arch[len(old_arch):], "MAP.md", texts["MAP.md"])
    assert _heading_then(arch[len(old_arch):], "THEORY.md", texts["THEORY.md"])
    contrib = _read(tmp_path, f"{LOCAL}/CONTRIBUTING.md")
    assert contrib.startswith(old_contrib)
    assert _heading_then(contrib[len(old_contrib):], "CONVENTIONS.md", texts["CONVENTIONS.md"])
    assert _heading_then(contrib[len(old_contrib):], "DOCS-SYSTEM.md", texts["DOCS-SYSTEM.md"])

    for name in ("MAP.md", "THEORY.md", "CONVENTIONS.md", "DOCS-SYSTEM.md"):
        assert not (tmp_path / LOCAL / name).exists(), name
    assert (tmp_path / LOCAL / "STATE.md").read_bytes() == texts["STATE.md"]
    assert LINE["STATE.md"].replace("STATE.md", f"{LOCAL}/STATE.md", 1) in _lines(out)

    after = _snapshot(tmp_path)
    assert {k: v for k, v in after.items() if not k.startswith(LOCAL)} == outside
    assert _under(after, f"{LOCAL}/.gitignore", f"{LOCAL}/README.md", f"{LOCAL}/decisions",
                  f"{LOCAL}/docs", f"{LOCAL}/CHANGELOG.md") == kept
    for name in ("ARCHITECTURE.md", "CONTRIBUTING.md", "MAP.md", "THEORY.md"):
        assert not (tmp_path / name).exists(), name


def test_local_mode_second_apply_changes_no_byte(tmp_path, capsys):  # 13, 10
    _build2(tmp_path, "local")
    spine_1x.write_1x(tmp_path, [n for n in spine_1x.NAMES if n != "STATE.md"], top=LOCAL)
    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err
    after_first = _snapshot(tmp_path)
    code, out, err = _run(capsys, tmp_path, "--apply")
    assert code == 0, err
    assert out.strip() == NOTHING
    assert _snapshot(tmp_path) == after_first
