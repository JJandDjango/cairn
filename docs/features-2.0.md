# Features - Cairn 2.0

> Drafted 2026-10-14 from [design-2.0.md](design-2.0.md), after the four
> THEORY rulings. Status: ratified 2026-10-14 with no lines struck. The
> kept set scopes the plan; nothing here is built.

Lines marked *(open)* depend on a question the design leaves open.

## Spine (portable, every project)

1. Root `CLAUDE.md` template: `@README.md`, `@ARCHITECTURE.md`, and the
   one line "read deeper only as the task needs."
2. `README.md` template for a user: title and one line, what it does,
   install, usage example, help and contributing, license.
3. `ARCHITECTURE.md` template: intent, invariants, the one diagram, the
   folder map with a link each, where each kind of fact lives, and the
   status command's name.
4. `CONTRIBUTING.md` template: set up and test, the workflow, house rules
   one line each, one link per kind of work to its recipe page.
5. Recipe page template under `docs/`: one kind of work, step by step.
6. ADR template under `decisions/`, append-only, as today.
7. Feature document and design document templates under `docs/`.
8. `CHANGELOG.md` template.
9. A local, untracked note for this machine's paths and tools.
10. Setup interview: name, one-line intent, project type, adoption
    (greenfield or brownfield), and tracked or local mode.
11. No-clobber on every write, as today.
12. Drop the graphify backend: it built `MAP.md`, which 2.0 retires.

## Software module

13. Folder pages: a `CLAUDE.md` in every folder a session might work in
    (purpose, one line per file and subfolder, local rules, links); none
    for git-ignored, fixture, vendored or generated folders.
14. Docstring script: copies each file's first docstring line into a
    marked block of its folder page; typed lines outside the block stay.
15. Status command: last done (git log, merged PRs), next (issues), and
    waiting on the user (issues labelled `needs-ruling`).
16. A pluggable source for "next," for projects that keep their order of
    work outside issues. *(open)*
17. `CONTRIBUTING.md` template states that a mid-work handoff stays in
    that work's own folder.

## Local mode

18. Folder pages as `CLAUDE.local.md`; top pages in `.docs-local/`,
    imported by a root `CLAUDE.local.md`.
19. `.docs-local/.gitignore` of `*`, and `CLAUDE.local.md` added once to
    `.git/info/exclude`; no tracked file is ever written.
20. Reruns give the same files: generated lines refresh, typed lines stay.
21. Setup prints the `git clean -x` caution.

## Checks (`/cairn audit`)

22. Size budgets per file.
23. No `@` outside code in `README.md`, `ARCHITECTURE.md` or a folder page.
24. Every link resolves.
25. Generated lines are fresh: rerun the script, fail on any difference.
26. Coverage: every folder that needs a page has one; every file there has
    its line.
27. Exit 1 on any failure in both modes; a CI workflow template runs the
    audit on PRs in tracked mode.
28. `/cairn maintain` reworked: audit, refresh generated lines, touch the
    pages for what changed; no `STATE.md` to regenerate.

## Migration and retirement

29. Migration from 1.x: on finding `THEORY.md`, `MAP.md`, `STATE.md`,
    `CONVENTIONS.md` and `DOCS-SYSTEM.md`, map each to its 2.0 home with
    no authored text lost. *(open: the exact behavior)*
30. Retire the 1.x templates and checks for the six strata, including the
    `STATE.md` and CONV checks.
31. Cairn adopts 2.0 in its own repo (dogfood).

## Not features (tracked so they are not lost)

- The THEORY amendments and the superseding ADR: Next step 3, own commits.
- Folder-page filename other than `CLAUDE.md` via a plugin hook: untested,
  out of 2.0 unless kept.
- Preloading a subagent's files from its prompt: unchecked, out of 2.0.
- Consumers outside this repo that read `STATE.md`: the SDLC kit's
  never-touch list, and the `resume-session`, `handoff-session` and
  `end-session` skills in `~/.claude/skills/`.
