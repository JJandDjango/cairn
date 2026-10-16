# tests

## Purpose
The pytest suite for the skill's scripts, its prompt and this repo's own docs.

## Files
<!-- cairn:files -->
- `spine_1x.py`: Test-side builder for a 1.x spine: the five files /cairn migrate moves.
- `test_audit.py`: Tests for the audit driver's contract (skills/cairn/audit.py) that outlive the 1.x checks.
- `test_checks.py`: Tests for the 2.0 checks (features 22-28) and the 1.x retirement (feature 30).
- `test_dogfood.py`: Pass 7 (feature 31): Cairn adopts its own 2.0 spine and releases 2.0.0.
- `test_local.py`: Tests for local mode (features 18-21): render.py and pages.py with mode "local".
- `test_migrate.py`: Tests for /cairn migrate (feature 29): skills/cairn/migrate.py.
- `test_pages.py`: Tests for the folder-page script (skills/cairn/pages.py).
- `test_promptlang.py`: PromptLang conformance gate for this repo's claimed prompt artifacts.
- `test_render.py`: Tests for the zero-dep 2.0 renderer (skills/cairn/render.py).
- `test_status.py`: Tests for status.py: last done, next, and waiting on you.
<!-- /cairn:files -->

## Rules
- Run `python -m pytest` from the repo root; `pyproject.toml` sets the import path.
- Tests build their projects in `tmp_path`; only `test_dogfood.py` audits this repo.

## Links
- [Set up and test](../CONTRIBUTING.md)
