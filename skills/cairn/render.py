"""Render the Cairn 2.0 spine into a project directory.

Cairn writes the few short documents a new collaborator reads on day one:
root CLAUDE.md, README.md, ARCHITECTURE.md, CONTRIBUTING.md, CHANGELOG.md,
decisions/, docs/ templates, and a local, untracked note. Local mode writes
the same set under .docs-local/ and touches nothing tracked. Zero
third-party dependencies.

Invoked two ways:
  1. By the /cairn skill after its interview (see SKILL.md), or
  2. Directly by a human:
       python render.py --answers '{"project_name": "...", ...}' [--cwd DIR]

Answer keys (all required):
  project_name  (str)   e.g. "my-novel"
  intent        (str)   one line: "why does this exist?"
  project_type  (str)   code | novel | content-site | business | research
  adoption      (str)   greenfield | brownfield
  mode          (str)   tracked | local

Behavior:
  - {{ var }} substitution across templates (including decisions/ and docs/).
  - date.today() stamps the seed ADR.
  - project_type=code -> ARCHITECTURE.md gains the one diagram and the
    status-command row; every other type gets the same spine without them.
  - adoption=brownfield -> intent rendered with an `(inferred - confirm)` tag.
  - mode=tracked -> .gitignore gains `CLAUDE.local.md` once, and every
    project type gets .github/workflows/cairn-audit.yml, which runs audit.py
    on each pull request (a shallow clone of the cairn repo at one pinned
    ref). Local mode writes nothing under .github/.
  - project_type=code -> pages.py then writes a folder page (CLAUDE.md) in
    each working folder and refreshes the docstring lines in existing ones.
  - mode=local -> nothing tracked is written. The spine goes under
    .docs-local/ (with a .gitignore of `*`, written only when missing); one
    root CLAUDE.local.md imports its README and ARCHITECTURE; folder pages
    are CLAUDE.local.md. CLAUDE.local.md is added once to the exclude file
    git reports (so worktrees work). Outside git the exclude is skipped and
    one line says so. The root .gitignore is never touched. Every local run
    prints the `git clean -x` caution.
  - NO-CLOBBER: any target that already exists is skipped and reported, never
    overwritten (safe to run on a partly-documented project).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pages


# The CI job that runs audit.py on every PR; written in tracked mode only.
WORKFLOW_TARGET = ".github/workflows/cairn-audit.yml"

TEMPLATE_TO_TARGET = {
    "CLAUDE.md.template": "CLAUDE.md",
    "README.md.template": "README.md",
    "ARCHITECTURE.md.template": "ARCHITECTURE.md",
    "CONTRIBUTING.md.template": "CONTRIBUTING.md",
    "CHANGELOG.md.template": "CHANGELOG.md",
    "CLAUDE.local.md.template": "CLAUDE.local.md",
    "decisions/0001-record-architecture-decisions.md.template": "decisions/0001-record-architecture-decisions.md",
    "decisions/ADR-template.md.template": "decisions/ADR-template.md",
    "docs/recipe-template.md.template": "docs/recipe-template.md",
    "docs/feature-template.md.template": "docs/feature-template.md",
    "docs/design-template.md.template": "docs/design-template.md",
    "cairn-audit.yml.template": WORKFLOW_TARGET,
}

REQUIRED_ANSWER_KEYS = {"project_name", "intent", "project_type", "adoption", "mode"}

PROJECT_TYPES = {"code", "novel", "content-site", "business", "research"}

MODES = {"tracked", "local"}

# The local note stays untracked; tracked mode keeps it out of git this way.
LOCAL_NOTE = "CLAUDE.local.md"

# Local mode: the same set under .docs-local/, plus one root note that imports
# its README and ARCHITECTURE. The tracked-mode root CLAUDE.md and note drop out.
LOCAL_DIR = ".docs-local"
LOCAL_ROOT_TEMPLATE = "CLAUDE.local-root.md.template"
LOCAL_TEMPLATE_TO_TARGET = {
    template: f"{LOCAL_DIR}/{target}"
    for template, target in TEMPLATE_TO_TARGET.items()
    if target not in {"CLAUDE.md", LOCAL_NOTE, WORKFLOW_TARGET}
}
LOCAL_TEMPLATE_TO_TARGET[LOCAL_ROOT_TEMPLATE] = LOCAL_NOTE
LOCAL_IMPORTS = (f"@{LOCAL_DIR}/README.md", f"@{LOCAL_DIR}/ARCHITECTURE.md")

# The folder hides itself and its contents from git with this file.
LOCAL_GITIGNORE = f"{LOCAL_DIR}/.gitignore"

CLEAN_CAUTION = (
    "caution  `git clean -x` deletes every file Cairn wrote in local mode: "
    "they are untracked and ignored."
)

CODE_DIAGRAM_SECTION = (
    "## Diagram\n"
    "\n"
    "```mermaid\n"
    "flowchart TD\n"
    "    A[component A] --> B[component B]\n"
    "```\n"
    "<!-- The ONE diagram in this project, at container zoom. Anything deeper\n"
    "     rots faster than you can maintain it. -->\n"
    "\n"
)

# The status command (status.py), named in the code ARCHITECTURE.md.
CODE_STATUS_ROW = "| Last done, next, and what waits on you | The status command, `/cairn status` |\n"


def substitute(template_text: str, variables: dict) -> str:
    """Substitute {{ var }} placeholders in one pass."""
    pattern = re.compile(r"\{\{\s*(\w+)\s*\}\}")

    def replace(match):
        key = match.group(1)
        if key not in variables:
            raise KeyError(f"Template references unknown variable: {key}")
        return str(variables[key])

    return pattern.sub(replace, template_text)


def build_var_dict(answers: dict, today: str) -> dict:
    """Expand interview answers into the full template variable namespace."""
    if "backend" in answers:
        raise ValueError(
            "the 'backend' answer was removed in Cairn 2.0; drop it from the answers"
        )
    project_type = answers["project_type"]
    if project_type not in PROJECT_TYPES:
        raise ValueError(
            f"project_type must be one of {sorted(PROJECT_TYPES)}, got {project_type!r}"
        )
    adoption = answers["adoption"]
    if adoption not in {"greenfield", "brownfield"}:
        raise ValueError(
            f"adoption must be 'greenfield' or 'brownfield', got {adoption!r}"
        )
    mode = answers.get("mode")
    if mode not in MODES:
        raise ValueError(f"mode must be 'tracked' or 'local', got {mode!r}")

    intent_plain = str(answers["intent"]).strip()
    if not intent_plain:
        raise ValueError("intent must be a non-empty one-line string")
    intent = (
        f"{intent_plain} _(inferred - confirm)_" if adoption == "brownfield"
        else intent_plain
    )

    is_code = project_type == "code"
    return {
        "project_name": answers["project_name"],
        "intent": intent,
        "diagram_section": CODE_DIAGRAM_SECTION if is_code else "",
        "status_row": CODE_STATUS_ROW if is_code else "",
        "date": today,
    }


def render_all(answers: dict, templates_dir: Path, cwd: Path, today: str):
    """Render every spine file. Returns (created, skipped) path lists. No-clobber."""
    variables = build_var_dict(answers, today)
    created: list[Path] = []
    skipped: list[Path] = []

    local = answers["mode"] == "local"
    targets = LOCAL_TEMPLATE_TO_TARGET if local else TEMPLATE_TO_TARGET

    for template_name, target_rel in targets.items():
        template_path = templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Missing template: {template_path}")

        target_path = cwd / target_rel
        if target_path.exists():
            skipped.append(target_path)
            continue

        rendered = substitute(template_path.read_text(encoding="utf-8"), variables)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(rendered, encoding="utf-8")
        created.append(target_path)

    if local:
        # Written only when missing: an existing one is never rewritten.
        hide = cwd / LOCAL_GITIGNORE
        if not hide.exists():
            hide.parent.mkdir(parents=True, exist_ok=True)
            hide.write_bytes(b"*\n")   # exactly `*` and a newline, on any OS
            created.append(hide)

    return created, skipped


def exclude_path(cwd: Path) -> Path | None:
    """The exclude file git reads for this project, or None outside git.

    Asked of git, not built from `.git/`, so a worktree (`.git` is a file)
    gets the right one.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-path", "info/exclude"],
            cwd=cwd, capture_output=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    text = result.stdout.decode("utf-8", errors="replace").strip()
    return cwd / text if text else None


