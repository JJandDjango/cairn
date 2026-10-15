# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-10-14._

## Now
- **Cairn 2.0 Pass 2 done.** PR #15 merged (`7385454`), CI green on
  Ubuntu and Windows. New `skills/cairn/pages.py` writes a `CLAUDE.md`
  folder page in each working folder of a code project (Purpose, Files,
  Rules, Links); docstring first lines (Python, leading `/** */`, Rust
  `//!`) live between `<!-- cairn:files -->` markers, the only text a
  rerun rewrites. `render.py` runs it for code; it also runs alone. The
  `CONTRIBUTING.md` template states the mid-work handoff rule. Features
  13, 14, 17 are green in `docs/usage-2.0.md`.
- **Folder rulings (2026-10-14, in `docs/design-2.0.md`)**: virtualenvs
  (`pyvenv.cfg`) count as vendored; root `decisions/` gets no page,
  `docs/` does; every file in a paged folder gets a line, dotfiles too.
- **Two-Key held**: verifier FAIL on attempt 1 (pages written into a
  virtualenv), PASS on attempt 2; run as a one-agent workflow.
- **Known gap until Pass 5**: `/cairn audit` checks the 1.x strata, so a
  fresh 2.0 project reports "no spine" (exit 2).
- **The build plan** is `plan.md` at the repo root (untracked). Each
  pass: test list for approval, build, verifier, PR, CI, merge.
- **Known audit warnings**: `BUDGET-ADR` on 0007 (accepted scar); three
  `CONV-SUPERSEDED` on CONVENTIONS.md, by design (Pass 7 retires it).
- **Session settings**: `promptCacheTtl: "1h"` in user settings; the
  ccstatusline cache-timer widget set to 3600 s.
- **Skill install is a junction** - `~/.claude/skills/cairn` ->
  `E:\cairn\skills\cairn`; remove it before the marketplace install-test.

## Blockers
- None.

## Next actions
1. **Pass 3, status command** (features 15, 16): last done, next,
   `needs-ruling`. Rule on feature 16's open item (pluggable "next"
   source) first, then the unit test list for approval.
2. Passes 4-7 per `plan.md`; rule on feature 29 before Pass 6.
3. Before Pass 7 removes Cairn's own `STATE.md`: update the
   `resume-session`, `handoff-session` and `end-session` skills.
4. Deferred carry-overs (`plan.md`): Pass 2 verifier nits (`_safe`
   single-pass strip, root-level `pyvenv.cfg` git vs non-git, no test for
   `render.main`'s pages error exit); `--answers` non-object JSON;
   `required_status_checks`; drop `_v0` from test names. Publish HELD.

## Open questions
- Feature 16 (pluggable "next" source) and feature 29 (1.x migration
  behavior), each ruled at the start of its pass.
