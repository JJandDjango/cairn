"""Tests for the zero-dep spine auditor (skills/cairn/audit.py).

Focus: the acceptance constraint (a freshly rendered scaffold passes its own
audit), each finding code firing on a deliberately broken spine, exit-code
contract (0 clean / 1 findings / 2 no spine), and the report-only invariant
(audit never writes). Git-dependent checks are guarded so the suite stays
green without git.
"""
import json
import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest

import audit
import render

TEMPLATES = Path(render.__file__).parent / "templates"


def _scaffold(root, **overrides):
    answers = {
        "project_name": "demo",
        "intent": "why it exists",
        "project_type": "code",
        "backend": "none",
        "material": "greenfield",
    }
    answers.update(overrides)
    root.mkdir(parents=True, exist_ok=True)
    # Stamp with the real today so mtime-based freshness sees a fresh spine.
    render.render_all(answers, TEMPLATES, root, date.today().isoformat())
    return root


def _actionable(findings):
    """Codes of findings that affect the exit code (ERROR + WARN)."""
    return [f.code for f in findings if f.severity in ("ERROR", "WARN")]


# ------------------------------------------------- fresh scaffolds are clean

def test_fresh_greenfield_code_scaffold_is_clean(tmp_path):
    root = _scaffold(tmp_path)
    findings = audit.run_audit(root)
    assert _actionable(findings) == []
    assert audit.main(["--cwd", str(root)]) == 0


def test_fresh_novel_scaffold_is_clean_with_zero_diagram_info(tmp_path):
    root = _scaffold(tmp_path, project_type="novel")
    findings = audit.run_audit(root)
    assert _actionable(findings) == []
    infos = [f.code for f in findings if f.severity == "INFO"]
    assert "DIAGRAM-COUNT" in infos  # zero diagrams is fine for non-code
    assert audit.main(["--cwd", str(root)]) == 0


def test_brownfield_scaffold_flags_exactly_the_inferred_tag(tmp_path):
    root = _scaffold(tmp_path, material="brownfield")
    findings = audit.run_audit(root)
    assert _actionable(findings) == ["INFERRED-TAG"]
    assert audit.main(["--cwd", str(root)]) == 1


# --------------------------------------------------------- MAP <-> docs/ links

def test_map_row_linking_missing_doc_is_an_error(tmp_path):
    root = _scaffold(tmp_path)
    map_path = root / "MAP.md"
    map_path.write_text(
        map_path.read_text(encoding="utf-8").rstrip("\n")
        + "\n| widget | does x | new | docs/widget.md |\n",
        encoding="utf-8",
    )
    codes = _actionable(audit.run_audit(root))
    assert "MAP-DOC-MISSING" in codes


def test_map_row_with_no_doc_yet_is_clean_and_existing_link_ok(tmp_path):
    root = _scaffold(tmp_path)
    (root / "docs" / "widget.md").write_text("# widget\n", encoding="utf-8")
    map_path = root / "MAP.md"
    map_path.write_text(
        map_path.read_text(encoding="utf-8").rstrip("\n")
        + "\n| widget | does x | new | `docs/widget.md` |\n"
        + "| gadget | does y | new | no doc yet |\n",
        encoding="utf-8",
    )
    findings = audit.run_audit(root)
    assert "MAP-DOC-MISSING" not in [f.code for f in findings]


def test_unreferenced_docs_page_is_an_orphan_info(tmp_path):
    root = _scaffold(tmp_path)
    (root / "docs" / "stray.md").write_text("# stray\n", encoding="utf-8")
    findings = audit.run_audit(root)
    orphans = [f for f in findings if f.code == "DOCS-ORPHAN"]
    assert len(orphans) == 1 and orphans[0].severity == "INFO"
    assert orphans[0].path == "docs/stray.md"


# ------------------------------------------------------------------ diagrams

def test_second_diagram_and_wrong_placement_are_flagged(tmp_path):
    root = _scaffold(tmp_path)
    theory = root / "THEORY.md"
    theory.write_text(
        theory.read_text(encoding="utf-8") + "\n```mermaid\nflowchart TD\nA-->B\n```\n",
        encoding="utf-8",
    )
    codes = _actionable(audit.run_audit(root))
    assert "DIAGRAM-COUNT" in codes
    assert "DIAGRAM-PLACE" in codes


# ------------------------------------------------------------------- budgets

def test_theory_over_one_page_warns(tmp_path):
    root = _scaffold(tmp_path)
    theory = root / "THEORY.md"
    theory.write_text(
        theory.read_text(encoding="utf-8") + "filler\n" * 100, encoding="utf-8"
    )
    assert "BUDGET-THEORY" in _actionable(audit.run_audit(root))


def test_adr_over_half_page_warns(tmp_path):
    root = _scaffold(tmp_path)
    (root / "decisions" / "0002-long.md").write_text(
        "# 2. Long\n" + "line\n" * 60, encoding="utf-8"
    )
    assert "BUDGET-ADR" in _actionable(audit.run_audit(root))


# ---------------------------------------------------------------------- ADRs

def test_dangling_supersede_reference_is_an_error(tmp_path):
    root = _scaffold(tmp_path)
    (root / "decisions" / "0002-choice.md").write_text(
        "# 2. Choice\n\nStatus: superseded by 9999\n", encoding="utf-8"
    )
    assert "ADR-SUPERSEDE" in _actionable(audit.run_audit(root))


