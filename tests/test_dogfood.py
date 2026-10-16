"""Pass 7 (feature 31): Cairn adopts its own 2.0 spine and releases 2.0.0.

These tests read this repository, not a temp project. They fail until the
repo is migrated, documented and stamped; after that they guard against
drift back to the 1.x files.
"""

import json
import re
from pathlib import Path

import audit
import render

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = Path(render.__file__).parent / "templates"

GONE_1X = ["THEORY.md", "MAP.md", "STATE.md", "CONVENTIONS.md",
           "DOCS-SYSTEM.md", "USAGE.md", "ROADMAP.md"]
SPINE = ["CLAUDE.md", "README.md", "ARCHITECTURE.md", "CONTRIBUTING.md",
         "CHANGELOG.md"]


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_repo_audits_clean():  # 1
    findings = audit.run_checks(ROOT, audit.spine_mode(ROOT))
    bad = [(f.code, f.path) for f in findings if f.severity in ("ERROR", "WARN")]
    assert bad == []
    assert audit.main(["--cwd", str(ROOT)]) == 0


def test_no_1x_file_remains_at_the_root():  # 2
    assert [n for n in GONE_1X if (ROOT / n).exists()] == []


def test_the_2_0_spine_exists():  # 3
    assert [n for n in SPINE if not (ROOT / n).is_file()] == []
    assert (ROOT / "decisions").is_dir()
    assert (ROOT / "docs").is_dir()


def test_root_claude_md_imports_exactly_readme_and_architecture():  # 4
    imports = re.findall(r"^@(\S+)\s*$", _read("CLAUDE.md"), re.M)
    assert sorted(imports) == ["ARCHITECTURE.md", "README.md"]


def test_version_is_2_0_0_and_changelog_names_it():  # 5
    plugin = json.loads(_read(".claude-plugin/plugin.json"))
    assert plugin["version"] == "2.0.0"
    assert "strata" not in plugin["description"].lower()
    assert re.search(r"^##\s.*2\.0\.0", _read("CHANGELOG.md"), re.M)


def test_readme_is_2kb_links_the_guide_and_drops_1x_words():  # 6
    text = _read("README.md")
    assert len(text.encode("utf-8")) <= 2048
    assert "docs/usage.md" in text
    assert "USAGE.md" not in text
    for word in ("strata", "graphify"):
        assert word not in text.lower()


def test_usage_guide_is_final():  # 7
    text = _read("docs/usage.md")
    assert "🟡" not in text and "🔴" not in text
    assert "Pass 0" not in text
    assert not (ROOT / "docs" / "usage-2.0.md").exists()


def test_audit_workflow_template_pins_v2_0_0_once():  # 8
    text = (TEMPLATES / "cairn-audit.yml.template").read_text(encoding="utf-8")
    assert text.count("CAIRN_REF: v2.0.0") == 1
    assert "CAIRN_REF: main" not in text


def test_ci_runs_the_audit_on_the_repo_root():  # 9
    text = _read(".github/workflows/ci.yml")
    assert re.search(r"audit\.py\s+--cwd\s+\.", text)
