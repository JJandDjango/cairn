# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-10-14._

## Now
- **Cairn 2.0 Pass 3 done** on `build-2.0-pass-3`. New
  `skills/cairn/status.py`, run as `/cairn status`, prints Last done
  (5 non-merge commits, 5 merged PRs), Next (5 oldest open issues) and
  Waiting on you (issues labelled `needs-ruling`). Every `gh` call goes
  through one seam that tests fake; `gh` missing or logged out degrades
  per section, exit 0. The `ARCHITECTURE.md` row names the command.
  Features 15, 16 are green in `docs/usage-2.0.md`.
- **Feature 16 ruling (2026-10-14, in `docs/design-2.0.md`)**:
  `git config cairn.plan <path>` names a markdown file; its first
  unfinished top-level numbered step (not starting `~~` or `[x]`) is Next,
  replacing issues with no fallback. Issues stay the default.
- **Two-Key held**: verifier PASS on attempt 1 (158 passed, 1 skipped);
  developer and verifier ran as subagents in one workflow.
- **Known gap until Pass 5**: `/cairn audit` checks the 1.x strata, so a
  fresh 2.0 project reports "no spine" (exit 2).
- **The build plan** is `plan.md` at the repo root (untracked). Each
  pass: test list for approval, build, verifier, PR, CI, merge.
- **Known audit warnings**: `BUDGET-ADR` on 0007 (accepted scar); three
  `CONV-SUPERSEDED` on CONVENTIONS.md, by design (Pass 7 retires it).
- **Skill install is a junction** - `~/.claude/skills/cairn` ->
  `E:\cairn\skills\cairn`; remove it before the marketplace install-test.

## Blockers
- None.

## Next actions
1. **Pass 4, local mode** (features 18-21): `CLAUDE.local.md`,
   `.docs-local/`, exclude entry, idempotent reruns, `git clean -x`
   caution. Unit test list for approval first.
2. Passes 5-7 per `plan.md`; rule on feature 29 before Pass 6.
3. Before Pass 7 removes Cairn's own `STATE.md`: update the
   `resume-session`, `handoff-session` and `end-session` skills.
4. Deferred carry-overs (`plan.md`): Pass 3 verifier nits
   (`test_promptlang.py` skips without `prompt_lang` installed, so CI
   should install it; `gh pr list` default limit could miss out-of-order
   merges; redundant BOM strip in `status.py`); Pass 2 verifier nits;
   `--answers` non-object JSON; `required_status_checks`; drop `_v0`
   from test names. Publish HELD.

## Open questions
- Feature 29 (1.x migration behavior), ruled at the start of Pass 6.
