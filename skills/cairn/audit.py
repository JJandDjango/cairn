"""Audit a Cairn documentation spine - the DOCS-SYSTEM checklist, executable.

Deterministic, REPORT-ONLY: audit never writes, creates, or modifies anything.
It automates the *detection* half of day-2 upkeep (what is stale, missing, or
over budget); the *authorship* stays human - see decisions/0006.

Zero third-party dependencies; git is optional (checks that need history
silently degrade to mtimes or are skipped when git or .git is absent), so a
novel in a bare folder audits as cleanly as a code repo.

Invoked two ways:
  1. By the /cairn skill (`/cairn audit`), or
  2. Directly:  python audit.py [--cwd DIR] [--format text|json]

Exit codes:
  0 - clean (INFO findings allowed)
  1 - at least one WARN or ERROR finding
  2 - not a Cairn spine (no DOCS-SYSTEM.md and no THEORY.md+MAP.md), or bad usage

Finding codes:
  SPINE-MISSING    a stratum file/directory is absent
  MAP-DOC-MISSING  a MAP row's Deep-doc cell links a file that does not exist
  DOCS-ORPHAN      a docs/ page no MAP row references                    (INFO)
  DIAGRAM-COUNT    more than one mermaid diagram (0 diagrams -> INFO)
  DIAGRAM-PLACE    a diagram lives outside MAP.md
  BUDGET-*         a stratum exceeds its size budget (page ~= 80 lines)
  STATE-STALE      STATE.md's Generated stamp predates newer spine activity
  ADR-EDITED       an ADR was modified after creation (git only; an edited ADR
                   carrying a "superseded by" mark is INFO - the one sanctioned edit)
  ADR-DUP          two ADRs share a number
  ADR-SUPERSEDE    "superseded by NNNN" references a missing ADR
  INFERRED-TAG     THEORY.md still carries an "(inferred)" intent tag
  DOCS-STALE       a docs/ page is older than a file its covers-marker names;
                   pages without a marker are one aggregate INFO

The covers marker (optional, per docs/ page):  <!-- covers: path, dir/, glob* -->
declares which files a page explains, so staleness is checkable.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import namedtuple
from datetime import date
from pathlib import Path

# The size-budget proxy: one "page" of markdown as raw line count (generous, so
# only real overruns warn). Budgets: THEORY/STATE 1 page, MAP 2, each ADR 1/2.
LINES_PER_PAGE = 80

SEVERITY_RANK = {"ERROR": 0, "WARN": 1, "INFO": 2}

# Never treated as covered-file activity (derived/regenerable churn).
IGNORED_PARTS = {"__pycache__", ".git", "graphify-out", "node_modules", ".pytest_cache"}

Finding = namedtuple("Finding", ["severity", "code", "message", "path"])


# ---------------------------------------------------------------- git helpers

def _git_available(cwd: Path) -> bool:
    return (cwd / ".git").exists() and shutil.which("git") is not None


def _git_run(cwd: Path, args: list[str]) -> str | None:
    """Run one git command; stdout stripped, or None on any failure."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _git_last_date(cwd: Path, paths: list[str]) -> str | None:
    """ISO date (YYYY-MM-DD) of the last commit touching any of paths."""
    out = _git_run(cwd, ["log", "-1", "--format=%cs", "--", *paths])
    return out or None


def _mtime_date(p: Path) -> str:
    return date.fromtimestamp(p.stat().st_mtime).isoformat()


def _file_date(cwd: Path, p: Path, use_git: bool) -> str:
    """Last-touch date: git commit date when tracked, else mtime."""
    if use_git:
        d = _git_last_date(cwd, [p.relative_to(cwd).as_posix()])
        if d:
            return d
    return _mtime_date(p)


# ------------------------------------------------------------- spine helpers

def _spine_md_files(cwd: Path) -> list[Path]:
    """Every markdown file the strata own (top files + decisions/ + docs/)."""
    files = [cwd / n for n in ("THEORY.md", "MAP.md", "STATE.md", "DOCS-SYSTEM.md")
             if (cwd / n).is_file()]
    for d in ("decisions", "docs"):
        if (cwd / d).is_dir():
            files.extend(sorted((cwd / d).rglob("*.md")))
    return files


def _adr_files(cwd: Path) -> list[Path]:
    decisions = cwd / "decisions"
    if not decisions.is_dir():
        return []
    return sorted(p for p in decisions.glob("*.md") if p.name != "ADR-template.md")


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ------------------------------------------------------------------- checks

