"""Render the Cairn 2.0 spine into a project directory.

Cairn writes the few short documents a new collaborator reads on day one:
root CLAUDE.md, README.md, ARCHITECTURE.md, CONTRIBUTING.md, CHANGELOG.md,
decisions/, docs/ templates, and a local, untracked note. Zero third-party
dependencies.

Invoked two ways:
  1. By the /cairn skill after its interview (see SKILL.md), or
  2. Directly by a human:
       python render.py --answers '{"project_name": "...", ...}' [--cwd DIR]

Answer keys (all required):
  project_name  (str)   e.g. "my-novel"
  intent        (str)   one line: "why does this exist?"
  project_type  (str)   code | novel | content-site | business | research
  adoption      (str)   greenfield | brownfield
  mode          (str)   tracked | local   (local is not built yet: exits 1)

Behavior:
  - {{ var }} substitution across templates (including decisions/ and docs/).
  - date.today() stamps the seed ADR.
  - project_type=code -> ARCHITECTURE.md gains the one diagram and the
    status-command row; every other type gets the same spine without them.
  - adoption=brownfield -> intent rendered with an `(inferred - confirm)` tag.
  - mode=tracked -> .gitignore gains `CLAUDE.local.md` once.
  - NO-CLOBBER: any target that already exists is skipped and reported, never
    overwritten (safe to run on a partly-documented project).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


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
}

REQUIRED_ANSWER_KEYS = {"project_name", "intent", "project_type", "adoption", "mode"}

PROJECT_TYPES = {"code", "novel", "content-site", "business", "research"}

MODES = {"tracked", "local"}

# The local note stays untracked; tracked mode keeps it out of git this way.
LOCAL_NOTE = "CLAUDE.local.md"

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

# The status command ships in a later pass of the 2.0 build, which names it.
CODE_STATUS_ROW = "| Last done, next, and what waits on you | The status command (to be named) |\n"


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
    if mode == "local":
        raise ValueError(
            "local mode is not built yet (Cairn 2.0 build, Pass 4); "
            "rerun with mode 'tracked'"
        )

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

    for template_name, target_rel in TEMPLATE_TO_TARGET.items():
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

    return created, skipped


def update_gitignore(cwd: Path) -> bool:
    """Append the local note to .gitignore once. Returns True if modified."""
    gitignore = cwd / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""

    if LOCAL_NOTE in existing.splitlines():
        return False

    if not existing:
        lead = ""              # fresh file: no leading blank line
    elif existing.endswith("\n"):
        lead = "\n"            # prior content ends cleanly: one blank separator
    else:
        lead = "\n\n"          # prior content lacks trailing newline: finish it, then separate
    block = lead + "# this machine's untracked note (added by cairn)\n" + LOCAL_NOTE + "\n"

    gitignore.write_text(existing + block, encoding="utf-8")
    return True


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
    try:
        created, skipped = render_all(answers, templates_dir, cwd, today)
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: render failed: {exc}", file=sys.stderr)
        return 1

    gitignore_modified = update_gitignore(cwd)

    for f in created:
        print(f"created  {f.relative_to(cwd)}")
    for f in skipped:
        print(f"skipped  {f.relative_to(cwd)}  (exists)")
    if gitignore_modified:
        print("updated  .gitignore")

    if not created:
        print("\nNothing new to create - every spine file already exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
