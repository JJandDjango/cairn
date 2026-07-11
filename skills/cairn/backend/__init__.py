"""Cairn backend — project-modeling primitive (authored layer over graphify's derived graph).

Pass 1 skeleton: schema parser, thin graphify adapter, vault management. This is
Cairn's optional code-project backend (graphify-guarded), surfaced via the
global `/cairn` skill (`~/.claude/skills/cairn/SKILL.md`).
"""
from . import graphify_adapter, schema, vault  # noqa: F401

ATLAS_SCHEMA_VERSION = schema.ATLAS_SCHEMA_VERSION
__all__ = ["schema", "graphify_adapter", "vault", "ATLAS_SCHEMA_VERSION"]
