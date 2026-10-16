# Audit: what `/cairn audit` checks

`audit.py` is the zero-dependency checker behind `/cairn audit` and the
detection half of `/cairn maintain`
([0006](../decisions/0006-automate-detection-not-authorship.md)). It
reports; it never writes.

## Run it

Run `/cairn audit`, or
`python skills/cairn/audit.py [--cwd DIR] [--format text|json]`.

| Exit | Meaning |
|---|---|
| 0 | Clean. INFO findings are allowed. |
| 1 | At least one ERROR or WARN finding. |
| 2 | No 2.0 spine, or bad usage. A folder holding only 1.x files gets a one-line pointer to `/cairn migrate`. |

The spine is `ARCHITECTURE.md` in `.docs-local/` (local mode, which wins
when both exist) or at the root (tracked mode). Local mode reads the top
pages in `.docs-local/` and folder pages named `CLAUDE.local.md`; tracked
mode reads the root files and folder pages named `CLAUDE.md`. Git is
optional: it only lists files for the folder checks, so a novel in a bare
folder audits as cleanly as a code repo.

## The checks

| Code | Fires when | Severity |
|---|---|---|
| `SIZE-BUDGET` | A file is over budget (1 KB = 1024 bytes): `README.md` 2 KB, `ARCHITECTURE.md` 3 KB, `CONTRIBUTING.md` 3 KB, a folder page 2 KB. The tracked root `CLAUDE.md` may hold 10 lines. | ERROR |
| `AT-IMPORT` | An import-shaped `@` (one that starts a word) sits outside code in `README.md`, `ARCHITECTURE.md` or a folder page. The finding names the line. | ERROR |
| `LINK-BROKEN` | A relative link in a top page or folder page points at a file or folder that does not exist. Anchors are stripped; external, `mailto`, `#`-only and in-code links are skipped. | ERROR |
| `GEN-STALE` | A folder page's generated block differs from what `pages.py` would write now. | ERROR |
| `GEN-STALE` | A folder page has no block markers, so its lines cannot be verified. | INFO |
| `COVER-PAGE` | A working folder has no page. | ERROR |
| `COVER-FILE` | A file in a paged folder has no line in its page. | ERROR |
| `LEGACY-1X` | 1.x files (`THEORY.md`, `MAP.md`, `STATE.md`, `CONVENTIONS.md`, `DOCS-SYSTEM.md`) still sit beside the 2.0 spine. The message names `/cairn migrate`; no 1.x check runs. | INFO |

## Folder checks

`GEN-STALE`, `COVER-PAGE` and `COVER-FILE` run for a code project. The
audit knows it is one from the `/cairn status` row in `ARCHITECTURE.md`,
which `render.py` writes for code only, so a code project whose pages
were never made or were deleted still gets `COVER-PAGE`. When the row is
absent, the folder checks run only if at least one folder page exists. A
novel or a business plan has no folder checks.

## Retired in 2.0

The 1.x checks are gone: `SPINE-MISSING`, the strata budgets (`BUDGET-*`),
`STATE-STALE`, `DOCS-STALE` and its covers marker, `MAP-DOC-MISSING`,
`DOCS-ORPHAN`, the diagram checks, `ADR-*`, `INFERRED-TAG` and `CONV-*`.
`/cairn migrate` moves a 1.x spine to the 2.0 pages.

## The one invariant

Audit detects; it never authors. Fix-ups stay with the human, or with
`/cairn maintain`, whose touches land uncommitted for review.
