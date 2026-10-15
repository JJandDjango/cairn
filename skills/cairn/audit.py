"""Audit a Cairn documentation spine - the 2.0 checks and the 1.x checklist.

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
  2 - not a Cairn spine (no ARCHITECTURE.md, no DOCS-SYSTEM.md and no
      THEORY.md+MAP.md), or bad usage

Two spines, detected by file:
  - 2.0: ARCHITECTURE.md in .docs-local/ (local mode, which wins when both
    exist) or at the root (tracked mode). Local mode reads the top pages in
    .docs-local/ and folder pages named CLAUDE.local.md; tracked mode reads
    the root files and folder pages named CLAUDE.md.
  - 1.x: DOCS-SYSTEM.md, or THEORY.md with MAP.md. Its checks are below.
A folder with both runs both sets of checks.

2.0 finding codes (all ERROR, so any one gives exit 1):
  SIZE-BUDGET   a file is over budget, in bytes (1 KB = 1024): README 2048,
                ARCHITECTURE 3072, CONTRIBUTING 3072, a folder page 2048; the
                tracked root CLAUDE.md may hold 10 lines
  AT-IMPORT     an import-shaped @ (one that starts a word) outside code, in
                README, ARCHITECTURE or a folder page; reports the line
  LINK-BROKEN   a relative link in a top page or folder page whose target
                file or folder does not exist (anchors stripped; external,
                mailto, #-only and in-code links are skipped)
  GEN-STALE     a folder page's generated block differs from what pages.py
                would write now; a page with no block markers is one INFO,
                since its lines cannot be verified
  COVER-PAGE    a working folder has no page
  COVER-FILE    a file in a paged folder has no line in its page
Folder checks run for a code project, known from ARCHITECTURE.md (it holds
the `/cairn status` table row, which render.py writes for code only), so a code
project whose pages were never made or were deleted still gets COVER-PAGE.
When that row is absent, they run only if at least one folder page exists.
A project with neither (a novel, a business plan) has no folder checks.

1.x finding codes:
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
  INFERRED-TAG     THEORY.md intent or CONVENTIONS.md entries still carry an
                   "(inferred)" tag (text inside HTML comments does not count)
  CONV-LINK        a CONVENTIONS.md entry cites an ADR that does not exist
  CONV-SUPERSEDED  a CONVENTIONS.md entry cites a superseded ADR
  DOCS-STALE       a docs/ page is older than a file its covers-marker names;
                   pages without a marker are one aggregate INFO

CONVENTIONS.md itself is optional (pre-1.2 spines): absent means no findings;
present means the full contract is enforced.

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
from urllib.parse import unquote

import pages
import render

# The size-budget proxy: one "page" of markdown as raw line count (generous, so
# only real overruns warn). Budgets: THEORY/STATE 1 page, MAP 2, each ADR 1/2.
LINES_PER_PAGE = 80

SEVERITY_RANK = {"ERROR": 0, "WARN": 1, "INFO": 2}

# Never treated as covered-file activity (derived/regenerable churn).
IGNORED_PARTS = {"__pycache__", ".git", "node_modules", ".pytest_cache"}

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
    files = [cwd / n
             for n in ("THEORY.md", "MAP.md", "STATE.md", "CONVENTIONS.md",
                       "DOCS-SYSTEM.md")
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


def _visible(text: str) -> str:
    """Text with HTML comments removed. Conventions-facing checks use this so
    template guidance may NAME the inferred tag, and a commented-out entry
    neither link-checks nor flags."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


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
        ("CONVENTIONS.md", LINES_PER_PAGE, "BUDGET-CONVENTIONS", "1 page"),
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
    findings = []
    for name, what in (("THEORY.md", "intent"), ("CONVENTIONS.md", "entries")):
        p = cwd / name
        if p.is_file() and "(inferred" in _visible(_read(p)):
            findings.append(Finding("WARN", "INFERRED-TAG",
                                    f"{what} still tagged '(inferred)' - confirm and "
                                    f"delete the tag", name))
    return findings


def check_conventions(cwd: Path) -> list[Finding]:
    """CONVENTIONS.md entry links: cited ADRs must exist and be current.
    The file itself is optional (pre-1.2 spines) - absent means no findings."""
    conv = cwd / "CONVENTIONS.md"
    if not conv.is_file():
        return []
    findings: list[Finding] = []
    text = _visible(_read(conv))

    adr_numbers: dict[int, Path] = {}
    for adr in _adr_files(cwd):
        m = re.match(r"(\d{1,4})-", adr.name)
        if m:
            adr_numbers.setdefault(int(m.group(1)), adr)

    cited: dict[int, str] = {}
    for m in re.finditer(r"\[\[(\d{1,4})-[^\]]*\]\]", text):
        cited.setdefault(int(m.group(1)), m.group(0))
    for m in re.finditer(r"decisions/(\d{1,4})[\w.-]*\.md", text):
        cited.setdefault(int(m.group(1)), m.group(0))

    for num, ref in sorted(cited.items()):
        adr = adr_numbers.get(num)
        if adr is None:
            findings.append(Finding("ERROR", "CONV-LINK",
                                    f"entry cites '{ref}' but no ADR {num:04d} exists",
                                    "CONVENTIONS.md"))
        elif re.search(r"superseded by[ :#]*\d", _read(adr), re.IGNORECASE):
            findings.append(Finding("WARN", "CONV-SUPERSEDED",
                                    f"entry cites {adr.name} which is superseded - "
                                    f"revise or retire the rule",
                                    "CONVENTIONS.md"))
    return findings


