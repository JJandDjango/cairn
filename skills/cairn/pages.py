"""Write and refresh folder pages: a CLAUDE.md in each working folder.

A folder page holds the folder's purpose, one line per file and subfolder,
local rules, and links. Claude Code loads it the first time a session reads
a file in that folder. Zero third-party dependencies.

Invoked two ways:
  1. By render.py, for code projects, after the spine is written, or
  2. Directly, to refresh pages after code changes:
       python pages.py [--cwd DIR]

Behavior:
  - Working folders: every folder below the root that holds a file, found
    with `git ls-files` in a git repo (so git-ignored folders get no page),
    else by walking the tree. Skipped, with everything under them: the root
    (its CLAUDE.md is the spine page), dot-folders, the root decisions/
    folder, virtualenvs (a pyvenv.cfg at their root), and fixture, vendored
    and generated folders by name, in any case.
    A fixture folder gets one line in its parent's page instead.
  - Docstrings: a Python module docstring, a leading `/** */` doc comment,
    or a Rust `//!` comment gives a file's line. Those lines live between
    the block markers, and only they are ever rewritten.
  - Every other file gets a starter line outside the block when the page is
    created; from then on that line is typed, and the script never touches it.
  - An existing CLAUDE.md without the block markers is skipped, never edited.
"""

from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
from pathlib import Path


PAGE = "CLAUDE.md"
PAGE_FILES = {PAGE, "CLAUDE.local.md"}

BLOCK_START = "<!-- cairn:files -->"
BLOCK_END = "<!-- /cairn:files -->"

# Folders that never get a page; the fixture names get a line in the parent's.
FIXTURE_NAMES = {"fixtures", "testdata"}
EXCLUDED_NAMES = FIXTURE_NAMES | {
    "vendor", "third_party", "node_modules", "dist", "build", "generated",
    "__pycache__",
}
VENV_MARKER = "pyvenv.cfg"
# The spine's append-only ADR folder, at the root only: ARCHITECTURE.md names it.
SPINE_FOLDERS = {"decisions"}

DOC_COMMENT_SUFFIXES = {
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".java", ".kt", ".scala",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".go", ".php", ".swift",
}

TYPED_FILE_HINT = "<!-- one line: what this file is for -->"
TYPED_FOLDER_HINT = "<!-- one line: what this folder is for -->"
FIXTURE_HINT = "test fixtures <!-- what they hold -->"


# ------------------------------------------------------------ finding folders

def _listed_files(cwd: Path) -> list[str] | None:
    """Tracked and untracked-but-not-ignored files, or None outside git."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=cwd, capture_output=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    paths = result.stdout.decode("utf-8", errors="replace").split("\0")
    return [p for p in paths if p and (cwd / p).is_file()]


def _walked_files(cwd: Path) -> list[str]:
    files = []
    for dirpath, dirnames, filenames in os.walk(cwd):
        if VENV_MARKER in filenames:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        rel_dir = Path(dirpath).relative_to(cwd)
        files.extend((rel_dir / name).as_posix() for name in filenames)
    return files


def _excluded(parts: tuple[str, ...], venvs: set) -> bool:
    """True if a folder (given as path parts below the root) gets no page."""
    if parts and parts[0] in SPINE_FOLDERS:
        return True
    if any(parts[:i] in venvs for i in range(1, len(parts) + 1)):
        return True
    return any(p.startswith(".") or p.lower() in EXCLUDED_NAMES for p in parts)


def find_folders(cwd: Path) -> dict[tuple[str, ...], dict]:
    """Map each working folder to its files, subfolders and fixture folders."""
    listed = _listed_files(cwd)
    files = listed if listed is not None else _walked_files(cwd)
    # A virtualenv under any name is vendored code: its root holds pyvenv.cfg.
    venvs = {Path(rel).parts[:-1] for rel in files if Path(rel).name == VENV_MARKER}

    folders: dict[tuple[str, ...], dict] = {}

    def folder(parts):
        """Register a kept folder and every ancestor below the root."""
        for i in range(1, len(parts)):
            folders.setdefault(parts[:i], _empty())["subfolders"].add(parts[i])
        return folders.setdefault(parts, _empty())

    for rel in files:
        parts = Path(rel).parts
        name, dir_parts = parts[-1], parts[:-1]
        # A fixture folder's parent records it, provided the parent is kept.
        for i, part in enumerate(dir_parts):
            if part.lower() in FIXTURE_NAMES and i > 0 and not _excluded(dir_parts[:i], venvs):
                folder(dir_parts[:i])["fixtures"].add(part)
        if not dir_parts or _excluded(dir_parts, venvs):
            continue
        info = folder(dir_parts)
        if name not in PAGE_FILES:
            info["files"].add(name)

    return folders


def _empty() -> dict:
    return {"files": set(), "subfolders": set(), "fixtures": set()}


# ------------------------------------------------------------- docstrings

def _first_text_line(lines) -> str | None:
    for line in lines:
        line = line.strip()
        if line and not line.startswith("@"):
            return line
    return None


def _python_docstring(source: str) -> str | None:
    try:
        doc = ast.get_docstring(ast.parse(source))
    except (SyntaxError, ValueError):
        return None
    return _first_text_line(doc.splitlines()) if doc else None


def _strip_shebang(source: str) -> str:
    if source.startswith("#!"):
        source = source.split("\n", 1)[1] if "\n" in source else ""
    return source.lstrip()


def _doc_comment(source: str) -> str | None:
    """First text line of a leading /** ... */ comment."""
    source = _strip_shebang(source)
    if not source.startswith("/**") or source.startswith("/**/"):
        return None
    end = source.find("*/", 3)
    if end == -1:
        return None
    body = source[3:end].splitlines()
    return _first_text_line(line.strip().lstrip("*") for line in body)


def _rust_doc(source: str) -> str | None:
    """First text line of the leading //! comment lines."""
    lines = []
    for line in _strip_shebang(source).splitlines():
        stripped = line.strip()
        if not stripped.startswith("//!"):
            break
        lines.append(stripped[3:])
    return _first_text_line(lines)


