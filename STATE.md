# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-10-15._

## Now
- **Cairn 2.0 Pass 6 done** on `build-2.0-pass-6`. New `migrate.py`
  (`/cairn migrate`): a dry run prints one line per 1.x file; `--apply`
  renames `MAP.md` to `ARCHITECTURE.md`, appends `THEORY.md` there and
  `CONVENTIONS.md` / `DOCS-SYSTEM.md` into `CONTRIBUTING.md` under
  `## From <FILE>.md`, and removes a source only after its text is found
  in the destination. It never touches `STATE.md` (Claude routes its parts,
  trims to budget, then removes it) or `decisions/` and `docs/`. Local mode
  migrates inside `.docs-local/`. Features 29, 30 are green in
  `docs/usage-2.0.md`.
- **1.x retired**: the five 1.x templates and every 1.x check are gone from
  `audit.py`. A 1.x-only spine audits to exit 2 with a pointer to
  `/cairn migrate`; a 2.0 spine with leftover 1.x files gets one INFO,
  `LEGACY-1X`. **This repo is a 1.x spine, so its own audit exits 2 until
  Pass 7** (its CI does not run the audit).
- **Two-Key held**: verifier PASS on attempt 1 (347 passed, 0 skipped),
  plus hand probes (CRLF, empty sources, existing destinations, local
  mode, write failure). Test author, developer and verifier ran as
  subagents (Sonnet 5.5) in one workflow; the developer never read `tests/`.
- **Feature 29 ruled 2026-10-15**: report-first; the script does the
  mechanical moves, Claude does the judgment calls.
- **The build plan** is `plan.md` at the repo root (untracked). Each
  pass: test list for approval, build, verifier, PR, CI, merge.
- **Known audit warnings**: none now (the 1.x checks that raised
  `BUDGET-ADR` and `CONV-SUPERSEDED` are retired).
- **Skill install is a junction** - `~/.claude/skills/cairn` ->
  `E:\cairn\skills\cairn`; remove it before the marketplace install-test.

## Blockers
- None.

## Next actions
1. **Pass 7, dogfood and release** (31): Cairn adopts 2.0 in this repo
   (migrate it with `/cairn migrate`); `docs/usage-2.0.md` replaces
   `USAGE.md`; rewrite `README.md`; version `2.0.0`; pin `CAIRN_REF`.
2. Before Pass 7 removes Cairn's own `STATE.md`: update the
   `resume-session`, `handoff-session` and `end-session` skills.
3. Deferred carry-overs (`plan.md`): Pass 6 verifier nits (non-atomic
   `migrate._merge` write; duplicate `## From` heading; CRLF separator;
   `.docs-local` 1.x pointer mismatch between audit and migrate); Pass 5,
   4, 3, 2 nits (`MAP.md` rows for `audit.py` and `render.py` are stale);
   `--answers` non-object JSON; `required_status_checks`; drop `_v0` from
   test names. Publish HELD.

## Open questions
- None.
