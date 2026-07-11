"""CLI-wiring tests for the backend entry point (backend/__main__.py).

Asserts the argparse wiring only (no graphify binary needed): `reconcile` exists
with `refresh` as an alias and both dispatch to cmd_refresh, the authored-truth
file defaults to MAP.md and is overridable, and the program name is `cairn`.
Running a command end-to-end needs graphify + a graph.json and is covered by the
reconcile library tests.
"""
from backend.__main__ import AUTHORED_DOC, build_parser, cmd_refresh, cmd_stage


def test_authored_doc_default_is_map():
    assert AUTHORED_DOC == "MAP.md"


def test_prog_name_is_cairn():
    assert build_parser().prog == "cairn"


def test_reconcile_dispatches_to_refresh_with_map_default():
    args = build_parser().parse_args(["reconcile", "somedir"])
    assert args.fn is cmd_refresh
    assert args.file == "MAP.md"
    assert args.apply is False
    assert args.no_derive is False


def test_refresh_alias_still_works():
    args = build_parser().parse_args(["refresh", "somedir"])
    assert args.fn is cmd_refresh
    assert args.file == "MAP.md"


def test_file_override_on_reconcile():
    args = build_parser().parse_args(["reconcile", "somedir", "--file", "ATLAS.md"])
    assert args.file == "ATLAS.md"


def test_stage_defaults_to_map_and_dispatches():
    args = build_parser().parse_args(["stage", "somedir"])
    assert args.fn is cmd_stage
    assert args.file == "MAP.md"
    assert args.force is False
    assert args.accept is False


def test_stage_file_override():
    args = build_parser().parse_args(["stage", "somedir", "--file", "MODEL.md"])
    assert args.file == "MODEL.md"


def test_view_parses_without_path():
    args = build_parser().parse_args(["view"])
    assert args.fn.__name__ == "cmd_view"


def test_validate_and_derive_take_path():
    for cmd in ("validate", "derive"):
        args = build_parser().parse_args([cmd, "somedir"])
        assert args.path == "somedir"


def test_launcher_exposes_main():
    # The absolute-path launcher the /cairn skill invokes must re-export main.
    import backend_cli
    assert callable(backend_cli.main)
