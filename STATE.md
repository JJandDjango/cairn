# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-10-15._

## Now
- **Cairn 2.0 Pass 4 done** on `build-2.0-pass-4`. Local mode: spine under
  `.docs-local/` (its `.gitignore` is `*`, written only when missing), one
  root `CLAUDE.local.md` with the two imports and the "This machine" note,
  folder pages as `CLAUDE.local.md` (`pages.py --page`). `CLAUDE.local.md`
  is added once to the exclude file found via
  `git rev-parse --git-path info/exclude`; outside git, files are written
  and the exclude is skipped with one line. Every local run prints the
  `git clean -x` caution. No tracked file is written.
  Features 18-21 are green in `docs/usage-2.0.md`.
- **Two-Key held**: verifier PASS on attempt 1 (202 passed, 0 skipped),
  plus an end-to-end run in a scratch git repo and a non-git folder.
  Developer and verifier ran as subagents in one workflow.
- **Known gap until Pass 5**: `/cairn audit` checks the 1.x strata, so a
  fresh 2.0 project, local or tracked, reports "no spine" (exit 2).
- **The build plan** is `plan.md` at the repo root (untracked). Each
  pass: test list for approval, build, verifier, PR, CI, merge.
- **Known audit warnings**: `BUDGET-ADR` on 0007 (accepted scar); three
  `CONV-SUPERSEDED` on CONVENTIONS.md, by design (Pass 7 retires it).
- **Skill install is a junction** - `~/.claude/skills/cairn` ->
  `E:\cairn\skills\cairn`; remove it before the marketplace install-test.

## Blockers
- None.

## Next actions
1. **Pass 5, checks** (features 22-28): five audit checks, exit 1, CI
   workflow template, reworked `/cairn maintain`. Unit test list for
   approval first.
2. Pass 6 per `plan.md`; rule on feature 29 before it.
3. Before Pass 7 removes Cairn's own `STATE.md`: update the
   `resume-session`, `handoff-session` and `end-session` skills.
4. Deferred carry-overs (`plan.md`): Pass 4 verifier nits (run output
   mixes `\` and `/` in paths; exclude is written before `render_all`, so
   a later failure leaves the entry, harmless; `MAP.md` still says
   `render.py` is "tracked mode"); Pass 3 and Pass 2 verifier nits;
   `--answers` non-object JSON; `required_status_checks`; drop `_v0`
   from test names. Publish HELD.

## Open questions
- Feature 29 (1.x migration behavior), ruled at the start of Pass 6.
