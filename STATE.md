# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-10-14._

## Now
- **Cairn 2.0 build started: Pass 0 done.** PR #11 merged (`25ee2f3`):
  `docs/usage-2.0.md`, the 2.0 user guide written before the code. Each
  section names its feature numbers and is marked 🔴; each pass flips its
  own. `USAGE.md` stays on 1.2 until Pass 7. Two calls made in it:
  non-code projects get the spine only, and the status command stays
  unnamed until Pass 3 names it.
- **The build plan** is `plan.md` at the repo root (untracked; a read-only
  copy at https://claude.ai/artifact/UQn9XXM4UxBTkfP9aZQmSM). Seven passes,
  one per session, each its own branch and PR, each opening with its unit
  test list for approval, then developer and verifier (Two-Key).
- The shipped code is still 1.2 (six strata); THEORY and ADR 0009 describe
  2.0. That gap is the accepted cost until the build lands.
- **Known audit warnings**: `BUDGET-ADR` on 0007 (accepted scar);
  three `CONV-SUPERSEDED` on CONVENTIONS.md, by design (Pass 7 retires
  that file into CONTRIBUTING.md).
- **Working style that held**: one ruling per question, recommendation
  first; the user reviews pushed PR links and artifact links on a phone.
- **Skill install is a junction** - `~/.claude/skills/cairn` ->
  `E:\cairn\skills\cairn`; remove it before the marketplace install-test.

## Blockers
- None.

## Next actions
1. **Pass 1, spine** (features 1-12): new templates, the interview's
   tracked/local mode, the graphify backend removed with its code and
   tests. Open with the unit test list for approval.
2. Passes 2-7 per `plan.md`; rule on feature 16 before Pass 3 and on
   feature 29 before Pass 6.
3. Before Pass 7 removes Cairn's own `STATE.md`: update the
   `resume-session`, `handoff-session` and `end-session` skills.
4. Publish stays HELD (explicit go). Optional carry-overs:
   `required_status_checks` on protect-main; drop `_v0` from test names.

## Open questions
- Feature 16 (pluggable "next" source) and feature 29 (1.x migration
  behavior), each ruled at the start of its pass.
