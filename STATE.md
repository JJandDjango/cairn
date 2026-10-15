# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-10-15._

## Now
- **Cairn 2.0 Pass 5 done** on `build-2.0-pass-5`. `audit.py` runs five
  2.0 checks (`SIZE-BUDGET`, `AT-IMPORT`, `LINK-BROKEN`, `GEN-STALE`,
  `COVER-PAGE`/`COVER-FILE`; all ERROR, exit 1) in tracked and local mode.
  `pages.plan()` is the no-write step behind freshness and coverage.
  Detection: `ARCHITECTURE.md` at the root or in `.docs-local/`; a folder
  with both spines runs both check sets, neither exits 2. Tracked mode
  writes `.github/workflows/cairn-audit.yml` (no-clobber, every type);
  it clones the cairn repo at `CAIRN_REF: main`, so it works for other
  projects only once the repo is public. `/cairn maintain` has a 2.0
  branch with no `STATE.md`. Features 22-28 are green in
  `docs/usage-2.0.md`.
- **Two-Key held**: verifier PASS on attempt 1 (283 passed, 0 skipped),
  plus an end-to-end break-each-check run in both modes. Developer and
  verifier ran as subagents in one workflow.
- **Code detection ruled 2026-10-15**: audit reads a project as code
  from the status-command table row in `ARCHITECTURE.md` (outside a
  code fence); with no row it falls back to a folder page existing. A
  code project with its pages deleted now gets `COVER-PAGE`. Verifier
  PASS on attempt 2 (293 passed); attempt 1 let prose mentions of
  `/cairn status` count as the marker.
- **The 1.x checks remain** until Pass 6; this repo still audits as 1.x.
- **The build plan** is `plan.md` at the repo root (untracked). Each
  pass: test list for approval, build, verifier, PR, CI, merge.
- **Known audit warnings**: `BUDGET-ADR` on 0007 (accepted scar); three
  `CONV-SUPERSEDED` on CONVENTIONS.md, by design (Pass 7 retires it).
- **Skill install is a junction** - `~/.claude/skills/cairn` ->
  `E:\cairn\skills\cairn`; remove it before the marketplace install-test.

## Blockers
- None.

## Next actions
1. **Pass 6, migration and retirement** (features 29, 30): rule on
   feature 29's behavior first; then retire the six-strata templates and
   checks. Unit test list for approval.
2. **Pass 7, dogfood and release** (31); pin `CAIRN_REF` to `2.0.0`.
3. Before Pass 7 removes Cairn's own `STATE.md`: update the
   `resume-session`, `handoff-session` and `end-session` skills.
4. Deferred carry-overs (`plan.md`): Pass 5 verifier nits (`AT-IMPORT`
   flags `@` after `/` or `(` in prose; reference-style links not
   checked; `MAP.md` rows for `audit.py` and `render.py` stale); Pass 4,
   3, 2 nits; `--answers` non-object JSON; `required_status_checks`;
   drop `_v0` from test names. Publish HELD.

## Open questions
- Feature 29 (1.x migration behavior), ruled at the start of Pass 6.
