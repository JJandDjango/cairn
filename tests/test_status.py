"""Tests for status.py: last done, next, and waiting on you.

Real git in tmp_path; gh is faked at the `_gh` seam (or one level below it,
at subprocess.run, where the seam itself is under test). No test reaches
the network: an autouse fixture fails any gh call that was not faked.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "cairn"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

import render  # noqa: E402
import status  # noqa: E402

REAL_GH = status._gh
REAL_RUN = subprocess.run
COMMIT_LINE = re.compile(r"^  [0-9a-f]{7,} ")


@pytest.fixture(autouse=True)
def _no_unfaked_gh(monkeypatch, tmp_path):
    def refuse(args, cwd):
        pytest.fail(f"gh was called without a fake: {args}")

    monkeypatch.setattr(status, "_gh", refuse)
    # A tmp dir outside any repo must not find a repo above it.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))


# ------------------------------------------------------------------ helpers

def _git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "-c", "commit.gpgsign=false", *args],
        cwd=cwd, check=True, capture_output=True,
    )


def _init(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    return path


def _commit(path: Path, subject: str) -> None:
    _git(path, "commit", "-q", "--allow-empty", "-m", subject)


def _repo(tmp_path: Path, subjects=("first", "second", "third")) -> Path:
    repo = _init(tmp_path / "repo")
    for subject in subjects:
        _commit(repo, subject)
    return repo


def _pr(n: int) -> dict:
    return {"number": n, "title": f"PR {n}", "mergedAt": f"2026-02-{n:02d}T00:00:00Z"}


def _issue(n: int, labels=(), title=None) -> dict:
    return {
        "number": n,
        "title": title or f"Issue {n}",
        "labels": [{"name": name} for name in labels],
        "createdAt": f"2026-01-{n:02d}T00:00:00Z",
    }


def _fake(monkeypatch, prs=(), issues=()):
    def fake(args, cwd):
        if args[:2] == ["pr", "list"]:
            return list(prs)
        if args[:2] == ["issue", "list"]:
            return list(issues)
        raise AssertionError(f"unexpected gh call: {args}")

    monkeypatch.setattr(status, "_gh", fake)


def _fake_gh_process(monkeypatch, behave):
    """Put the real `_gh` back and fake only the gh process under it."""
    monkeypatch.setattr(status, "_gh", REAL_GH)

    def run(argv, *args, **kwargs):
        if argv[0] == "gh":
            return behave(argv)
        return REAL_RUN(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)


def _run(repo: Path, capsys):
    code = status.main(["--cwd", str(repo)])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _sections(out: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    current = None
    for line in out.splitlines():
        if line and not line.startswith(" "):
            current = result.setdefault(line, [])
        elif line.strip() and current is not None:
            current.append(line.strip())
    return result


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


# ------------------------------------------------------------------ feature 15

def test_golden_output_three_sections(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    _fake(
        monkeypatch,
        prs=[_pr(1), _pr(2)],
        issues=[_issue(1), _issue(2, ["needs-ruling"]), _issue(3)],
    )
    log = subprocess.run(
        ["git", "log", "--no-merges", "--format=%h %s"], cwd=repo,
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    code, out, _ = _run(repo, capsys)
    assert code == 0
    expected = "\n".join([
        "Last done",
        *[f"  {line}" for line in log],
        "  #2 PR 2",
        "  #1 PR 1",
        "",
        "Next",
        "  #1 Issue 1",
        "  #3 Issue 3",
        "",
        "Waiting on you",
        "  #2 Issue 2",
        "",
    ])
    assert out == expected
    assert [h for h in out.splitlines() if h and not h.startswith(" ")] == [
        "Last done", "Next", "Waiting on you"]


def test_needs_ruling_issue_only_under_waiting(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    _fake(monkeypatch, issues=[_issue(1), _issue(2, ["needs-ruling"], "Rule on it")])
    _, out, _ = _run(repo, capsys)
    sections = _sections(out)
    assert sections["Waiting on you"] == ["#2 Rule on it"]
    assert sections["Next"] == ["#1 Issue 1"]
    assert "Rule on it" not in "\n".join(sections["Next"])


def test_last_done_caps_and_skips_merge_commits(tmp_path, monkeypatch, capsys):
    repo = _init(tmp_path / "repo")
    _commit(repo, "c1")
    _commit(repo, "c2")
    _git(repo, "checkout", "-q", "-b", "side")
    _commit(repo, "s1")
    _git(repo, "checkout", "-q", "-")
    _git(repo, "merge", "-q", "--no-ff", "-m", "Merge side branch", "side")
    for n in range(3, 7):
        _commit(repo, f"c{n}")
    _fake(monkeypatch, prs=[_pr(n) for n in range(1, 9)])
    _, out, _ = _run(repo, capsys)
    last = _sections(out)["Last done"]
    commits = [line for line in out.splitlines() if COMMIT_LINE.match(line)]
    assert len(commits) == 5
    assert all("Merge" not in line for line in commits)
    assert commits[0].endswith(" c6") and commits[3].endswith(" c3")
    assert not any(line.endswith(" c1") for line in commits)
    assert [line for line in last if line.startswith("#")] == [
        "#8 PR 8", "#7 PR 7", "#6 PR 6", "#5 PR 5", "#4 PR 4"]


def test_next_caps_issues_oldest_first(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    _fake(monkeypatch, issues=[_issue(n) for n in range(8, 0, -1)])
    _, out, _ = _run(repo, capsys)
    assert _sections(out)["Next"] == [f"#{n} Issue {n}" for n in range(1, 6)]


def test_empty_sections_print_none(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    _fake(monkeypatch, issues=[])
    _, out, _ = _run(repo, capsys)
    sections = _sections(out)
    assert sections["Next"] == ["(none)"]
    assert sections["Waiting on you"] == ["(none)"]
    assert list(sections) == ["Last done", "Next", "Waiting on you"]


def test_gh_missing_degrades(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)

    def missing(argv):
        raise FileNotFoundError("gh")

    _fake_gh_process(monkeypatch, missing)
    code, out, err = _run(repo, capsys)
    sections = _sections(out)
    assert code == 0
    assert "Traceback" not in out + err
    assert sum(bool(COMMIT_LINE.match(line)) for line in out.splitlines()) == 3
    assert any("merged PRs" in line and "gh is not installed" in line
               for line in sections["Last done"])
    assert "gh is not installed" in sections["Next"][0]
    assert "gh is not installed" in sections["Waiting on you"][0]


@pytest.mark.parametrize("stderr", [
    "To get started with GitHub CLI, please run:  gh auth login\nor set GH_TOKEN\n",
    "none of the git remotes configured for this repository point to a known GitHub host\n",
])
def test_gh_error_degrades_with_reason(tmp_path, monkeypatch, capsys, stderr):
    repo = _repo(tmp_path)
    reason = stderr.splitlines()[0]
    _fake_gh_process(
        monkeypatch,
        lambda argv: subprocess.CompletedProcess(argv, 1, stdout="", stderr=stderr),
    )
    code, out, _ = _run(repo, capsys)
    sections = _sections(out)
    assert code == 0
    assert sum(bool(COMMIT_LINE.match(line)) for line in out.splitlines()) == 3
    assert any(reason in line for line in sections["Last done"])
    assert reason in sections["Next"][0]
    assert reason in sections["Waiting on you"][0]
    assert "GH_TOKEN" not in out


def test_not_a_git_repo_exits_1(tmp_path, capsys):
    plain = tmp_path / "plain"
    plain.mkdir()
    code, out, err = _run(plain, capsys)
    assert code == 1
    assert "not a git repository" in err
    assert out == ""


def test_repo_without_commits(tmp_path, monkeypatch, capsys):
    repo = _init(tmp_path / "empty")
    _fake(monkeypatch)
    code, out, err = _run(repo, capsys)
    assert code == 0
    assert "(no commits yet)" in _sections(out)["Last done"]
    assert "fatal" not in out + err


def test_bad_cwd_exits_1(tmp_path, capsys):
    code, out, err = _run(tmp_path / "missing", capsys)
    assert code == 1
    assert "not a directory" in err


def test_gh_only_through_seam(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    _fake(monkeypatch, prs=[_pr(1)], issues=[_issue(1)])
    seen = []

    def record(argv, *args, **kwargs):
        seen.append(list(argv))
        return REAL_RUN(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", record)
    code, _, _ = _run(repo, capsys)
    assert code == 0
    assert seen
    assert not [argv for argv in seen if argv[0] == "gh"]


def _answers(project_type: str) -> str:
    return json.dumps({
        "project_name": "demo",
        "intent": "A demo project.",
        "project_type": project_type,
        "adoption": "greenfield",
        "mode": "tracked",
    })


def test_code_architecture_names_status_command(tmp_path, capsys):
    code_dir = tmp_path / "code"
    novel_dir = tmp_path / "novel"
    code_dir.mkdir()
    novel_dir.mkdir()
    assert render.main(["--answers", _answers("code"), "--cwd", str(code_dir)]) == 0
    assert render.main(["--answers", _answers("novel"), "--cwd", str(novel_dir)]) == 0
    capsys.readouterr()
    arch = (code_dir / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "`/cairn status`" in arch
    assert "(to be named)" not in arch
    novel_arch = (novel_dir / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "/cairn status" not in novel_arch
    assert "Last done, next, and what waits on you" not in novel_arch


def test_skill_dispatch_routes_status():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    dispatch = text[text.index("0. DISPATCH"):text.index("1. CONFIRM")]
    assert "`status`" in dispatch
    assert 'python "{skill-dir}/status.py" --cwd .' in text


# ------------------------------------------------------------------ feature 16

PLAN = "1. ~~Done step~~\n2. Second step\n3. Third step\n"


def _plan_repo(tmp_path: Path, plan_text: str | None, setting="docs/plan.md") -> Path:
    repo = _repo(tmp_path)
    if plan_text is not None:
        _write(repo / setting, plan_text)
    _git(repo, "config", "cairn.plan", setting)
    return repo


def test_plan_setting_replaces_issues_for_next(tmp_path, monkeypatch, capsys):
    repo = _plan_repo(tmp_path, PLAN)
    _fake(monkeypatch, issues=[_issue(1, title="Plain issue"),
                               _issue(2, ["needs-ruling"], "Rule on it")])
    code, out, _ = _run(repo, capsys)
    sections = _sections(out)
    assert code == 0
    assert sections["Next"] == ["Second step"]
    assert "Plain issue" not in out
    assert sections["Waiting on you"] == ["#2 Rule on it"]


@pytest.mark.parametrize("text, expected", [
    ("1. ~~All struck~~\n2. Live\n", "Live"),
    ("1. ~~**Pass 2**~~: done, PR #15\n2. Live\n", "Live"),
    ("1. [x] checked\n2. Live\n", "Live"),
    ("1. [X] checked\n2. Live\n", "Live"),
    ("1. Plain\n2. Live\n", "Plain"),
    ("1. [ ] open\n2. Live\n", "[ ] open"),
    ("1. Mid ~~struck~~ text\n", "Mid ~~struck~~ text"),
])
def test_done_markers(text, expected):
    assert status.next_step(text) == expected


def test_step_detection_rules():
    assert status.next_step("1. Dot step\n") == "Dot step"
    assert status.next_step("1) Paren step\n") == "Paren step"
    text = (
        "# Plan\n"
        "\n"
        "- bullet is not a step\n"
        "  1. indented is not a step\n"
        "```\n"
        "1. inside a fence is not a step\n"
        "```\n"
        "1) Real step\n"
        "   goes on here\n"
        "2. Later step\n"
    )
    assert status.next_step(text) == "Real step goes on here"
    assert [step for step, _ in status._steps(text)] == [
        "Real step goes on here", "Later step"]
    junk = "- bullet\n  1. indented\n```\n1. fenced\n```\n"
    assert status._steps(junk) == []
    assert status.next_step(junk) is None


def test_plan_file_missing(tmp_path, monkeypatch, capsys):
    repo = _plan_repo(tmp_path, None)
    _fake(monkeypatch, issues=[_issue(1, title="Plain issue")])
    code, out, _ = _run(repo, capsys)
    assert code == 0
    assert _sections(out)["Next"] == ["(plan file docs/plan.md not found)"]
    assert "Plain issue" not in out


def test_plan_all_steps_done(tmp_path, monkeypatch, capsys):
    repo = _plan_repo(tmp_path, "1. ~~One~~\n2. [x] Two\n")
    _fake(monkeypatch, issues=[_issue(1, title="Plain issue")])
    _, out, _ = _run(repo, capsys)
    assert _sections(out)["Next"] == ["(every step in docs/plan.md is done)"]
    assert "Plain issue" not in out


def test_no_setting_ignores_root_plan_md(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    _write(repo / "plan.md", "1. Root plan step\n")
    _fake(monkeypatch, issues=[_issue(1, title="Plain issue")])
    _, out, _ = _run(repo, capsys)
    assert _sections(out)["Next"] == ["#1 Plain issue"]
    assert "Root plan step" not in out


def test_plan_crlf_and_bom(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    lf = "1. ~~Done~~\n2. Café step\n   and more\n3. Last\n".encode("utf-8")
    crlf = b"\xef\xbb\xbf" + lf.replace(b"\n", b"\r\n")
    (repo / "docs").mkdir()
    (repo / "docs" / "lf.md").write_bytes(lf)
    (repo / "docs" / "crlf.md").write_bytes(crlf)
    _fake(monkeypatch)
    found = []
    for name in ("lf.md", "crlf.md"):
        _git(repo, "config", "cairn.plan", f"docs/{name}")
        _, out, _ = _run(repo, capsys)
        found.append(_sections(out)["Next"])
    assert found[0] == found[1] == ["Café step and more"]