def check_spine_presence(cwd: Path) -> list[Finding]:
    findings = []
    for name in ("THEORY.md", "MAP.md", "STATE.md", "DOCS-SYSTEM.md"):
        if not (cwd / name).is_file():
            findings.append(Finding("ERROR", "SPINE-MISSING",
                                    "stratum file missing (run /cairn to re-stub it)", name))
    for d in ("decisions", "docs"):
        if not (cwd / d).is_dir():
            findings.append(Finding("ERROR", "SPINE-MISSING",
                                    "stratum directory missing (run /cairn to re-stub it)", d))
    return findings


def _deep_doc_rows(map_text: str):
    """Yield (component_cell, deep_doc_cell) from every table whose header's
    last column is 'Deep doc'."""
    lines = map_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and cells[-1].lower() == "deep doc":
                i += 1  # separator row
                while i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
                    i += 1
                    row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    if row and set(row[0]) <= {"-", ":", " "}:
                        continue  # a stray separator
                    if len(row) >= 2:
                        yield row[0], row[-1]
        i += 1


def check_map_doc_links(cwd: Path) -> tuple[list[Finding], set[str]]:
    """MAP-DOC-MISSING per broken Deep-doc cell; returns referenced paths too."""
    findings: list[Finding] = []
    referenced: set[str] = set()
    map_path = cwd / "MAP.md"
    if not map_path.is_file():
        return findings, referenced

    for component, cell in _deep_doc_rows(_read(map_path)):
        clean = cell.replace("`", "").strip()
        if clean.lower().startswith("no doc yet"):
            continue
        tokens = re.findall(r"[\w./\\-]+\.md", clean)
        if not tokens:
            findings.append(Finding("ERROR", "MAP-DOC-MISSING",
                                    f"row '{component}': Deep-doc cell '{cell}' is neither "
                                    f"'no doc yet' nor an existing file", "MAP.md"))
            continue
        for tok in tokens:
            rel = tok.replace("\\", "/")
            referenced.add(rel.lower())
            if not (cwd / rel).is_file():
                findings.append(Finding("ERROR", "MAP-DOC-MISSING",
                                        f"row '{component}' links '{rel}' which does not exist",
                                        "MAP.md"))
    return findings, referenced


def check_docs_orphans(cwd: Path, referenced: set[str]) -> list[Finding]:
    findings = []
    docs = cwd / "docs"
    if not docs.is_dir():
        return findings
    for page in sorted(docs.rglob("*.md")):
        rel = page.relative_to(cwd).as_posix()
        if rel.lower() not in referenced:
            findings.append(Finding("INFO", "DOCS-ORPHAN",
                                    "page is referenced by no MAP.md row", rel))
    return findings


def check_diagrams(cwd: Path) -> list[Finding]:
    findings = []
    counts = {p: _read(p).count("```mermaid") for p in _spine_md_files(cwd)}
    total = sum(counts.values())
    if total == 0:
        findings.append(Finding("INFO", "DIAGRAM-COUNT",
                                "no diagram found - fine for non-code projects; code "
                                "projects usually keep one in MAP.md", ""))
    elif total > 1:
        findings.append(Finding("WARN", "DIAGRAM-COUNT",
                                f"{total} mermaid diagrams found - the rule is one per "
                                f"project, in MAP.md", ""))
    for p, n in counts.items():
        rel = p.relative_to(cwd).as_posix()
        if n > 0 and rel != "MAP.md":
            findings.append(Finding("WARN", "DIAGRAM-PLACE",
                                    "diagram lives outside MAP.md", rel))
    return findings


def check_budgets(cwd: Path) -> list[Finding]:
    findings = []
    budgets = [
        ("THEORY.md", LINES_PER_PAGE, "BUDGET-THEORY", "1 page"),
        ("MAP.md", 2 * LINES_PER_PAGE, "BUDGET-MAP", "2 pages"),
        ("STATE.md", LINES_PER_PAGE, "BUDGET-STATE", "1 page"),
    ]
    for name, limit, code, label in budgets:
        p = cwd / name
        if p.is_file():
            n = len(_read(p).splitlines())
            if n > limit:
                findings.append(Finding("WARN", code,
                                        f"{n} lines exceeds the {label} budget "
                                        f"(~{limit} lines)", name))
    adr_limit = LINES_PER_PAGE // 2
    for adr in _adr_files(cwd):
        n = len(_read(adr).splitlines())
        if n > adr_limit:
            findings.append(Finding("WARN", "BUDGET-ADR",
                                    f"{n} lines exceeds the 1/2-page budget "
                                    f"(~{adr_limit} lines)",
                                    adr.relative_to(cwd).as_posix()))
    return findings


