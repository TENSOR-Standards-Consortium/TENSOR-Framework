"""Bounded supplementary question assessments. Supplied evidence is not verified truth.

The original seven entry paths keep their separate evaluator. Resuming a restored
question re-evaluates its prerequisites; a graph entry is never an authorization
to skip evidence checks. Nothing in a fixture is fetched or executed.
"""
from __future__ import annotations

import copy
import math

from evaluate_entry_scenarios import (bound_assessment, context_ready, downstream_answer,
    equality_answer, fact, instant, match_answer, matches, merge_patch, named, references, validation_answer, subject_identity)

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
    start, end = instant(case["interval"]["start"]), instant(case["interval"]["end"])
    for record, uncertainty in zip((selected, target), clocks):
        when = instant(record["eventTime"])
        if (when - start).total_seconds() < uncertainty or (end - when).total_seconds() <= uncertainty:
            return "unknown", "A source clock bound crosses the investigation interval; event membership is unresolved"
    distance = abs((instant(selected["eventTime"]) - instant(target["eventTime"])).total_seconds())
    low, high = max(0, distance - sum(clocks)), distance + sum(clocks)
    if high <= tolerance:
        return "yes", "Even the outer clock bounds meet the declared coincidence tolerance; no causation is inferred"
    if low > tolerance:
        return "no", "Even the closest clock bounds contradict this coincidence tolerance"
    return "unknown", "Clock uncertainty overlaps the coincidence threshold"


def retention_answer(card, case, criteria):
    ledger = case.get("retention", {})
    if (ledger.get("subjects") != case.get("bindings") or ledger.get("interval") != case.get("interval")
            or ledger.get("graphVersion") != criteria["graphVersion"] or ledger.get("closesInvestigation") is not False):
        return "unknown", "Retention must preserve the exact bounds/version and must not claim investigation closure"
    if ledger.get("knownMissing") is True:
        return "no", "A required assessment is known to be missing from this bound retained record"
    rows = ledger.get("assessments")
    if not isinstance(rows, list) or not rows:
        return "unknown", "No attributed assessments were retained"
    prerequisites = ledger.get("prerequisiteAssessments", [])
    if not isinstance(prerequisites, list):
        return "unknown", "Retained prerequisite assessments must be separate structured records"
    rows = rows + prerequisites
    seen = {}
    hypothesis_id = case.get("analysis", {}).get("hypothesis", {}).get("hypothesisId")
    for row in rows:
        if (row.get("nodeId") not in criteria["nodes"] or criteria["nodes"][row["nodeId"]]["domain"] != case["domain"]
                or row.get("subjects") != case.get("bindings") or row.get("interval") != case.get("interval")
                or row.get("hypothesisId") != hypothesis_id
                or row.get("answer") not in ("yes", "no", "unknown")
                or not named(row.get("method")) or not named(row.get("rationale"))
                or not references(row.get("evidenceRefs")) or not references(row.get("limitations"))):
            return "unknown", "Each retained answer needs its question, method, references, rationale and limitations"
        if row["nodeId"] in seen and seen[row["nodeId"]] != row["answer"]:
            return "unknown", "Conflicting answers for one versioned question need an explicit separate assessment history"
        seen[row["nodeId"]] = row["answer"]
    focus_name = card.get("sourceFacet", case.get("focus"))
    focus = ledger.get("focusDispositions", {}).get(focus_name)
    if focus not in ("assessed", "open"):
        return "unknown", "The terminal focus must be retained as assessed or explicitly open"
    if focus == "assessed" and not any(criteria["nodes"][r["nodeId"]].get("sourceFacet") == focus_name
                                      and criteria["nodes"][r["nodeId"]].get("stage") != "terminal" for r in rows):
        return "unknown", "An assessed focus needs a retained assessment of that focus"
    trace = case.get("retainedTrace", [])
    if any(not any(r.get("nodeId") == s["nodeId"] and r.get("answer") == s["answer"] for r in rows) for s in trace):
        return "no", "The retained record drops or changes a preceding assessment"
    return "yes", "Separate answers, limitations and open questions are retained; this route ends only"


