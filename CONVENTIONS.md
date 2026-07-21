# Conventions - cairn

> **Contract** - one question: *how do we do things here?*
> <=1 page - update when a rule is adopted / revised / retired - hand-edited,
> significant entries link their ADR.

<!-- An index, not an essay: one line per rule (bold name + statement, ADR link
     when significant). Detail overflows to docs/conventions/ pages. -->

- **Zero-dependency core.** render / audit / detect need only the stdlib;
  optional deps live behind `detect.py` ([[0002-optional-graphify-backend]],
  [[0003-1.0-scope]]).
- **No-clobber.** Cairn never overwrites authored content - render fills gaps
  only.
- **Six strata, one contract.** Every stratum = one question + budget + trigger
  + mode; CONVENTIONS itself is an index, not an essay
  ([[0008-conventions-sixth-stratum]]).
- **ADRs are append-only.** Supersede, don't edit; the digit-bearing
  "superseded by NNNN" stamp is the one sanctioned edit
  ([[0001-record-architecture-decisions]]).
- **MAP stays hand-authored.** Derived structure reconciles against authored
  truth, never replaces it ([[0004-map-stays-hand-authored]]).
- **Automate detection, not authorship.** Machines flag; humans (or their
  commit-reviewed agent) write ([[0006-automate-detection-not-authorship]]).
- **PromptLang governs the skill prompt.** SKILL.md validates under
  `prompt-lang.config.yaml`; placeholders stay brace-form
  ([[0007-adopt-promptlang-for-the-skill-prompt]]).
- **Version is single-sourced.** `.claude-plugin/plugin.json` is authoritative;
  `pyproject.toml` stays pytest-config-only.
- **LF line endings**, pinned by `.gitattributes`.
- **main is PR-only.** No direct pushes (protected, owner bound); suite + CI
  green before merge.
- **Commit footers carry the real session URL** - copied verbatim from the live
  session, never fabricated ([[0005-record-commit-footer-errata]]).
