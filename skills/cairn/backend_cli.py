"""Absolute-path launcher for Cairn's optional backend CLI.

The `/cairn` skill runs the backend from the TARGET project's cwd, where the
`backend` package is not importable. This launcher puts its own directory (the
skill dir) on sys.path, then delegates to backend.__main__ -- so the skill can
invoke `python <skill-dir>/backend_cli.py <subcommand> ...` by absolute path, the
same way it invokes render.py, with no cd and no PYTHONPATH. (backend/__main__.py
uses package-relative imports and so cannot be run as a bare file, and `python -m
backend` is not resolvable from the target cwd.)

Reached only after detect.py reports the backend available, so the backend
imports (PyYAML via schema) are known to succeed by the time this runs.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.__main__ import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
