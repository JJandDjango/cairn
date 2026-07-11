"""Contract tests: graphify_adapter decodes subprocess output UTF-8/replace.

graphify is an external CLI whose output is not guaranteed ASCII; on Windows the
locale codec (cp1252, strict) crashes on bytes undefined there (e.g. 0x90, a
UTF-8 continuation byte). These tests lock the encoding="utf-8", errors="replace"
decode policy so a refactor can't silently regress to text=True alone. (#133
cp1252 audit; mirrors the harness-wide policy in cli_runner.py.)

This is the first test coverage of atlas/graphify_adapter.py. The decode itself
happens inside subprocess, so the proportionate guard is a contract assertion on
the kwargs (a real non-cp1252 graphify run isn't reproducible without the tool).
"""

from __future__ import annotations

import subprocess as subprocess_mod

import pytest

from backend import graphify_adapter


def _fake_completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess_mod.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


class TestGraphifyDecodePolicy:
    """Every graphify subprocess call carries encoding="utf-8", errors="replace"."""

    def test_version_decodes_utf8_replace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list = []

        def fake_run(cmd, **kwargs):
            calls.append(kwargs)
            return _fake_completed(stdout="graphifyy 0.8.31\n")

        monkeypatch.setattr(graphify_adapter, "_graphify", lambda: "graphify")
        monkeypatch.setattr(graphify_adapter.subprocess, "run", fake_run)

        assert graphify_adapter.version() == "graphifyy 0.8.31"
        assert calls and calls[0].get("encoding") == "utf-8"
        assert calls[0].get("errors") == "replace"

    def test_update_decodes_utf8_replace(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list = []

        def fake_run(cmd, **kwargs):
            calls.append(kwargs)
            return _fake_completed(returncode=0)

        monkeypatch.setattr(graphify_adapter, "_graphify", lambda: "graphify")
        monkeypatch.setattr(graphify_adapter.subprocess, "run", fake_run)

        # The fake produces no graph.json, so update() raises after the call;
        # the decode-policy kwargs (asserted below) are the contract under test.
        with pytest.raises(graphify_adapter.GraphifyError):
            graphify_adapter.update(tmp_path)
        assert calls and calls[0].get("encoding") == "utf-8"
        assert calls[0].get("errors") == "replace"
