# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-07-12._

## Now
- **Standalone scrub complete.** Cairn now carries no knowledge of anything
  outside itself: the backend was renamed off its origin (schema key -> `cairn_schema`,
  symbols, file conventions), all provenance / external-spec references removed
  from code, tests, config, and docs, and the test fixtures genericized. Fast
  suite green (178 passed).
- **1.0 spec spine present + reworked.** `THEORY` / `MAP` / `decisions` / `ROADMAP`
  describe a focused, standalone, zero-dependency living doc system; the backend
  is an optional graphify integration ([[0002-optional-graphify-backend]]) and 1.0
  ships it, scrubbed ([[0003-1.0-scope]]).

## Blockers
- None. No git remote yet - publish is a post-1.0 step (per `ROADMAP.md`).

## Next actions
1. **Remaining 1.0 gates** (`ROADMAP.md`): complete the `DOCS-SYSTEM.md` day-2
   discipline; write a `docs/` page for the optional backend (derive / reconcile /
   view).
2. **Commit** the standalone repo (owner's call).
3. Optional tidy: the `_v0` suffix on the functional contract tests is a leftover
   naming convention, not a leak - rename at leisure.

## Open questions
- Does Cairn dogfood its *own* backend (derive its MAP via graphify) later, or
  stay hand-authored?
