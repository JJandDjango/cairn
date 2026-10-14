# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-10-14._

## Now
- **Cairn 2.0 Pass 1 done.** PR #13 merged (`8a23103`), CI green on
  Ubuntu and Windows. `render.py` writes the 2.0 spine: root `CLAUDE.md`
  (imports README and ARCHITECTURE), `README.md`, `ARCHITECTURE.md`,
  `CONTRIBUTING.md`, `CHANGELOG.md`, the ADR seed and template,
  `docs/{recipe,feature,design}-template.md`, and an untracked
  `CLAUDE.local.md`. The interview asks tracked or local mode. The graphify
  backend is gone, with its code, tests and `docs/backend.md`.
- **Rulings A-D** (in PR #13): the local note is root `CLAUDE.local.md`,
  which tracked mode adds to `.gitignore` once; local mode exits 1 until
  Pass 4; the 1.x templates stay only as the audit fixture
  (`tests/spine_1x.py`) until Pass 6; docs templates are `*-template.md`.
- **Known gap until Pass 5**: `/cairn audit` checks the 1.x strata, so a
  fresh 2.0 project reports "no spine" (exit 2).
- **PromptLang scope**: `*.md.template` files are never validated (the
  validator collects `*.md` only) and stay unclaimed by design (ADR 0007);
  only `SKILL.md` is claimed.
- **The build plan** is `plan.md` at the repo root (untracked; read-only
  copy at https://claude.ai/artifact/UQn9XXM4UxBTkfP9aZQmSM). Each pass:
  test list for approval, build, independent verifier (Two-Key, run as a
  one-agent workflow since no Task tool is present), PR, CI, merge.
- **Known audit warnings**: `BUDGET-ADR` on 0007 (accepted scar); three
  `CONV-SUPERSEDED` on CONVENTIONS.md, by design (Pass 7 retires it).
- **Working style that held**: one ruling per question, recommendation
  first; PR and artifact links reviewed on a phone.
- **Skill install is a junction** - `~/.claude/skills/cairn` ->
  `E:\cairn\skills\cairn`; remove it before the marketplace install-test.

## Blockers
- None.

## Next actions
1. **Pass 2, folder pages** (features 13, 14, 17): a page per working
   folder, the docstring script and its marked block, the handoff line in
   `CONTRIBUTING.md`. Open with the unit test list for approval.
2. Passes 3-7 per `plan.md`; rule on feature 16 before Pass 3 and on
   feature 29 before Pass 6.
3. Before Pass 7 removes Cairn's own `STATE.md`: update the
   `resume-session`, `handoff-session` and `end-session` skills.
4. Publish stays HELD (explicit go). Optional carry-overs:
   `required_status_checks` on protect-main; drop `_v0` from test names;
   `render.main` should reject `--answers` JSON that is not an object
   (verifier nit, Pass 1).

## Open questions
- Feature 16 (pluggable "next" source) and feature 29 (1.x migration
  behavior), each ruled at the start of its pass.
