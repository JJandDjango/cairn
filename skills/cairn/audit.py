"""Audit a Cairn 2.0 documentation spine.

Deterministic, REPORT-ONLY: audit never writes, creates, or modifies anything.
It automates the *detection* half of day-2 upkeep (what is stale, missing, or
over budget); the *authorship* stays human - see decisions/0006.

Zero third-party dependencies; git is optional (the folder checks use it to
list files when it is there), so a novel in a bare folder audits as cleanly as
a code repo.

Invoked two ways:
  1. By the /cairn skill (`/cairn audit`), or
  2. Directly:  python audit.py [--cwd DIR] [--format text|json]

Exit codes:
  0 - clean (INFO findings allowed)
  1 - at least one WARN or ERROR finding
  2 - no 2.0 spine (no ARCHITECTURE.md), or bad usage; a folder holding only
      1.x files gets a one-line pointer to `/cairn migrate`

The spine is ARCHITECTURE.md in .docs-local/ (local mode, which wins when both
exist) or at the root (tracked mode). Local mode reads the top pages in
.docs-local/ and folder pages named CLAUDE.local.md; tracked mode reads the
root files and folder pages named CLAUDE.md. The 1.x checks are retired.

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

One more code, INFO only:
  LEGACY-1X     1.x files (THEORY, MAP, STATE, CONVENTIONS, DOCS-SYSTEM) are
                still here beside the 2.0 spine; the message names
                `/cairn migrate`. No 1.x check runs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import namedtuple
from pathlib import Path
from urllib.parse import unquote

import pages
import render

SEVERITY_RANK = {"ERROR": 0, "WARN": 1, "INFO": 2}

Finding = namedtuple("Finding", ["severity", "code", "message", "path"])

# The five 1.x spine files, retired in 2.0; /cairn migrate moves them.
LEGACY_FILES = ("THEORY.md", "MAP.md", "STATE.md", "CONVENTIONS.md", "DOCS-SYSTEM.md")

# ------------------------------------------------------------------- checks

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


def legacy_files(cwd: Path) -> list[str]:
    """The 1.x spine files still here, at the root or in .docs-local/."""
    found = []
    for prefix in ("", render.LOCAL_DIR + "/"):
        found += [prefix + name for name in LEGACY_FILES
                  if (cwd / (prefix + name)).is_file()]
    return found


# -------------------------------------------------------------------- driver

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

    mode = spine_mode(cwd)
    legacy = legacy_files(cwd)
    if mode is None:
        if legacy:
            print(f"ERROR: 1.x spine at {cwd} (no ARCHITECTURE.md) - run /cairn migrate",
                  file=sys.stderr)
        else:
            print(f"ERROR: no Cairn spine at {cwd} (no ARCHITECTURE.md) - run /cairn first",
                  file=sys.stderr)
        return 2

    findings = run_checks(cwd, mode)
    if legacy:
        findings.append(Finding("INFO", "LEGACY-1X",
                                f"1.x files remain ({', '.join(legacy)}) - run /cairn migrate",
                                ""))
    findings.sort(key=lambda f: (SEVERITY_RANK[f.severity], f.code, f.path, f.message))
    print(report_text(cwd, findings) if args.format == "text" else report_json(cwd, findings))
    s = _summary(findings)
    return 1 if (s["errors"] or s["warnings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
