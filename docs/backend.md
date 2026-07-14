# Backend - the optional graphify tier

> **docs/ stratum** - *how does this piece work?* This page covers the OPTIONAL
> backend. The zero-dependency core (`render.py` + `templates/` + `/cairn`) needs
> none of it.

<!-- covers: skills/cairn/backend/, skills/cairn/backend_cli.py, skills/cairn/detect.py -->

## What it is
An optional, code-only tier that automates ONE stratum - `MAP.md` - by deriving a
structured code graph and reconciling it against your authored MAP. It is
dependency-gated (graphify + PyYAML, via `detect.py`); the core's value holds with
it entirely absent ([[0002-optional-graphify-backend]], [[0003-1.0-scope]]).

## The one invariant
Derived output is never the source of record. `graphify-out/` + `/manifest.json`
are regenerable and **gitignored**; your authored `MAP.md` is truth. Derivation
*proposes*, you accept. Cairn's own MAP is hand-authored for exactly this reason -
`derive` collapses its graph to one opaque node vs. the nine authored
([[0004-map-stays-hand-authored]]).

## When to use it
Reach for it on a large or churning **codebase** where hand-listing components is
toil, to bootstrap a MAP from an existing repo (`stage`), or for a cross-project
roll-up (`view`). Skip it - the default - for non-code projects, small or stable
codebases, or any spine that stays cheap to keep by hand.

## Commands
The `/cairn` skill dispatches these; or run directly from the target project:
`python <skill-dir>/backend_cli.py <cmd> ...`. All graphify contact is isolated to
`graphify_adapter.py`; a pinned-version skew warns but never blocks.

| Command | Does | Writes |
|---|---|---|
| `derive <path>` | graphify over the repo (no-LLM, 0 tokens) -> a code graph | `graphify-out/graph.json` *(gitignored)* |
| `reconcile <path>` | derive, then diff graph vs authored MAP at file/dir granularity -> ranked, editable proposals | `graphify-out/proposals.md` |
| `reconcile <path> --apply` | write the **checked** proposals into the MAP - the only write into authored truth | `MAP.md` |
| `stage <path>` | derive-first: draft a MAP for a repo that has none; `--accept` validates + writes it | `…/MAP.draft.md` -> `MAP.md` |
| `view [--project N]` | portfolio roll-up across MAPs registered in the vault (or one project) | stdout |
| `vault-add <MAP.md>` | symlink a project's MAP into the vault + reindex, so `view` sees it | vault index |
| `validate <MAP.md>` | check a structured MAP against the schema (a hand-authored `backend: none` MAP reports cleanly, never crashes) | exit 0/1 |

`--no-derive` reuses the existing `graph.json` instead of re-deriving; `--file`
overrides the authored doc (default `MAP.md`).

## The reconcile loop (the intended workflow)
1. `reconcile <path>` - derive + diff -> `proposals.md`.
2. Edit `proposals.md`; check only the rows you accept.
3. `reconcile <path> --apply` - the checked rows land in `MAP.md`.

You stay the author; the graph only ever proposes. `contracts.py` is a separate,
deterministic consumer of the same graph (a per-file dependency report) - see its
own `MAP.md` row.
