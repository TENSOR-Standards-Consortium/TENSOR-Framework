#!/usr/bin/env python3
"""Offline, author-side evaluation of the bounded entry-evidence review cases.

Normalized observations and provenance assessments are supplied claims. This is
neither a log parser nor an evidence-truth, authorization, or Core conformance
validator. Nothing is fetched or executed from case content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COVERAGE_FLAGS = (
    "applicableLogging", "continuousCollection", "retentionComplete",
    "clockBounded", "searchComplete", "integrityAssessed",
)


def instant(value):
    if not isinstance(value, str):
        return None
    if re.search(r"\.\d{7,}", value):
        return None  # Do not silently round evidence time beyond this test tool's precision.
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def context_ready(case, domain):
    interval = case.get("interval", {})
    start, end = instant(interval.get("start")), instant(interval.get("end"))
    return (all(isinstance(case.get("bindings", {}).get(k), str) and case["bindings"][k].strip() for k in domain["bindings"])
            and start is not None and end is not None and start < end)


def matches(record, case, domain):
    if not context_ready(case, domain):
        return False
    when = instant(record.get("eventTime"))
    return (all(record.get("subjects", {}).get(k) == case["bindings"][k] for k in domain["bindings"])
            and when is not None
            and instant(case["interval"]["start"]) <= when < instant(case["interval"]["end"]))


def match_answer(case, domain, independent=False):
    group = case["independent" if independent else "primary"]
    if not context_ready(case, domain):
        return "unknown", "Subject or time binding is unresolved", None
    if case.get("materialConflict"):
        return "unknown", "Material counterevidence is unresolved", None
    if group.get("accessible") is not True or group.get("searched") is not True:
        return "unknown", "Evidence is unavailable or the search is incomplete", None
    uncertain = False
    for record in group.get("records", []):
        if not instant(record.get("eventTime")):
            uncertain = True
            continue
        if not matches(record, case, domain):
            continue
        if independent and (not record.get("origin") or record["origin"] == case.get("primaryOrigin")):
            uncertain = True
            continue
        return "yes", "A record matches the exact bound subjects and interval", record
    return ("unknown", "Record time or independent lineage is unresolved", None) if uncertain else (
        "no", "The completed search found no matching record in the examined material", None)


def validation_answer(record, case):
    if record is None or case.get("materialConflict"):
        return "unknown", "No uncontradicted matching record was selected"
    assessments = [record.get("provenanceAssessment"), record.get("interpretationAssessment")]
    if "rejected" in assessments:
        return "no", "A supplied provenance or interpretation assessment rejects the selected record"
    refs = record.get("assessmentEvidenceRefs")
    if (assessments == ["accepted", "accepted"] and record.get("origin")
            and isinstance(refs, list) and refs and all(isinstance(ref, str) and ref.strip() for ref in refs)):
        return "yes", "Supplied provenance and interpretation assessments cite a supporting basis"
    return "unknown", "The provenance or event interpretation basis is incomplete"


def exclusion_answer(case, domain):
    if not context_ready(case, domain) or case.get("materialConflict"):
        return "unknown", "Bound context or material counterevidence is unresolved"
    coverage = case.get("coverage", {})
    if coverage.get("subjects") != case["bindings"] or coverage.get("interval") != case["interval"]:
        return "unknown", "No coverage assessment is bound to these exact subjects and interval"
    if any(coverage.get(k) is False for k in COVERAGE_FLAGS):
        return "no", "A known logging, collection, retention, clock, search, or integrity gap prevents exclusion"
    if not coverage.get("evidenceRefs") or any(coverage.get(k) is not True for k in COVERAGE_FLAGS):
        return "unknown", "Complete applicable evidence coverage has not been established"
    for group in (case["primary"], case["independent"]):
        if any(matches(record, case, domain) for record in group.get("records", [])):
            return "no", "A matching record is counterevidence to an absence claim; reassessment is required"
    return "yes", "The supplied applicable coverage/search basis supports this bounded exclusion only"


def evaluate_case(graph, criteria, case):
    domain = criteria["domains"][case["domain"]]
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = {(e["source"], e["decision"]): e["target"] for e in graph["edges"]}
    current, selected = domain["entry"], None
    trace = []
    seen = set()
    while current in criteria["nodes"]:
        if current in seen:
            raise ValueError("Entry route contains a cycle")
        seen.add(current)
        card = criteria["nodes"][current]
        if nodes[current]["category"] != case["domain"] or card["domain"] != case["domain"]:
            raise ValueError("The entry assessment changed domain without a bound evidentiary relationship")
        role = card["role"]
        if role in ("entry", "alternate"):
            answer, reason, selected = match_answer(case, domain, role == "alternate")
        elif role in ("primaryValidation", "independentValidation"):
            answer, reason = validation_answer(selected, case)
        elif role == "exclusion":
            answer, reason = exclusion_answer(case, domain)
        elif role == "unresolved":
            answer, reason = "yes", "The prior assessment retained a material evidence, context, or verification limitation"
        else:
            raise ValueError(f"Unimplemented review role: {role}")
        trace.append({"nodeId": current, "answer": answer, "reason": reason,
                      "recordId": selected.get("id") if selected else None})
        if nodes[current]["archetype"] == "terminal":
            return {"caseId": case["id"], "trace": trace,
                    "state": "bounded-exclusion" if role == "exclusion" and answer == "yes" else "unresolved"}
        current = edges[(current, answer)]
    if current not in domain["positiveReviewBoundaries"]:
        raise ValueError(f"Route escaped the reviewed entry boundary at {current}")
    return {"caseId": case["id"], "trace": trace, "state": "positive-review-boundary", "nextQuestionId": current}


def run_cases(graph, criteria, suite):
    if graph["version"] != criteria["graphVersion"] or suite["graphVersion"] != graph["version"]:
        raise ValueError("Graph, criteria and scenario versions disagree")
    results = []
    for case in suite["cases"]:
        result = evaluate_case(graph, criteria, case)
        actual = [[t["nodeId"], t["answer"]] for t in result["trace"]]
        result["passed"] = actual == case["expectedTrace"] and result["state"] == case["expectedState"]
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional new receipt path outside releases; refuses overwrite")
    args = parser.parse_args()
    paths = [ROOT / "drafts/core/tensor.core.graph.json", ROOT / "drafts/core/entry-evidence-criteria.json",
             ROOT / "drafts/core/scenarios/entry-evidence-cases.json"]
    graph, criteria, suite = [json.loads(p.read_text()) for p in paths]
    if hashlib.sha256(paths[0].read_bytes()).hexdigest() != criteria.get("graphSha256"):
        parser.error("The exact graph bytes do not match the public evidence-criteria pin")
    results = run_cases(graph, criteria, suite)
    receipt = {"scope": "Offline author-side scenario evaluation; source reports and supplied evidence assessments are not independently verified",
               "graphVersion": graph["version"], "inputs": [{"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],
               "caseCount": len(results), "passed": sum(r["passed"] for r in results), "results": results}
    if args.output:
        target = args.output.resolve()
        if target == (ROOT / "releases").resolve() or (ROOT / "releases").resolve() in target.parents:
            parser.error("Scenario receipts cannot overwrite releases")
        with target.open("x") as handle:
            json.dump(receipt, handle, indent=2)
            handle.write("\n")
    print(f"Entry scenarios: {receipt['passed']}/{receipt['caseCount']} passed")
    for result in results:
        if not result["passed"]:
            print(json.dumps(result))
    return 0 if receipt["passed"] == receipt["caseCount"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
