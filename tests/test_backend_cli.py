"""CLI-wiring tests for the backend entry point (backend/__main__.py).

Asserts the argparse wiring only (no graphify binary needed): `reconcile` exists
with `refresh` as an alias and both dispatch to cmd_refresh, the authored-truth
file defaults to MAP.md and is overridable, and the program name is `cairn`.
Running a command end-to-end needs graphify + a graph.json and is covered by the
reconcile library tests. One exception: cmd_validate's graceful handling of a
frontmatter-less (backend: none) MAP needs no graphify, so its regression lives here.
"""
from backend.__main__ import (
    AUTHORED_DOC,
    build_parser,
    cmd_refresh,
    cmd_stage,
    cmd_validate,
)


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
    args = build_parser().parse_args(["reconcile", "somedir", "--file", "MAP.md"])
    assert args.file == "MAP.md"


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


def test_validate_reports_cleanly_on_frontmatterless_map(tmp_path, capsys):
    """Regression: cmd_validate on a hand-authored MAP with no '---' frontmatter
    (the backend: none default — e.g. Cairn's own MAP.md) must report INVALID and
    return 1, never crash with a MapParseError traceback. See decisions/0004."""
    m = tmp_path / "MAP.md"
    m.write_text("# Map - demo\n\nno frontmatter here.\n", encoding="utf-8")
    rc = cmd_validate(build_parser().parse_args(["validate", str(m)]))
    assert rc == 1
    out = capsys.readouterr().out
    assert "INVALID" in out
    assert "frontmatter" in out


def test_validate_reports_cleanly_on_missing_file(tmp_path, capsys):
    """Regression: cmd_validate on a nonexistent path reports 'cannot read' and
    returns 1, never an OSError/FileNotFoundError traceback."""
    missing = tmp_path / "nope.md"
    rc = cmd_validate(build_parser().parse_args(["validate", str(missing)]))
    assert rc == 1
    assert "cannot read" in capsys.readouterr().out


def test_validate_reports_cleanly_on_malformed_yaml(tmp_path, capsys):
    """Regression: cmd_validate on a MAP whose frontmatter is malformed YAML
    reports INVALID and returns 1, never a yaml.YAMLError traceback."""
    m = tmp_path / "MAP.md"
    m.write_text("---\nname: [unclosed\n---\n\nbody\n", encoding="utf-8")
    rc = cmd_validate(build_parser().parse_args(["validate", str(m)]))
    assert rc == 1
    assert "INVALID" in capsys.readouterr().out


def test_validate_reports_cleanly_on_non_utf8_file(tmp_path, capsys):
    """Regression: cmd_validate on a non-UTF-8 file reports 'cannot read' and
    returns 1, never a UnicodeDecodeError traceback."""
    m = tmp_path / "MAP.md"
    m.write_bytes(b"\xff\xfe not valid utf-8 \x80\x81\n")
    rc = cmd_validate(build_parser().parse_args(["validate", str(m)]))
    assert rc == 1
    assert "cannot read" in capsys.readouterr().out
