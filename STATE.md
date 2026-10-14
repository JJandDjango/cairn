# State - cairn

> **Contract** - one question: *what is in flight right now?*
> <=1 page - regenerate at every session end - disposable, always safe to overwrite.
> _Generated 2026-10-14._

## Now
- **Cairn 2.0 is decided, not built.** PR #9 merged to main (`90f299c`):
  `docs/design-2.0.md` (onboarding-documents design + the four THEORY
  rulings), `docs/features-2.0.md` (31 features, ratified, none struck),
  THEORY.md amended, ADR 0009 superseding 0002, 0004 and 0008.
- Design's Next steps 1-3 are done; step 4 (the build, then the SDLC
  kit's migration as first consumer) is next.
- The shipped code is still 1.2 (six strata); THEORY and ADR 0009 now
  describe 2.0. That gap is the accepted cost until the build lands.
- **Known audit warnings**: `BUDGET-ADR` on 0007 (accepted scar, see
  ADR 0007 history); three `CONV-SUPERSEDED` on CONVENTIONS.md, by
  design - the build retires that file into CONTRIBUTING.md.
- **Working style that held**: one ruling per question, recommendation
  first; the user reviews pushed branch links on a phone, so push the
  design branch before asking for a ratification.
- **Skill install is a junction** - `~/.claude/skills/cairn` ->
  `E:\cairn\skills\cairn`; remove it before the marketplace install-test.

## Blockers
- None.

## Next actions
1. **Start the 2.0 build in a fresh session**: author `plan.md` from
   `docs/features-2.0.md` (all 31), user-facing doc first (Pass 0).
2. Resolve the design's open items as the build reaches them: migration
   behavior for 1.x spines (feature 29), the pluggable "next" source
   (feature 16).
3. Publish stays HELD (explicit go): stranger onboarding, marketplace
   add + install-test.
4. Optional carry-overs: `required_status_checks` on the protect-main
   ruleset; rename the `_v0` suffix on the functional contract tests.

## Open questions
- None pending a ruling; the design's open items are listed in
  `docs/design-2.0.md` under Open.