def _with_local_note(existing: str) -> str | None:
    """The ignore text with the local note appended, or None if it has it."""
    if LOCAL_NOTE in existing.splitlines():
        return None

    if not existing:
        lead = ""              # fresh file: no leading blank line
    elif existing.endswith("\n"):
        lead = "\n"            # prior content ends cleanly: one blank separator
    else:
        lead = "\n\n"          # prior content lacks trailing newline: finish it, then separate
    return existing + lead + "# this machine's untracked note (added by cairn)\n" + LOCAL_NOTE + "\n"


def update_gitignore(cwd: Path) -> bool:
    """Append the local note to .gitignore once. Returns True if modified."""
    gitignore = cwd / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""

    updated = _with_local_note(existing)
    if updated is None:
        return False

    gitignore.write_text(updated, encoding="utf-8")
    return True


def update_exclude(exclude: Path) -> bool:
    """Append the local note to the exclude file once. Returns True if modified.

    Read and written byte for byte (no newline translation): the file is
    the user's, and everything already in it stays as it was.
    """
    existing = ""
    if exclude.exists():
        with open(exclude, encoding="utf-8", newline="") as f:
            existing = f.read()

    updated = _with_local_note(existing)
    if updated is None:
        return False

    exclude.parent.mkdir(parents=True, exist_ok=True)
    with open(exclude, "w", encoding="utf-8", newline="") as f:
        f.write(updated)
    return True


