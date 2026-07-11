"""Tests for the zero-dep backend feature-detector (skills/cairn/detect.py).

Monkeypatched so the result is independent of whether graphify / PyYAML are
actually installed here — the point is the gating logic, not this machine.
Importing `detect` must NOT drag in the backend package (PyYAML); it is stdlib
only, so this module imports cleanly even with the optional deps absent.
"""
import detect


def test_available_when_both_present(monkeypatch):
    monkeypatch.setattr(detect.shutil, "which", lambda name: "/usr/bin/graphify")
    monkeypatch.setattr(detect, "_has_module", lambda name: True)
    available, reason = detect.backend_status()
    assert available is True
    assert reason == "ready"
    assert detect.backend_available() is True


def test_unavailable_when_graphify_missing(monkeypatch):
    monkeypatch.setattr(detect.shutil, "which", lambda name: None)
    monkeypatch.setattr(detect, "_has_module", lambda name: True)
    available, reason = detect.backend_status()
    assert available is False
    assert "graphify" in reason
    assert "PyYAML" not in reason


def test_unavailable_when_yaml_missing(monkeypatch):
    monkeypatch.setattr(detect.shutil, "which", lambda name: "/usr/bin/graphify")
    monkeypatch.setattr(detect, "_has_module", lambda name: False)
    available, reason = detect.backend_status()
    assert available is False
    assert "PyYAML" in reason
    assert "graphify" not in reason


def test_unavailable_lists_both_when_both_missing(monkeypatch):
    monkeypatch.setattr(detect.shutil, "which", lambda name: None)
    monkeypatch.setattr(detect, "_has_module", lambda name: False)
    available, reason = detect.backend_status()
    assert available is False
    assert "graphify" in reason
    assert "PyYAML" in reason


def test_has_module_true_for_stdlib():
    # A module that is always importable — exercises the real find_spec path.
    assert detect._has_module("json") is True


def test_has_module_false_for_absent():
    assert detect._has_module("no_such_module_xyzzy") is False


def test_main_exit_codes(monkeypatch, capsys):
    monkeypatch.setattr(detect, "_has_module", lambda name: True)
    monkeypatch.setattr(detect.shutil, "which", lambda name: "/usr/bin/graphify")
    assert detect.main([]) == 0
    assert capsys.readouterr().out.strip() == "ready"

    monkeypatch.setattr(detect.shutil, "which", lambda name: None)
    assert detect.main([]) == 1
    assert "unavailable" in capsys.readouterr().out