def test_duplicate_adr_number_is_an_error(tmp_path):
    root = _scaffold(tmp_path)
    (root / "decisions" / "0001-other.md").write_text(
        "# 1. Other\n", encoding="utf-8"
    )
    assert "ADR-DUP" in _actionable(audit.run_audit(root))


# ----------------------------------------------------------- STATE freshness

def test_backdated_state_stamp_warns_via_mtime_path(tmp_path):
    root = _scaffold(tmp_path)
    state = root / "STATE.md"
    state.write_text(
        state.read_text(encoding="utf-8").replace(
            date.today().isoformat(), "2020-01-01"
        ),
        encoding="utf-8",
    )
    assert "STATE-STALE" in _actionable(audit.run_audit(root))


def test_state_without_stamp_warns(tmp_path):
    root = _scaffold(tmp_path)
    (root / "STATE.md").write_text("# State - demo\n\n## Now\n", encoding="utf-8")
    assert "STATE-STALE" in _actionable(audit.run_audit(root))


# ------------------------------------------------------- docs/ covers marker

def test_stale_covered_page_warns_and_fresh_page_is_clean(tmp_path):
    root = _scaffold(tmp_path)
    src = root / "src"
    src.mkdir()
    (src / "thing.py").write_text("x = 1\n", encoding="utf-8")

    page = root / "docs" / "thing.md"
    page.write_text("<!-- covers: src/thing.py -->\n# thing\n", encoding="utf-8")

    findings = audit.run_audit(root)
    assert "DOCS-STALE" not in _actionable(findings)  # fresh page: clean

    old = 1_500_000_000  # 2017 - well before the source's mtime
    os.utime(page, (old, old))
    assert "DOCS-STALE" in _actionable(audit.run_audit(root))


def test_covers_token_matching_nothing_warns(tmp_path):
    root = _scaffold(tmp_path)
    (root / "docs" / "ghost.md").write_text(
        "<!-- covers: src/missing.py -->\n# ghost\n", encoding="utf-8"
    )
    stale = [f for f in audit.run_audit(root) if f.code == "DOCS-STALE"]
    assert any(f.severity == "WARN" and "matches no files" in f.message for f in stale)


def test_unmarked_pages_produce_one_aggregate_info(tmp_path):
    root = _scaffold(tmp_path)
    (root / "docs" / "a.md").write_text("# a\n", encoding="utf-8")
    (root / "docs" / "b.md").write_text("# b\n", encoding="utf-8")
    stale = [f for f in audit.run_audit(root) if f.code == "DOCS-STALE"]
    assert len(stale) == 1
    assert stale[0].severity == "INFO"
    assert "docs/a.md" in stale[0].message and "docs/b.md" in stale[0].message


# --------------------------------------------------------- CLI contract

def test_json_format_parses_and_carries_summary(tmp_path, capsys):
    root = _scaffold(tmp_path, material="brownfield")
    exit_code = audit.main(["--cwd", str(root), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["summary"]["warnings"] >= 1
    assert any(f["code"] == "INFERRED-TAG" for f in payload["findings"])
    assert set(payload["findings"][0]) == {"severity", "code", "message", "path"}


def test_no_spine_exits_2(tmp_path):
    assert audit.main(["--cwd", str(tmp_path)]) == 2


def test_missing_stratum_reported_on_partial_spine(tmp_path):
    root = _scaffold(tmp_path)
    (root / "STATE.md").unlink()
    findings = audit.run_audit(root)
    missing = [f for f in findings if f.code == "SPINE-MISSING"]
    assert [f.path for f in missing] == ["STATE.md"]


def test_audit_never_writes(tmp_path, capsys):
    root = _scaffold(tmp_path, material="brownfield")
    before = {
        p: (p.stat().st_size, p.stat().st_mtime_ns)
        for p in root.rglob("*") if p.is_file()
    }
    audit.main(["--cwd", str(root)])
    audit.main(["--cwd", str(root), "--format", "json"])
    capsys.readouterr()
    after = {
        p: (p.stat().st_size, p.stat().st_mtime_ns)
        for p in root.rglob("*") if p.is_file()
    }
    assert before == after


# ------------------------------------------------------------- git-dependent

@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_adr_edited_after_creation_warns_under_git(tmp_path):
    root = _scaffold(tmp_path)

    def git(*args):
        subprocess.run(
            ["git", "-C", str(root),
             "-c", "user.email=t@t", "-c", "user.name=t", *args],
            check=True, capture_output=True, text=True,
        )

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "scaffold")

    adr = root / "decisions" / "0001-record-architecture-decisions.md"
    adr.write_text(adr.read_text(encoding="utf-8") + "\nrewritten\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "edit adr")

    edited = [f for f in audit.run_audit(root) if f.code == "ADR-EDITED"]
    assert any(f.severity == "WARN" for f in edited)

    # The one sanctioned edit - adding a "superseded by" stamp - downgrades to INFO.
    (root / "decisions" / "0002-new.md").write_text("# 2. New\n", encoding="utf-8")
    adr.write_text(
        adr.read_text(encoding="utf-8").replace("rewritten", "superseded by 0002"),
        encoding="utf-8",
    )
    git("add", "-A")
    git("commit", "-q", "-m", "supersede stamp")

    edited = [f for f in audit.run_audit(root) if f.code == "ADR-EDITED"]
    assert edited and all(f.severity == "INFO" for f in edited)
