# Roadmap - cairn

The milestone ladder and per-release requirements. `THEORY.md` holds the *why*
and the invariants; this file holds the *sequence and the gates*. Direction: a
focused, standalone, zero-dependency **living** documentation system - built for
the author now, public-ready later.

**Current:** `v1.1.0` (per `.claude-plugin/plugin.json`), functional, MIT. Cairn's
own spine is present (this repo dogfoods itself) and standalone - code, tests, and
docs carry no knowledge of any external tool. See `STATE.md` for what's in flight.

---

## 1.0 - the standalone tool

The zero-dependency scaffold core (a living system) plus the optional graphify
backend, all self-contained ([[0003-1.0-scope]]). Gates:

- [x] **Core hardened** - `render.py` + `templates/` + `/cairn` skill + `detect.py`
      stable, no-clobber proven, test suite green.
- [x] **Standalone** - code, tests, and docs carry zero knowledge of any external
      tool or consumer; the core imports nothing from the optional backend.
- [x] **Cairn dogfoods itself** - own five-strata spine present + maintained.
- [x] **Version single-sourced** - `.claude-plugin/plugin.json` is authoritative;
      `pyproject.toml` is pytest-config-only (documented in-file).
- [x] **"Any project" scoped honestly** - README + USAGE state the *spine*
      generalizes while *derived* / backend features are code-only + optional.
- [x] **Maintenance discipline complete** - `DOCS-SYSTEM.md` fully specifies the
      day-2 routine + audit checklist (the "living" in living system).
- [x] **Backend documented** - `derive` / `reconcile` / `view` written up as the
      optional automation tier (a `docs/` page).

## 1.1 - the living-system tier

Automate the *detection* half of day-2 upkeep; authorship stays human-reviewed
([[0006-automate-detection-not-authorship]]). Gates:

- [x] **Audit shipped** - `/cairn audit` (`audit.py`, zero-dep core): the
      DOCS-SYSTEM checklist executable, report-only, git-optional; a fresh
      scaffold passes its own audit (regression-tested).
- [x] **Maintain documented** - `/cairn maintain` session-end routine in
      SKILL.md: agent touches MAP / docs / STATE grounded in the observed diff;
      THEORY and old ADRs are flag-only.
- [x] **Version stamped `1.1.0`** - `.claude-plugin/plugin.json` (stamped
      2026-07-15 on the user's release call).

## 1.2 - the conventions stratum (proposed)

Give normative "how we do things here" rules a home the five strata don't own:
a hand-edited, top-level `CONVENTIONS.md` holding the *current* rule set, with
significant entries backed by an ADR (the why-history). Generalizes across
project types (code -> coding rules, novel -> style rules, research ->
methodology). Unscheduled - sequencing against the public flip is the
maintainer's call. Gates:

- [x] **ADR recorded** - the sixth-stratum decision, with the contract row:
      question *"how do we do things here?"*, size budget, trigger =
      adopt / revise / retire a rule, mode = hand-edited (entries link ADRs)
      ([[0008-conventions-sixth-stratum]]).
- [x] **Template + render wiring** - `CONVENTIONS.md` scaffolded for all
      project types, no-clobber, type-specific rule examples.
- [x] **Audit extended** - budget check + entry ADR links resolve + flag
      entries citing superseded ADRs; an absent file stays clean (opt-in for
      pre-1.2 spines).
- [x] **Maintain stays hands-off** - CONVENTIONS is flag-only like THEORY;
      authorship is human-owned.
- [x] **Docs sweep** - five -> six strata across DOCS-SYSTEM (repo + template),
      USAGE, README, MAP's templates row.
- [ ] **Dogfooded + stamped** - cairn's own `CONVENTIONS.md` authored; version
      `1.2.0`.

## Post-1.0 - public

Flip from personal to distributable (the standalone invariants held since 1.0 make
this a flip, not a rewrite).

- [x] **GitHub remote** + `marketplace.json` validated + `plugin.json` complete.
      *(public at `github.com/JJandDjango/cairn`, `main` PR-protected; manifests validated + completed.)*
- [ ] **Stranger onboarding** - quickstart hardened for someone who has never seen
      Cairn.
- [ ] **Publish** to the plugin marketplace.

---

## Non-goals
Anti-scope lives in `THEORY.md` (not owned by any consumer, not a code-analysis
engine, not a docs-site generator, not a universal everything-tool, not a content
author). The roadmap never adds a milestone that violates one.
