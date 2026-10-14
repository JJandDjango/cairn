---
name: cairn
description: Scaffold the short onboarding documents any project needs - code or not. Interviews for project name, one-line intent, project type (code/novel/content-site/business/research), greenfield vs brownfield, and tracked vs local mode, then renders root CLAUDE.md (imports README and ARCHITECTURE), README.md, ARCHITECTURE.md, CONTRIBUTING.md, CHANGELOG.md, decisions/ (append-only ADRs), docs/ templates (recipe, feature, design), and a local, untracked CLAUDE.local.md. No-clobber, so it is safe to run on a partly-documented project. Day-2 subcommands - `/cairn audit` (zero-dep, report-only checker) and `/cairn maintain` (session-end routine). Use when starting, standardizing, or maintaining a project's documentation.
---

# `/cairn` - scaffold the onboarding documents

<purpose>
Lay down the few short documents a new collaborator reads on day one, for any
project - a codebase, a novel, a content site, a business, a research program.
Every session, human or agent, starts on CLAUDE.md + README.md +
ARCHITECTURE.md and reads deeper only as its task needs. The skill interviews
the user, then calls a zero-dependency renderer.
</purpose>

<context>
Runs in the target project's Claude Code session; cwd is the project. This
skill's own directory holds the renderer, the auditor, and templates:
  {skill-dir}/render.py
  {skill-dir}/audit.py               (zero-dep spine checker, report-only)
  {skill-dir}/templates/*.template   (plus templates/decisions/)

Portability: Cairn does NOT require a git repo - a
novel or a business plan is a valid target. It detects a git root only to offer
it, never to gate.

Outputs (into the target dir; none overwritten if already present):
  CLAUDE.md - README.md - ARCHITECTURE.md - CONTRIBUTING.md - CHANGELOG.md
  CLAUDE.local.md  (untracked: this machine's paths and tools)
  decisions/0001-record-architecture-decisions.md - decisions/ADR-template.md
  docs/recipe-template.md - docs/feature-template.md - docs/design-template.md
  .gitignore  (tracked mode: + CLAUDE.local.md, once)

Build status: audit and maintain still check the 1.x six-strata spine until
the 2.0 build reworks them; on a fresh 2.0 project audit reports no spine.
</context>

<instructions>
0. DISPATCH. If this skill was invoked with a first argument naming a subcommand, do NOT run the interview:
   - `audit` - CORE, zero-dep: go to the audit-subcommand section.
   - `maintain` - CORE, the session-end routine: go to the maintain-subcommand section.
   Otherwise (no args, or a scaffold / `init` intent) run the interview scaffold, steps 1-7. When the invocation text itself supplies interview answers (a charter- or script-driven run), treat them as interview-equivalent - steps 2-4 ask only for what is missing.

1. CONFIRM the target directory. Default to cwd. Run `git rev-parse --show-toplevel` via Bash; if it succeeds and differs from cwd, ASK the user (AskUserQuestion) whether to target the git root or cwd. If it is not a git repo, that is fine - proceed with cwd. NEVER refuse for lack of git.

2. COLLECT the one-line intent (free text). Ask the user: "One line - why does this project exist?" For a brownfield project you MAY draft an inferred line from what is visible in the directory and ask the user to confirm or correct it.

3. INTERVIEW batch - invoke AskUserQuestion with 4 questions in one call:
   - Q1 header "Project name": "Name for this project?" options: "Use cwd directory name" / "Use git remote name" (offer only if a remote exists) / Other.
   - Q2 header "Project type": "What kind of project is this? (code gets the diagram and status-command row)" options: "code" / "novel" / "content-site" / "business" / "research".
   - Q3 header "Adoption": "Greenfield or brownfield?" options: "greenfield - author the intent now" / "brownfield - infer and mark (inferred)".
   - Q4 header "Mode": "Commit the documents, or keep them local?" options: "tracked - files are committed (Recommended)" / "local - nothing tracked is ever written (not built yet)".

4. CONFIRM local mode is unavailable. If Q4 == "local", TELL the user local mode is not built yet in this release and ASK (AskUserQuestion) whether to continue in tracked mode or stop. On stop, EXIT.

5. PARSE answers into a JSON dict with keys project_name, intent, project_type, adoption, mode:
   - project_name: for "Use cwd directory name" run `(Get-Location).Path | Split-Path -Leaf` (PowerShell); for "Use git remote name" run `git remote get-url origin` and take the last path segment minus `.git`; for Other use the text verbatim. Validate: non-empty, no `/` or `\`.
   - intent: the line from step 2. Validate: non-empty.
   - project_type: one of code|novel|content-site|business|research.
   - adoption: greenfield|brownfield.
   - mode: tracked|local.
   If a validation fails, REPORT it and re-ask just that item (up to 3 times), then EXIT.

6. RENDER - one Bash call:
       python {skill-dir}/render.py --answers '{json}'
   where {skill-dir} is this skill's base directory and {json} is the answer dict
   as a single-quoted shell argument (escape inner double quotes as the shell
   needs). The renderer substitutes {{ var }} placeholders, stamps the date, skips
   any file that already exists, and (tracked mode) adds CLAUDE.local.md to
   .gitignore once. Exit 0 on success; non-zero with a stderr message on failure.

7. REPORT the renderer's stdout (the created / skipped lines) plus next steps:
   "Fill in README.md for a user; fill ARCHITECTURE.md's invariants and folder
   map; write CONTRIBUTING.md's setup, workflow and house rules; add an ADR
   (copy decisions/ADR-template.md) the next time you make a decision a future
   session would question; keep this machine's paths and tools in
   CLAUDE.local.md, which is never committed." If render failed, REPORT the
   stderr and EXIT.
</instructions>

<audit-subcommand>
`/cairn audit` runs the zero-dependency spine checker - the DOCS-SYSTEM audit
checklist, executable. Report-only: it never writes anything.

1. RUN - one Bash call, by absolute path:
       python "{skill-dir}/audit.py" --cwd .
2. REPORT stdout verbatim. Exit 0 = clean; exit 1 = findings, each carrying a
   code (e.g. MAP-DOC-MISSING, STATE-STALE, DOCS-STALE); exit 2 = no spine here
   (offer the scaffold interview instead). Do NOT fix findings unasked - audit
   automates detection; the touches stay with the user (or `/cairn maintain`).
</audit-subcommand>

<maintain-subcommand>
`/cairn maintain` is the session-end routine: automate the DETECTION, keep the
authorship human-reviewed. The agent performs the day-2 touches for what this
session actually changed; every write lands uncommitted for the user's review.

1. AUDIT (before) - one Bash call:
       python "{skill-dir}/audit.py" --cwd . --format json
   Collect the findings. Exit 2 = no spine: offer the scaffold interview and end
   maintain there.
2. GATHER what actually changed this session. In a git repo run
   `git status --porcelain` (one Bash call) and `git diff --stat` (another);
   otherwise ASK the user for a one-line summary of the session's work.
3. TOUCH MAP.md - for each piece the observed changes show was added, removed,
   or rewired, update that row (add / edit / delete). NEVER invent or embellish
   a row beyond the observed changes; when unsure whether a piece was rewired,
   ask.
4. TOUCH docs/ - for each piece deeply worked this session, author or refresh
   its `docs/{piece}.md`, and set/refresh the page's `<!-- covers: ... -->`
   marker so future staleness stays checkable.
5. FLAG the human-owned strata - NEVER edit THEORY.md, CONVENTIONS.md, or any
   existing decisions/*.md. If the session's changes look purpose- or
   invariant-shaped, TELL the user to hand-edit THEORY.md. If they look
   rule-shaped (a new "how we do things here"), TELL the user to hand-edit
   CONVENTIONS.md - adopt / revise / retire, ADR-linked when significant. If a
   change is decision-shaped (a future session would ask "why is it done this
   way?"), ASK (AskUserQuestion) whether to draft a new ADR from
   decisions/ADR-template.md; draft ONLY on an explicit yes.
6. REGENERATE STATE.md wholesale - Now / Blockers / Next actions / Open
   questions, stamped with today's date. Overwrite; never hand-patch.
7. AUDIT (after) - one Bash call:
       python "{skill-dir}/audit.py" --cwd .
   REPORT before -> after findings plus every file touched. Do NOT commit -
   the user reviews and commits.
</maintain-subcommand>

<constraints>
- Do NOT overwrite existing documentation. The renderer is no-clobber by design; never add a flag or step that forces an overwrite.
- Do NOT require a git repository. Non-code projects are first-class targets.
- Do NOT hand-edit the templates during a run. Project values land via {{ var }} substitution only.
- Do NOT author docs/ pages up front. The scaffold writes only the recipe, feature and design templates; real pages are authored on touch.
- Do NOT commit CLAUDE.local.md. It holds this machine's paths and tools only.
- `audit` is core and report-only: never "fix" its findings unasked.
- `maintain` writes ONLY MAP.md, docs/, and STATE.md. THEORY.md, CONVENTIONS.md, and existing decisions/ records are flag-only; a new ADR requires the user's explicit yes. Every touch must be grounded in the session's observed changes, and nothing is ever committed by the skill.
</constraints>

<criteria>
- [ ] Target directory confirmed (cwd, or git root if the user chose it); no git requirement enforced.
- [ ] One-line intent collected (authored, or inferred-and-confirmed for brownfield).
- [ ] Answers captured - project_name, project_type, adoption, mode - from the interview or supplied by the invocation.
- [ ] Local mode, if chosen, was confirmed unavailable and the user chose tracked or stop.
- [ ] Answers parsed to valid JSON; render.py invoked; exit 0.
- [ ] Spine files present at target (or reported skipped where pre-existing); nothing overwritten.
- [ ] Outcome + next steps reported to the user.
- [ ] If invoked as `audit`: audit.py ran by absolute path; findings reported verbatim; nothing was written.
- [ ] If invoked as `maintain`: every touch grounded in observed changes; THEORY.md, CONVENTIONS.md, and existing ADRs untouched (flagged / asked only); STATE.md regenerated with today's stamp; before->after audit reported; nothing committed.
</criteria>
