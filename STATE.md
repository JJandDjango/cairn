# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-07-14._

## Now
- **1.1 "living-system" tier built** ([[0006-automate-detection-not-authorship]]
  + `ROADMAP.md` 1.1): day-2 *detection* is now automated; authorship stays
  human-reviewed.
  - **`/cairn audit`** - `skills/cairn/audit.py` (zero-dep core, report-only,
    git-optional): the DOCS-SYSTEM checklist, executable. Exit 0 clean / 1
    findings / 2 no spine. New covers-marker convention
    (`<!-- covers: paths -->`) makes docs-page staleness checkable.
  - **`/cairn maintain`** - session-end routine in SKILL.md: the agent runs
    audit, touches MAP / docs / STATE grounded in the observed diff, never
    THEORY or old ADRs, and leaves everything uncommitted for review.
  - Dogfooded on this repo: MAP gained the `audit.py` row + diagram node;
    `docs/audit.md` authored; covers markers on both docs pages; DOCS-SYSTEM
    (repo + template), USAGE, and README point at the new subcommands; this
    STATE was regenerated via the maintain flow itself.
- Suite **203 passed** (was 182; +21 audit tests, incl. the acceptance
  constraint "a fresh scaffold passes its own audit").
- Verified end-to-end: fresh scratchpad scaffold audits clean; three deliberate
  breaks (missing doc link / second diagram / backdated stamp) each flagged
  with the right code; dogfood `audit --cwd E:\cairn` exits 0.

## Blockers
- None.

## Next actions
1. **Review + commit this session's diff** (per the maintain contract, nothing
   was committed).
2. **Stamp `v1.1.0`** in `.claude-plugin/plugin.json` when ready to release
   (the open ROADMAP 1.1 gate - user's call).
3. **Publish** *(HELD - explicit go required)*: flip the repo public, then
   marketplace add + install-test (unchanged from 1.0).
4. Stranger-onboarding hardening pass, best timed right before publish.
5. Optional tidy: rename the `_v0` suffix on the functional contract tests.

## Open questions
- None.
