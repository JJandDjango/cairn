# Contributing to Cairn

Read this before working or committing.

## Set up and test
Python 3.12, standard library only. Install pytest, then run
`python -m pytest`; green before you push. Check the docs with
`python skills/cairn/audit.py --cwd .`; it must exit 0. For a `SKILL.md`
change, run `/cairn` in a scratch directory and confirm what it writes.
To turn on the PromptLang test, `pip install git+https://github.com/JJandDjango/foundations`.

## Workflow
`main` is protected by a [ruleset](scripts/ruleset-protect-main.json): no
force-push, no deletion, and every change by pull request, the
maintainer's included. So: fork, branch, make the change, push to your
fork, open a PR against `main` saying what changed and why. For anything
non-trivial, open an issue first; for a typo or small fix, just send the
PR. Review takes a few days, and CI must be
green. A handoff in the middle of a piece of work stays in that work's own
folder, never in a top-level file.

## House rules
- **Zero-dependency core.** Engine scripts import only the standard library.
- **No-clobber.** Render fills gaps; it never overwrites authored text.
- **ADRs are append-only.** Copy [the template](decisions/ADR-template.md)
  to `NNNN-title.md`; supersede, never edit
  ([0001](decisions/0001-record-architecture-decisions.md)).
- **The doc touch is part of done.** A piece added, removed or rewired
  updates its row in `ARCHITECTURE.md`; a decision a future maintainer
  would question gets an ADR.
- **Automate detection, not authorship.** Machines flag; people write
  ([0006](decisions/0006-automate-detection-not-authorship.md)).
- **PromptLang governs `SKILL.md`.** It validates under
  `prompt-lang.config.yaml`; placeholders stay brace-form
  ([0007](decisions/0007-adopt-promptlang-for-the-skill-prompt.md)).
- **One version source.** `.claude-plugin/plugin.json`; `pyproject.toml`
  is pytest config only.
- **LF line endings**, pinned by `.gitattributes`.
- **Commit footers** carry the real session URL, copied from the live
  session, never fabricated
  ([0005](decisions/0005-record-commit-footer-errata.md)).
- **License.** By contributing you license your work under the MIT
  [License](LICENSE); inbound equals outbound.
