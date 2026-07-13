# Cairn

**A durable documentation spine for any project — code or not.**

A cairn is a stack of stones that marks a trail: built up over time, each stone
added but never moved, so the next traveler finds the way. Your project's docs,
exactly — **append-only, pace-layered, for wayfinding.**

Cairn scaffolds a **pace-layered** documentation spine: five files, each changing
at its own rate under a fixed contract, so fast edits never tear slow truth.

> **Want to use it? → [USAGE.md](USAGE.md)** — the explicit step-by-step guide:
> invoke → interview (answer-by-answer) → outputs → day-2 workflow → worked example.

## The five strata

| Stratum | Question it answers | Budget | Update trigger | Mode |
|---|---|---|---|---|
| `THEORY.md` | Why exist? What must stay true? | ≤1 page | purpose / invariants change | hand-edited, rare |
| `MAP.md` | What are the pieces & how connected? | ≤2 pages | piece add / remove / rewire | hand-edited (or graphify-derived) |
| `decisions/` | Why done this way? | ≤½ page each | a new significant decision | append-only, never edited |
| `docs/` | How does each piece work? | mirrors structure | internals change | authored on touch (or generated) |
| `STATE.md` | What's in flight now? | ≤1 page | every session end | regenerated, disposable |

Read `THEORY.md → MAP.md → STATE.md` (~2–3k tokens) and you know *what, how, and
where*. Descend into `decisions/` and `docs/` only on demand.

Works on **any** project — a codebase, a novel, a content site, a business, a
research program. "Component" simply becomes chapter / section / workstream / claim.
The pace-layered **spine** is what generalizes; the optional graphify backend (a
derived MAP) is code-only.

## Install

### As a Claude Code skill (simplest)
Copy the skill into your Claude Code skills directory, then run `/cairn`:

```bash
cp -r skills/cairn ~/.claude/skills/cairn            # macOS / Linux
```
```powershell
Copy-Item -Recurse skills\cairn $HOME\.claude\skills\cairn   # Windows
```

### As a Claude Code plugin
Once this repo is on GitHub, add it as a marketplace and install:

```
/plugin marketplace add <you>/cairn
/plugin install cairn
```

### Standalone (no Claude Code)
The engine is zero-dependency Python (stdlib only). Assemble the answers as JSON
and run the renderer directly:

```bash
python skills/cairn/render.py --cwd ./my-project --answers '{
  "project_name": "my-novel",
  "intent": "A historical novel on a hard deadline.",
  "project_type": "novel",
  "backend": "none",
  "material": "greenfield"
}'
```

## How it works

`/cairn` interviews you — name, one-line intent, project type, greenfield vs
brownfield, and (for code) whether to wire an optional graphify backend —
then renders the strata into your project. It **never overwrites** an existing
file: run it on a half-documented project and it fills only the gaps.

- **Greenfield** authors `THEORY.md` now.
- **Brownfield** marks inferred intent `(inferred — confirm)` for the owner to correct.
- **Non-code** projects drop the diagram mandate and rename the component unit.
- **The `graphify` backend** (code only) adds an optional structured-MAP stub and
  `graphify-out/` + `/manifest.json` to `.gitignore`; `/cairn derive`/`reconcile`/`view`
  build and reconcile a structured MAP from the code graph.

## Principle

Pace layering (Stewart Brand's shearing layers): stratify documentation by rate
of change. Every stratum answers exactly one question, carries a size budget, has
an explicit update trigger, and a maintenance mode (hand-edited, append-only, or
regenerated). That fixed contract is what makes the system formulaic across
projects of any kind.

## Layout

```
skills/cairn/
├─ SKILL.md            # the /cairn interview
├─ render.py           # zero-dependency renderer (also runnable standalone)
└─ templates/          # the five strata + DOCS-SYSTEM.md + ADR seed & template
```

## License

MIT © 2026 Johnathan Hyden
