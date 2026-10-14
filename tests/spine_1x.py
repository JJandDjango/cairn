"""Test-side renderer for the 1.x six-strata spine (the audit fixture).

render.py writes only the 2.0 spine. audit.py still checks the 1.x strata
until the 2.0 build reworks it (Pass 5) and retires them (Pass 6), so its
tests build a 1.x spine here from the 1.x templates still on disk. Delete
this file with those templates in Pass 6.
"""
from __future__ import annotations

from pathlib import Path

import render

TEMPLATES = Path(render.__file__).parent / "templates"

TEMPLATE_TO_TARGET = {
    "THEORY.md.template": "THEORY.md",
    "MAP.md.template": "MAP.md",
    "STATE.md.template": "STATE.md",
    "CONVENTIONS.md.template": "CONVENTIONS.md",
    "DOCS-SYSTEM.md.template": "DOCS-SYSTEM.md",
    "decisions/0001-record-architecture-decisions.md.template": "decisions/0001-record-architecture-decisions.md",
    "decisions/ADR-template.md.template": "decisions/ADR-template.md",
}

COMPONENT_UNIT = {
    "code": ("Component", "Components"),
    "novel": ("Chapter", "Chapters"),
    "content-site": ("Section", "Sections"),
    "business": ("Workstream", "Workstreams"),
    "research": ("Claim", "Claims"),
}

CONVENTIONS_EXAMPLE = {
    "code": "- **Match the idiom.** New code follows the touched layer's dominant pattern.",
    "novel": "- **Tense and POV hold.** One narrative voice; a break is a marked choice.",
    "content-site": "- **One voice.** Active voice, second person, no unexplained jargon.",
    "business": "- **Decisions have owners.** Every decision names one accountable owner.",
    "research": "- **Claims cite methods.** No claim without the method and data behind it.",
}

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


def render_1x(answers: dict, cwd: Path, today: str) -> None:
    """Write the 1.x spine into cwd, as 1.2's render_all did (no backend)."""
    project_type = answers["project_type"]
    intent = str(answers["intent"]).strip()
    if answers["adoption"] == "brownfield":
        intent = f"{intent} _(inferred - confirm)_"
    unit_col, unit_plural = COMPONENT_UNIT[project_type]
    variables = {
        "project_name": answers["project_name"],
        "intent": intent,
        "project_type": project_type,
        "component_unit_col": unit_col,
        "component_unit_plural": unit_plural,
        "conventions_example": CONVENTIONS_EXAMPLE[project_type],
        "diagram_note": CODE_DIAGRAM_NOTE if project_type == "code" else NONCODE_DIAGRAM_NOTE,
        "map_mode": "hand-edited",
        "map_structured_stub": "",
        "backend_note": "",
        "date": today,
    }
    for template_name, target_rel in TEMPLATE_TO_TARGET.items():
        target = cwd / target_rel
        if target.exists():
            continue
        text = render.substitute((TEMPLATES / template_name).read_text(encoding="utf-8"), variables)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    (cwd / "docs").mkdir(parents=True, exist_ok=True)
    (cwd / "docs" / ".gitkeep").touch()
