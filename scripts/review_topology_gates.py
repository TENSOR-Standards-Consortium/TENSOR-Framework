#!/usr/bin/env python3
"""Reproduce topology-gate counterexamples without modifying any graph artifact."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from core_graph_math_assurance import build_math_assurance_payload, _reachable_ratio
from core_graph_pipeline import DOMAINS, validate_and_measure
from graph_assurance_policy import assess_evidence

ROOT = Path(__file__).resolve().parents[1]


def snapshot(graph):
    errors, _, metrics = validate_and_measure(graph["nodes"], graph["edges"], graph["entryNodeIds"], [])
    payload = build_math_assurance_payload(graph["version"], graph["nodes"], graph["edges"], graph["entryNodeIds"], metrics)
    theories = {t["id"]: t["metrics"] for t in payload["theories"]}
    return {"scores": {k: v for k, v in payload["summary"].items() if k != "recommendations"},
            "reference": payload["monitoring"]["legacyReferenceThresholds"],
            "maximumBetweennessShare": theories["centrality"]["betweennessCentralization"],
            "targetedReachability": theories["robustness"]["targetedReachabilityAt5Percent"],
            "crossDomainRatio": metrics["crossDomainRatio"], "authoringErrors": errors}


def experiments(graph, criteria, suite):
    baseline = snapshot(graph)
    nonsense = copy.deepcopy(graph)
    for node in nonsense["nodes"]:
        node["text"] = "Does this deliberately meaningless predicate establish anything?"
    nonsense_metrics = snapshot(nonsense)
    invalid_cards = assess_evidence(nonsense, "modified-in-memory", criteria, suite)

    scattered = copy.deepcopy(graph)
    for index, node in enumerate(scattered["nodes"]):
        node["category"] = DOMAINS[index % len(DOMAINS)]
    scattered_metrics = snapshot(scattered)

    replicated = copy.deepcopy(graph)
    for node in graph["nodes"]:
        clone = copy.deepcopy(node)
        clone["id"] = f"Q{1000 + int(node['id'][1:])}"
        replicated["nodes"].append(clone)
    for edge in graph["edges"]:
        source = f"Q{1000 + int(edge['source'][1:])}"
        target = f"Q{1000 + int(edge['target'][1:])}"
        replicated["edges"].append({"id": f"{source}-{edge['decision']}-{target}",
                                    "source": source, "target": target, "decision": edge["decision"]})
    replicated["entryNodeIds"] += [f"Q{1000 + int(n[1:])}" for n in graph["entryNodeIds"]]
    replicated_metrics = snapshot(replicated)

    all_nodes = {"Q1", "Q2", "Q3"}
    safe_chain = {"Q1": ["Q2"], "Q2": ["Q3"]}
    unsafe_bypass = {"Q1": ["Q2", "Q3"], "Q2": ["Q3"]}
    return {
        "scope": "In-memory counterexamples, not proposed graph changes, empirical investigator outcomes or schema conformance proofs",
        "baseline": baseline,
        "meaninglessPredicates": {"metrics": nonsense_metrics,
                                  "scoresUnchanged": nonsense_metrics["scores"] == baseline["scores"],
                                  "failedEvidenceChecks": [g["id"] for g in invalid_cards if not g["passed"]],
                                  "interpretation": "Historical scores cannot detect loss of predicate meaning; exact public-card binding rejects this unreviewed edit"},
        "scatteredDomainLabels": {"metrics": scattered_metrics,
                                  "interpretation": "Unsupported label changes meet the cross-domain quota and improve its derived routing score while violating authoring coherence"},
        "identicalRouteReplication": {"metrics": replicated_metrics,
                                      "interpretation": "An identical disconnected copy changes no original route but halves maximum betweenness share and crosses the 0.02 threshold"},
        "deletedPrerequisiteToy": {"remainingReachabilityWithoutBypass": _reachable_ratio(["Q1"], safe_chain, {"Q2"}, all_nodes),
                                   "remainingReachabilityWithUnsafeBypass": _reachable_ratio(["Q1"], unsafe_bypass, {"Q2"}, all_nodes),
                                   "interpretation": "Reachability after deleting a prerequisite rewards an unsafe shortcut; use unknown evidence routes instead"},
        "duplicateFailure": {"robustnessScore": baseline["scores"]["robustnessScore"],
                             "100TimesTargetedReachability": round(100 * baseline["targetedReachability"], 6)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New receipt path outside releases; refuses overwrite")
    args = parser.parse_args()
    paths = [ROOT / name for name in ("drafts/core/tensor.core.graph.json", "drafts/core/entry-evidence-criteria.json", "drafts/core/scenarios/entry-evidence-cases.json")]
    receipt = experiments(*(json.loads(p.read_bytes()) for p in paths))
    receipt["inputs"] = [{"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
    for name in ("scripts/review_topology_gates.py", "scripts/core_graph_math_assurance.py", "scripts/core_graph_pipeline.py", "scripts/graph_assurance_policy.py", "scripts/evaluate_entry_scenarios.py", "standards/graph-assurance-policy.md"):
        receipt["inputs"].append({"path": name, "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()})
    target = args.output.resolve()
    releases = (ROOT / "releases").resolve()
    if target == releases or releases in target.parents:
        parser.error("Counterexample receipts must not write into releases")
    with target.open("x") as handle:
        json.dump(receipt, handle, indent=2)
        handle.write("\n")
    print("Recorded topology counterexamples; graph artifacts were not modified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
