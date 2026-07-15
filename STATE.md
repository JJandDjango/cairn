# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-07-15._

## Now
- **PR #2 merged** (rebase) - the 1.1 living-system tier (`/cairn audit` +
  `/cairn maintain`, [[0006-automate-detection-not-authorship]]) is live on
  `main` at `94df71e`. Local checkout is back on `main`; the
  `add-audit-maintain` branch is deleted (local + remote). Suite unchanged at
  **203 passing** as of the merge.
- **Conventions direction recorded** - normative "how we do things here" rules
  (e.g. "no nested ternaries") get a proposed **sixth stratum**: a hand-edited,
  top-level `CONVENTIONS.md` holding the *current* rule set, significant entries
  backed by ADRs (the why-history). Recorded as ROADMAP
  `1.2 - the conventions stratum (proposed)` with its gate list; the ADR lands
  with the build, not before.
- **Skill install is now a junction** - `~/.claude/skills/cairn` ->
  `E:\cairn\skills\cairn`, replacing a stale 1.0 file copy. The repo working
  tree IS the live skill in every session (feature branches included - by
  design, for dogfooding). Remove the junction before the publish gate's
  marketplace install-test, or the names collide.

## Blockers
- None.

## Next actions
1. **Stamp `v1.1.0`** in `.claude-plugin/plugin.json` when ready to release (the
   open ROADMAP 1.1 gate) - goes via branch + PR; main requires PR.
2. **Cut the 1.2 conventions branch** when ready - ROADMAP's gate list is the
   spec; the ADR is the first gate. Sequencing vs the public flip is the
   maintainer's call.
3. **Publish** *(HELD - explicit go required)*: stranger-onboarding hardening,
   then flip public + marketplace add + install-test (junction removed first).
4. Optional tidy: rename the `_v0` suffix on the functional contract tests.

## Open questions
- None.