def _conventions_doc_refs(cwd: Path) -> set[str]:
    """Doc pages CONVENTIONS.md references (lowercased posix rels) - overflow
    pages under docs/conventions/ are referenced, not orphans."""
    conv = cwd / "CONVENTIONS.md"
    if not conv.is_file():
        return set()
    return {t.replace("\\", "/").lower()
            for t in re.findall(r"[\w./\\-]+\.md", _visible(_read(conv)))}


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


# --------------------------------------------------------------- 2.0 checks

# Byte budgets, 1 KB = 1024; the root CLAUDE.md is held to lines instead.
TOP_BUDGETS = {"README.md": 2048, "ARCHITECTURE.md": 3072, "CONTRIBUTING.md": 3072}
PAGE_BUDGET = 2048
ROOT_LINE_BUDGET = 10

# Top pages scanned for an @ import: CONTRIBUTING.md is read on demand and the
# root importer holds the imports by design, so neither is scanned.
AT_SCANNED = ("README.md", "ARCHITECTURE.md")

# Present in ARCHITECTURE.md only for a code project: it is in render.py's
# CODE_STATUS_ROW, which is written for project_type code alone.
STATUS_MARKER = "/cairn status"

AT_IMPORT = re.compile(r"(?<![\w@])@([\w./~-]+)")
MD_LINK = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+[^)]*)?\)")
SCHEME = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*:")


def spine_mode(cwd: Path) -> str | None:
    """'local' or 'tracked' when a 2.0 spine is here, else None."""
    if (cwd / render.LOCAL_DIR / "ARCHITECTURE.md").is_file():
        return "local"
    if (cwd / "ARCHITECTURE.md").is_file():
        return "tracked"
    return None


