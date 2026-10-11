#!/usr/bin/env python3
"""Build a legacy draft graph, or explicitly prepare a new unpromoted release graph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core_graph_pipeline import (
    ValidationError,
    build_graph_payload,
    canonical_generated_at,
    load_entry_config,
    load_jsonl,
    validate_and_measure,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        required=True,
        help="Graph version in <MAJOR>.<YYYYMMDD>[REV] format (for example: 0.20260206c).",
    )
    outputs = parser.add_mutually_exclusive_group()
    parser.add_argument(
        "--schema-version",
        help="Exact existing schema version; defaults to graph version. Does not create or modify a schema.",
    )
    outputs.add_argument(
        "--draft-only",
        action="store_true",
        help="Compatibility alias for the default: write only the draft graph.",
    )
    outputs.add_argument(
        "--prepare-release",
        action="store_true",
        help="Prepare a NEW versioned graph only; refuse existing versions and leave latest, manifest and checksums unchanged.",
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parent.parent,
        type=Path,
        help="Repository root path.",
    )
    parser.add_argument(
        "--nodes-path",
        default=Path("drafts/core/source/nodes.jsonl"),
        type=Path,
        help="Path to nodes JSONL, relative to repo root.",
    )
    parser.add_argument(
        "--edges-path",
        default=Path("drafts/core/source/edges.jsonl"),
        type=Path,
        help="Path to edges JSONL, relative to repo root.",
    )
    parser.add_argument(
        "--entry-path",
        default=Path("drafts/core/source/entry_nodes.json"),
        type=Path,
        help="Path to entry node config JSON, relative to repo root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root: Path = args.repo_root.resolve()
    nodes_path = (repo_root / args.nodes_path).resolve()
    edges_path = (repo_root / args.edges_path).resolve()
    entry_path = (repo_root / args.entry_path).resolve()

    try:
        nodes = load_jsonl(nodes_path)
        edges = load_jsonl(edges_path)
        entry_node_ids, fanin_exception_ids = load_entry_config(entry_path)

        errors, warnings, metrics = validate_and_measure(
            nodes=nodes,
            edges=edges,
            entry_node_ids=entry_node_ids,
            fanin_exception_node_ids=fanin_exception_ids,
        )

        if errors:
            print("Core graph build failed validation:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1

        if warnings:
            print("Core graph build warnings:")
            for warning in warnings:
                print(f"- {warning}")

        payload = build_graph_payload(
            version=args.version,
            nodes=nodes,
            edges=edges,
            entry_node_ids=entry_node_ids,
            schema_version=args.schema_version,
        )

        draft_graph_path = repo_root / "drafts/core/tensor.core.graph.json"
        if args.prepare_release:
            release_dir = repo_root / f"releases/core/graphs/v{args.version}"
            manifest_path = repo_root / "releases/manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if any(release.get("graphVersion") == args.version for release in manifest.get("releases", [])):
                    raise ValidationError(f"Graph version {args.version} is already recorded in the release manifest.")
            # Exclusive directory creation rejects files, symlinks and even empty
            # existing version directories before any graph or pointer is changed.
            release_dir.mkdir(parents=True, exist_ok=False)
            release_graph_path = release_dir / "tensor.core.graph.json"
            with release_graph_path.open("x", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=True)
                handle.write("\n")
        else:
            releases_dir = (repo_root / "releases").resolve()
            if releases_dir in draft_graph_path.resolve().parents:
                raise ValidationError("Draft output resolves into releases; refusing to modify a released artifact.")
            write_json(draft_graph_path, payload)

        print(f"Built graph version: {args.version}")
        print(f"Generated at: {canonical_generated_at(args.version)}")
        print(f"Nodes: {metrics['nodeCount']} | Edges: {metrics['edgeCount']}")
        print(f"Entry nodes: {metrics['entryCount']} | Cross-domain ratio: {metrics['crossDomainRatio']:.4f}")
        if args.prepare_release:
            print(f"Unpromoted release graph: {release_graph_path.relative_to(repo_root)}")
            print("Complete and review the schema, reports, manifest, latest pointers and checksums before promotion.")
        else:
            print(f"Draft output: {draft_graph_path.relative_to(repo_root)}")
        return 0

    except (ValidationError, OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
