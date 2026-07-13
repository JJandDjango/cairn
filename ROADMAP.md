# Roadmap - cairn

The milestone ladder and per-release requirements. `THEORY.md` holds the *why*
and the invariants; this file holds the *sequence and the gates*. Direction: a
focused, standalone, zero-dependency **living** documentation system - built for
the author now, public-ready later.

**Current:** `v1.0.0` (per `.claude-plugin/plugin.json`), functional, MIT. Cairn's
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

## Post-1.0 - public

Flip from personal to distributable (the standalone invariants held since 1.0 make
this a flip, not a rewrite).

- [x] **GitHub remote** + `marketplace.json` validated + `plugin.json` complete.
      *(remote exists — private; manifests validated + completed. Public flip is the `Publish` gate below.)*
- [ ] **Stranger onboarding** - quickstart hardened for someone who has never seen
      Cairn.
- [ ] **Publish** to the plugin marketplace.

---

## Non-goals
Anti-scope lives in `THEORY.md` (not owned by any consumer, not a code-analysis
engine, not a docs-site generator, not a universal everything-tool, not a content
author). The roadmap never adds a milestone that violates one.
