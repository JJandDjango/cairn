# Theory - cairn

> **Contract** - one question: *why does this exist, and what must stay true?*
> <=1 page - update when purpose or invariants change - hand-edited, rare.

## Intent
A zero-dependency, pace-layered documentation spine that keeps any project
legible over time: cheap to start, cheap to keep true. Cairn scaffolds the spine
**and** carries the day-2 discipline that keeps it alive, so a reader (human or
LLM) learns *what, how, and where* from THEORY -> MAP -> STATE in minutes - on a
codebase or a novel alike.

## Invariants
<!-- What must stay true no matter what changes below. The load-bearing constraints. -->
- **Zero-dependency core.** The scaffolder and renderer never require anything
  beyond the Python standard library. An optional backend may add dependencies;
  the core never does.
- **No-clobber, always.** Cairn never overwrites authored content. It is safe to
  run on a half-documented project - it fills only the gaps.
- **The pace-layer contract.** Every stratum answers exactly one question and
  carries a size budget, an update trigger, and a maintenance mode. That fixed
  contract is what makes the system formulaic across a project of any kind.
- **Structural anti-rot rules.** One diagram per project (in MAP); decisions are
  append-only (never edited, only superseded); STATE is disposable (regenerated,
  never hand-patched).
- **Human owns the why; machines own only regenerable structure.** Derived output
  (e.g. a graphify-built MAP) is optional, gitignored, and reconciled against
  authored truth - never the source of record.
- **Portable by construction.** Works without a git repository and without code.
  A novel, a business plan, or a research program is a first-class target.

## Success criteria
<!-- How you'll know it's working. -->
- A newcomer reads THEORY -> MAP -> STATE (~2-3k tokens) and can act without
  reading the source.
- The spine survives contact with time: months on, it still reflects reality
  because each stratum had exactly one cheap update trigger.
- Running Cairn on a half-documented project adds only what is missing and breaks
  nothing.
- The same routine works unchanged on code and non-code projects - only the
  component label and the diagram differ.

## Non-goals
<!-- What this explicitly does NOT try to do - the anti-scope that stops drift. -->
- **Not owned by any consumer.** Cairn feeds other tools - one may consume its
  output - but is never owned by or dependent on one. Cairn stands alone; coupling
  to any specific consumer is out of scope.
- **Not a code-analysis engine.** The graphify backend is an *optional*
  enhancement of one stratum (MAP), not Cairn's identity; the core's value holds
  with the backend absent. (See [[0003-1.0-scope]].)
- **Not a docs-site / wiki / API-reference generator.** Cairn is a spine for
  *reasoning*, not a publishing pipeline or an auto-extracted reference.
- **Not a universal everything-tool.** "Any project" means the *pace-layered
  spine* generalizes; derived and automated features are code-only and stay
  optional. Cairn is strongest on code and knowledge work.
- **Not a content author.** Cairn scaffolds frames and records decisions; it does
  not write your docs for you. The lone exception - a brownfield intent line - is
  inferred and tagged for correction.
