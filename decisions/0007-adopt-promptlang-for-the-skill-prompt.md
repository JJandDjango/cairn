# 0007. Adopt PromptLang for the skill prompt

Status: accepted
Date: 2026-07-19

## Context

The skill entry point (`skills/cairn/SKILL.md`) is a load-bearing prompt:
agents dispatch on its sections and follow its steps verbatim. The foundations
repo's PromptLang standard validates prompt form deterministically
(`python -m prompt_lang`), and its packaged default config already claims
`**/skills/*/SKILL.md` - so machines carrying the standard were already
write-time-checking this file against rules it could not satisfy: its
subcommand sections use custom tags, and inline placeholders like
`<skill-dir>` parse as unclosed tags (27 errors).

Alternatives weighed: restructure SKILL.md down to the standard tag set
(larger rewrite of a shipped artifact, regression risk in the dispatch step),
or ignore the standard (leaves the latent write-time friction in place).
Constraint: cairn is public and zero-dependency while foundations is private,
so a hard test or CI dependency on it would break strangers' `pytest`.

## Decision

Adopt by claim, not restructure. A repo-root `prompt-lang.config.yaml` claims
`**/skills/*/SKILL.md` and registers the three section tags
(`audit-subcommand`, `maintain-subcommand`, `backend-subcommands`) as optional
tags; inline placeholders switch to brace form (`{skill-dir}`, `{subcommand}`,
`{args}`, `{piece}`), matching the existing `{{ var }}` / `{json}` idiom.
Batch teeth are a pytest gate (`tests/test_promptlang.py`) that
`importorskip`s prompt_lang - enforcing where foundations is installed,
skipping silently where it is not. CI enforcement is deferred to the
foundations public flip.

## Consequences

Easier: deterministic form checks on the skill prompt (write-time hook + test
gate); the config documents exactly which artifact class is claimed; any
future CI that installs foundations inherits the gate for free. Harder: new
section tags or placeholders in SKILL.md must be registered / kept de-angled
to stay green. Accepted: spine docs and templates remain unclaimed reference
text, and the token-count warning (~2.9k, fail at 4k) stands as a size
watchdog.
