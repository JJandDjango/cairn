# Audit - the executable checklist

> **docs/ stratum** - *how does this piece work?* This page covers `audit.py`,
> the zero-dependency spine checker behind `/cairn audit` and the detection
> half of `/cairn maintain` ([[0006-automate-detection-not-authorship]]).

<!-- covers: skills/cairn/audit.py -->

## What it is
A deterministic, REPORT-ONLY checker that makes the `DOCS-SYSTEM.md` audit
checklist executable. Core tier: stdlib only, works
on non-code spines and without git (history checks degrade to mtimes or skip).

Run it via `/cairn audit`, or standalone:
`python skills/cairn/audit.py [--cwd DIR] [--format text|json]`.
Exit codes: **0** clean (INFO allowed) - **1** any WARN/ERROR - **2** no spine.

## The checks

| Code | Fires when | Severity |
|---|---|---|
| `SPINE-MISSING` | a stratum file/dir is absent | ERROR |
| `MAP-DOC-MISSING` | a MAP Deep-doc cell is neither "no doc yet" nor an existing file | ERROR |
| `DOCS-ORPHAN` | a docs/ page no MAP row references | INFO |
| `DIAGRAM-COUNT` / `DIAGRAM-PLACE` | >1 mermaid diagram, or one outside MAP.md (zero -> INFO) | WARN |
| `BUDGET-*` | a stratum exceeds its budget; a page ~= 80 raw lines (ADR = 1/2) | WARN |
| `STATE-STALE` | STATE's `_Generated_` stamp predates newer spine activity, or is missing | WARN |
| `ADR-EDITED` | git only: an ADR modified after creation (a digit-bearing "superseded by" stamp -> INFO, the one sanctioned edit) | WARN |
| `ADR-DUP` / `ADR-SUPERSEDE` | duplicate ADR numbers / "superseded by NNNN" pointing nowhere | ERROR |
| `INFERRED-TAG` | THEORY.md intent or CONVENTIONS.md entries still carry `(inferred)` outside HTML comments | WARN |
| `CONV-LINK` / `CONV-SUPERSEDED` | a CONVENTIONS.md entry cites an ADR that does not exist / one that is superseded | ERROR / WARN |
| `DOCS-STALE` | a page is older than a file its covers marker names (no marker -> one aggregate INFO) | WARN |

`CONVENTIONS.md` is opt-in (pre-1.2 spines never scaffolded it): absent means no
findings; present means budget, links, and tags are enforced. HTML comments are
invisible to its checks, so guidance text and commented-out entries never flag.

## The covers marker
A docs page may declare what it explains, so staleness is checkable:
`<!-- covers: skills/cairn/render.py, skills/cairn/templates/ -->` -
comma-separated files, directories, or globs, relative to the project root.
Derived churn (`__pycache__`, `.git`, `node_modules`, `.pytest_cache`, `.pyc`) never counts as
activity. Last-touch dates come from git when available, else mtimes.

## The one invariant
Audit detects; it never authors. Fix-ups stay with the human - or with
`/cairn maintain`, whose agent-made touches land uncommitted for review.
