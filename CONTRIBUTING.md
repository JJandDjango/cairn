# Contributing to Cairn

Thanks for wanting to add a stone to the cairn. This project is small,
solo-maintained, and documented with its own system — so contributing has a
little structure, and this page is all of it.

## The one rule: `main` is protected — contribute by fork + PR

`main` carries a ruleset ([`scripts/ruleset-protect-main.json`](scripts/ruleset-protect-main.json))
that blocks force-pushes, blocks deletion, and **requires a pull request for every
change** — including from the maintainer. Only the maintainer has write access to
this repo; nobody pushes to `main` directly. That isn't a snub — it's the same
*"never touch main directly"* discipline Cairn preaches, enforced on Cairn itself.

So the flow for any outside change is **fork → branch → PR**:

1. **Fork** the repo and clone your fork.
2. **Branch:** `git checkout -b fix-short-description`
3. Make the change.
4. **Run the suite:** `python -m pytest` (the engine is stdlib-only; the tests
   need `pytest`). Green before you push.
5. Keep the docs spine honest — see below.
6. **Push to your fork and open a PR against `main`.** Say *what* changed and *why*.

For anything non-trivial, **open an issue first** so we can agree on the shape
before you build — it saves you a wasted PR. Typos and small fixes: just send the PR.

## Keep the spine honest (Cairn dogfoods its own system)

Cairn is documented *with Cairn*. A change isn't done until the right stratum is
updated — reviewers check this against [`DOCS-SYSTEM.md`](DOCS-SYSTEM.md):

| You… | Update |
|---|---|
| add / remove / rewire a piece | that Component's row in [`MAP.md`](MAP.md) (hand-authored) |
| make a decision a future maintainer would question | a new ADR — copy [`decisions/ADR-template.md`](decisions/ADR-template.md) to `NNNN-title.md`. **Never edit an existing ADR; supersede it.** |
| work a piece in depth | author / refresh its `docs/<piece>.md` page |

Leave **`STATE.md`** alone — it's the maintainer's disposable session handoff,
regenerated at session end, not a contribution surface. Hold the size budgets and
keep the single diagram in `MAP.md` at container zoom.

## Testing your change

- **Engine (`render.py`)** — `python -m pytest`, plus the standalone `render.py`
  command in [`USAGE.md`](USAGE.md) exercises a real render end to end.
- **Skill / interview (`SKILL.md`)** — run `/cairn` in a scratch directory and
  confirm the spine it writes.

## Commits & license

- Focused commits, imperative subject line.
- If you author with an AI coding agent, follow the footer convention in
  [`decisions/0005`](decisions/0005-record-commit-footer-errata.md) — copy the
  session URL from the live session, never from memory.
- By contributing, you agree your work is licensed under the **MIT License**
  ([`LICENSE`](LICENSE)) — inbound = outbound.

## What to expect

Solo-maintained, so review may take a few days. External PRs are read before
merge; once CI is wired up, it must be green.