def check_state_freshness(cwd: Path, use_git: bool) -> list[Finding]:
    state = cwd / "STATE.md"
    if not state.is_file():
        return []
    m = re.search(r"_Generated (\d{4}-\d{2}-\d{2})", _read(state))
    if not m:
        return [Finding("WARN", "STATE-STALE",
                        "no '_Generated YYYY-MM-DD_' stamp - cannot check freshness",
                        "STATE.md")]
    stamp = m.group(1)

    others = [p for p in _spine_md_files(cwd) if p.name != "STATE.md"]
    if use_git:
        rels = [p.relative_to(cwd).as_posix() for p in others]
        activity = _git_last_date(cwd, rels) if rels else None
    else:
        activity = max((_mtime_date(p) for p in others), default=None)

    if activity and activity > stamp:
        return [Finding("WARN", "STATE-STALE",
                        f"stamped {stamp} but spine activity is newer ({activity}) - "
                        f"regenerate STATE.md at session end", "STATE.md")]
    return []


def check_adrs(cwd: Path, use_git: bool) -> list[Finding]:
    findings = []
    numbers: dict[int, list[Path]] = {}
    texts: dict[Path, str] = {}

    for adr in _adr_files(cwd):
        m = re.match(r"(\d{1,4})-", adr.name)
        if not m:
            continue
        numbers.setdefault(int(m.group(1)), []).append(adr)
        texts[adr] = _read(adr)

    for num, files in sorted(numbers.items()):
        if len(files) > 1:
            names = ", ".join(f.name for f in files)
            findings.append(Finding("ERROR", "ADR-DUP",
                                    f"ADR number {num} is used by {len(files)} files: {names}",
                                    "decisions"))

    for adr, text in texts.items():
        rel = adr.relative_to(cwd).as_posix()
        for m in re.finditer(r"superseded by[ :#]*(\d{1,4})", text, re.IGNORECASE):
            target = int(m.group(1))
            if target not in numbers:
                findings.append(Finding("ERROR", "ADR-SUPERSEDE",
                                        f"marked 'superseded by {m.group(1)}' but no such "
                                        f"ADR exists", rel))
        if use_git:
            modified = _git_run(cwd, ["log", "--diff-filter=M", "--format=%h", "--", rel])
            if modified:
                # A real supersede stamp has digits; advisory prose like
                # "superseded by NNNN" (the seed ADR) must not exempt an edit.
                if re.search(r"superseded by[ :#]*\d", text, re.IGNORECASE):
                    findings.append(Finding("INFO", "ADR-EDITED",
                                            "modified after creation - presumably the "
                                            "sanctioned 'superseded by' stamp", rel))
                else:
                    findings.append(Finding("WARN", "ADR-EDITED",
                                            "modified after creation - ADRs are append-only "
                                            "(supersede, don't edit)", rel))
    return findings


def check_inferred(cwd: Path) -> list[Finding]:
    theory = cwd / "THEORY.md"
    if theory.is_file() and "(inferred" in _read(theory):
        return [Finding("WARN", "INFERRED-TAG",
                        "intent still tagged '(inferred)' - confirm it and delete the tag",
                        "THEORY.md")]
    return []


def _expand_covers_token(cwd: Path, token: str) -> list[Path]:
    tok = token.replace("\\", "/").strip().lstrip("/").rstrip("/")
    if any(ch in tok for ch in "*?["):
        hits = list(cwd.glob(tok))
    else:
        p = cwd / tok
        if p.is_dir():
            hits = list(p.rglob("*"))
        elif p.is_file():
            hits = [p]
        else:
            hits = []
    return [h for h in hits
            if h.is_file() and not (set(h.parts) & IGNORED_PARTS) and h.suffix != ".pyc"]


def _newest_date(cwd: Path, hits: list[Path], use_git: bool) -> str | None:
    """Most recent last-touch date across hits. In git mode this is two git
    calls total (ls-files to split tracked/untracked, one log over the tracked
    set), not one per file; untracked files fall back to mtime."""
    if not use_git:
        return max((_mtime_date(h) for h in hits), default=None)
    rels = [h.relative_to(cwd).as_posix() for h in hits]
    tracked_out = _git_run(cwd, ["ls-files", "--", *rels])
    tracked = set(tracked_out.splitlines()) if tracked_out else set()
    dates = []
    if tracked:
        d = _git_last_date(cwd, sorted(tracked))
        if d:
            dates.append(d)
    dates.extend(_mtime_date(h) for h, r in zip(hits, rels) if r not in tracked)
    return max(dates) if dates else None


