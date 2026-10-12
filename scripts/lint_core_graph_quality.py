#!/usr/bin/env python3
"""Validate graph quality gates and emit deterministic quality artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from core_graph_pipeline import (
    ValidationError,
    build_coverage_matrix_markdown,
    build_coverage_matrix_payload,
    build_quality_report_markdown,
    load_entry_config,
    load_jsonl,
    validate_and_measure,
    write_json,
)
from core_graph_math_assurance import (
    build_math_assurance_markdown,
    build_math_assurance_payload,
)
from graph_assurance_policy import POLICY_ID, DIAGNOSTIC_IDS, assess_evidence, build_acceptance, gate, EVIDENCE_IDS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Expected graph version; required with JSONL sources.")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parent.parent, type=Path)
    parser.add_argument("--graph-path", type=Path, help="Exact graph JSON to assess.")
    parser.add_argument("--nodes-path", type=Path, help="Explicit nodes JSONL source path.")
    parser.add_argument("--edges-path", type=Path, help="Explicit edges JSONL source path.")
    parser.add_argument("--entry-path", type=Path, help="Entry configuration and fan-in exceptions.")
    parser.add_argument("--criteria-path", type=Path, help="Exact evidence criteria; canonical draft defaults to its adjacent criteria.")
    parser.add_argument("--scenarios-path", type=Path, help="Exact normalized evidence scenarios; canonical draft defaults to its scenario suite.")
    parser.add_argument(
        "--draft-review", action="store_true",
        help="Compatibility alias restricted to the canonical draft; applies the same current policy as default lint, with no waived checks.",
    )
    parser.add_argument(
        "--output-dir", type=Path, required=True,
        help="Report directory outside releases; never updates published reports or latest pointers.",
    )
    args = parser.parse_args()
    if args.graph_path:
        if args.nodes_path or args.edges_path:
            parser.error("--graph-path cannot be mixed with JSONL source paths")
    elif not all((args.nodes_path, args.edges_path, args.entry_path, args.version)):
        parser.error("provide --graph-path, or all of --nodes-path, --edges-path, --entry-path and --version")
    return args


def load_inputs(args: argparse.Namespace, repo_root: Path):
    """Load only explicit artifacts; bind the report to their exact bytes."""
    inputs = []

    def resolved(path: Path) -> Path:
        target = (repo_root / path).resolve()
        inputs.append({"path": str(path), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        return target

    fanin_exception_ids = set()
    if args.graph_path:
        graph = json.loads(resolved(args.graph_path).read_text(encoding="utf-8"))
        version = graph.get("version")
        if not isinstance(version, str) or not version:
            raise ValidationError("Input graph must declare its version.")
        if args.version is not None and args.version != version:
            raise ValidationError(f"Expected version {args.version!r}, but exact graph declares {version!r}.")
        nodes = [item.get("data", item) for item in graph["nodes"]]
        edges = [item.get("data", item) for item in graph["edges"]]
        entry_node_ids = graph["entryNodeIds"]
        if args.entry_path:
            configured_entries, fanin_exception_ids = load_entry_config(resolved(args.entry_path))
            if configured_entries != entry_node_ids:
                raise ValidationError("Entry configuration does not match the exact graph's entryNodeIds.")
        mode = "graph-artifact"
    else:
        nodes = load_jsonl(resolved(args.nodes_path))
        edges = load_jsonl(resolved(args.edges_path))
        entry_node_ids, fanin_exception_ids = load_entry_config(resolved(args.entry_path))
        version = args.version
        mode = "authoring-sources"
    return version, nodes, edges, entry_node_ids, fanin_exception_ids, {
        "inputMode": mode,
        "inputs": inputs,
        "policy": POLICY_ID,
        "scope": "Structural and simulated authoring checks; not release conformance or investigative effectiveness.",
    }


def main() -> int:
    args = parse_args()
    repo_root: Path = args.repo_root.resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    releases_dir = (repo_root / "releases").resolve()
    if output_dir == releases_dir or releases_dir in output_dir.parents:
        print("ERROR: Reports must be written outside releases; published artifacts are preserved.", file=sys.stderr)
        return 1
    if args.draft_review and (
        args.graph_path is None
        or (repo_root / args.graph_path).resolve() != (repo_root / "drafts/core/tensor.core.graph.json").resolve()
        or (repo_root / "releases").resolve() in (repo_root / args.graph_path).resolve().parents
    ):
        print("ERROR: --draft-review is restricted to the canonical unpromoted draft graph.", file=sys.stderr)
        return 1

    try:
        version, nodes, edges, entry_node_ids, fanin_exception_ids, provenance = load_inputs(args, repo_root)
        provenance["assessmentMode"] = "current-authoring-acceptance"
        errors, warnings, metrics = validate_and_measure(
            nodes=nodes,
            edges=edges,
            entry_node_ids=entry_node_ids,
            fanin_exception_node_ids=fanin_exception_ids,
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        quality_json_path = output_dir / "graph-quality.json"
        quality_md_path = output_dir / "graph-quality.md"
        coverage_json_path = output_dir / "coverage-matrix.json"
        coverage_md_path = output_dir / "coverage-matrix.md"
        math_json_path = output_dir / "math-assurance.json"
        math_md_path = output_dir / "math-assurance.md"

        quality_json_payload = {
            "version": version,
            "provenance": provenance,
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics,
        }
        coverage_payload = build_coverage_matrix_payload(version, metrics)
        coverage_payload["provenance"] = provenance
        write_json(coverage_json_path, coverage_payload)
        coverage_md_path.write_text(
            build_coverage_matrix_markdown(version, metrics),
            encoding="utf-8",
        )

        math_payload = build_math_assurance_payload(
            version=version,
            nodes=nodes,
            edges=edges,
            entry_node_ids=entry_node_ids,
            quality_metrics=metrics,
        )
        canonical = args.graph_path is not None and (repo_root / args.graph_path).resolve() == (repo_root / "drafts/core/tensor.core.graph.json").resolve()
        criteria_path = args.criteria_path or (Path("drafts/core/entry-evidence-criteria.json") if canonical else None)
        scenarios_path = args.scenarios_path or (Path("drafts/core/scenarios/entry-evidence-cases.json") if canonical else None)
        evidence_gates = None
        if args.graph_path is not None and criteria_path is not None and scenarios_path is not None:
            try:
                evidence_inputs = []
                for path in (criteria_path, scenarios_path):
                    raw = (repo_root / path).read_bytes()
                    provenance["inputs"].append({"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()})
                    evidence_inputs.append(json.loads(raw))
                raw_graph = (repo_root / args.graph_path).read_bytes()
                evidence_gates = assess_evidence(json.loads(raw_graph), hashlib.sha256(raw_graph).hexdigest(), *evidence_inputs)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                evidence_gates = [gate(gid, [f"Evidence input could not be loaded: {exc}"], "notRun") for gid in EVIDENCE_IDS]
        for relative in ("standards/graph-assurance-policy.md", "scripts/graph_assurance_policy.py", "scripts/core_graph_pipeline.py",
                         "scripts/core_graph_math_assurance.py", "scripts/evaluate_entry_scenarios.py", "scripts/lint_core_graph_quality.py",
                         "scripts/restored_evidence.py", "scripts/restoration_assurance.py", "scripts/restore_original_questions.py",
                         "drafts/core/reviews/2026-10-12-restoration/analysis.json"):
            provenance["inputs"].append({"path": relative, "sha256": hashlib.sha256((repo_root / relative).read_bytes()).hexdigest()})
        reference = math_payload["monitoring"]["legacyReferenceThresholds"]
        acceptance = build_acceptance(errors, reference, evidence_gates)
        math_payload["monitoring"]["publishGates"] = acceptance
        quality_json_payload["acceptance"] = acceptance
        if not acceptance["allPassed"]:
            errors.append("Authoring acceptance failed: " + ", ".join(acceptance["failedGateIds"]))
        unmet = set(reference["failedGateIds"]) & DIAGNOSTIC_IDS
        if unmet:
            warnings.append("Historical diagnostic thresholds not met: " + ", ".join(sorted(unmet)) + ". Values remain visible; no score was recalibrated and this is not release authorization.")
        math_payload["provenance"] = provenance
        write_json(coverage_json_path, coverage_payload)
        write_json(math_json_path, math_payload)
        # Include authoring and simulated gate failures in the same quality report.
        write_json(quality_json_path, quality_json_payload)
        quality_md_path.write_text(build_quality_report_markdown(version, errors, warnings, metrics), encoding="utf-8")
        math_md_path.write_text(
            build_math_assurance_markdown(math_payload),
            encoding="utf-8",
        )

        provenance_text = "\n\n## Assessment boundary\n\n" + provenance["scope"] + "\n\n"
        provenance_text += "\n".join(f"- `{item['path']}`: SHA-256 `{item['sha256']}`" for item in provenance["inputs"]) + "\n"
        for report in (quality_md_path, coverage_md_path, math_md_path):
            with report.open("a", encoding="utf-8") as handle:
                handle.write(provenance_text)
        for report in (quality_json_path, quality_md_path, coverage_json_path, coverage_md_path, math_json_path, math_md_path):
            print(f"Wrote {report}")

        if errors:
            print("Graph quality validation failed:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1

        if warnings:
            print("Graph quality warnings:")
            for warning in warnings:
                print(f"- {warning}")

        print("Graph quality validation passed.")
        return 0

    except (ValidationError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
