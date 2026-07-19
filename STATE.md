# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-07-19._

## Now
- **CI wired** (this PR): `.github/workflows/ci.yml` runs the suite on
  ubuntu+windows (py 3.12) and installs foundations from its now-public
  repo, so the `tests/test_promptlang.py` importorskip gate is *enforced*
  in CI instead of skipping (204 expected green). CONTRIBUTING's "once CI
  is wired up, it must be green" is now live.
- **PromptLang adoption is merged** - ADR-0007 landed on `main` at
  `d782165` (repo `prompt-lang.config.yaml` claims `skills/*/SKILL.md`;
  SKILL.md validates clean; suite 204). The prior STATE's "PR pending" is
  stale history.
- **ROADMAP post-1.0 remote line fixed** (was "remote exists - private";
  cairn has been public with PR-protected main since the #166 publish).
- **Skill install is a junction** - `~/.claude/skills/cairn` ->
  `E:\cairn\skills\cairn`; the repo working tree IS the live skill.
  Remove the junction before the publish gate's marketplace install-test,
  or the names collide.

## Blockers
- None.

## Next actions
1. **Publish** *(HELD - explicit go required)*: stranger-onboarding
   hardening, then marketplace add + install-test (junction removed first).
2. **Cut the 1.2 conventions branch** when ready - ROADMAP's gate list is
   the spec; the ADR is the first gate.
3. Optional: add `required_status_checks` (the new CI) to the protect-main
   ruleset; rename the `_v0` suffix on the functional contract tests.

## Open questions
- None.
