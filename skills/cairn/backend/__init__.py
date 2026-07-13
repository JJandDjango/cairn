"""Cairn backend — the optional project-modeling layer over graphify's derived graph.

Schema parser, thin graphify adapter, and vault management. Cairn's optional
code-project backend (graphify-guarded), surfaced via the `/cairn` skill.
"""
from . import graphify_adapter, schema, vault  # noqa: F401

CAIRN_SCHEMA_VERSION = schema.CAIRN_SCHEMA_VERSION
__all__ = ["schema", "graphify_adapter", "vault", "CAIRN_SCHEMA_VERSION"]
