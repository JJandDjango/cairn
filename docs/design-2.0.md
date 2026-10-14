# Design - Cairn 2.0: onboarding documents

> Ratified piece by piece with the user, 2026-10-13 and 2026-10-14, in a
> talk that started from the SDLC kit's 86 KB `STATE.md`. Status: design,
> not built. The feature list and THEORY amendments come next.

## Goal

Every new session is onboarded like a new collaborator: a few short,
human-readable documents, read top-down and only as deep as the task
needs, where each fact lives in exactly one place and everything else is
derived or looked up.

**Scope:** software first. Other project types become modules once this
works; ImSimWiki (the user's game wiki) is the first candidate.

## Why

The SDLC kit's `STATE.md` grew from 2.4 KB to 86 KB in 96 sessions: a
section exempt from the rewrite, procedures with no other home, adding
cheaper than deleting, a budget stated in prose only, and no lower level
to send detail to. Every session re-sent it with every request. 2.0 fixes
each cause: no carried-forward section, a home for every kind of fact,
budgets as checks, and a level below the top.

## The read path

| Level | Loaded | Files |
|---|---|---|
| 0 | At launch, by Claude Code | Root `CLAUDE.md`, which imports `README.md` and `ARCHITECTURE.md` |
| 1 | On demand, with the first Read of a file in a folder | That folder's `CLAUDE.md` |
| 2 | When the task leads there | `CONTRIBUTING.md`, a recipe page, an ADR, a feature or design document |
| 3 | By search | The code |

A session starts on about 5 KB (about 1,300 tokens).

## The files

| File | Holds | Budget |
|---|---|---|
| Root `CLAUDE.md` | `@README.md`, `@ARCHITECTURE.md`, and one line: read deeper only as the task needs, following ARCHITECTURE's link for the folder in hand | A few lines |
| `README.md` | For a user: title and one line, what it does, install, a short usage example, help and contributing, license. No structure, reasoning, invariants or counts | 2 KB |
| `ARCHITECTURE.md` | Intent; invariants; a map of the top-level folders with a link each; where each kind of fact lives | 3 KB |
| A folder's `CLAUDE.md` | Purpose; each file and subfolder in one line; local rules for that folder only; links to the docs that cover it, never their content | 2 KB |
| `CONTRIBUTING.md` | Read before working or committing: set up and test; the workflow; house rules, one line each; one link per kind of work to its recipe page | 3 KB |

**Which folders get a page:** every folder a session might work in; not
git-ignored folders, test fixture folders (the parent's page covers them
in one line), or vendored or generated code.

**No `STATE.md`.** A status command prints last done (git log, merged
PRs), next (issues, or a project's own source) and what waits on the
user (issues labelled `needs-ruling`). `ARCHITECTURE.md` names it. A
handoff in the middle of a piece of work stays in that work's own folder.

## Where things live

What the project is and how to use it: `README.md`. Intent, invariants
and the folder map: `ARCHITECTURE.md`. A folder's purpose, contents and
local rules: its `CLAUDE.md`. A file's purpose: its docstring, else its
line in the folder page. How work is done: `CONTRIBUTING.md`. One kind of
work: its recipe page. A decision: its ADR. A feature's what and why: its
feature document; its design: its design document. Order of work and done
conditions: the project's plan or contracts. Last done, next and waiting
on: the status command. Backlog and open questions: issues. Releases:
`CHANGELOG.md`. This machine's paths and tools: a local, untracked note.

## Docstrings

One rule, file by file, so documented, undocumented and mixed codebases
all work with no setting. If the file has a docstring (or doc comment),
its first line is the file's description, and a script copies it into the
folder page. Otherwise the line is typed in the folder page, which is its
home. A marked block in the page holds the lines the script may rewrite.

## Local mode

Chosen at setup, for a repo whose files may not change (the user's work
repo has a tracked `CLAUDE.md` that may not be edited).

- Folder pages are `CLAUDE.local.md`. The top pages live in `.docs-local/`,
  imported by a root `CLAUDE.local.md`.
- `.docs-local/` holds a `.gitignore` of `*`, which hides the folder and
  itself. `CLAUDE.local.md` is added once to `.git/info/exclude`.
- Reruns give the same files, refresh generated lines and keep typed
  ones. No tracked file is ever written. The checks run as a command.
- Caution: `git clean -x` deletes all of it.

## Checks

Each fails the PR in CI (tracked mode) or exits 1 (local mode), as part
of `/cairn audit`:

1. Size budgets, per the table above.
2. No `@` outside code in `README.md`, `ARCHITECTURE.md` or a folder page,
   so nothing loads in a chain.
3. Every link resolves.
4. Generated lines are fresh: the script reruns and any difference fails.
5. Coverage: every folder that needs a page has one, and every file there
   has its line.

## Measured

Claude Code 2.1.299, headless, Haiku, 2026-10-14:

- A subfolder `CLAUDE.md` or `CLAUDE.local.md` loads with the first Read
  of a file in that folder, at no extra call.
- An `@` import inside it is not expanded on demand; neither is one in a
  path-scoped rule (`.claude/rules/`). Imports expand only at launch, up to
  four hops (documented).
- A root `CLAUDE.local.md` importing `.docs-local/ARCHITECTURE.md` loads at
  launch beside a tracked `CLAUDE.md`.
- A subfolder `AGENTS.md` loads only under the user-level
  `claude-md-and-agents-md` setting, which a repo cannot set. Claude Code
  loads it through a built-in plugin's hook.
- `.gitignore` of `*` plus `.git/info/exclude`: `git status` clean, the
  repo's files unchanged.

## Conflicts with today's Cairn

Each needs the user's ruling before the build:

- **THEORY, "Portable by construction"**: 2.0 is software first; the spine
  stays generic, and folder pages and docstrings are the software module.
  *Ruled 2026-10-14:* amend to "the spine is portable; modules are not."
  The spine is root `CLAUDE.md`, `README.md`, `ARCHITECTURE.md` and
  `CONTRIBUTING.md`; the status command (git, issues) is software module.
- **THEORY, "Human owns the why; machines own only regenerable
  structure"**: it says derived output is gitignored and never the source
  of record. Copied docstring lines are committed in tracked mode, though
  their source of record stays the docstring.
  *Ruled 2026-10-14:* drop "gitignored"; keep "never the source of record";
  add that derived text may be committed only behind the freshness check
  (check 4).
- **THEORY, the strata and "STATE is disposable"**: the six strata become
  the files above; `STATE.md` goes. ADR 0008 and the strata wording are
  superseded.
  *Ruled 2026-10-14:* keep the pace-layer contract (one question, budget as
  a check, update trigger, maintenance mode), applied to the new files; the
  one diagram moves to `ARCHITECTURE.md`; decisions stay append-only;
  "STATE is disposable" becomes "nothing in flight is stored: the status
  command derives it." One new ADR supersedes ADR 0008 and the strata.
- **THEORY's success criterion** reads THEORY -> MAP -> STATE in 2-3K
  tokens; 2.0 reads CLAUDE.md -> README -> ARCHITECTURE in about 1.3K.
  *Ruled 2026-10-14:* rewrite it as "A newcomer reads root `CLAUDE.md` ->
  `README.md` -> `ARCHITECTURE.md` (about 1.3K tokens, held there by the
  size budgets) and can act without reading the source." The
  code-and-non-code criterion becomes "The spine works unchanged on any
  project; a type module adds only its own files and checks."
- **ADR 0006, automate detection, not authorship**: holds. The script
  copies human-written text; it writes none.

## Open

- The folder-page filename: `CLAUDE.md` for now. A plugin hook could load
  any name, such as `SUMMARY.md`, at no extra call; not built or tested.
- Preloading a subagent's files from its prompt: the launching script
  inlines them, or a hook injects them; the hook route is not checked.
- How a project that keeps its order of work outside issues plugs its
  source into the status command.
- Migration for spines already on 1.x (the user's deadlock-mod repo and
  work repo use the six files): what `/cairn` does on finding THEORY, MAP,
  STATE, CONVENTIONS and DOCS-SYSTEM, without clobbering authored text.

## First consumer

The SDLC kit adopts 2.0 in its own repo; its PL-DOC gate runs
`/cairn audit` in CI. Its ratified migration: `MAP.md` becomes
`ARCHITECTURE.md`; `THEORY.md` merges into it (the foundations theory
checker never reads `THEORY.md`; it reads `MAP.md`'s frontmatter, which
the kit lacks); `CONVENTIONS.md` and `DOCS-SYSTEM.md` merge into
`CONTRIBUTING.md`; `STATE.md` is removed, its parts sent to their homes;
`USAGE.md`, the `NOTES_*.md` files and the HANDOFF move under `docs/`;
`CHANGELOG.md`, `LICENSE` and `SDLC.md` stay. The kit's
`skills/sdlc/SKILL.md` names the 1.x files in its rule never to touch
Cairn's documents; that list changes when 2.0 lands.

## Next

1. ~~The user rules on the four conflicts above, one at a time.~~ Done
   2026-10-14.
2. ~~A strikeable feature list from this design, ratified before any plan.~~
   Done 2026-10-14: [features-2.0.md](features-2.0.md), all 31 kept.
3. ~~The THEORY amendments and superseding ADRs, as their own commits.~~
   Done 2026-10-14: THEORY amended; ADR 0009 supersedes 0002, 0004, 0008.
4. The build, then the kit's migration as the first consumer.

Work with the user piece by piece: short replies, one question each.
