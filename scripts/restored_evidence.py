"""Bounded supplementary question assessments. Supplied evidence is not verified truth.

The original seven entry paths keep their separate evaluator. Resuming a restored
question re-evaluates its prerequisites; a graph entry is never an authorization
to skip evidence checks. Nothing in a fixture is fetched or executed.
"""
from __future__ import annotations

import copy
import math

from evaluate_entry_scenarios import (bound_assessment, context_ready, downstream_answer,
    equality_answer, fact, instant, match_answer, matches, merge_patch, named, references, validation_answer)

STAGES = ("detect", "validate", "classify", "scope", "correlate", "attribute", "impact", "terminal")


def relation_endpoint(case, selected, criteria, assessment):
    domain = criteria["domains"].get(assessment.get("targetDomain"))
    target = assessment.get("targetRecord")
    target_case = {"bindings": assessment.get("targetSubjects"), "interval": case["interval"]}
    if (domain is None or not isinstance(target, dict) or not matches(target, target_case, domain)
            or assessment.get("sourceRecordId") != selected.get("id")
            or target.get("id") == selected.get("id") or target.get("origin") == selected.get("origin")
            or validation_answer(target, case)[0] != "yes"):
        return None
    return target


def temporal_answer(case, selected, criteria):
    a = case.get("analysis", {}).get("correlation", {})
    hypothesis_id = case.get("analysis", {}).get("hypothesis", {}).get("hypothesisId")
    if (not bound_assessment(a, case, hypothesis_id) or not named(a.get("method"))
            or not references(a.get("evidenceRefs")) or a.get("relationKind") != "bounded-time-coincidence"):
        return "unknown", "A bound temporal relation and its assessment basis are required"
    target = relation_endpoint(case, selected, criteria, a)
    if target is None:
        return "unknown", "Temporal endpoints need separate validated origins and bound subjects"
    tolerance = a.get("toleranceSeconds")
    clocks = [r.get("clockUncertaintySeconds") for r in (selected, target)]
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in [tolerance, *clocks]):
        return "unknown", "Finite nonnegative tolerance and clock uncertainty bounds are required"
    distance = abs((instant(selected["eventTime"]) - instant(target["eventTime"])).total_seconds())
    low, high = max(0, distance - sum(clocks)), distance + sum(clocks)
    if high <= tolerance:
        return "yes", "Even the outer clock bounds meet the declared coincidence tolerance; no causation is inferred"
    if low > tolerance:
        return "no", "Even the closest clock bounds contradict this coincidence tolerance"
    return "unknown", "Clock uncertainty overlaps the coincidence threshold"


def retention_answer(card, case, criteria):
    ledger = case.get("retention", {})
    if ledger.get("knownMissing") is True:
        return "no", "A required assessment is known to be missing from the retained record"
    if (ledger.get("subjects") != case.get("bindings") or ledger.get("interval") != case.get("interval")
            or ledger.get("graphVersion") != criteria["graphVersion"] or ledger.get("closesInvestigation") is not False):
        return "unknown", "Retention must preserve the exact bounds/version and must not claim investigation closure"
    rows = ledger.get("assessments")
    if not isinstance(rows, list) or not rows:
        return "unknown", "No attributed assessments were retained"
    for row in rows:
        if (row.get("nodeId") not in criteria["nodes"] or criteria["nodes"][row["nodeId"]]["domain"] != case["domain"]
                or row.get("answer") not in ("yes", "no", "unknown")
                or not named(row.get("method")) or not named(row.get("rationale"))
                or not references(row.get("evidenceRefs")) or not references(row.get("limitations"))):
            return "unknown", "Each retained answer needs its question, method, references, rationale and limitations"
    focus = ledger.get("focusDispositions", {}).get(card["sourceFacet"])
    if focus not in ("assessed", "open"):
        return "unknown", "The terminal focus must be retained as assessed or explicitly open"
    trace = case.get("retainedTrace", [])
    if any(not any(r.get("nodeId") == s["nodeId"] and r.get("answer") == s["answer"] for r in rows) for s in trace):
        return "no", "The retained record drops or changes a preceding assessment"
    return "yes", "Separate answers, limitations and open questions are retained; this route ends only"


