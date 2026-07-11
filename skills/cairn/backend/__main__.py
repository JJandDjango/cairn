"""Atlas CLI — invoked by the `/atlas` skill (``~/.claude/skills/atlas/SKILL.md``)
and usable directly from the repo root:

    python -m atlas validate <path/ATLAS.md>     # check against the schema
    python -m atlas vault-add <path/ATLAS.md>    # symlink into the vault + reindex
    python -m atlas view [--project <name>]       # portfolio roll-up or one project
    python -m atlas derive <path>                 # graphify update (no-LLM, 0 tokens)
    python -m atlas refresh <path>                # derive + reconcile -> proposals.md
    python -m atlas refresh <path> --apply        # write checked proposals into ATLAS.md

Pass 1 shipped the schema parser, thin graphify adapter, vault, and author-first
`/atlas init` (driven by SKILL.md). Pass 2 (this file + reconcile.py) adds the
reconciliation loop: `refresh` derives, diffs the graph against ATLAS.md at
file/dir granularity, and writes confidence-ranked proposals to an editable
graphify-out/proposals.md; `refresh --apply` writes the checked items into
ATLAS.md (the only write into authored truth). Query flags + overlay are Pass 3.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import graphify_adapter as gfx
from . import reconcile, schema, vault


def cmd_validate(args: argparse.Namespace) -> int:
    fm, _ = schema.parse(args.path)
    errors = schema.validate(fm)
    if errors:
        print(f"INVALID ({len(errors)} error(s)):")
        for e in errors:
            print(f"  - {e}")
        return 1
    n_comp = len(fm.get("components") or [])
    n_flow = len(fm.get("flows") or [])
    print(f"OK: {fm.get('name')} "
          f"({n_comp} component{'' if n_comp == 1 else 's'}, "
          f"{n_flow} flow{'' if n_flow == 1 else 's'})")
    return 0


def cmd_vault_add(args: argparse.Namespace) -> int:
    link = vault.add_project(args.path)
    print(f"linked -> {link}")
    print(f"index  -> {vault.VAULT / 'index.md'}")
    return 0


def cmd_view(args: argparse.Namespace) -> int:
    if args.project:
        for p in vault.list_projects():
            if p["name"] == args.project:
                print(f"{p['name']}  [{p['status']}]")
                print(f"  {p['purpose']}")
                print(f"  components: {p['components']}   flows: {p['flows']}")
                return 0
        print(f"no project '{args.project}' in vault {vault.VAULT}")
        return 1
    print(vault.render_index(), end="")
    return 0


def cmd_derive(args: argparse.Namespace) -> int:
    ok, ver = gfx.check_version()
    if not ok:
        print(f"warning: graphify {ver!r} != pinned {gfx.PINNED_VERSION}",
              file=sys.stderr)
    graph_path = gfx.update(args.path)
    g = gfx.load_graph(graph_path)
    print(f"derived -> {graph_path}")
    print(f"  {len(g['nodes'])} nodes, {len(g['edges'])} edges")
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    atlas_md = root / "ATLAS.md"
    proposals_md = root / "graphify-out" / "proposals.md"
    if not atlas_md.exists():
        print(f"no ATLAS.md at {atlas_md}; run `atlas init` first", file=sys.stderr)
        return 1

    if args.apply:
        if not proposals_md.exists():
            print(f"no {proposals_md}; run `refresh` (without --apply) first",
                  file=sys.stderr)
            return 1
        res = reconcile.apply(atlas_md, proposals_md)
        if not res["written"]:
            print("NOT applied — ATLAS.md would be invalid:")
            for e in res["errors"]:
                print(f"  - {e}")
            return 1
        print(f"applied -> {atlas_md}")
        if res["added"]:
            print(f"  +{len(res['added'])} component(s): {', '.join(res['added'])}")
        if res["removed"]:
            print(f"  -{len(res['removed'])} removed: {', '.join(res['removed'])}")
        if not res["added"] and not res["removed"]:
            print("  (nothing checked)")
        return 0

    if not args.no_derive:
        ok, ver = gfx.check_version()
        if not ok:
            print(f"warning: graphify {ver!r} != pinned {gfx.PINNED_VERSION}",
                  file=sys.stderr)
        gfx.update(root)
    graph = root / "graphify-out" / "graph.json"
    if not graph.exists():
        print(f"no graph at {graph}; run without --no-derive", file=sys.stderr)
        return 1
    fm, _ = schema.parse(atlas_md)
    proposals = reconcile.reconcile(atlas_md, graph, root)
    reconcile.render(proposals, proposals_md, name=fm.get("name", "project"),
                     path_hint=args.path)
    new = sum(1 for p in proposals if p.kind == "new_component")
    dang = sum(1 for p in proposals if p.kind == "dangling_component")
    print(f"reconciled -> {proposals_md}")
    print(f"  {new} new-component, {dang} dangling proposal(s)")
    print(f"  edit it, check the keepers, then: "
          f"python -m atlas refresh {args.path} --apply")
    return 0


def cmd_stage(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    atlas_md = root / "ATLAS.md"
    draft_md = root / "graphify-out" / "ATLAS.draft.md"

    if args.accept:
        if not draft_md.exists():
            print(f"no {draft_md}; run `stage` first", file=sys.stderr)
            return 1
        res = reconcile.accept_draft(draft_md, atlas_md)
        if not res["written"]:
            print("NOT accepted — draft is invalid:")
            for e in res["errors"]:
                print(f"  - {e}")
            return 1
        print(f"accepted -> {atlas_md}")
        if "EDIT ME" in atlas_md.read_text(encoding="utf-8"):
            print("  note: 'EDIT ME' stubs remain — edit identity/roles, then validate.")
        return 0

    if atlas_md.exists() and not args.force:
        print(f"{atlas_md} already exists; use `refresh` to reconcile, "
              f"or `stage --force` to re-stage", file=sys.stderr)
        return 1
    if not args.no_derive:
        ok, ver = gfx.check_version()
        if not ok:
            print(f"warning: graphify {ver!r} != pinned {gfx.PINNED_VERSION}",
                  file=sys.stderr)
        gfx.update(root)
    graph = root / "graphify-out" / "graph.json"
    if not graph.exists():
        print(f"no graph at {graph}; run without --no-derive", file=sys.stderr)
        return 1
    draft_md.parent.mkdir(parents=True, exist_ok=True)
    draft_md.write_text(reconcile.stage_draft(graph, root), encoding="utf-8")
    fm, _ = schema.parse(draft_md)
    print(f"staged -> {draft_md}")
    print(f"  {len(fm.get('components') or [])} candidate component(s); "
          f"review/edit (delete noise, fill EDIT ME),")
    print(f"  then: python -m atlas stage {args.path} --accept")
    return 0


def main(argv: list[str] | None = None) -> int:
    # UTF-8 output regardless of the Windows console codepage (authored content
    # routinely contains em-dashes / smart quotes).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="atlas")
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="validate an ATLAS.md against the schema")
    pv.add_argument("path")
    pv.set_defaults(fn=cmd_validate)

    pa = sub.add_parser("vault-add", help="symlink an ATLAS.md into the vault")
    pa.add_argument("path")
    pa.set_defaults(fn=cmd_vault_add)

    pw = sub.add_parser("view", help="render the portfolio or a single project")
    pw.add_argument("--project")
    pw.set_defaults(fn=cmd_view)

    pd = sub.add_parser("derive", help="graphify update (no-LLM) over a repo")
    pd.add_argument("path")
    pd.set_defaults(fn=cmd_derive)

    pr = sub.add_parser("refresh",
                        help="re-derive + reconcile against ATLAS.md -> proposals.md")
    pr.add_argument("path")
    pr.add_argument("--apply", action="store_true",
                    help="write the checked proposals.md items into ATLAS.md")
    pr.add_argument("--no-derive", action="store_true",
                    help="skip graphify re-derive; reconcile the existing graph.json")
    pr.set_defaults(fn=cmd_refresh)

    ps = sub.add_parser("stage",
                        help="derive-first: stage a candidate ATLAS.md from the graph")
    ps.add_argument("path")
    ps.add_argument("--accept", action="store_true",
                    help="validate graphify-out/ATLAS.draft.md and write it to ATLAS.md")
    ps.add_argument("--no-derive", action="store_true",
                    help="skip graphify re-derive; stage from the existing graph.json")
    ps.add_argument("--force", action="store_true",
                    help="re-stage even if ATLAS.md already exists")
    ps.set_defaults(fn=cmd_stage)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
