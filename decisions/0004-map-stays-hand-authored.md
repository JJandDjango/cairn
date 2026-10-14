# 4. Cairn's own MAP stays hand-authored — no self-derive

Status: superseded by 0009
Date: 2026-07-13

## Context
Cairn ships an optional graphify backend, yet its own `MAP.md` is hand-authored
`backend: none` (no `cairn_schema` frontmatter). STATE carried the standing open
question: should Cairn dogfood its own backend — derive its MAP via graphify — or
stay hand-authored? A dogfooding run settled it empirically. `derive` over Cairn's
own source yields 628 nodes / 1193 edges, but `stage` rolls that into a **single
opaque `module` component** at `skills/cairn/`, because all shipped code nests
under one directory. The nine articulated Core + Backend components in the authored
MAP carry far more meaning than the one the machine derives.

## Decision
**Cairn's own `MAP.md` stays hand-authored.** We do not wire the graphify backend
onto Cairn itself. Here the derived MAP is strictly less legible than the authored
one, so authored truth remains the source of record — a direct application of
THEORY's invariant *"human owns the why; machines own only regenerable structure."*

## Consequences
- The authored nine-component MAP stands; no `cairn_schema` frontmatter is added,
  and `graphify-out/` stays out of `.gitignore` (nothing derived is committed).
- `validate MAP.md` on the frontmatter-less authored MAP now reports a clean
  `INVALID` instead of crashing — the schema applies only to graphify-backed MAPs
  ([[0002-optional-graphify-backend]]).
- Dogfooding the *backend* (`derive` / `stage` / `reconcile`) stays available on
  demand for demonstration; it is simply not adopted as Cairn's source of record.
- This closes STATE's open question. Re-open only if Cairn's layout flattens such
  that `derive` yields component-level granularity ([[0003-1.0-scope]]).