def answer(card, case, criteria):
    """Evaluate an explicitly resumed question, including its evidence prerequisites."""
    domain = criteria["domains"][card["domain"]]
    if (case.get("domain") != card["domain"] or not context_ready(case, domain)
            or case.get("focus") != card["sourceFacet"] or case.get("materialConflict")):
        return "unknown", "Domain, focus, subject/time binding or material counterevidence is unresolved"
    stage, kind = card["stage"], card["assessmentKind"]
    if stage == "terminal":
        return retention_answer(card, case, criteria)
    match, reason, selected = match_answer(case, domain)
    if selected is not None and selected.get("evidenceFacet") != card["sourceFacet"]:
        return "unknown", "The selected material has not been explicitly bound to this evidence facet"
    if stage == "detect":
        return match, reason
    if match != "yes":
        return "unknown", "Resumption requires a matching event record, not an assumed prior answer"
    valid, reason = validation_answer(selected, case)
    if stage == "validate":
        if valid != "yes" or kind == "provenance":
            return valid, reason
        if kind == "baseline":
            baseline = case.get("analysis", {}).get("baseline", {})
            hid = case.get("analysis", {}).get("hypothesis", {}).get("hypothesisId")
            if (not bound_assessment(baseline, case, hid) or not named(baseline.get("comparatorId"))
                    or not references(baseline.get("evidenceRefs"))):
                return "unknown", "The operational comparator, its applicability and evidence basis must be bound"
            return equality_answer(selected, baseline.get("criterion"))
        if kind == "corroboration":
            _, _, other = match_answer(case, domain, independent=True)
            if (other is None or validation_answer(other, case)[0] != "yes"
                    or other.get("evidenceFacet") != card["sourceFacet"]
                    or other.get("id") == selected.get("id") or other.get("origin") == selected.get("origin")):
                return "unknown", "A copy is not independent corroboration; both matching records need a provenance basis"
            left, right = fact(selected, "event.id"), fact(other, "event.id")
            if left is None or right is None or type(left) is not type(right):
                return "unknown", "A declared assessed event discriminator is required on both origins"
            return ("yes", "Independent assessed records agree on the bound event discriminator") if left == right else (
                "no", "Independent event discriminators contradict the claimed corroboration")
    if valid != "yes":
        return "unknown", "Resumption requires accepted event provenance and interpretation"
    role = {"classify": "classification", "scope": "scope", "correlate": "correlation",
            "attribute": "attribution", "impact": "impact"}[stage]
    classification = downstream_answer("classification", case, selected, criteria)
    if stage == "classify":
        return classification
    if classification[0] != "yes":
        return "unknown", "Resumption requires a supported single technical hypothesis with evaluated alternatives"
    scope = downstream_answer("scope", case, selected, criteria)
    if stage == "scope":
        if scope[0] != "yes" or kind == "scope-bound":
            return scope
        a = case["analysis"]["scope"]
        if kind == "additional-entities":
            source = case["bindings"][domain["bindings"][0]]
            extra = [e for e in a["entities"] if e["disposition"] == "included"
                     and (e["domain"], e["subjectId"]) != (case["domain"], source)]
            return ("yes", "Additional named entities have evidenced inclusions; population completeness remains open") if extra else (
                "no", "The recorded scope contains no evidenced additional inclusion")
        dependency = case.get("analysis", {}).get("dependency", {})
        hid = case["analysis"]["hypothesis"]["hypothesisId"]
        if (not bound_assessment(dependency, case, hid) or not named(dependency.get("method"))
                or not references(dependency.get("evidenceRefs"))
                or dependency.get("direction") not in ("upstream", "downstream")
                or dependency.get("claimKind") != "documented-dependency"):
            return "unknown", "Dependency direction, documented relation and bound evidence basis are required"
        target = relation_endpoint(case, selected, criteria, dependency)
        if target is None:
            return "unknown", "The proposed dependency endpoints are not independently validated"
        target_domain = criteria["domains"][dependency["targetDomain"]]
        target_subject = dependency["targetSubjects"][target_domain["bindings"][0]]
        source_subject = case["bindings"][domain["bindings"][0]]
        source_fact, target_fact = fact(selected, "dependency.source"), fact(target, "dependency.target")
        if source_fact is None or target_fact is None:
            return "unknown", "Dependency endpoint discriminators are missing or unassessed"
        if source_fact != source_subject or target_fact != target_subject:
            return "no", "Assessed dependency endpoint discriminators contradict the named relation"
        return "yes", "An explicit evidenced dependency is included; shared time or identifiers alone do not establish it"
    if scope[0] != "yes":
        return "unknown", "Resumption requires a recorded bounded scope with evidence-backed entity dispositions"
    if stage == "correlate" and kind == "temporal":
        return temporal_answer(case, selected, criteria)
    if stage == "attribute" and kind == "behavior-pattern":
        pattern = case.get("analysis", {}).get("pattern", {})
        hid = case["analysis"]["hypothesis"]["hypothesisId"]
        if (not bound_assessment(pattern, case, hid) or pattern.get("claimKind") != "technical-behavior-pattern"
                or not named(pattern.get("patternId")) or not references(pattern.get("alternatives"))
                or not references(pattern.get("evidenceRefs"))):
            return "unknown", "A technical behavior pattern, discriminator and competing explanations are required; actor intent is separate"
        if pattern.get("criterion", {}).get("equals") != pattern["patternId"]:
            return "unknown", "The declared criterion does not test the named pattern"
        return equality_answer(selected, pattern.get("criterion"))
    if stage == "impact" and kind == "additional-impact":
        a = case.get("analysis", {}).get("additionalEffect", {})
        hid = case["analysis"]["hypothesis"]["hypothesisId"]
        if (not bound_assessment(a, case, hid) or not named(a.get("method"))
                or not references(a.get("evidenceRefs")) or a.get("relationKind") != "shared-identifier"):
            return "unknown", "The additional effect subject needs an explicitly assessed source relationship"
        target = relation_endpoint(case, selected, criteria, a)
        if target is None:
            return "unknown", "The additional effect subject lacks a separately validated bound record"
        source_fact, target_fact = fact(selected, a.get("sourceFact")), fact(target, a.get("targetFact"))
        if source_fact is None or target_fact is None or type(source_fact) is not type(target_fact) or source_fact != target_fact:
            return "unknown", "A validated link to the additional subject has not been established"
        target_domain = criteria["domains"][a["targetDomain"]]
        target_subject = a["targetSubjects"][target_domain["bindings"][0]]
        if a["targetDomain"] == case["domain"] and target_subject == case["bindings"][domain["bindings"][0]]:
            return "unknown", "The effect assessment must bind an additional subject"
        additional = a.get("assessment", {})
        if (additional.get("bindings") != a["targetSubjects"] or additional.get("interval") != case["interval"]
                or additional.get("domain") != a["targetDomain"]):
            return "unknown", "The additional metric context disagrees with the linked endpoint"
        return downstream_answer("impact", additional, target, criteria)
    return downstream_answer(role, case, selected, criteria)


