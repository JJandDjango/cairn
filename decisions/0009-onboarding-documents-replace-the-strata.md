# 9. Onboarding documents replace the six strata

Status: accepted
Date: 2026-10-14

## Context
The SDLC kit's `STATE.md` grew from 2.4 KB to 86 KB in 96 sessions: a
section exempt from the rewrite, procedures with no other home, a budget
in prose only, and no lower level to send detail to. Claude Code loads the
root `CLAUDE.md` and its imports at launch, and a folder's `CLAUDE.md` with
the first Read of a file there (measured 2026-10-14); the 1.x strata use
neither. Design: `docs/design-2.0.md`; ratified features:
`docs/features-2.0.md`; THEORY amended to match.

## Decision
The six strata and `DOCS-SYSTEM.md` give way to onboarding documents: a
root `CLAUDE.md` importing `README.md` and `ARCHITECTURE.md`, then
`CONTRIBUTING.md`, with `decisions/` and `docs/` kept. THEORY and MAP merge
into ARCHITECTURE; CONVENTIONS and DOCS-SYSTEM merge into CONTRIBUTING;
`STATE.md` goes, and a status command derives what is in flight. The
software module adds folder pages, docstring lines and the status command.
The graphify backend retires. This supersedes
[[0002-optional-graphify-backend]], [[0004-map-stays-hand-authored]] and
[[0008-conventions-sixth-stratum]].

## Consequences
- 0002, 0004 and 0008 carry a "superseded by 0009" stamp. Until the build
  retires `CONVENTIONS.md`, its entries citing them raise CONV-SUPERSEDED:
  that warning is the build's to-do, not noise.
- The 1.x strata checks retire; five 2.0 checks replace them.
- Spines on 1.x need the migration path; the SDLC kit migrates first.
- Unchanged: the zero-dependency core, no-clobber, append-only ADRs, and
  [[0006-automate-detection-not-authorship]].
- Accepted cost: until the build lands, the shipped 1.x code and docs
  still describe the strata.
