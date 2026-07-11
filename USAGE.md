# Using Cairn

Cairn lays down a **five-file documentation spine** for a project and gives you a
fixed routine for keeping it alive. This is the explicit, step-by-step guide;
`README.md` is the short overview.

**The whole idea in one sentence:** each of the five files answers exactly one
question and changes at its own pace, so you always know which file to touch, and
you never maintain more than the moment requires.

---

## 1. When to run it

| Situation | Run Cairn? | Mode |
|---|---|---|
| Brand-new project (any kind) | Yes, early | greenfield |
| Existing project with no real docs | Yes | brownfield |
| Project already on Cairn | No — just maintain it (§5) | — |
| You only need generated API reference | No — that's the `docs/` layer, authored on touch (or via graphify) | — |

Cairn works on **any** project — a codebase, a novel, a content site, a business,
a research program. It is not code-specific.

---

## 2. Three ways to run it

### A) In Claude Code — `/cairn` (recommended)
1. Open / `cd` into the project you want to document — Cairn writes into the
   current project directory.
2. Type `/cairn`.
3. Answer the five questions it asks (§3). You don't need to memorize anything;
   the skill interviews you.
4. It writes the spine and prints what it created. Done.

No git repository is required — a folder of chapters is a valid target.

### B) Standalone — `python render.py` (no Claude Code needed)
The engine is zero-dependency Python. Supply the five answers as one JSON object:

```bash
python skills/cairn/render.py --cwd ./my-project --answers '{
  "project_name": "my-novel",
  "intent": "A historical novel on a hard deadline.",
  "project_type": "novel",
  "backend": "none",
  "material": "greenfield"
}'
```

`--cwd` is where files are written (defaults to the current directory). The answer
keys are exactly the five in §3.

### C) As a plugin (for distribution)
Once the repo is on GitHub:

```
/plugin marketplace add <you>/cairn
/plugin install cairn
```

Or install by hand — copy the skill into your skills directory:

```bash
cp -r skills/cairn ~/.claude/skills/cairn                     # macOS / Linux
Copy-Item -Recurse skills\cairn $HOME\.claude\skills\cairn    # Windows
```

---

## 3. The five answers — what each means, how to choose

| # | Answer | What it drives | How to choose |
|---|--------|----------------|---------------|
| 1 | **project_name** | Titles every file (`# Theory - <name>`) | The project's name. In `/cairn` you can pick the folder name or the git-remote name. |
| 2 | **intent** | `THEORY.md`'s Intent — the one-line "why does this exist?" | One sentence. Greenfield: state it. Brownfield: Cairn drafts an inferred line and tags it `_(inferred - confirm)_` for you to correct. |
| 3 | **project_type** | `code` / `novel` / `content-site` / `business` / `research`. Sets the component label (Component / Chapter / Section / Workstream / Claim) and whether a diagram is expected (code only). | Pick the closest. It only affects labels and the diagram — both are editable later. |
| 4 | **material** | `greenfield` (author THEORY now) or `brownfield` (infer + mark). | New project → greenfield. Existing project → brownfield, then confirm the inferred intent first thing. |
| 5 | **backend** *(code only)* | `none` = pure authored markdown. `graphify` = add an optional structured-MAP stub + graphify artifacts to `.gitignore`, and enable `/cairn derive`/`reconcile`/`view`. | Pick **none** unless you use graphify and want a derived, reconciled code-graph map. Non-code projects never see this question. |

---

## 4. What you get

```
THEORY.md          why it exists + what must stay true         (read 1st)
MAP.md             the pieces + how they connect               (read 2nd)
STATE.md           what's in flight right now                  (read 3rd)
decisions/
  0001-record-architecture-decisions.md    the seed ADR
  ADR-template.md                           copy this for each new decision
docs/              one page per piece, authored on touch       (starts empty)
DOCS-SYSTEM.md     the contract + audit checklist for all of the above
```

Read order for anyone (human or LLM) arriving cold: **`THEORY.md → MAP.md →
STATE.md`** (~2-3k tokens) tells you *what, how, and where*. Everything below that
is on-demand.

**Cairn never overwrites.** Run it on a half-documented project and it fills only
the missing files, reporting what it skipped.

---

## 5. Day 2 — keeping the spine alive

This is the part that makes the system work. Each file has ONE trigger — touch it
only then.

| File | Touch it when… | How |
|------|----------------|-----|
| `THEORY.md` | purpose or an invariant changes (rare) | Hand-edit. **Brownfield first task:** confirm the `(inferred)` intent and delete the tag. |
| `MAP.md` | you add / remove / rewire a piece | Update the table row. Keep the ONE diagram at container zoom — no deeper. |
| `decisions/` | you make a choice a future you would question | Copy `ADR-template.md` → `NNNN-short-title.md`; fill Context / Decision / Consequences. **Never edit an old ADR** — supersede it (mark the old one `superseded by NNNN`). |
| `docs/<piece>.md` | you first work on a piece in depth | Author the page then, not upfront. |
| `STATE.md` | end of every work session | Overwrite it freely — it's disposable, your running handoff. |

If you remember only one rule: **decisions are append-only, and `STATE.md` is
throwaway.** Everything else is edited in place, rarely.

---

## 6. A worked example (a novel, start to finish)

```
/cairn
  → name:     gettysburg-novel
  → intent:   "A historical novel about a field surgeon at Gettysburg, hard deadline."
  → type:     novel
  → material: greenfield
```

Cairn writes `THEORY.md`, `MAP.md` (with a **Chapters** table, no diagram),
`STATE.md`, the seed ADR, and `DOCS-SYSTEM.md`. Then you:

1. Fill `THEORY.md` **Invariants** ("stays in 1863; surgeon's POV only") and
   **Non-goals** ("not a battlefield-tactics manual").
2. Add rows to `MAP.md`'s Chapters table as you outline.
3. When you settle a structural choice — say, present tense throughout — copy
   `ADR-template.md` to `decisions/0002-present-tense.md` and record why.
4. End each writing session by overwriting `STATE.md` (Now / Blockers / Next /
   Open questions).

Swap "Chapters" for "Components" and it's the identical routine for a codebase.

---

## 7. The rules that keep it from rotting

Every scaffolded project carries `DOCS-SYSTEM.md` with the full contract plus this
checklist:

- [ ] ADRs are never edited; superseding records exist where decisions changed.
- [ ] Exactly one diagram in the project, in `MAP.md`.
- [ ] Size budgets held — THEORY ≤1p · MAP ≤2p · ADR ≤½p · STATE ≤1p.
- [ ] `STATE.md` regenerated at session end, not hand-patched mid-session.
- [ ] Every `MAP.md` row links a `docs/` page or is marked "no doc yet".
- [ ] No lingering `(inferred)` tags in `THEORY.md`.

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| "It didn't overwrite my file" | By design (no-clobber). Delete the file and re-run, or just edit it in place. |
| "`/cairn` isn't listed" | Reload the Claude Code session after installing the skill. |
| "Wrong project type" | The output is plain markdown — edit the labels, or delete the files and re-run. |
| "Standalone: `--answers is not valid JSON`" | Pass the JSON as a single quoted shell argument; keys must be the five in §3. |
| "Non-code project" | Expected — the component unit becomes chapter / section / etc., and the diagram is omitted. |
