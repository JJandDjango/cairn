# Map - cairn

> **Contract** - one question: *what are the pieces, and how do they connect?*
> <=2 pages - update on add / remove / rewire of a Component - hand-edited.

## Diagram
```mermaid
flowchart TD
    U[/cairn skill - SKILL.md/] --> R[render.py - zero-dep core]
    R --> T[templates/ - the five strata]
    U -. backend subcommand .-> D[detect.py - dependency gate]
    D -. only if available .-> B[backend/ - OPTIONAL graphify integration]
    B --> G[graphify adapter - derive]
    B --> RC[reconcile - authored vs derived]
    B --> C[contracts - per-file dependency report]
```
<!-- The ONE diagram, at container zoom. Solid edges = the zero-dep core;
     dashed edges = the optional, dependency-gated backend. -->

## Components

### Core - zero-dependency
| Component | Responsibility (one line) | Status | Deep doc |
|---|---|---|---|
| `render.py` | Substitute the five templates into a project (no-clobber, date-stamped). The whole core engine. | stable | USAGE.md |
| `templates/` | The five strata + DOCS-SYSTEM + seed ADR & ADR-template, with `{{ var }}` slots. | stable | DOCS-SYSTEM.md |
| `SKILL.md` (`/cairn`) | The Claude Code interview that collects the five answers and calls the renderer. | stable | no doc yet |
| `detect.py` | Feature-detector that gates the optional backend (absent deps report cleanly, never crash). | stable | no doc yet |

### Backend - OPTIONAL, code-only graphify integration ([[0002-optional-graphify-backend]])
| Component | Responsibility (one line) | Status | Deep doc |
|---|---|---|---|
| `backend/graphify_adapter.py` | `derive` a structured code graph -> `graphify-out/graph.json`. | optional | no doc yet |
| `backend/reconcile.py` | Diff derived graph vs authored MAP -> `proposals.md`; `--apply` writes accepted rows. | optional | no doc yet |
| `backend/contracts.py` | Render a deterministic per-file dependency-contract report from the graph. | optional | no doc yet |
| `backend/schema.py` + `vault.py` | Structured-MAP schema (PyYAML) + portfolio vault roll-up (`view`). | optional | no doc yet |
| `backend_cli.py` + `backend/__main__.py` | Absolute-path launcher + subcommand dispatch (derive / reconcile / view / stage / validate / vault-add). | stable | no doc yet |

## Cross-cutting notes
- **Core vs backend is the load-bearing seam.** The core is zero-dependency and
  self-contained; everything under Backend is optional and dependency-gated by
  `detect.py` ([[0002-optional-graphify-backend]]).
- **Derived output is regenerable + gitignored** (`graphify-out/`,
  `/manifest.json`); authored markdown is the source of record.
- Docs live outside the strata: `README.md` (overview) + `USAGE.md`
  (step-by-step). No `docs/` pages authored yet.
