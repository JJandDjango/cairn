# skills/cairn/templates

## Purpose
Text templates that `render.py` fills and writes into a project.

## Files
<!-- cairn:files -->
<!-- /cairn:files -->
- `ARCHITECTURE.md.template`: Intent, invariants, folder map and where things live.
- `CHANGELOG.md.template`: An empty changelog.
- `CLAUDE.local-root.md.template`: The local-mode root note that imports `.docs-local/`.
- `CLAUDE.local.md.template`: The untracked note for this machine's paths and tools.
- `CLAUDE.md.template`: The root page that imports README and ARCHITECTURE.
- `CONTRIBUTING.md.template`: Set up, workflow, house rules and recipe links.
- `README.md.template`: The user-facing README skeleton.
- `cairn-audit.yml.template`: The CI workflow that runs the audit on every PR, pinned to a Cairn tag.
- `decisions/`: Seed ADR and the ADR template.
- `docs/`: The recipe, feature and design templates.

## Rules
- A template holds `{{ var }}` slots only; no logic.
- The workflow template pins `CAIRN_REF` once, at the top.

## Links
- [Usage guide](../../../docs/usage.md)
