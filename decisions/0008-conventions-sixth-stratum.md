# 8. Conventions is the sixth stratum

Status: accepted
Date: 2026-07-21

## Context
Normative "how we do things here" rules have no home the five strata own:
THEORY holds invariants, MAP holds structure, ADRs hold why-history - but
the *current* rule set (coding rules, style rules, methodology) lives in
heads or scatters across all three. ROADMAP 1.2 reserved this home; a
2026-07-20 conventions/ontology design session sharpened the shape. Its
boundary holds: Cairn documents and detects rules; analyzers and rule
mining stay out (THEORY: not a code-analysis engine).

## Decision
`CONVENTIONS.md` joins the spine as the sixth top-level stratum. Contract:
question *how do we do things here?* - budget <=1 page - trigger =
adopt / revise / retire a rule - mode = hand-edited, significant entries
link their ADR.
- **Index, not essay.** Entries are one-line rules; detail overflows to
  `docs/conventions/` pages. The budget is the forcing function.
- **Generalizes by project type**, like every stratum: code -> coding
  rules, novel -> style rules, research -> methodology.
- **Brownfield bootstrap.** On an existing project the scaffolding agent
  MAY propose starter entries inferred from what is visible, each tagged
  `(inferred - confirm)`. This widens THEORY's lone content-authorship
  exception (the brownfield intent line) to conventions starters under
  [[0006-automate-detection-not-authorship]]'s doctrine: machines propose
  tagged text, the human confirms and deletes the tag, audit flags what
  lingers. THEORY's non-goal wording updates to name both exceptions.

## Consequences
- Audit extends: BUDGET-CONVENTIONS (1 page); entry ADR links must
  resolve; entries citing superseded ADRs are flagged; INFERRED-TAG
  covers CONVENTIONS.md. An absent file stays clean - the stratum is
  opt-in for pre-1.2 spines.
- Maintain stays hands-off: CONVENTIONS is flag-only like THEORY.
- Render scaffolds it for all five project types, no-clobber, with a
  type-specific starter example; docs and templates count five -> six.
