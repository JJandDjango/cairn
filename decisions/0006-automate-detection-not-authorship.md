# 6. Automate detection, not authorship

Status: accepted
Date: 2026-07-14

## Context
Day-2 upkeep was pure human discipline: every stratum has one update trigger,
but nothing *noticed* a stale docs page, an unmapped component, or a busted
budget - the DOCS-SYSTEM audit checklist was prose, not a program. The obvious
fix, regenerating MAP/docs mechanically, is ruled out: THEORY forbids Cairn
authoring content, and [[0004-map-stays-hand-authored]] showed empirically that
derived structure is less legible than authored meaning.

## Decision
Split the routine: **machines detect, humans (or their reviewed agent) author.**
- `/cairn audit` (`audit.py`, zero-dep core, NOT behind the backend gate): the
  checklist made executable - report-only, never writes, git optional. Exit
  0 clean / 1 findings / 2 no spine.
- `/cairn maintain` (skill-layer routine): at session end the agent runs audit,
  does the MAP-row / docs-page touches grounded in the session's observed diff,
  regenerates STATE, and leaves everything uncommitted - the human's acceptance
  gate is commit review. THEORY and existing ADRs are never machine-edited,
  only flagged.

Interpretations fixed here: a "page" ~= 80 raw lines; the diagram rule is
enforced as "at most one, and it lives in MAP.md" (zero is fine - non-code
scaffolds have none); a docs page may declare `<!-- covers: paths -->` so its
staleness is checkable; a modified ADR that gained a digit-bearing "superseded
by" stamp is the one sanctioned edit (INFO, not WARN).

## Consequences
- The audit checklist stops rotting: `/cairn audit` is runnable by anyone,
  including CI, on code and non-code spines alike.
- A freshly rendered scaffold passes its own audit (regression-tested).
- "Human owns the why" holds: deterministic Cairn still writes no authored
  stratum; maintain's writes are the user's agent acting under commit review.
