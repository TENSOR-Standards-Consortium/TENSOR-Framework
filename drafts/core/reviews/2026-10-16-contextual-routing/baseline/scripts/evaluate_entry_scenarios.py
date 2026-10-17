#!/usr/bin/env python3
"""Offline, author-side evaluation of bounded investigation-evidence cases.

Normalized observations and provenance assessments are supplied claims. This is
neither a log parser nor an evidence-truth, authorization, or Core conformance
validator. Nothing is fetched or executed from case content.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
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
    if not isinstance(interval, dict) or not isinstance(case.get("bindings", {}), dict):
        return False
    start, end = instant(interval.get("start")), instant(interval.get("end"))
    return (all(isinstance(case.get("bindings", {}).get(k), str) and case["bindings"][k].strip() for k in domain["bindings"])
            and start is not None and end is not None and start < end)


def semantic_case(case, criteria):
    """Historical snapshots opt into their original missing-clock compatibility."""
    if criteria.get("semanticReview") and not case.get("semanticReview"):
        return {**case, "semanticReview": True}
    return case


def finite_nonnegative(value):
    return (type(value) in (int, float) and value >= 0
            and (type(value) is int or math.isfinite(value)))


def membership(record, case, domain):
    """Three-valued membership of an entire clock bound in a half-open interval."""
    if not context_ready(case, domain) or not isinstance(record, dict):
        return "unknown"
    subjects = record.get("subjects", {})
    if not isinstance(subjects, dict):
        return "unknown"
    if any(k in subjects and subjects[k] != case["bindings"][k] for k in domain["bindings"]):
        return "no"
    if not all(k in subjects for k in domain["bindings"]):
        return "unknown"
    when = instant(record.get("eventTime"))
    uncertainty = record.get("clockUncertaintySeconds")
    if uncertainty is None and "clockUncertaintySeconds" not in record and not case.get("semanticReview"):
        uncertainty = 0  # Explicit compatibility for the retained pre-review fixture format.
    if when is None or not finite_nonnegative(uncertainty):
        return "unknown"
    start, end = (instant(case["interval"][k]) for k in ("start", "end"))
    before, after = (when - start).total_seconds(), (end - when).total_seconds()
    if before < -uncertainty or after <= -uncertainty:
        return "no"
    if before < uncertainty or after <= uncertainty:
        return "unknown"
    return "yes"


def matches(record, case, domain):
    return membership(record, case, domain) == "yes"


def independent_record(record, case):
    """A copy of any primary observation cannot become an independent witness."""
    if not isinstance(record, dict) or not named(record.get("id")) or not named(record.get("origin")):
        return False
    primary = case.get("primary", {}).get("records", [])
    if not isinstance(primary, list) or any(not isinstance(r, dict) or not named(r.get("id"))
                                          or not named(r.get("origin")) for r in primary):
        return False
    ids, origins = {r["id"] for r in primary}, {r["origin"] for r in primary}
    if named(case.get("primaryOrigin")):
        origins.add(case["primaryOrigin"])  # A supplied known origin can further constrain independence.
    return record["id"] not in ids and record["origin"] not in origins


def record_group(card, case, criteria):
    """The declared independent question variants retain their witness semantics."""
    role = card.get("role")
    if role in ("alternate", "independentValidation"):
        return "independent"
    if role in ("classification", "scope"):
        variants = criteria["domains"][card["domain"]].get(role, [])
        if isinstance(variants, list):
            identities = [index for index, node_id in enumerate(variants)
                          if card is criteria["nodes"].get(node_id) or card.get("nodeId") == node_id]
            if not identities:
                identities = [index for index, node_id in enumerate(variants)
                              if card == criteria["nodes"].get(node_id)]
            if len(identities) > 1:
                return "unknown"  # Equal copied cards cannot identify one of two distinct questions.
            if identities and identities[0] > 0:
                return "independent"
            if role == "classification" and len(variants) > 1 and identities == [0]:
                return "primary"
    return "primary" if role == "entry" else case.get("_selectedGroup", "primary")


def match_answer(case, domain, independent=False):
    group_name = "independent" if independent else "primary"
    group = case.get(group_name, {})
    if not context_ready(case, domain):
        return "unknown", "Subject or time binding is unresolved", None
    if case.get("materialConflict"):
        return "unknown", "Material counterevidence is unresolved", None
    if group.get("accessible") is not True or group.get("searched") is not True:
        return "unknown", "Evidence is unavailable or the search is incomplete", None
    records = group.get("records", [])
    if not isinstance(records, list):
        return "unknown", "The examined material is not a declared record list", None
    selected_id = (case.get("_selectedRecordId") if case.get("_selectedGroup") == group_name
                   and named(case.get("_selectedRecordId")) else group.get("selectedRecordId"))
    if selected_id is not None:
        selected = [r for r in records if isinstance(r, dict) and r.get("id") == selected_id]
        if not named(selected_id) or len(selected) != 1:
            return "unknown", "The selected observation must identify exactly one supplied record", None
        records = selected
    uncertain, candidates = False, []
    for record in records:
        result = membership(record, case, domain)
        if result == "unknown":
            uncertain = True
        if result != "yes":
            continue
        if independent and not independent_record(record, case):
            uncertain = True
            continue
        candidates.append(record)
    if len(candidates) > 1 or (candidates and uncertain):
        return "unknown", "Ambiguous matching observations require an explicit unique selectedRecordId", None
    if candidates:
        return "yes", "The selected record's entire clock bound matches the exact subjects and interval", candidates[0]
    if selected_id is not None:
        return "unknown", "The explicitly selected observation is not a resolved matching record", None
    return ("unknown", "Record time or independent lineage is unresolved", None) if uncertain else (
        "no", "The completed search found no matching record in the examined material", None)


def validation_answer(record, case, independent=False):
    if not isinstance(record, dict) or case.get("materialConflict"):
        return "unknown", "No uncontradicted matching record was selected"
    if independent and not independent_record(record, case):
        return "unknown", "Independent validation needs lineage separate from every primary observation"
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
    if not references(coverage.get("evidenceRefs")) or any(coverage.get(k) is not True for k in COVERAGE_FLAGS):
        return "unknown", "Complete applicable evidence coverage has not been established"
    unresolved = False
    for name in ("primary", "independent"):
        group = case.get(name, {})
        if (group.get("accessible") is not True or group.get("searched") is not True
                or not isinstance(group.get("records"), list)):
            return "unknown", "Both declared evidence groups need available, completed searches"
        answers = [membership(record, case, domain) for record in group["records"]]
        if "yes" in answers:
            return "no", "A matching record is counterevidence to an absence claim; reassessment is required"
        unresolved |= "unknown" in answers
    if unresolved:
        return "unknown", "Ambiguous subjects, record times or clock bounds prevent an absence finding"
    return "yes", "The supplied applicable coverage/search basis supports this bounded exclusion only"


def references(value):
    return isinstance(value, list) and bool(value) and all(isinstance(v, str) and v.strip() for v in value)


def named(value):
    return isinstance(value, str) and bool(value.strip())


def bound_assessment(assessment, case, hypothesis_id):
    return (isinstance(assessment, dict) and assessment.get("subjects") == case["bindings"]
            and assessment.get("interval") == case["interval"]
            and assessment.get("hypothesisId") == hypothesis_id)


def hypothesis_context(case):
    """An absent hypothesis is valid for fact-led questions; a supplied one stays bound."""
    analysis = case.get("analysis", {})
    if not isinstance(analysis, dict):
        return False, None
    if "hypothesis" not in analysis:
        return True, None
    hypothesis = analysis["hypothesis"]
    if not isinstance(hypothesis, dict) or not named(hypothesis.get("hypothesisId")):
        return False, None
    hid = hypothesis["hypothesisId"]
    return bound_assessment(hypothesis, case, hid), hid


def target_context(case, assessment):
    return {"bindings": assessment.get("targetSubjects", {}),
            "interval": assessment.get("targetInterval", case["interval"]),
            "semanticReview": case.get("semanticReview", False)}


def subject_identity(criteria, domain, subjects):
    """Identity is the declared field projection; arbitrary metadata adds no entity."""
    return tuple(subjects.get(field) for field in criteria["domains"][domain]["bindings"])


def fact(record, name):
    """Return a supplied assessed fact; never coerce unknown values or types."""
    if not isinstance(name, str) or not name.strip() or not isinstance(record, dict):
        return None
    facts = record.get("facts", {})
    item = facts.get(name) if isinstance(facts, dict) else None
    if (not isinstance(item, dict) or item.get("assessment") != "accepted"
            or not references(item.get("evidenceRefs")) or not named(item.get("method"))):
        return None
    value = item.get("value")
    if type(value) not in (str, int, float, bool) or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def equality_answer(record, criterion):
    if not isinstance(criterion, dict) or not named(criterion.get("method")) or "equals" not in criterion:
        return "unknown", "No operational equality criterion was declared"
    actual, expected = fact(record, criterion.get("fact")), criterion["equals"]
    if actual is None or type(actual) is not type(expected):
        return "unknown", "The discriminator is missing, unassessed, or has incompatible types"
    return ("yes", "The assessed discriminator satisfies the declared criterion") if actual == expected else (
        "no", "The assessed discriminator contradicts the declared criterion")


def downstream_answer(role, case, selected, criteria):
    case = semantic_case(case, criteria)
    analysis = case.get("analysis", {})
    if not isinstance(analysis, dict):
        return "unknown", "No structured hypothesis assessment was supplied"
    domain = criteria["domains"].get(case.get("domain"))
    if (domain is None or not context_ready(case, domain) or not matches(selected, case, domain)
            or validation_answer(selected, case)[0] != "yes"):
        return "unknown", "This assessment needs its own matching, validated event and exact bound context"
    hypothesis = analysis.get("hypothesis", {})
    hypothesis_ready, hypothesis_id = hypothesis_context(case)
    if case.get("materialConflict") or not hypothesis_ready:
        return "unknown", "The original subject/time or supplied hypothesis context is unresolved"
    if role == "classification":
        if (not named(hypothesis_id) or not named(hypothesis.get("statement"))
                or not references(hypothesis.get("alternatives"))):
            return "unknown", "The single hypothesis and competing explanations are not explicit"
        return equality_answer(selected, hypothesis.get("criterion"))
    assessment = analysis.get(role, {})
    if (not bound_assessment(assessment, case, hypothesis_id)
            or not references(assessment.get("evidenceRefs")) or not named(assessment.get("method"))):
        return "unknown", "The assessment lacks its bound context, method, or evidence basis"
    if role == "scope":
        # This is a documented scope boundary, not proof that all affected entities were found.
        if selected.get("id") not in assessment["evidenceRefs"]:
            return "unknown", "Scope does not cite the selected event record"
        if assessment.get("claimsCompletePopulation") is not False:
            return "unknown", "Population completeness cannot be inferred from the selected event"
        entities = assessment.get("entities")
        if not isinstance(entities, list) or not entities:
            return "unknown", "Scope entities and dispositions have not been recorded"
        for entity in entities:
            if (not isinstance(entity, dict) or entity.get("domain") not in criteria["domains"]
                    or not isinstance(entity.get("subjectId"), str) or not entity["subjectId"].strip()
                    or entity.get("disposition") not in ("included", "excluded", "unknown")):
                return "unknown", "An entity scope disposition is incomplete"
            if entity["disposition"] != "unknown" and not references(entity.get("evidenceRefs")):
                return "unknown", "A scope inclusion or exclusion has no supporting reference"
            fields = criteria["domains"][entity["domain"]]["bindings"]
            if entity["disposition"] != "unknown" or "subjects" in entity:
                if (not isinstance(entity.get("subjects"), dict) or not all(named(entity["subjects"].get(k)) for k in fields)
                        or entity["subjects"][fields[0]] != entity["subjectId"]):
                    return "unknown", "A scope inclusion or exclusion must retain all declared endpoint fields"
        dispositions = {}
        partial_identities = {}
        for entity in entities:
            identity = (entity["domain"], subject_identity(criteria, entity["domain"], entity["subjects"]) if "subjects" in entity else entity["subjectId"])
            if identity in dispositions and dispositions[identity] != entity["disposition"]:
                return "unknown", "Conflicting dispositions for one entity require reassessment"
            dispositions[identity] = entity["disposition"]
            partial_id = (entity["domain"], entity["subjectId"])
            previous = partial_identities.setdefault(partial_id, [])
            if any(e["disposition"] != entity["disposition"] and ("subjects" not in e or "subjects" not in entity) for e in previous):
                return "unknown", "Conflicting partial and composite identities overlap; disambiguate the scope records"
            previous.append(entity)
        source_subject = case["bindings"][criteria["domains"][case["domain"]]["bindings"][0]]
        source_entities = [e for e in entities if e["domain"] == case["domain"] and e["subjectId"] == source_subject
                           and "subjects" in e and subject_identity(criteria, case["domain"], e["subjects"]) == subject_identity(criteria, case["domain"], case["bindings"])]
        if any(e["disposition"] == "excluded" for e in source_entities):
            return "no", "The proposed scope excludes the bound source event subject"
        if not any(e["disposition"] == "included" for e in source_entities):
            return "unknown", "The bound source subject has no complete evidenced inclusion"
        return "yes", "Bound scope and entity dispositions are documented; completeness is not asserted"
    if role == "correlation":
        target_domain = criteria["domains"].get(assessment.get("targetDomain"))
        target = assessment.get("targetRecord")
        target_case = target_context(case, assessment)
        if (target_domain is None or not isinstance(target, dict)
                or not matches(target, target_case, target_domain)
                or assessment.get("sourceRecordId") != selected.get("id")):
            return "unknown", "The named relation endpoints are not validated in the bound interval"
        if validation_answer(target, case)[0] != "yes":
            return "unknown", "The target record has no accepted provenance and interpretation basis"
        if (not named(target.get("id")) or not named(selected.get("id"))
                or target.get("id") == selected.get("id") or target.get("origin") == selected.get("origin")):
            return "unknown", "A copied or same-origin observation is not separate corroboration for this relation test"
        if assessment.get("relationKind") != "shared-identifier":
            return "unknown", "This evaluator only tests a declared shared identifier, not causation"
        left = fact(selected, assessment.get("sourceFact"))
        right = fact(target, assessment.get("targetFact"))
        if left is None or right is None or type(left) is not type(right):
            return "unknown", "The explicit relationship discriminator is not assessed on both endpoints"
        return ("yes", "Validated endpoints share the declared identifier; this does not prove causation") if left == right else (
            "no", "The endpoint discriminators contradict the declared shared-identifier relation")
    if role == "attribution":
        if (assessment.get("claimKind") != "technical-source" or not references(assessment.get("alternatives"))
                or not isinstance(assessment.get("sourceEntityId"), str) or not assessment["sourceEntityId"].strip()):
            return "unknown", "A bounded technical source and competing explanations are required; intent is not inferred"
        criterion = assessment.get("criterion", {})
        if criterion.get("equals") != assessment["sourceEntityId"]:
            return "unknown", "The discriminator does not test the named technical source"
        return equality_answer(selected, criterion)
    if role == "impact":
        if assessment.get("claimKind") != "observed-metric-change" or not named(assessment.get("unit")) or not named(assessment.get("metricId")):
            return "unknown", "Only a named observed metric change is evaluated; exposure is not realized loss"
        baseline = fact(selected, assessment.get("baselineFact"))
        observed = fact(selected, assessment.get("observedFact"))
        units = [fact(selected, assessment.get(k)) for k in ("baselineUnitFact", "observedUnitFact")]
        metrics = [fact(selected, assessment.get(k)) for k in ("baselineMetricFact", "observedMetricFact")]
        times = [instant(fact(selected, assessment.get(k))) for k in ("baselineTimeFact", "observedTimeFact")]
        baseline_context = {"bindings": case["bindings"],
                            "interval": assessment.get("baselineInterval", case["interval"])}
        if (type(baseline) not in (int, float) or type(observed) not in (int, float)
                or units != [assessment["unit"]] * 2 or metrics != [assessment["metricId"]] * 2
                or not context_ready(baseline_context, domain) or None in times
                or not instant(baseline_context["interval"]["start"]) <= times[0] < instant(baseline_context["interval"]["end"])
                or not instant(case["interval"]["start"]) <= times[1] < instant(case["interval"]["end"])
                or not times[0] < times[1]):
            return "unknown", "Comparable metric and units need ordered measurements in the explicit baseline and observation intervals"
        return ("yes", "The supplied bounded metric changed; attribution and broader impact remain separate") if observed != baseline else (
            "no", "The supplied bounded metric is unchanged; other effects have not been excluded")
    raise ValueError(f"Unimplemented downstream role: {role}")


def evaluate_case(graph, criteria, case):
    case = semantic_case(case, criteria)
    domain = criteria["domains"][case["domain"]]
    nodes = {n["id"]: n for n in graph["nodes"]}
    # These retained fixtures explicitly select the original continuation. New
    # branching scenarios select edge IDs; never let a dictionary choose a lead.
    from investigative_routing import continuation_edges
    edges = {(e["source"], e["decision"]): e["target"] for e in continuation_edges(graph)}
    current, selected = domain["entry"], None
    trace = []
    seen = set()
    while current in criteria["nodes"]:
        if current in seen:
            raise ValueError("Reviewed route contains a cycle")
        seen.add(current)
        card = criteria["nodes"][current]
        if nodes[current]["category"] != case["domain"] or card["domain"] != case["domain"]:
            raise ValueError("The assessment changed domain without a bound evidentiary relationship")
        role = card["role"]
        if role in ("entry", "alternate"):
            answer, reason, selected = match_answer(case, domain, role == "alternate")
        elif role in ("primaryValidation", "independentValidation"):
            answer, reason = validation_answer(selected, case, role == "independentValidation")
        elif role == "exclusion":
            answer, reason = exclusion_answer(case, domain)
        elif role == "unresolved":
            gaps = [t for t in trace if t["answer"] == "unknown" or (t["answer"] == "no" and
                    criteria["nodes"][t["nodeId"]]["role"] in ("primaryValidation", "independentValidation", "scope", "exclusion"))]
            answer = "yes" if gaps else "unknown"
            reason = "Retain the named unresolved assessment or evidence limitation separately from known event findings"
        elif role in ("classification", "scope", "correlation", "attribution", "impact"):
            answer, reason = downstream_answer(role, case, selected, criteria)
        elif role == "refuted":
            answer = "yes" if any(t["answer"] == "no" and criteria["nodes"][t["nodeId"]]["role"] == "classification" for t in trace) else "unknown"
            reason = "Retain the contradicted explicit hypothesis; the recorded event and competing hypotheses remain separate"
        elif role == "assessed":
            answer = "yes" if trace else "unknown"
            reason = "Retain each separate assessment, including negative and unknown answers; this does not close the investigation"
        else:
            raise ValueError(f"Unimplemented review role: {role}")
        trace.append({"nodeId": current, "answer": answer, "reason": reason,
                      "recordId": selected.get("id") if selected else None})
        if role in ("classification", "scope", "correlation", "attribution", "impact"):
            analysis = case.get("analysis", {})
            analysis = analysis if isinstance(analysis, dict) else {}
            hypothesis = analysis.get("hypothesis", {})
            hypothesis = hypothesis if isinstance(hypothesis, dict) else {}
            assessment = hypothesis if role == "classification" else analysis.get(role, {})
            assessment = assessment if isinstance(assessment, dict) else {}
            criterion = assessment.get("criterion", {})
            criterion = criterion if isinstance(criterion, dict) else {}
            trace[-1].update({"hypothesisId": hypothesis.get("hypothesisId"),
                              "method": criterion.get("method") if role == "classification" else assessment.get("method"),
                              "evidenceRefs": selected.get("assessmentEvidenceRefs", []) if role == "classification" and selected else assessment.get("evidenceRefs", [])})
        if nodes[current]["archetype"] == "terminal":
            state = "unresolved"
            if role == "exclusion" and answer == "yes":
                state = "bounded-exclusion"
            elif role == "refuted" and answer == "yes":
                state = "hypothesis-refuted"
            elif role == "assessed" and answer == "yes":
                findings = [t for t in trace if criteria["nodes"][t["nodeId"]]["role"] in ("classification", "scope", "correlation", "attribution", "impact")]
                state = "bounded-findings" if all(t["answer"] == "yes" for t in findings) else "partial-findings"
            return {"caseId": case["id"], "trace": trace, "state": state}
        current = edges[(current, answer)]
    raise ValueError(f"Route escaped the reviewed boundary at {current}")


def run_cases(graph, criteria, suite):
    if graph["version"] != criteria["graphVersion"] or suite["graphVersion"] != graph["version"]:
        raise ValueError("Graph, criteria and scenario versions disagree")
    results = []
    for case in expand_suite(suite)["cases"]:
        result = evaluate_case(graph, criteria, case)
        actual = [[t["nodeId"], t["answer"]] for t in result["trace"]]
        result["passed"] = actual == case["expectedTrace"] and result["state"] == case["expectedState"]
        results.append(result)
    return results


def merge_patch(base, patch):
    """Object merge patch: null removes a field; arrays and scalars replace."""
    if not isinstance(patch, dict):
        return copy.deepcopy(patch)
    result = copy.deepcopy(base) if isinstance(base, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = merge_patch(result.get(key), value)
    return result


def expand_suite(suite):
    """Resolve earlier fixture references only; expectations must be explicit."""
    cases = {}
    for raw in suite["cases"]:
        case_id = raw["id"]
        if case_id in cases:
            raise ValueError(f"Duplicate scenario id: {case_id}")
        if "extends" in raw:
            if raw["extends"] not in cases:
                raise ValueError("Scenario base must be an earlier case; forward references and cycles are forbidden")
            patch = raw.get("patch")
            if not isinstance(patch, dict) or {"id", "expectedTrace", "expectedState", "extends", "patch"} & patch.keys():
                raise ValueError("Fixture patches may change evidence only")
            if "expectedTrace" not in raw or "expectedState" not in raw:
                raise ValueError("Derived scenarios require explicit independent expectations")
            case = merge_patch(cases[raw["extends"]], patch)
            case.update({k: copy.deepcopy(raw[k]) for k in ("id", "expectedTrace", "expectedState")})
        else:
            case = copy.deepcopy(raw)
        cases[case_id] = case
    return {**suite, "cases": list(cases.values())}


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
    if "restoration" in criteria:
        from restored_evidence import run_cases as run_restored_cases
        results += run_restored_cases(graph, criteria, suite)
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
    print(f"Evidence scenarios: {receipt['passed']}/{receipt['caseCount']} passed")
    for result in results:
        if not result["passed"]:
            print(json.dumps(result))
    return 0 if receipt["passed"] == receipt["caseCount"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
