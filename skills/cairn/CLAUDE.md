# skills/cairn

## Purpose
The `/cairn` skill: the interview prompt and the zero-dependency scripts it drives.

## Files
<!-- cairn:files -->
- `audit.py`: Audit a Cairn 2.0 documentation spine.
- `migrate.py`: Move a 1.x spine to its 2.0 homes: a dry-run plan, then the mechanical moves.
- `pages.py`: Write and refresh folder pages: a CLAUDE.md in each working folder.
- `render.py`: Render the Cairn 2.0 spine into a project directory.
- `status.py`: Print what is in flight: last done, next, and what waits on you.
<!-- /cairn:files -->
- `SKILL.md`: The `/cairn` prompt: the interview and the subcommands.
- `templates/`: The spine and folder-page templates with `{{ var }}` slots.

## Rules
- Standard library only. A script never writes outside the target project.
- `SKILL.md` validates under PromptLang (`prompt-lang.config.yaml`).

## Links
- [Usage guide](../../docs/usage.md)
- [What the audit checks](../../docs/audit.md)
