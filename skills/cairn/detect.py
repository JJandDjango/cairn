"""Feature-detector for Cairn's optional backend — zero-dependency, stdlib only.

The CORE (render.py) and the `/cairn` skill use this to decide whether the
optional, graphify-backed backend can run *without importing the backend
package*. That indirection is load-bearing: `import backend` pulls in
`backend/schema.py`, which imports PyYAML at module top and would raise
ImportError precisely in the case we are guarding against (deps absent). So the
detector probes presence with `importlib.util.find_spec` / `shutil.which` and
never imports anything optional.

Backend availability requires BOTH:
  - the `graphify` CLI on PATH (the derived code-graph engine), and
  - PyYAML importable (the authored-schema parser, backend/schema.py).

Absent either, the authored zero-dep spine still renders end-to-end; only the
derived operations (derive / reconcile / view) report unavailable. Version-pin
matching is NOT checked here (presence only) — graphify_adapter.check_version
surfaces a pin mismatch when a command actually runs.
"""
from __future__ import annotations

import importlib.util
import shutil


def _has_module(name: str) -> bool:
    """True if `name` is importable, without importing it. Defensive against
    find_spec raising when a namespace parent is broken."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def backend_status() -> tuple[bool, str]:
    """Return (available, reason).

    available is True only when graphify is on PATH AND PyYAML imports.
    reason names what is missing (with an install hint), or 'ready'.
    """
    missing: list[str] = []
    if shutil.which("graphify") is None:
        missing.append("graphify (install: uv tool install graphifyy==0.8.31)")
    if not _has_module("yaml"):
        missing.append("PyYAML (install: pip install pyyaml)")
    if missing:
        return False, "backend unavailable - missing: " + "; ".join(missing)
    return True, "ready"


def backend_available() -> bool:
    """Convenience boolean wrapper over backend_status()."""
    return backend_status()[0]


def main(argv: list[str] | None = None) -> int:
    """CLI probe: print the reason, exit 0 if available else 1.

    The `/cairn` skill runs this before dispatching a backend subcommand: exit 0
    -> dispatch; non-zero -> report the printed reason and stay on the core path.
    """
    available, reason = backend_status()
    print(reason)
    return 0 if available else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
