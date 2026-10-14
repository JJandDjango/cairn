# Using Cairn 2.0

> Pass 0 of the 2.0 build: written before the code, from
> [design-2.0.md](design-2.0.md) and [features-2.0.md](features-2.0.md).
> Each section carries its feature numbers and a status marker: 🟢 shipped,
> 🟡 partly shipped, 🔴 not built. Until Pass 7, the shipped tool is 1.2;
> see [USAGE.md](../USAGE.md).

Cairn writes the few short documents a new collaborator reads on day one,
and checks that they stay short, current and linked. Every session, human
or agent, starts on about 5 KB and reads deeper only as its task needs.

## Install 🔴

As a Claude Code skill: copy `skills/cairn` into `~/.claude/skills/`, then
run `/cairn` in your project. No dependencies beyond Python's standard
library.

## Set up a project 🟢 (10, 11, 12)

Run `/cairn` in the project folder and answer five questions:

| Answer | Choices |
|---|---|
| Name | The project's name |
| Intent | One sentence: why the project exists |
| Project type | `code` gets the software module; other types get the spine only, for now |
| Adoption | `greenfield` (new project) or `brownfield` (existing project; inferred lines are tagged for you to confirm) |
| Mode | `tracked` (files are committed) or `local` (nothing tracked is ever written; ships in Pass 4) |

Cairn never overwrites a file. Run it on a half-documented project and it
fills only the gaps, then lists what it skipped.

## What you get 🟢 (1-9)

```
CLAUDE.md          imports README and ARCHITECTURE; loads at launch
README.md          for a user: what it does, install, usage, license   (2 KB)
ARCHITECTURE.md    intent, invariants, the diagram, the folder map     (3 KB)
CONTRIBUTING.md    set up, test, workflow, house rules, recipe links   (3 KB)
CHANGELOG.md       releases
decisions/         ADRs, append-only
docs/              recipe pages, feature and design documents
```

Plus a local, untracked note for this machine's paths and tools.

A session reads in this order, stopping when it knows enough:

| Level | When | What |
|---|---|---|
| 0 | At launch | `CLAUDE.md`, `README.md`, `ARCHITECTURE.md` (about 1,300 tokens) |
| 1 | First file read in a folder | That folder's page |
| 2 | When the task leads there | `CONTRIBUTING.md`, a recipe, an ADR, a feature or design doc |
| 3 | By search | The code |

Each fact lives in one place. `ARCHITECTURE.md` lists where each kind
lives, so a reader looks it up instead of guessing.

## Folder pages 🔴 (13, 14, 17)

*Code projects.* Every folder a session might work in gets a `CLAUDE.md`:
its purpose, one line per file and subfolder, local rules, and links to
the docs that cover it. Claude Code loads it the first time a session
reads a file in that folder. Git-ignored, fixture, vendored and generated
folders get none.

**Docstrings.** If a file has a docstring or doc comment, its first line
is the file's description: a script copies it into a marked block of the
folder page. Otherwise you type the line in the page, outside the block,
and it stays yours. Documented, undocumented and mixed codebases all work
with no setting.

**Handoffs.** A handoff in the middle of a piece of work stays in that
work's own folder, never in a top-level file.

## What's in flight: the status command 🔴 (15, 16)

*Code projects.* There is no `STATE.md`. Ask the status command instead;
`ARCHITECTURE.md` names it. It prints:

- **Last done:** recent commits and merged PRs.
- **Next:** open issues, or your project's own source of order of work.
- **Waiting on you:** issues labelled `needs-ruling`.

## Local mode 🔴 (18-21)

For a repo whose files you may not change. Folder pages become
`CLAUDE.local.md`; the top pages live in `.docs-local/`, imported by a
root `CLAUDE.local.md`. Cairn writes `.docs-local/.gitignore` (`*`) and
adds `CLAUDE.local.md` to `.git/info/exclude` once, so `git status`
stays clean. Reruns refresh generated lines and keep the ones you typed.

**Caution:** `git clean -x` deletes all of it.

## Checks: `/cairn audit` 🔴 (22-27)

Report-only. Exits 1 on any failure, in both modes.

1. Each file holds its size budget.
2. No `@` import outside code in `README.md`, `ARCHITECTURE.md` or a
   folder page, so nothing loads in a chain.
3. Every link resolves.
4. Generated lines are fresh: the docstring script reruns, and any
   difference fails.
5. Every folder that needs a page has one, and every file there has its
   line.

In tracked mode, a CI workflow template runs the audit on every PR.

## Session end: `/cairn maintain` 🔴 (28)

Your agent runs the audit, refreshes generated lines, and touches the
pages for what the session changed. Every edit stays uncommitted for your
review. There is no state file to regenerate.

## Moving from 1.x 🔴 (29, 30)

On finding `THEORY.md`, `MAP.md`, `STATE.md`, `CONVENTIONS.md` or
`DOCS-SYSTEM.md`, `/cairn` maps each to its 2.0 home with no text you
wrote lost. The exact behavior is decided in Pass 6.