def docstring_line(path: Path) -> str | None:
    """A file's first docstring line, or None when it has none."""
    suffix = path.suffix.lower()
    if suffix != ".py" and suffix != ".rs" and suffix not in DOC_COMMENT_SUFFIXES:
        return None
    try:
        source = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    if suffix == ".py":
        line = _python_docstring(source)
    elif suffix == ".rs":
        line = _rust_doc(source)
    else:
        line = _doc_comment(source)
    return _safe(line) if line else None


def _safe(line: str) -> str:
    """Keep a copied line inert: no comment delimiters, no @ outside code."""
    line = line.replace("<!--", "").replace("-->", "").strip()
    if "@" in line:
        return "`" + line.replace("`", "'") + "`"
    return line


# ------------------------------------------------------------- pages

def _block_lines(folder_path: Path, info: dict) -> list[str]:
    lines = []
    for name in sorted(info["files"]):
        doc = docstring_line(folder_path / name)
        if doc:
            lines.append(f"- `{name}`: {doc}")
    return lines


def _new_page(parts: tuple[str, ...], folder_path: Path, info: dict) -> str:
    block = _block_lines(folder_path, info)
    documented = {line.split("`")[1] for line in block}
    typed = [f"- `{name}`: {TYPED_FILE_HINT}"
             for name in sorted(info["files"]) if name not in documented]
    typed += [f"- `{name}/`: {TYPED_FOLDER_HINT}" for name in sorted(info["subfolders"])]
    typed += [f"- `{name}/`: {FIXTURE_HINT}" for name in sorted(info["fixtures"])]

    out = [f"# {'/'.join(parts)}", "",
           "## Purpose", TYPED_FOLDER_HINT, "",
           "## Files", BLOCK_START, *block, BLOCK_END, *typed, "",
           "## Rules", "<!-- Local rules for this folder only; one line each. -->", "",
           "## Links", "<!-- Links to the docs that cover this folder, never their content. -->", ""]
    return "\n".join(out)


def _refresh(raw: str, block: list[str]) -> str | None:
    """The page with its block rewritten, or None when it has no block.

    Works on the raw text, so every byte outside the block, line endings
    included, stays as it was.
    """
    start = raw.find(BLOCK_START)
    end = raw.find(BLOCK_END, start + len(BLOCK_START)) if start != -1 else -1
    if start == -1 or end == -1:
        return None
    head = raw[:start + len(BLOCK_START)]
    newline = "\r\n" if raw[len(head):].startswith("\r\n") else "\n"
    body = "".join(line + newline for line in block)
    return head + newline + body + raw[end:]


def _read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def run(cwd: Path) -> list[tuple[str, str]]:
    """Create missing pages and refresh blocks. Returns (action, page) pairs."""
    actions = []
    for parts, info in sorted(find_folders(cwd).items()):
        folder_path = cwd.joinpath(*parts)
        page = folder_path / PAGE
        rel = page.relative_to(cwd).as_posix()
        if not page.exists():
            _write(page, _new_page(parts, folder_path, info))
            actions.append(("created", rel))
            continue
        try:
            raw = _read(page)
        except (OSError, UnicodeDecodeError):
            actions.append(("skipped", rel))
            continue
        refreshed = _refresh(raw, _block_lines(folder_path, info))
        if refreshed is None:
            actions.append(("skipped", rel))
        elif refreshed != raw:
            _write(page, refreshed)
            actions.append(("updated", rel))
    return actions


def report(actions: list[tuple[str, str]]) -> None:
    for action, rel in actions:
        note = "  (no cairn:files block)" if action == "skipped" else ""
        print(f"{action:<8} {rel}{note}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write and refresh folder pages (a CLAUDE.md per working folder)."
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Target project root (default: current directory).",
    )
    args = parser.parse_args(argv)

    cwd = Path(args.cwd).resolve()
    if not cwd.is_dir():
        print(f"ERROR: not a directory: {cwd}", file=sys.stderr)
        return 1

    actions = run(cwd)
    report(actions)
    if not actions:
        print("Every folder page is fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
