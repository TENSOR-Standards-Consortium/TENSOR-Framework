"""Bounded supplementary question assessments. Supplied evidence is not verified truth.

The original seven entry paths keep their separate evaluator. Resuming a restored
question re-evaluates its prerequisites; a graph entry is never an authorization
to skip evidence checks. Nothing in a fixture is fetched or executed.
"""
from __future__ import annotations

import copy

from evaluate_entry_scenarios import (bound_assessment, context_ready, downstream_answer,
    equality_answer, fact, instant, match_answer, matches, merge_patch, named, references, validation_answer,
    subject_identity, hypothesis_context, independent_record, semantic_case, target_context, finite_nonnegative, record_group)

STAGES = ("detect", "validate", "classify", "scope", "correlate", "attribute", "impact", "terminal")


def relation_endpoint(case, selected, criteria, assessment):
    domain = criteria["domains"].get(assessment.get("targetDomain"))
    target = assessment.get("targetRecord")
    target_case = target_context(case, assessment)
    if (domain is None or not isinstance(target, dict) or not matches(target, target_case, domain)
            or assessment.get("sourceRecordId") != selected.get("id")
            or not named(target.get("id")) or not named(selected.get("id"))
            or target.get("id") == selected.get("id") or target.get("origin") == selected.get("origin")
            or validation_answer(target, case)[0] != "yes"):
        return None
    return target


def temporal_answer(case, selected, criteria):
    a = case.get("analysis", {}).get("correlation", {})
    hypothesis_ready, hypothesis_id = hypothesis_context(case)
    if (not hypothesis_ready or not bound_assessment(a, case, hypothesis_id) or not named(a.get("method"))
            or not references(a.get("evidenceRefs")) or a.get("relationKind") != "bounded-time-coincidence"):
        return "unknown", "A bound temporal relation and its assessment basis are required"
    target = relation_endpoint(case, selected, criteria, a)
    if target is None:
        return "unknown", "Temporal endpoints need separate validated origins and bound subjects"
    tolerance = a.get("toleranceSeconds")
    clocks = [r.get("clockUncertaintySeconds") for r in (selected, target)]
    if any(not finite_nonnegative(v) for v in [tolerance, *clocks]):
        return "unknown", "Finite nonnegative tolerance and clock uncertainty bounds are required"
    for record, uncertainty, interval in zip((selected, target), clocks, (case["interval"], a.get("targetInterval", case["interval"]))):
        start, end = instant(interval["start"]), instant(interval["end"])
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
    case = semantic_case(case, criteria)
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
    trace = case.get("retainedTrace", [])
    if (not isinstance(trace, list) or any(not isinstance(step, dict) or
            ("focus" in step and not named(step["focus"])) for step in trace)):
        return "unknown", "The retained trace must preserve explicit valid visited question focuses"
    seen = {}
    assessed_focuses = set()
    hypothesis_ready, hypothesis_id = hypothesis_context(case)
    hypothesis = case.get("analysis", {}).get("hypothesis")
    if not hypothesis_ready:
        return "unknown", "The retained hypothesis context is not bound to the original subjects and interval"
    if case.get("semanticReview") and ledger.get("hypothesis") != hypothesis:
        return "unknown", "Retention must preserve the exact hypothesis statement, criterion, alternatives and context"
    for row in rows:
        if (not isinstance(row, dict) or row.get("nodeId") not in criteria["nodes"] or criteria["nodes"][row["nodeId"]]["domain"] != case["domain"]
                or row.get("subjects") != case.get("bindings") or row.get("interval") != case.get("interval")
                or row.get("hypothesisId") != hypothesis_id
                or row.get("answer") not in ("yes", "no", "unknown")
                or not named(row.get("method")) or not named(row.get("rationale"))
                or not references(row.get("evidenceRefs")) or not references(row.get("limitations"))):
            return "unknown", "Each retained answer needs its question, method, references, rationale and limitations"
        if "hypothesis" in row and row["hypothesis"] != hypothesis:
            return "unknown", "A retained row changes the exact original hypothesis"
        for key, field in (("hypothesisStatement", "statement"), ("hypothesisCriterion", "criterion"),
                           ("hypothesisAlternatives", "alternatives")):
            if key in row and (hypothesis is None or row[key] != hypothesis.get(field)):
                return "unknown", "A reused hypothesis identifier does not preserve a changed statement or test"
        previous = criteria["nodes"][row["nodeId"]]
        nonterminal = (previous.get("stage") != "terminal"
                       and previous.get("role") not in ("assessed", "unresolved", "refuted", "exclusion"))
        fixed_focus = previous.get("sourceFacet") if previous.get("role") == "restored" and nonterminal else None
        if fixed_focus is not None:
            if "focus" in row and row["focus"] != fixed_focus:
                return "unknown", "A fixed-facet question cannot be retained under a different evidence focus"
            row_focus = fixed_focus
        else:
            row_focus = row.get("focus")
            actual_focuses = {step["focus"] for step in trace if step.get("nodeId") == row["nodeId"] and "focus" in step}
            if "focus" in row and (not named(row_focus) or row_focus not in (actual_focuses or {case.get("focus")})):
                return "unknown", "A generic retained row must preserve its actual visited or supplied evidence focus"
        if nonterminal and named(row_focus):
            assessed_focuses.add(row_focus)
        identity = (row["nodeId"], row_focus)
        if identity in seen and seen[identity] != row["answer"]:
            return "unknown", "Conflicting answers for one question and evidence focus need an explicit separate assessment history"
        seen[identity] = row["answer"]
    dispositions = ledger.get("focusDispositions", {})
    if (not isinstance(dispositions, dict) or any(not named(focus) or disposition not in ("assessed", "open")
                                               for focus, disposition in dispositions.items())):
        return "unknown", "Each retained evidence focus needs an explicit assessed or open disposition"
    focus_name = (card.get("sourceFacet") if card.get("role") == "restored"
                  and not card.get("focusBinding") else case.get("focus"))
    focus = dispositions.get(focus_name)
    if focus not in ("assessed", "open"):
        return "unknown", "The terminal focus must be retained as assessed or explicitly open"
    if any(disposition == "assessed" and focus not in assessed_focuses for focus, disposition in dispositions.items()):
        return "unknown", "Every assessed focus needs its own applicable retained nonterminal assessment"
    if any("focus" in step and any(row.get("nodeId") == step.get("nodeId")
            and row.get("answer") == step.get("answer") for row in rows)
            and not any(row.get("nodeId") == step.get("nodeId") and row.get("answer") == step.get("answer")
                        and row.get("focus") == step["focus"] for row in rows) for step in trace):
        return "unknown", "A retained answer changes or drops the actual visited evidence focus"
    if any(not any(r.get("nodeId") == s["nodeId"] and r.get("answer") == s["answer"] for r in rows) for s in trace):
        return "no", "The retained record drops or changes a preceding assessment"
    return "yes", "Separate answers, limitations and open questions are retained; this route ends only"


