# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-07-13._

## Now
- **Self-dogfood pass complete.** Ran Cairn against its own source - suite, spine
  audit, and the derived backend (`derive` / `stage` / `validate`). Healthy tool;
  three fixable items surfaced and all shipped, pushed to `origin/main` = `0ebd26c`
  (`github.com/JJandDjango/cairn`, private).
- **`validate` hardened.** It crashed with a raw traceback on a frontmatter-less
  MAP (the `backend: none` default, including Cairn's own). Now every parse failure
  degrades cleanly: read/decode (OSError, UnicodeDecodeError) -> `cannot read`;
  content (MapParseError, yaml.YAMLError) -> `INVALID`, each exit 1, never a
  traceback. +4 regression tests.
- **Self-application settled ([[0004-map-stays-hand-authored]]).** Cairn's own MAP
  stays hand-authored - `derive` collapses its 628-node self-graph to 1 opaque
  component vs. the 9 authored, so authored truth is the source of record. Closed
  the standing "dogfood our own backend?" question.
- **Suite hygiene.** Removed the vestigial AC-8 `@slow` real-graph regression
  (non-hermetic cwd read, pinned to a pre-standalone fixture project) + its
  orphaned `slow` marker/refs; the file-loading path stays covered hermetically.
  **182 passed, 0 skipped, 0 warnings.**
- **Errata.** Commits `6af1f09` / `0ebd26c` / `e86f47b` carry an inaccurate
  `Claude-Session` footer; the correct session and the rationale for leaving
  history intact are recorded in [[0005-record-commit-footer-errata]].

## Blockers
- None.

## Next actions
1. **Remaining 1.0 gates** (`ROADMAP.md`): finish the `DOCS-SYSTEM.md` day-2
   discipline; write a `docs/` page for the optional backend (derive / reconcile /
   view).
2. **Pre-public hygiene**: pin line endings via `.gitattributes` (LF) - Git flags
   `LF -> CRLF` on commits here; marketplace / public listing stays post-1.0.
3. Optional tidy: the `_v0` suffix on the functional contract tests is a leftover
   naming convention - rename at leisure.

## Open questions
- None open - [[0004-map-stays-hand-authored]] closed the dogfood question.
