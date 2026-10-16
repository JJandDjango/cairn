# Changelog

Notable changes to Cairn, newest first.

## 2.0.0

The strata are replaced by a few short onboarding documents, read top-down.

- **New spine**: root `CLAUDE.md` (imports `README.md` and `ARCHITECTURE.md`),
  `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, with
  size budgets enforced as checks.
- **Folder pages** (code projects): a `CLAUDE.md` per working folder, its
  file lines copied from docstrings.
- **`/cairn status`**: last done, next and what waits on you, derived from
  git and issues. There is no `STATE.md`.
- **Local mode**: nothing tracked is ever written.
- **`/cairn audit`**: budgets, no `@` imports, links, fresh generated
  lines, folder coverage. CI template included.
- **`/cairn migrate`**: moves a 1.x spine to the 2.0 pages, report-first.
- **Removed**: the six strata, the graphify backend, and every 1.x check
  and template ([ADR 0009](decisions/0009-onboarding-documents-replace-the-strata.md)).

## 1.2.0

The conventions stratum (`CONVENTIONS.md`).

## 1.1.0

`/cairn audit` and `/cairn maintain`.

## 1.0.0

The standalone tool: scaffold core and optional graphify backend.