def _shown(path: Path, cwd: Path) -> Path:
    """The path relative to the project when it is under it, else as given."""
    try:
        return path.relative_to(cwd)
    except ValueError:
        return path


def _missing_imports(cwd: Path, skipped: list[Path]) -> list[str]:
    """Lines telling the user which imports a kept root note lacks.

    A root CLAUDE.local.md that already existed is never edited, so Claude
    Code would not load the local docs until the user adds the imports.
    """
    note = cwd / LOCAL_NOTE
    if note not in skipped:
        return []
    try:
        have = note.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        have = []
    lacking = [line for line in LOCAL_IMPORTS if line not in have]
    if not lacking:
        return []
    return [f"add to {LOCAL_NOTE} so the local docs load:"] + [f"  {line}" for line in lacking]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render the Cairn 2.0 spine for a project."
    )
    parser.add_argument(
        "--answers",
        required=True,
        help=(
            "JSON dict of interview answers. Required keys: project_name (str), "
            "intent (str), project_type (code|novel|content-site|business|research), "
            "adoption (greenfield|brownfield), mode (tracked|local)."
        ),
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Target project root (default: current directory).",
    )
    args = parser.parse_args(argv)

    try:
        answers = json.loads(args.answers)
    except json.JSONDecodeError as exc:
        print(f"ERROR: --answers is not valid JSON: {exc}", file=sys.stderr)
        return 1

    missing = REQUIRED_ANSWER_KEYS - set(answers)
    if missing:
        print(f"ERROR: missing required answer keys: {sorted(missing)}", file=sys.stderr)
        return 1

    cwd = Path(args.cwd).resolve()
    templates_dir = Path(__file__).parent / "templates"
    if not templates_dir.exists():
        print(f"ERROR: templates directory not found: {templates_dir}", file=sys.stderr)
        return 1

    today = date.today().isoformat()
    local = answers["mode"] == "local"
    exclude = None
    exclude_modified = False
    if local:
        # Check the answers, then write the exclude, before any file lands: a
        # failure leaves nothing for git to show.
        try:
            build_var_dict(answers, today)
        except (KeyError, TypeError, ValueError) as exc:
            print(f"ERROR: render failed: {exc}", file=sys.stderr)
            return 1
        exclude = exclude_path(cwd)
        if exclude is not None:
            try:
                exclude_modified = update_exclude(exclude)
            except OSError as exc:
                print(f"ERROR: could not write {exclude}: {exc}", file=sys.stderr)
                return 1

    try:
        created, skipped = render_all(answers, templates_dir, cwd, today)
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: render failed: {exc}", file=sys.stderr)
        return 1

    # Local mode never creates or edits the root .gitignore.
    gitignore_modified = False if local else update_gitignore(cwd)

    for f in created:
        print(f"created  {f.relative_to(cwd)}")
    for f in skipped:
        print(f"skipped  {f.relative_to(cwd)}  (exists)")
    if gitignore_modified:
        print("updated  .gitignore")

    if local:
        if exclude is None:
            print("note     not a git repository: no exclude file to update")
        elif exclude_modified:
            print(f"updated  {_shown(exclude, cwd)}")
        for line in _missing_imports(cwd, skipped):
            print(line)
        print(CLEAN_CAUTION)

    if answers["project_type"] == "code":
        try:
            pages.report(pages.run(cwd, pages.LOCAL_PAGE if local else pages.PAGE))
        except OSError as exc:
            print(f"ERROR: folder pages failed: {exc}", file=sys.stderr)
            return 1

    if not created:
        print("\nNothing new to create - every spine file already exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