def answer(card, case, criteria):
    """Evaluate an explicitly resumed question, including its evidence prerequisites."""
    if card.get("role") != "restored":
        return base_resumption_answer(card, case, criteria)
    domain = criteria["domains"][card["domain"]]
    if (case.get("domain") != card["domain"] or not context_ready(case, domain) or not named(case.get("focus"))
            or (card["stage"] != "terminal" and case.get("focus") != card["sourceFacet"]) or case.get("materialConflict")):
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
            return (valid, reason) if kind == "provenance" else ("unknown", "Comparator or corroboration needs an accepted event record; rejected provenance cannot test this proposition")
        if kind == "baseline":
            baseline = case.get("analysis", {}).get("baseline", {})
            hid = case.get("analysis", {}).get("hypothesis", {}).get("hypothesisId")
            if (not bound_assessment(baseline, case, hid) or not named(baseline.get("comparatorId"))
                    or not references(baseline.get("evidenceRefs"))):
                return "unknown", "The operational comparator, its applicability and evidence basis must be bound"
            return equality_answer(selected, baseline.get("criterion"))
        if kind == "corroboration":
            group = case.get("independent", {})
            if group.get("accessible") is not True or group.get("searched") is not True:
                return "unknown", "The separately originating material is unavailable or its examination incomplete"
            candidates = [r for r in group.get("records", []) if matches(r, case, domain)
                          and validation_answer(r, case)[0] == "yes" and r.get("evidenceFacet") == card["sourceFacet"]
                          and r.get("id") != selected.get("id") and r.get("origin") != selected.get("origin")]
            if not candidates:
                return "unknown", "A copy is not independent corroboration; both matching records need a provenance basis"
            left, rights = fact(selected, "event.id"), [fact(r, "event.id") for r in candidates]
            if left is None or any(right is None or type(left) is not type(right) for right in rights):
                return "unknown", "A declared assessed event discriminator is required on both origins"
            agrees = [left == right for right in rights]
            if any(agrees) and not all(agrees):
                return "unknown", "Accepted independent observations disagree; witness ordering cannot resolve material counterevidence"
            return ("yes", "Independent assessed records agree on the bound event discriminator") if all(agrees) else (
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
                     and ((e["domain"], e["subjectId"]) != (case["domain"], source)
                          or ("subjects" in e and subject_identity(criteria, e["domain"], e["subjects"]) != subject_identity(criteria, case["domain"], case["bindings"])))]
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
        for endpoint, prefix, binding_domain, bindings in ((selected, "source", case["domain"], case["bindings"]),
                                            (target, "target", dependency["targetDomain"], dependency["targetSubjects"])):
            for field in criteria["domains"][binding_domain]["bindings"]:
                expected = bindings[field]
                actual = fact(endpoint, f"dependency.{prefix}.{field}")
                if actual is None:
                    return "unknown", "The documented dependency must bind every endpoint field"
                if type(actual) is not type(expected) or actual != expected:
                    return "no", "The documented dependency contradicts the full endpoint identity"
        ids = [fact(r, "dependency.relationId") for r in (selected, target)]
        directions = [fact(r, "dependency.direction") for r in (selected, target)]
        if any(not named(v) for v in ids + directions):
            return "unknown", "Endpoint identities alone do not establish a documented directional dependency"
        if ids[0] != ids[1] or directions != [dependency["direction"]] * 2:
            return "no", "Assessed dependency relationship or direction contradicts the proposed relation"
        dispositions = [e["disposition"] for e in a["entities"] if e["domain"] == dependency["targetDomain"]
                        and e["subjectId"] == target_subject
                        and (("subjects" in e and subject_identity(criteria, e["domain"], e["subjects"]) == subject_identity(criteria, dependency["targetDomain"], dependency["targetSubjects"])) or ("subjects" not in e
                             and (dependency["targetDomain"] != case["domain"] or target_subject != source_subject)))]
        if "excluded" in dispositions:
            return "no", "The proposed bounded scope excludes the dependency target"
        if "included" not in dispositions:
            return "unknown", "The dependency target has no evidenced scope inclusion"
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
        if a["targetDomain"] == case["domain"] and subject_identity(criteria, case["domain"], a["targetSubjects"]) == subject_identity(criteria, case["domain"], case["bindings"]):
            return "unknown", "The effect assessment must bind an additional subject"
        additional = a.get("assessment", {})
        if (additional.get("bindings") != a["targetSubjects"] or additional.get("interval") != case["interval"]
                or additional.get("domain") != a["targetDomain"]):
            return "unknown", "The additional metric context disagrees with the linked endpoint"
        return downstream_answer("impact", additional, target, criteria)
    return downstream_answer(role, case, selected, criteria)


