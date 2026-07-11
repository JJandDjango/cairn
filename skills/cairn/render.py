"""Render the Cairn documentation spine into a project directory.

Cairn lays down a pace-layered documentation spine — five strata, each under a
fixed contract (one question / size budget / update trigger / maintenance mode) —
for any project, code or not. Zero third-party dependencies.

Invoked two ways:
  1. By the /cairn skill after its interview (see SKILL.md), or
  2. Directly by a human:
       python render.py --answers '{"project_name": "...", ...}' [--cwd DIR]

Answer keys (all required):
  project_name  (str)   e.g. "my-novel"
  intent        (str)   one line: "why does this exist?"
  project_type  (str)   code | novel | content-site | business | research
  backend       (str)   none | graphify   (graphify only meaningful for code)
  material      (str)   greenfield | brownfield

Behavior:
  - {{ var }} substitution across templates (including nested decisions/).
  - date.today() stamps STATE.md and the seed ADR.
  - project_type -> component unit (Component / Chapter / Section / ...).
  - backend=graphify (code only) -> MAP gains an optional structured-schema stub
    and points at `/cairn derive`; .gitignore gains graphify-out/ + /manifest.json.
  - material=brownfield -> intent rendered with an `(inferred - confirm)` tag.
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
    "THEORY.md.template": "THEORY.md",
    "MAP.md.template": "MAP.md",
    "STATE.md.template": "STATE.md",
    "DOCS-SYSTEM.md.template": "DOCS-SYSTEM.md",
    "decisions/0001-record-architecture-decisions.md.template": "decisions/0001-record-architecture-decisions.md",
    "decisions/ADR-template.md.template": "decisions/ADR-template.md",
}

REQUIRED_ANSWER_KEYS = {"project_name", "intent", "project_type", "backend", "material"}

PROJECT_TYPES = {"code", "novel", "content-site", "business", "research"}

# project_type -> (column label [singular], section heading [plural])
COMPONENT_UNIT = {
    "code": ("Component", "Components"),
    "novel": ("Chapter", "Chapters"),
    "content-site": ("Section", "Sections"),
    "business": ("Workstream", "Workstreams"),
    "research": ("Claim", "Claims"),
}

# .gitignore entries added ONLY when the graphify backend is chosen.
BACKEND_GITIGNORE_ENTRIES = ["graphify-out/", "/manifest.json"]

CODE_DIAGRAM_NOTE = (
    "```mermaid\n"
    "flowchart TD\n"
    "    A[component A] --> B[component B]\n"
    "```\n"
    "<!-- The ONE diagram in this project, at ~C4 container zoom. Anything deeper\n"
    "     rots faster than you can maintain it - use the table below for detail. -->"
)

NONCODE_DIAGRAM_NOTE = (
    "<!-- No diagram for a non-code project - the table below is the map.\n"
    "     Add a single Mermaid diagram here only if it genuinely earns its upkeep. -->"
)


def _structured_map_stub(project_name: str, purpose: str) -> str:
    """OPTIONAL structured-model stub prepended to MAP.md for graphify-backend code
    projects (Slice 2, Decision C). A commented block mirroring backend/schema.py so
    the schema is discoverable without forcing frontmatter onto a fresh MAP: a
    hand-author uncomments and fills it, or `/cairn derive` generates it from the
    code graph. Returns "" for every non-backend project -> that MAP renders
    unchanged. Values are interpolated here (not via {{ }}) so the single-pass
    substitutor never rescans this block. `atlas_schema` is the schema version key
    (backend/schema.py), not the retired backend name."""
    return (
        "<!-- OPTIONAL structured model - graphify-backend projects only.\n"
        "     Uncomment the YAML and fill it, or run `/cairn derive` to generate it\n"
        "     from the code graph (then `/cairn reconcile` to keep authored vs\n"
        "     derived honest). Schema + validation: backend/schema.py.\n"
        "\n"
        "atlas_schema: 1\n"
        f"name: {project_name}\n"
        f"purpose: {purpose}\n"
        "status: active            # greenfield | active | maintenance | archived\n"
        "components:                # >=1 required once uncommented\n"
        "  - name: example-component\n"
        "    role: what it does (one line)\n"
        "    level: module          # system | module | implementation\n"
        "    location: path/to/file.py\n"
        "# flows:                   # optional: named paths through >=2 components\n"
        "#   - name: main-flow\n"
        "#     entry: example-component\n"
        "#     stages:\n"
        "#       - component: example-component\n"
        "#         role: start\n"
        "#         stage: entry\n"
        "-->\n\n"
    )


def _docs_backend_note() -> str:
    """The optional-backend bullet appended to DOCS-SYSTEM.md for graphify-backend
    projects. Returns "" otherwise -> that DOCS-SYSTEM renders unchanged."""
    return (
        "\n- **Optional structured MAP (backend projects).** With the graphify "
        "backend, `MAP.md` may carry a YAML frontmatter model (components / flows / "
        "typed relationships; schema in `backend/schema.py`). Generate it with "
        "`/cairn derive`, reconcile authored vs derived with `/cairn reconcile`, and "
        "roll up the portfolio with `/cairn view`. Without the backend, `MAP.md` is a "
        "hand-edited table - no frontmatter required."
    )


def substitute(template_text: str, variables: dict) -> str:
    """Substitute {{ var }} placeholders in one pass."""
    pattern = re.compile(r"\{\{\s*(\w+)\s*\}\}")

    def replace(match):
        key = match.group(1)
        if key not in variables:
            raise KeyError(f"Template references unknown variable: {key}")
        return str(variables[key])

    return pattern.sub(replace, template_text)


def effective_backend(answers: dict) -> str:
    """The graphify backend is only meaningful for code; coerce to none otherwise."""
    backend = answers.get("backend", "none")
    if backend == "graphify" and answers.get("project_type") != "code":
        return "none"
    return backend


def build_var_dict(answers: dict, today: str) -> dict:
    """Expand interview answers into the full template variable namespace."""
    project_type = answers["project_type"]
    if project_type not in PROJECT_TYPES:
        raise ValueError(
            f"project_type must be one of {sorted(PROJECT_TYPES)}, got {project_type!r}"
        )
    material = answers["material"]
    if material not in {"greenfield", "brownfield"}:
        raise ValueError(
            f"material must be 'greenfield' or 'brownfield', got {material!r}"
        )
    if answers.get("backend") not in {"none", "graphify"}:
        raise ValueError(
            f"backend must be 'none' or 'graphify', got {answers.get('backend')!r}"
        )

    backend = effective_backend(answers)
    unit_col, unit_plural = COMPONENT_UNIT[project_type]

    intent_plain = str(answers["intent"]).strip()
    if not intent_plain:
        raise ValueError("intent must be a non-empty one-line string")
    intent = (
        f"{intent_plain} _(inferred - confirm)_" if material == "brownfield"
        else intent_plain
    )

    diagram_note = CODE_DIAGRAM_NOTE if project_type == "code" else NONCODE_DIAGRAM_NOTE

    if backend == "graphify":
        map_mode = (
            "hand-edited **or** graphify-derived (run `/cairn derive` to regenerate "
            "the component table from the code graph)"
        )
        map_structured_stub = _structured_map_stub(answers["project_name"], intent_plain)
        backend_note = _docs_backend_note()
    else:
        map_mode = "hand-edited"
        map_structured_stub = ""
        backend_note = ""

    return {
        "project_name": answers["project_name"],
        "intent": intent,
        "project_type": project_type,
        "component_unit_col": unit_col,
        "component_unit_plural": unit_plural,
        "diagram_note": diagram_note,
        "map_mode": map_mode,
        "map_structured_stub": map_structured_stub,
        "backend_note": backend_note,
        "date": today,
    }


def render_all(answers: dict, templates_dir: Path, cwd: Path, today: str):
    """Render every stratum. Returns (created, skipped) path lists. No-clobber."""
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

    # docs/ stratum: an empty directory (pages are authored on touch, not up front).
    gitkeep = cwd / "docs" / ".gitkeep"
    if gitkeep.exists():
        skipped.append(gitkeep)
    else:
        gitkeep.parent.mkdir(parents=True, exist_ok=True)
        gitkeep.touch()
        created.append(gitkeep)

    return created, skipped


def update_gitignore(cwd: Path, backend: str) -> bool:
    """Append graphify-backend entries to .gitignore. Returns True if modified."""
    if backend != "graphify":
        return False

    gitignore = cwd / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""

    additions = [e for e in BACKEND_GITIGNORE_ENTRIES if e not in existing]
    if not additions:
        return False

    if not existing:
        lead = ""              # fresh file: no leading blank line
    elif existing.endswith("\n"):
        lead = "\n"            # prior content ends cleanly: one blank separator
    else:
        lead = "\n\n"          # prior content lacks trailing newline: finish it, then separate
    block = lead + "# graphify derived artifacts (added by cairn)\n"
    block += "".join(f"{e}\n" for e in additions)

    gitignore.write_text(existing + block, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render the Cairn documentation spine for a project."
    )
    parser.add_argument(
        "--answers",
        required=True,
        help=(
            "JSON dict of interview answers. Required keys: project_name (str), "
            "intent (str), project_type (code|novel|content-site|business|research), "
            "backend (none|graphify), material (greenfield|brownfield)."
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

    gitignore_modified = update_gitignore(cwd, effective_backend(answers))

    for f in created:
        print(f"created  {f.relative_to(cwd)}")
    for f in skipped:
        print(f"skipped  {f.relative_to(cwd)}  (exists)")
    if gitignore_modified:
        print("updated  .gitignore")

    if not created:
        print("\nNothing new to create - every stratum already exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