def answer(card, case, criteria):
    """Evaluate an explicitly resumed question, including its evidence prerequisites."""
    case = semantic_case(case, criteria)
    if card.get("role") != "restored":
        return base_resumption_answer(card, case, criteria)
    domain = criteria["domains"][card["domain"]]
    if (case.get("domain") != card["domain"] or not context_ready(case, domain) or not named(case.get("focus"))
            or (card["stage"] != "terminal" and case.get("focus") != card["sourceFacet"]) or case.get("materialConflict")):
        return "unknown", "Domain, focus, subject/time binding or material counterevidence is unresolved"
    stage, kind = card["stage"], card["assessmentKind"]
    if stage == "terminal":
        return retention_answer(card, case, criteria)
    match, reason, selected = match_answer(case, domain, case.get("_selectedGroup") == "independent")
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
                          and independent_record(r, case)
                          and r.get("id") != selected.get("id") and r.get("origin") != selected.get("origin")]
            if not candidates:
                return "unknown", "A copy is not independent corroboration; both matching records need a provenance basis"
            corroboration = case.get("analysis", {}).get("corroboration", {})
            if corroboration or case.get("semanticReview"):
                ready, hid = hypothesis_context(case)
                if (not ready or not bound_assessment(corroboration, case, hid)
                        or not named(corroboration.get("method")) or not references(corroboration.get("evidenceRefs"))
                        or corroboration.get("sourceRecordId") != selected.get("id")
                        or not named(corroboration.get("sourceFact")) or not named(corroboration.get("targetFact"))
                        or not (named(corroboration.get("identifierNamespace")) or references(corroboration.get("mappingEvidenceRefs")))):
                    return "unknown", "Corroboration needs its explicitly bound discriminator, namespace or mapping and evidence basis"
                source_fact, target_fact = corroboration["sourceFact"], corroboration["targetFact"]
            else:
                source_fact = target_fact = "event.id"  # Retained pre-review fixture compatibility.
            left, rights = fact(selected, source_fact), [fact(r, target_fact) for r in candidates]
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
    if stage == "classify":
        return downstream_answer("classification", case, selected, criteria)
    if stage == "scope":
        scope = downstream_answer("scope", case, selected, criteria)
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
        ready, hid = hypothesis_context(case)
        if (not ready or not bound_assessment(dependency, case, hid) or not named(dependency.get("method"))
                or not references(dependency.get("evidenceRefs"))
                or dependency.get("direction") not in ("upstream", "downstream")
                or not named(dependency.get("relationId"))
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
        if ids != [dependency["relationId"]] * 2 or directions != [dependency["direction"]] * 2:
            return "no", "Assessed dependency relationship or direction contradicts the proposed relation"
        dispositions = [e["disposition"] for e in a["entities"] if e["domain"] == dependency["targetDomain"]
                        and e["subjectId"] == target_subject
                        and "subjects" in e and subject_identity(criteria, e["domain"], e["subjects"]) == subject_identity(criteria, dependency["targetDomain"], dependency["targetSubjects"])]
        if "excluded" in dispositions:
            return "no", "The proposed bounded scope excludes the dependency target"
        if "included" not in dispositions:
            return "unknown", "The dependency target has no evidenced scope inclusion"
        return "yes", "An explicit evidenced dependency is included; shared time or identifiers alone do not establish it"
    if stage == "correlate" and kind == "temporal":
        return temporal_answer(case, selected, criteria)
    if stage == "attribute" and kind == "behavior-pattern":
        pattern = case.get("analysis", {}).get("pattern", {})
        ready, hid = hypothesis_context(case)
        if (not ready or not bound_assessment(pattern, case, hid) or pattern.get("claimKind") != "technical-behavior-pattern"
                or not named(pattern.get("patternId")) or not references(pattern.get("alternatives"))
                or not references(pattern.get("evidenceRefs"))):
            return "unknown", "A technical behavior pattern, discriminator and competing explanations are required; actor intent is separate"
        if pattern.get("criterion", {}).get("equals") != pattern["patternId"]:
            return "unknown", "The declared criterion does not test the named pattern"
        return equality_answer(selected, pattern.get("criterion"))
    if stage == "impact" and kind == "additional-impact":
        a = case.get("analysis", {}).get("additionalEffect", {})
        ready, hid = hypothesis_context(case)
        if (not ready or not bound_assessment(a, case, hid) or not named(a.get("method"))
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
        if (additional.get("bindings") != a["targetSubjects"] or additional.get("interval") != a.get("targetInterval", case["interval"])
                or additional.get("domain") != a["targetDomain"]):
            return "unknown", "The additional metric context disagrees with the linked endpoint"
        return downstream_answer("impact", semantic_case(additional, case), target, criteria)
    return downstream_answer(role, case, selected, criteria)


def base_resumption_answer(card, case, criteria):
    """Explicit adapter to the existing parameterized base; never inherit an answer."""
    case = semantic_case(case, criteria)
    domain = criteria["domains"][card["domain"]]
    if case.get("domain") != card["domain"] or not context_ready(case, domain) or not named(case.get("focus")):
        return "unknown", "A generic resumption retains the explicit facet, domain and complete subject/time context"
    role = card["role"]
    if role == "exclusion":
        from evaluate_entry_scenarios import exclusion_answer
        return exclusion_answer(case, domain)
    if role in ("assessed", "refuted", "unresolved", "exclusion"):
        retained = retention_answer(card, case, criteria)
        if retained[0] != "yes":
            return retained
        if role == "unresolved":
            rows = case["retention"]["assessments"] + case["retention"].get("prerequisiteAssessments", [])
            if not any(r["answer"] == "unknown" or (r["answer"] == "no" and
                       (criteria["nodes"][r["nodeId"]].get("role") in ("primaryValidation", "independentValidation", "scope")
                        or criteria["nodes"][r["nodeId"]].get("assessmentKind") in ("provenance", "scope-bound"))) for r in rows):
                return "unknown", "An unresolved ending needs a named retained assessment or evidence gap"
            return "yes", "Named unresolved assessment or evidence gaps are retained separately from known event findings"
        if role == "assessed":
            return retained
    group = record_group(card, case, criteria)
    if group not in ("primary", "independent"):
        return "unknown", "The resumed question must identify its declared primary or independent variant"
    independent = group == "independent"
    matched, reason, selected = match_answer(case, domain, independent)
    if role in ("entry", "alternate"):
        return matched, reason
    if matched != "yes" or selected.get("evidenceFacet") != case["focus"]:
        return "unknown", "The generic target needs its own facet-bound matching event record"
    validated = validation_answer(selected, case, independent)
    if role in ("primaryValidation", "independentValidation"):
        return validated
    if validated[0] != "yes":
        return "unknown", "Generic resumption needs accepted event provenance and interpretation"
    if role == "classification":
        return downstream_answer("classification", case, selected, criteria)
    if role == "refuted":
        classification = downstream_answer("classification", case, selected, criteria)
        return ("yes", "Retain the exact refuted hypothesis, without refuting the event") if classification[0] == "no" else (
            "unknown", "No refutation of the bound hypothesis was demonstrated")
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
        selected_group, selected_id = None, None
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
            if selected_group is not None:
                evidence.update(_selectedGroup=selected_group, _selectedRecordId=selected_id)
            evidence["retainedTrace"] = trace
            actual, reason = answer(card, evidence, criteria)
            if (card.get("stage") != "terminal"
                    and card["role"] not in ("assessed", "unresolved", "refuted", "exclusion")):
                independent = record_group(card, evidence, criteria) == "independent"
                _, _, selected = match_answer(semantic_case(evidence, criteria), criteria["domains"][card["domain"]], independent)
                if selected is not None:
                    selected_group, selected_id = "independent" if independent else "primary", selected.get("id")
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
