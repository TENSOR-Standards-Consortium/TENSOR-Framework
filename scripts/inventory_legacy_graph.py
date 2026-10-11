#!/usr/bin/env python3
"""Inventory a legacy graph for human review without migrating or modifying it.

The deterministic inventory preserves parsed legacy items and proposes source-scoped
identifiers. It does not create investigation records or assert Core conformance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any

MAPPING_REVISION = "legacy-inventory-1"
REVIEW_ITEMS = [
    "proposition-and-answer-criteria",
    "evidence-requirements-and-unknown-reasons",
    "subject-time-and-typed-parameter-context",
    "applicability",
    "public-profile-placement",
]


def unwrap(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Every legacy node and edge must be an object.")
    payload = item.get("data", item)
    if not isinstance(payload, dict):
        raise ValueError("Wrapped legacy data must be an object.")
    return payload


def build_inventory(source_bytes: bytes, source_id: str) -> dict[str, Any]:
    if not isinstance(source_id, str) or not urlsplit(source_id).scheme or any(c.isspace() for c in source_id):
        raise ValueError("source-id must be a non-empty absolute URI without whitespace.")
    graph = json.loads(source_bytes)
    if not isinstance(graph, dict):
        raise ValueError("Legacy graph must be a JSON object.")
    version = graph.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("Legacy graph must declare a non-empty version.")
    if not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges"), list):
        raise ValueError("Legacy graph must contain nodes and edges arrays.")
    digest = hashlib.sha256(source_bytes).hexdigest()
    scope = json.dumps([MAPPING_REVISION, source_id, version, digest], separators=(",", ":"))

    def scoped_id(kind: str, legacy_id: str) -> str:
        name = json.dumps([scope, kind, legacy_id], separators=(",", ":"))
        return uuid.uuid5(uuid.NAMESPACE_URL, name).urn

    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    for kind, items, indexed in (("question", graph["nodes"], nodes), ("transition", graph["edges"], edges)):
        for item in items:
            payload = unwrap(item)
            item_id = payload.get("id")
            if not isinstance(item_id, str) or not item_id:
                raise ValueError(f"Each legacy {kind} must have a non-empty string id.")
            if item_id in indexed:
                raise ValueError(f"Duplicate {kind} id {item_id!r}; ambiguous mappings require source repair.")
            indexed[item_id] = item

    questions = []
    domain_counts = Counter()
    for legacy_id in sorted(nodes):
        item = nodes[legacy_id]
        payload = unwrap(item)
        domain_counts[str(payload.get("category", "undeclared"))] += 1
        review = list(REVIEW_ITEMS)
        if not isinstance(payload.get("text"), str) or not payload["text"].strip():
            review.append("missing-question-text")
        questions.append({
            "legacyId": legacy_id,
            "proposedId": scoped_id("question", legacy_id),
            "status": "needsReview",
            "needsReview": review,
            "legacyItem": item,
        })

    transitions = []
    unresolved_references = []
    for legacy_id in sorted(edges):
        item = edges[legacy_id]
        payload = unwrap(item)
        source, target, decision = payload.get("source"), payload.get("target"), payload.get("decision")
        review = ["guard-semantics-and-source-target-context", "revisit-and-cycle-policy"]
        for role, node_id in (("source", source), ("target", target)):
            if not isinstance(node_id, str) or node_id not in nodes:
                review.append(f"unresolved-{role}")
                unresolved_references.append({"edgeId": legacy_id, "role": role, "legacyNodeId": node_id})
        if decision not in ("yes", "no", "unknown"):
            review.append("unsupported-guard")
        transitions.append({
            "legacyId": legacy_id,
            "proposedId": scoped_id("transition", legacy_id),
            "sourceProposedId": scoped_id("question", source) if isinstance(source, str) and source in nodes else None,
            "targetProposedId": scoped_id("question", target) if isinstance(target, str) and target in nodes else None,
            "status": "needsReview",
            "needsReview": review,
            "legacyItem": item,
        })
    entry_ids = graph.get("entryNodeIds", [])
    if not isinstance(entry_ids, list):
        raise ValueError("Legacy entryNodeIds, when present, must be an array.")
    for entry_id in entry_ids:
        if not isinstance(entry_id, str) or entry_id not in nodes:
            unresolved_references.append({"role": "entry", "legacyNodeId": entry_id})

    return {
        "artifactType": "legacyMigrationInventory",
        "mappingRevision": MAPPING_REVISION,
        "migrationPerformed": False,
        "candidateConformance": "notAssessed",
        "source": {"id": source_id, "version": version, "digest": {"algorithm": "sha256", "value": digest},
                   "schemaVersion": graph.get("schemaVersion"), "byteLength": len(source_bytes)},
        "identityPolicy": "Proposed IDs are stable only for this mapping revision, source ID, version, exact-byte digest and legacy ID. They are review handles, not approved Core identifiers or semantic-equivalence claims.",
        "summary": {"questions": len(questions), "transitions": len(transitions), "entryNodes": len(entry_ids),
                    "questionsNeedingReview": len(questions), "transitionsNeedingReview": len(transitions),
                    "unresolvedReferences": len(unresolved_references), "legacyCategoryCounts": dict(sorted(domain_counts.items()))},
        "legacyTopLevelMetadata": {key: value for key, value in graph.items() if key not in ("nodes", "edges")},
        "questionMappings": questions,
        "transitionMappings": transitions,
        "unresolvedReferences": unresolved_references,
        "losses": [
            {"kind": "source-formatting", "description": "The inventory preserves parsed legacy fields, not their original JSON whitespace, key order or exact bytes. The source file is unchanged; its digest pins the original artifact."},
            {"kind": "semantic-upgrade-not-performed", "description": "No legacy label, field, extension or yes/no/unknown route has been reinterpreted as approved Core semantics."},
        ],
        "notReconstructableFromGraphAlone": [
            "historical-actors-and-attribution", "question-instances-and-context", "evidence-and-observations",
            "assessments-and-disagreements", "policy-and-authority", "decisions-and-action-history",
        ],
        "needsReview": [
            "Approve question propositions, mutually exclusive answer criteria, applicability and evidence requirements.",
            "Review source-scoped IDs and any cross-version semantic-equivalence claims.",
            "Declare public profiles and legacy extension meanings; assess the legacy DAG restriction separately from Core cycle support.",
            "Create a new definition artifact and version only after review; never overwrite a released source.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-path", required=True, type=Path)
    parser.add_argument("--source-id", required=True, help="Stable absolute URI identifying the legacy definition series.")
    parser.add_argument("--output", required=True, type=Path, help="New JSON inventory file; input is never modified.")
    args = parser.parse_args()
    try:
        source, destination = args.graph_path.resolve(), args.output.resolve()
        releases = Path(__file__).resolve().parent.parent / "releases"
        if source == destination:
            raise ValueError("Output must not overwrite the source graph.")
        if destination == releases or releases in destination.parents:
            raise ValueError("Inventory output must be outside preserved releases.")
        payload = build_inventory(source.read_bytes(), args.source_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation avoids accidental loss of an earlier review inventory.
        with destination.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        print(f"Wrote {destination}: {payload['summary']['questions']} questions, {payload['summary']['transitions']} transitions; all require review. No migration performed.")
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