def _read_or_none(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _blank(text: str) -> str:
    """Spaces in place of every character but the newlines."""
    return re.sub(r"[^\r\n]", " ", text)


def _outside_code(text: str, inline: bool = True) -> str:
    """The text with fenced blocks and, when inline is true, inline code
    blanked. Newlines stay, so a line number in the result is the line number
    in the file."""
    out = []
    fence = None
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if fence:
            if stripped.startswith(fence):
                fence = None
            out.append(_blank(line))
        elif stripped.startswith(("```", "~~~")):
            fence = stripped[:3]
            out.append(_blank(line))
        elif inline:
            out.append(re.sub(r"(`+).+?\1", lambda m: _blank(m.group(0)), line))
        else:
            out.append(line)
    return "".join(out)


def is_code_project(top: Path) -> bool:
    """True when ARCHITECTURE.md in top carries the status-command table row
    that render.py writes only for a code project. A table line outside a
    fenced block counts; a prose or inline-code mention does not (the row's
    command sits in inline code, so only fences are blanked)."""
    text = _read_or_none(top / "ARCHITECTURE.md")
    if text is None:
        return False
    return any(line.lstrip().startswith("|") and STATUS_MARKER in line
               for line in _outside_code(text, inline=False).splitlines())


def _check_size(rel: str, size: int, limit: int) -> list[Finding]:
    if size > limit:
        return [Finding("ERROR", "SIZE-BUDGET",
                        f"{size} bytes exceeds the {limit}-byte budget", rel)]
    return []


def _check_at(rel: str, text: str) -> list[Finding]:
    findings = []
    for number, line in enumerate(_outside_code(text).splitlines(), 1):
        for m in AT_IMPORT.finditer(line):
            findings.append(Finding("ERROR", "AT-IMPORT",
                                    f"line {number}: '@{m.group(1)}' outside code would "
                                    f"load as an import - put it in code or drop the @",
                                    rel))
    return findings


def _check_links(cwd: Path, source: Path, text: str) -> list[Finding]:
    findings = []
    visible = re.sub(r"<!--.*?-->", "", _outside_code(text), flags=re.DOTALL)
    for m in MD_LINK.finditer(visible):
        target = m.group(1)
        if target.startswith(("#", "//")) or SCHEME.match(target):
            continue
        path_part = unquote(target.split("#")[0].split("?")[0])
        if not path_part:
            continue
        base = cwd if path_part.startswith("/") else source.parent
        if not (base / path_part.lstrip("/")).exists():
            findings.append(Finding("ERROR", "LINK-BROKEN",
                                    f"link '{target}' does not resolve",
                                    source.relative_to(cwd).as_posix()))
    return findings


def _has_line(page_text: str, name: str) -> bool:
    """True when the page names the file as a whole token, in a block line or
    a typed one. Hint comments are ignored."""
    visible = re.sub(r"<!--.*?-->", "", page_text, flags=re.DOTALL)
    return re.search(r"(?<![\w./-])" + re.escape(name) + r"(?![\w-]|\.\w)", visible) is not None


def check_folder_pages(cwd: Path, page_name: str, is_code: bool = False) -> list[Finding]:
    """Budget, @ and link checks on folder pages, then freshness and coverage.

    The checks run for a code project (is_code, read from ARCHITECTURE.md) or,
    failing that, when at least one folder page exists.

    pages.plan() supplies the freshness and missing-page findings, so the audit
    and the refresh script can never disagree about what is stale.
    """
    folders = pages.find_folders(cwd)
    present = {parts: cwd.joinpath(*parts) / page_name for parts in folders}
    present = {parts: p for parts, p in present.items() if p.is_file()}
    if not present and not is_code:
        return []

    findings: list[Finding] = []
    texts: dict[Path, str | None] = {}
    for parts, page in sorted(present.items()):
        rel = page.relative_to(cwd).as_posix()
        text = _read_or_none(page)
        texts[page] = text
        findings += _check_size(rel, page.stat().st_size, PAGE_BUDGET)
        if text is not None:
            findings += _check_at(rel, text)
            findings += _check_links(cwd, page, text)

    for action, rel in pages.plan(cwd, page_name):
        if action == "created":
            folder = Path(rel).parent.as_posix()
            findings.append(Finding("ERROR", "COVER-PAGE",
                                    f"working folder has no page (run pages.py to "
                                    f"write {rel})", folder))
        elif action == "updated":
            findings.append(Finding("ERROR", "GEN-STALE",
                                    "generated lines differ from the docstrings - "
                                    "run pages.py", rel))
        else:
            findings.append(Finding("INFO", "GEN-STALE",
                                    "no cairn:files block, so its generated lines "
                                    "cannot be verified", rel))

    for parts, page in sorted(present.items()):
        text = texts[page]
        if text is None:
            continue
        rel = page.relative_to(cwd).as_posix()
        for name in sorted(folders[parts]["files"]):
            if not _has_line(text, name):
                findings.append(Finding("ERROR", "COVER-FILE",
                                        f"'{name}' has no line in the page", rel))
    return findings


def run_checks(cwd: Path, mode: str) -> list[Finding]:
    """The 2.0 checks for one spine. mode is 'tracked' or 'local'."""
    local = mode == "local"
    top = cwd / render.LOCAL_DIR if local else cwd
    findings: list[Finding] = []

    for name in TOP_BUDGETS:
        p = top / name
        if not p.is_file():
            continue
        rel = p.relative_to(cwd).as_posix()
        findings += _check_size(rel, p.stat().st_size, TOP_BUDGETS[name])
        text = _read_or_none(p)
        if text is None:
            continue
        if name in AT_SCANNED:
            findings += _check_at(rel, text)
        findings += _check_links(cwd, p, text)

    if not local:
        root_page = _read_or_none(cwd / pages.PAGE)
        if root_page is not None:
            n = len(root_page.splitlines())
            if n > ROOT_LINE_BUDGET:
                findings.append(Finding("ERROR", "SIZE-BUDGET",
                                        f"{n} lines exceeds the {ROOT_LINE_BUDGET}-line "
                                        f"budget", pages.PAGE))

    findings += check_folder_pages(cwd, pages.LOCAL_PAGE if local else pages.PAGE,
                                   is_code_project(top))
    return findings


# -------------------------------------------------------------------- driver

def run_audit(cwd: Path) -> list[Finding]:
    use_git = _git_available(cwd)
    findings = []
    findings += check_spine_presence(cwd)
    map_findings, referenced = check_map_doc_links(cwd)
    findings += map_findings
    findings += check_docs_orphans(cwd, referenced | _conventions_doc_refs(cwd))
    findings += check_diagrams(cwd)
    findings += check_budgets(cwd)
    findings += check_state_freshness(cwd, use_git)
    findings += check_adrs(cwd, use_git)
    findings += check_inferred(cwd)
    findings += check_conventions(cwd)
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
    has_1x = has_docs_system or has_theory_map
    mode = spine_mode(cwd)
    if not has_1x and mode is None:
        print(f"ERROR: no Cairn spine at {cwd} (no ARCHITECTURE.md, no DOCS-SYSTEM.md, "
              f"no THEORY.md+MAP.md) - run /cairn first", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    if has_1x:
        findings += run_audit(cwd)
    if mode is not None:
        findings += run_checks(cwd, mode)
    findings.sort(key=lambda f: (SEVERITY_RANK[f.severity], f.code, f.path, f.message))
    print(report_text(cwd, findings) if args.format == "text" else report_json(cwd, findings))
    s = _summary(findings)
    return 1 if (s["errors"] or s["warnings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
