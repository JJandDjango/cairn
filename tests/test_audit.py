"""Tests for the audit driver's contract (skills/cairn/audit.py) that outlive the 1.x checks.

Focus: the JSON report shape, the exit code for bad usage, and the
report-only invariant (audit never writes). The 1.x check tests retired with
the checks in Pass 6; the 2.0 checks are tested in test_checks.py.
"""
import json

import pytest

import audit
import render


@pytest.fixture(autouse=True)
def _no_parent_repo(monkeypatch, tmp_path):
    """Keep git from finding a repo above the test's temp folder."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))


def _scaffold(root):
    root.mkdir(parents=True, exist_ok=True)
    answers = {"project_name": "demo", "intent": "why it exists",
               "project_type": "code", "adoption": "greenfield", "mode": "tracked"}
    assert render.main(["--answers", json.dumps(answers), "--cwd", str(root)]) == 0
    return root


def _break(root):
    """Push README.md over its byte budget: one SIZE-BUDGET error."""
    readme = root / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\n" + "x" * 2100 + "\n",
                      encoding="utf-8")


def _stats(root):
    return {p: (p.stat().st_size, p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def test_json_format_parses_and_carries_summary(tmp_path, capsys):
    root = _scaffold(tmp_path)
    _break(root)
    capsys.readouterr()
    exit_code = audit.main(["--cwd", str(root), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["summary"]["errors"] >= 1
    assert any(f["code"] == "SIZE-BUDGET" for f in payload["findings"])
    assert set(payload["findings"][0]) == {"severity", "code", "message", "path"}


def test_clean_json_report_has_empty_findings(tmp_path, capsys):
    root = _scaffold(tmp_path)
    capsys.readouterr()
    assert audit.main(["--cwd", str(root), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"] == []
    assert payload["summary"] == {"errors": 0, "warnings": 0, "infos": 0}


def test_not_a_directory_exits_2(tmp_path):
    assert audit.main(["--cwd", str(tmp_path / "missing")]) == 2


def test_audit_never_writes(tmp_path, capsys):
    root = _scaffold(tmp_path)
    _break(root)
    before = _stats(root)
    audit.main(["--cwd", str(root)])
    audit.main(["--cwd", str(root), "--format", "json"])
    capsys.readouterr()
    assert _stats(root) == before
