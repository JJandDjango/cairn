---
name: cairn
description: Scaffold a durable, pace-layered documentation spine into any project - code or not. Interviews for project name, one-line intent, project type (code/novel/content-site/business/research), greenfield vs brownfield, and (for code) an optional ATLAS/graphify backend, then renders five strata - THEORY.md (why), MAP.md (structure), decisions/ (append-only ADRs), docs/ (detail), STATE.md (in-flight) - each under a fixed one-question contract, plus a DOCS-SYSTEM.md audit checklist. No-clobber, so it is safe to run on a partly-documented project. Use when starting or standardizing a project's documentation.
---

# `/cairn` - scaffold a pace-layered documentation spine

<purpose>
Lay down a durable, portable documentation spine for any project - a codebase, a
novel, a content site, a business, a research program. Cairn renders five
pace-layered strata (each changing at its own rate under a fixed contract) so
that fast-moving notes never tear slow-moving truth, and a new reader (human or
LLM) learns *what, how, and where* from THEORY.md + MAP.md + STATE.md in minutes.
The skill interviews the user, then calls a zero-dependency renderer.
</purpose>

<context>
Runs in the target project's Claude Code session; cwd is the project. This
skill's own directory holds the renderer and templates:
  <skill-dir>/render.py
  <skill-dir>/templates/*.template   (plus templates/decisions/)

Portability: unlike a harness bootstrap, Cairn does NOT require a git repo - a
novel or a business plan is a valid target. It detects a git root only to offer
it, never to gate.

Outputs (into the target dir; none overwritten if already present):
  THEORY.md - MAP.md - STATE.md - DOCS-SYSTEM.md
  decisions/0001-record-architecture-decisions.md - decisions/ADR-template.md
  docs/.gitkeep
  .gitignore  (only when the ATLAS backend is chosen: + graphify-out/, /manifest.json)
</context>

<instructions>
1. CONFIRM the target directory. Default to cwd. Run `git rev-parse --show-toplevel` via Bash; if it succeeds and differs from cwd, ASK the user (AskUserQuestion) whether to target the git root or cwd. If it is not a git repo, that is fine - proceed with cwd. NEVER refuse for lack of git.

2. COLLECT the one-line intent (free text). Ask the user: "One line - why does this project exist?" For a brownfield project you MAY draft an inferred line from what is visible in the directory and ask the user to confirm or correct it.

3. INTERVIEW batch - invoke AskUserQuestion with 3 questions in one call:
   - Q1 header "Project name": "Name for this project?" options: "Use cwd directory name" / "Use git remote name" (offer only if a remote exists) / Other.
   - Q2 header "Project type": "What kind of project is this? (sets the component unit)" options: "code" / "novel" / "content-site" / "business" / "research".
   - Q3 header "Material": "Greenfield or brownfield?" options: "greenfield - author THEORY now" / "brownfield - infer and mark (inferred)".

4. CONDITIONAL backend question - ONLY if Q2 == "code": invoke AskUserQuestion with 1 question:
   - header "Backend": "Optional derived backend for the MAP + docs layers?" options: "none - zero-dependency authored markdown (Recommended)" / "atlas - point MAP at /atlas init + graphify for blast-radius".
   For any non-code project type, set backend = "none" WITHOUT asking.

5. PARSE answers into a JSON dict with keys project_name, intent, project_type, backend, material:
   - project_name: for "Use cwd directory name" run `(Get-Location).Path | Split-Path -Leaf` (PowerShell); for "Use git remote name" run `git remote get-url origin` and take the last path segment minus `.git`; for Other use the text verbatim. Validate: non-empty, no `/` or `\`.
   - intent: the line from step 2. Validate: non-empty.
   - project_type: one of code|novel|content-site|business|research.
   - backend: none|atlas (atlas only when project_type == code).
   - material: greenfield|brownfield.
   If a validation fails, REPORT it and re-ask just that item (up to 3 times), then EXIT.

6. RENDER - one Bash call:
       python <skill-dir>/render.py --answers '{json}'
   where <skill-dir> is this skill's base directory and {json} is the answer dict
   as a single-quoted shell argument (escape inner double quotes as the shell
   needs). The renderer substitutes {{ var }} placeholders, stamps the date, skips
   any file that already exists, and (for the atlas backend) appends to .gitignore.
   Exit 0 on success; non-zero with a stderr message on failure.

7. REPORT the renderer's stdout (the created / skipped lines) plus next steps:
   "Fill in THEORY.md's invariants and MAP.md's component table; keep STATE.md as
   your session-end handoff; add an ADR (copy decisions/ADR-template.md) the next
   time you make a decision a future session would question. See DOCS-SYSTEM.md for
   the full contract + audit checklist." If render failed, REPORT the stderr and EXIT.
</instructions>

<constraints>
- Do NOT overwrite existing documentation. The renderer is no-clobber by design; never add a flag or step that forces an overwrite.
- Do NOT require a git repository. Non-code projects are first-class targets.
- Do NOT reimplement ATLAS/graphify. The atlas backend only makes MAP.md point at `/atlas init` and adjusts .gitignore; if the user picks it, mention they can run `/atlas init` separately to populate the derived map.
- Do NOT hand-edit the templates during a run. Project values land via {{ var }} substitution only.
- Do NOT author docs/ pages up front. That layer is authored on touch (or generated); the scaffold leaves docs/ empty.
</constraints>

<criteria>
- [ ] Target directory confirmed (cwd, or git root if the user chose it); no git requirement enforced.
- [ ] One-line intent collected (authored, or inferred-and-confirmed for brownfield).
- [ ] Interview batch executed; project_name, project_type, material captured.
- [ ] Backend captured (asked only for code; forced none otherwise).
- [ ] Answers parsed to valid JSON; render.py invoked; exit 0.
- [ ] Strata present at target (or reported skipped where pre-existing); nothing overwritten.
- [ ] Outcome + next-steps + DOCS-SYSTEM.md pointer reported to the user.
</criteria>
