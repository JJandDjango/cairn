# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-07-14._

## Now
- **1.1 "living-system" tier built and delivered as PR #2**
  (`add-audit-maintain` -> `main`, commit `b3751a2`; see
  [[0006-automate-detection-not-authorship]] + `ROADMAP.md` 1.1). Day-2
  *detection* is now automated; authorship stays human-reviewed.
  - **`/cairn audit`** - `skills/cairn/audit.py` (zero-dep core, report-only,
    git-optional): the DOCS-SYSTEM checklist, executable. Exit 0 clean / 1
    findings / 2 no spine; `--format json`. New covers-marker convention
    (`<!-- covers: paths -->`) makes docs-page staleness checkable.
  - **`/cairn maintain`** - session-end routine in SKILL.md: the agent runs
    audit, touches MAP / docs / STATE grounded in the observed diff, never
    THEORY or old ADRs, and leaves everything uncommitted for review.
  - Spine dogfooded: MAP row + diagram node, `docs/audit.md`, covers markers,
    DOCS-SYSTEM (repo + template) / USAGE / README / ROADMAP pointers.
- Suite **203 passed** (was 182; +21 audit tests). Verified live: fresh
  scaffold audits clean; three deliberate breaks each flagged; dogfood
  `audit --cwd E:\cairn` exits 0.
- **Local checkout is on `add-audit-maintain`** - after the PR merges, switch
  back to `main` and pull.

## Blockers
- None.

## Next actions
1. **Review + merge PR #2** (https://github.com/JJandDjango/cairn/pull/2 -
   maintainer's call; main requires PR per the protection ruleset).
2. **Stamp `v1.1.0`** in `.claude-plugin/plugin.json` when ready to release
   (the open ROADMAP 1.1 gate - deliberately left out of the PR).
3. **Publish** *(HELD - explicit go required)*: flip the repo public, then
   marketplace add + install-test (unchanged from 1.0).
4. Stranger-onboarding hardening pass, best timed right before publish.
5. Optional tidy: rename the `_v0` suffix on the functional contract tests.

## Open questions
- None.
