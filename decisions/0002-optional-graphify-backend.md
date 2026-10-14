# 2. The graphify backend is optional and dependency-gated

Status: superseded by 0009
Date: 2026-07-12

## Context
Cairn's core is a zero-dependency scaffolder. It also ships an optional backend
(`skills/cairn/backend/`) that derives a structured MAP from a code graph via the
external `graphify` tool + PyYAML. That backend must never compromise the
zero-dependency promise of the core, and must be usable — or entirely absent —
without breaking anything.

## Decision
The backend is **optional and dependency-gated**, never part of the core. It is
reachable only through `detect.py`, which probes for `graphify` + PyYAML via
`find_spec` / `which` *without importing the backend package*. Absent either
dependency, `detect` reports "unavailable" and the zero-dependency spine still
renders end-to-end.

## Consequences
- The core (`render.py` + templates + skill) imports nothing from `backend/`; the
  zero-dependency-core invariant holds even though the backend pulls PyYAML +
  graphify.
- `derive` / `reconcile` / `view` / `stage` are offered only when the detector
  passes; they degrade to a clean message, never a crash.
- The backend is code-only (it models a code graph); non-code projects never see
  it. See [[0003-1.0-scope]].
