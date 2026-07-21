# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-07-21._

## Now
- **1.2 (conventions stratum) is EXECUTED on `conventions-1.2`** - all six
  ROADMAP gates in six commits (ADR 0008 -> template/render -> audit
  extension -> skill/maintain hands-off -> docs sweep five->six -> dogfood +
  `1.2.0` stamp). Suite 213 green (204 + 9 new). Branch is local,
  **not yet pushed** - main still shows v1.1.0 until the PR merges.
- **Cairn now dogfoods its own sixth stratum** - `CONVENTIONS.md` authored
  (11 rules, all ADR links current); audit's new CONV checks pass on it.
- **Known accepted finding**: `BUDGET-ADR` WARN on `decisions/0007` (43 > 40
  lines, pre-existing since #174). Both fixes are worse than the scar -
  trimming trips append-only ADR-EDITED forever; superseding over 3 lines is
  noise. Accepted as-is; audit exits 1 on this alone.
- **Skill install is a junction** - `~/.claude/skills/cairn` ->
  `E:\cairn\skills\cairn`; the working tree IS the live skill, so this
  branch's skill changes are already live locally. Remove the junction
  before the publish gate's marketplace install-test.

## Blockers
- None.

## Next actions
1. **Push `conventions-1.2` + open the PR** (main is PR-protected); merge on
   CI green (ubuntu+windows suite + PromptLang gate).
2. **Publish** *(HELD - explicit go required)*: stranger-onboarding
   hardening, then marketplace add + install-test (junction removed first).
3. Optional carry-overs: `required_status_checks` on the protect-main
   ruleset; rename the `_v0` suffix on the functional contract tests.

## Open questions
- None.