def check_docs_staleness(cwd: Path, use_git: bool) -> list[Finding]:
    findings = []
    docs = cwd / "docs"
    if not docs.is_dir():
        return findings

    unmarked: list[str] = []
    for page in sorted(docs.rglob("*.md")):
        rel = page.relative_to(cwd).as_posix()
        text = _read(page)
        m = re.search(r"<!--\s*covers:\s*(.*?)-->", text, re.DOTALL)
        if not m:
            unmarked.append(rel)
            continue
        tokens = [t.strip() for t in m.group(1).split(",") if t.strip()]
        page_date = _file_date(cwd, page, use_git)
        for tok in tokens:
            hits = _expand_covers_token(cwd, tok)
            if not hits:
                findings.append(Finding("WARN", "DOCS-STALE",
                                        f"covers token '{tok}' matches no files", rel))
                continue
            newest_date = _newest_date(cwd, hits, use_git)
            if newest_date and newest_date > page_date:
                findings.append(Finding("WARN", "DOCS-STALE",
                                        f"page last touched {page_date} but covered "
                                        f"'{tok}' changed {newest_date}", rel))

    if unmarked:
        findings.append(Finding("INFO", "DOCS-STALE",
                                f"{len(unmarked)} page(s) carry no '<!-- covers: ... -->' "
                                f"marker - staleness not tracked: {', '.join(unmarked)}", ""))
    return findings


# -------------------------------------------------------------------- driver

def run_audit(cwd: Path) -> list[Finding]:
    use_git = _git_available(cwd)
    findings = []
    findings += check_spine_presence(cwd)
    map_findings, referenced = check_map_doc_links(cwd)
    findings += map_findings
    findings += check_docs_orphans(cwd, referenced)
    findings += check_diagrams(cwd)
    findings += check_budgets(cwd)
    findings += check_state_freshness(cwd, use_git)
    findings += check_adrs(cwd, use_git)
    findings += check_inferred(cwd)
    findings += check_docs_staleness(cwd, use_git)
    findings.sort(key=lambda f: (SEVERITY_RANK[f.severity], f.code, f.path, f.message))
    return findings


def _summary(findings: list[Finding]) -> dict:
    return {
        "errors": sum(1 for f in findings if f.severity == "ERROR"),
        "warnings": sum(1 for f in findings if f.severity == "WARN"),
        "infos": sum(1 for f in findings if f.severity == "INFO"),
    }


def report_text(cwd: Path, findings: list[Finding]) -> str:
    lines = [f"cairn audit - {cwd}", ""]
    for f in findings:
        where = f"  ({f.path})" if f.path else ""
        lines.append(f"{f.severity:<5}  {f.code:<15}  {f.message}{where}")
    if findings:
        lines.append("")
    s = _summary(findings)
    if s["errors"] or s["warnings"]:
        lines.append(f"{s['errors']} error(s), {s['warnings']} warning(s), "
                     f"{s['infos']} info - findings need attention")
    else:
        lines.append(f"clean - all checks passed ({s['infos']} info)")
    return "\n".join(lines)


def report_json(cwd: Path, findings: list[Finding]) -> str:
    return json.dumps({
        "cwd": str(cwd),
        "findings": [f._asdict() for f in findings],
        "summary": _summary(findings),
    }, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit a Cairn documentation spine (report-only, never writes)."
    )
    parser.add_argument("--cwd", default=".",
                        help="Project root holding the spine (default: current directory).")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="Output format (default: text).")
    args = parser.parse_args(argv)

    cwd = Path(args.cwd).resolve()
    if not cwd.is_dir():
        print(f"ERROR: not a directory: {cwd}", file=sys.stderr)
        return 2

    has_docs_system = (cwd / "DOCS-SYSTEM.md").is_file()
    has_theory_map = (cwd / "THEORY.md").is_file() and (cwd / "MAP.md").is_file()
    if not has_docs_system and not has_theory_map:
        print(f"ERROR: no Cairn spine at {cwd} (no DOCS-SYSTEM.md, no THEORY.md+MAP.md) "
              f"- run /cairn first", file=sys.stderr)
        return 2

    findings = run_audit(cwd)
    print(report_text(cwd, findings) if args.format == "text" else report_json(cwd, findings))
    s = _summary(findings)
    return 1 if (s["errors"] or s["warnings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
