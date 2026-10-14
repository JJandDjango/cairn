# Theory - cairn

> **Contract** - one question: *why does this exist, and what must stay true?*
> <=1 page - update when purpose or invariants change - hand-edited, rare.

## Intent
A zero-dependency, pace-layered documentation spine that keeps any project
legible over time: cheap to start, cheap to keep true. Cairn scaffolds the spine
**and** carries the day-2 discipline that keeps it alive, so a reader (human or
LLM) learns *what, how, and where* from root CLAUDE.md -> README -> ARCHITECTURE
in minutes - on a codebase or a novel alike.

## Invariants
<!-- What must stay true no matter what changes below. The load-bearing constraints. -->
- **Zero-dependency core.** The scaffolder and renderer never require anything
  beyond the Python standard library. An optional backend may add dependencies;
  the core never does.
- **No-clobber, always.** Cairn never overwrites authored content. It is safe to
  run on a half-documented project - it fills only the gaps.
- **The pace-layer contract.** Every file answers exactly one question and
  carries a size budget (enforced as a check), an update trigger, and a
  maintenance mode. That fixed contract is what makes the system formulaic
  across a project of any kind.
- **Structural anti-rot rules.** One diagram per project (in ARCHITECTURE);
  decisions are append-only (never edited, only superseded); nothing in flight
  is stored - the status command derives it.
- **Human owns the why; machines own only regenerable structure.** Derived output
  (e.g. docstring lines copied into a folder page) is reconciled against
  authored truth and never the source of record; it may be committed only
  behind the freshness check.
- **The spine is portable; modules are not.** The spine (root CLAUDE.md,
  README, ARCHITECTURE, CONTRIBUTING) works without a git repository and
  without code; a novel, a business plan, or a research program is a
  first-class target. A type module (software first: folder pages,
  docstrings, the status command) may need git and code.

## Success criteria
<!-- How you'll know it's working. -->
- A newcomer reads root CLAUDE.md -> README -> ARCHITECTURE (about 1.3k tokens,
  held there by the size budgets) and can act without reading the source.
- The spine survives contact with time: months on, it still reflects reality
  because each file had exactly one cheap update trigger.
- Running Cairn on a half-documented project adds only what is missing and breaks
  nothing.
- The spine works unchanged on any project; a type module adds only its own
  files and checks.

## Non-goals
<!-- What this explicitly does NOT try to do - the anti-scope that stops drift. -->
- **Not owned by any consumer.** Cairn feeds other tools - one may consume its
  output - but is never owned by or dependent on one. Cairn stands alone; coupling
  to any specific consumer is out of scope.
- **Not a code-analysis engine.** The software module reads only the folder
  tree and each file's first docstring line; it parses no code. (The 1.x
  graphify backend is retired; see [[0003-1.0-scope]].)
- **Not a docs-site / wiki / API-reference generator.** Cairn is a spine for
  *reasoning*, not a publishing pipeline or an auto-extracted reference.
- **Not a universal everything-tool.** "Any project" means the *pace-layered
  spine* generalizes; derived and automated features are code-only and stay
  optional. Cairn is strongest on code and knowledge work.
- **Not a content author.** Cairn scaffolds frames and records decisions; it does
  not write your docs for you. The only exceptions - a brownfield intent line and
  brownfield conventions starters - are inferred and tagged for correction.
