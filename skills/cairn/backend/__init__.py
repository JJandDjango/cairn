"""Atlas — project-modeling primitive (authored layer over graphify's derived graph).

Pass 1 skeleton: schema parser, thin graphify adapter, vault management. See
`ATLAS.md` at the repo root for the full design. Atlas is *not* the harness
(`agentic/`); it lives as its own top-level package, surfaced via the global
`/atlas` skill (`~/.claude/skills/atlas/SKILL.md`).
"""
from . import graphify_adapter, schema, vault  # noqa: F401

ATLAS_SCHEMA_VERSION = schema.ATLAS_SCHEMA_VERSION
__all__ = ["schema", "graphify_adapter", "vault", "ATLAS_SCHEMA_VERSION"]