def base_resumption_answer(card, case, criteria):
    """Explicit adapter to the existing parameterized base; never inherit an answer."""
    domain = criteria["domains"][card["domain"]]
    if case.get("domain") != card["domain"] or not context_ready(case, domain) or not named(case.get("focus")):
        return "unknown", "A generic resumption retains the explicit facet, domain and complete subject/time context"
    role = card["role"]
    if role in ("assessed", "refuted", "unresolved", "exclusion"):
        retained = retention_answer(card, case, criteria)
        if retained[0] != "yes":
            return retained
        if role == "unresolved":
            rows = case["retention"]["assessments"]
            if not any(r["answer"] == "unknown" or (r["answer"] == "no" and
                       (criteria["nodes"][r["nodeId"]].get("role") in ("primaryValidation", "independentValidation", "scope")
                        or criteria["nodes"][r["nodeId"]].get("assessmentKind") in ("provenance", "scope-bound"))) for r in rows):
                return "unknown", "An unresolved ending needs a retained unresolved assessment, not only supported answers"
            return retained
        if role == "exclusion":
            from evaluate_entry_scenarios import exclusion_answer
            return exclusion_answer(case, domain)
    matched, reason, selected = match_answer(case, domain)
    if matched != "yes" or selected.get("evidenceFacet") != case["focus"]:
        return "unknown", "The generic target needs its own facet-bound matching event record"
    validated = validation_answer(selected, case)
    if role == "primaryValidation":
        return validated
    if validated[0] != "yes":
        return "unknown", "Generic resumption needs accepted event provenance and interpretation"
    classification = downstream_answer("classification", case, selected, criteria)
    if role == "classification":
        return classification
    if role == "refuted":
        return ("yes", "Retain the exact refuted hypothesis, without refuting the event") if classification[0] == "no" else (
            "unknown", "No refutation of the bound hypothesis was demonstrated")
    if classification[0] != "yes":
        return "unknown", "Generic resumption needs a supported bound technical hypothesis"
    scoped = downstream_answer("scope", case, selected, criteria)
    if role == "scope":
        return scoped
    if scoped[0] != "yes":
        return "unknown", "Generic resumption needs an independently assessed bounded scope"
    if role == "assessed":
        stages = {"classification": "classify", "correlation": "correlate", "attribution": "attribute"}
        retained = {}
        for row in case["retention"]["assessments"] + case["retention"].get("prerequisiteAssessments", []):
            previous = criteria["nodes"][row["nodeId"]]
            if previous.get("assessmentKind") in ("additional-entities", "dependencies", "behavior-pattern", "additional-impact"):
                continue  # Distinct assessment families cannot substitute mandatory findings.
            stage = previous.get("stage", stages.get(previous["role"], previous["role"]))
            retained.setdefault(stage, []).append(row["answer"])
        if ("yes" not in retained.get("classify", []) or "yes" not in retained.get("scope", [])
                or not all(stage in retained for stage in ("correlate", "attribute", "impact"))):
            return "unknown", "The qualified handoff must retain separate hypothesis, scope, relation, source and effect assessments"
        return "yes", "Separate retained answers and prerequisites support a qualified handoff only"
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
        from investigative_routing import continuation_edges
        edges = {(e["source"], e["decision"]): e["target"] for e in continuation_edges(graph)}
        current, trace = case["entry"], []
        initial_bounds = None
        seen = set()
        while True:
            if current in seen:
                raise ValueError("Restored route contains a cycle")
            seen.add(current)
            card = criteria["nodes"][current]
            evidence = case_evidence(suite, case["evidenceByNode"][current])
            bounds = (evidence.get("domain"), evidence.get("bindings"), evidence.get("interval"), evidence.get("focus"),
                      evidence.get("analysis", {}).get("hypothesis"))
            if initial_bounds is not None and bounds != initial_bounds:
                raise ValueError("A restored path silently changed its bound domain, subjects, interval or hypothesis")
            initial_bounds = copy.deepcopy(bounds)
            evidence["retainedTrace"] = trace
            actual, reason = answer(card, evidence, criteria)
            trace.append({"nodeId": current, "answer": actual})
            if next(n["archetype"] for n in graph["nodes"] if n["id"] == current) == "terminal":
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
