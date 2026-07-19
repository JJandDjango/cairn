"""PromptLang conformance gate for this repo's claimed prompt artifacts.

Runs the foundations ``prompt_lang`` validator over ``skills/`` under the
repo-root ``prompt-lang.config.yaml`` (the artifact-class claim). Auto-skips
where prompt_lang is not installed: cairn's zero-dependency contract holds
for strangers, machines carrying the standard get the batch gate, and any
future CI that installs foundations inherits it for free.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("prompt_lang")

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_claimed_prompt_artifacts_pass_validation() -> None:
    from prompt_lang.config import load_config
    from prompt_lang.validator import validate_directory

    config = load_config(REPO_ROOT / "prompt-lang.config.yaml")
    results = validate_directory(REPO_ROOT / "skills", config)
    assert results, "no .md files under skills/ - the claim is vacuous"
    failures = [
        f"{r.file_path}: "
        + "; ".join(f"line {e.line}: {e.message}" for e in r.errors)
        for r in results
        if not r.passed
    ]
    assert not failures, "PromptLang violations:\n" + "\n".join(failures)