def run_cases(graph, criteria, suite):
    if suite["graphVersion"] != graph["version"] or criteria["graphVersion"] != graph["version"]:
        raise ValueError("Restoration graph, criteria and scenario versions disagree")
    results = []
    for case in suite["restoredCases"]:
        card = criteria["nodes"][case["nodeId"]]
        actual, reason = answer(card, case_evidence(suite, case), criteria)
        results.append({"caseId": case["id"], "nodeId": case["nodeId"], "answer": actual,
                        "reason": reason, "passed": actual == case["expectedAnswer"]})
    for case in suite.get("restoredPaths", []):
        edges = {(e["source"], e["decision"]): e["target"] for e in graph["edges"]}
        current, trace = case["entry"], []
        initial_bounds = None
        seen = set()
        while True:
            if current in seen:
                raise ValueError("Restored route contains a cycle")
            seen.add(current)
            card = criteria["nodes"][current]
            evidence = case_evidence(suite, case["evidenceByNode"][current])
            bounds = (evidence.get("domain"), evidence.get("bindings"), evidence.get("interval"))
            if initial_bounds is not None and bounds != initial_bounds:
                raise ValueError("A restored path silently changed its bound domain, subjects or interval")
            initial_bounds = copy.deepcopy(bounds)
            evidence["retainedTrace"] = trace
            actual, reason = answer(card, evidence, criteria)
            trace.append({"nodeId": current, "answer": actual})
            if card["stage"] == "terminal":
                break
            current = edges[(current, actual)]
        results.append({"caseId": case["id"], "trace": trace,
                        "passed": [[s["nodeId"], s["answer"]] for s in trace] == case["expectedTrace"]})
    return results


def case_evidence(suite, case):
    result = copy.deepcopy(suite["restoredFixtures"][case["evidenceRef"]])
    edits = case.get("evidenceEdits", [])
    if not isinstance(edits, list) or len(edits) > 100:
        raise ValueError("Fixture evidence edits must be a bounded list")
    for edit in edits:
        path = edit.get("path")
        if (not isinstance(path, list) or not 1 <= len(path) <= 20
                or any(type(p) not in (str, int) for p in path) or edit.get("op") not in ("set", "remove")):
            raise ValueError("Invalid fixture evidence path/edit")
        parent = result
        for part in path[:-1]:
            parent = parent[part]
        if edit["op"] == "set":
            parent[path[-1]] = copy.deepcopy(edit["value"])
        else:
            del parent[path[-1]]
    return result
