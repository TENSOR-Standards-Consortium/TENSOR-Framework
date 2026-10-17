"""Hand-authored semantic challenges, independent of graph/fixture generators.

These are supplied normalized claims and author-side checks, not field efficacy
or external implementation proof.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import evaluate_entry_scenarios as base
import restored_evidence as restored

INTERVAL = {"start": "2026-10-01T10:00:00Z", "end": "2026-10-01T11:00:00Z"}
SUBJECTS = {"principalId": "principal:alice", "identityAction": "action:signin"}
FOCUS = "authentication pathways"
DOMAIN = {"bindings": list(SUBJECTS)}
CRITERIA = {"graphVersion": "hand-authored-review", "semanticReview": {"id": "tensor-semantic-review/1"},
            "domains": {"Identity": DOMAIN, "File": {"bindings": ["fileId", "systemId"]}},
            "nodes": {
                "entry": {"domain": "Identity", "role": "entry"},
                "classification": {"domain": "Identity", "role": "classification"},
                "scope": {"domain": "Identity", "role": "scope"},
                "effect": {"domain": "Identity", "role": "impact"},
                "focus-assessment": {"domain": "Identity", "role": "restored", "stage": "validate", "sourceFacet": FOCUS},
                "other-focus": {"domain": "Identity", "role": "restored", "stage": "validate", "sourceFacet": "other material"}}}


def fact(value):
    return {"value": value, "assessment": "accepted", "method": "manual exact-value examination",
            "evidenceRefs": ["evidence:measured-value"]}


def record(identifier="record:primary", origin="origin:idp", subjects=None):
    return {"id": identifier, "origin": origin, "subjects": deepcopy(SUBJECTS if subjects is None else subjects),
            "eventTime": "2026-10-01T10:30:00Z", "clockUncertaintySeconds": 0,
            "provenanceAssessment": "accepted", "interpretationAssessment": "accepted",
            "assessmentEvidenceRefs": ["evidence:integrity"], "evidenceFacet": FOCUS,
            "facts": {"signal": fact("observed"), "relation.key": fact("session:17"),
                      "event.id": fact("idp-local:17"), "source": fact("service:idp")}}


def case(with_hypothesis=True):
    result = {"id": "independent:manual", "semanticReview": True, "domain": "Identity", "focus": FOCUS,
              "bindings": deepcopy(SUBJECTS), "interval": deepcopy(INTERVAL),
              "primary": {"accessible": True, "searched": True, "records": [record()]},
              "independent": {"accessible": True, "searched": True, "records": []}, "analysis": {}}
    if with_hypothesis:
        result["analysis"]["hypothesis"] = {"hypothesisId": "hypothesis:signal", "subjects": deepcopy(SUBJECTS),
            "interval": deepcopy(INTERVAL), "statement": "The explicitly named signal was observed.",
            "alternatives": ["The signal was not observed."],
            "criterion": {"fact": "signal", "equals": "observed", "method": "inspect the named signal"}}
    return result


def assessment(c):
    result = {"subjects": deepcopy(c["bindings"]), "interval": deepcopy(c["interval"]),
              "method": "manual bounded assessment", "evidenceRefs": ["record:primary", "evidence:assessment"]}
    if "hypothesis" in c["analysis"]:
        result["hypothesisId"] = c["analysis"]["hypothesis"]["hypothesisId"]
    return result


def scope(c):
    c["analysis"]["scope"] = {**assessment(c), "claimsCompletePopulation": False,
        "entities": [{"domain": c["domain"], "subjectId": c["bindings"]["principalId"],
            "subjects": deepcopy(c["bindings"]), "disposition": "included", "evidenceRefs": ["evidence:source"]}]}


def metric(c):
    c["analysis"]["impact"] = {**assessment(c), "claimKind": "observed-metric-change", "metricId": "failed-signins",
        "unit": "count", "baselineFact": "metric.before", "observedFact": "metric.after",
        "baselineUnitFact": "metric.before.unit", "observedUnitFact": "metric.after.unit",
        "baselineMetricFact": "metric.before.id", "observedMetricFact": "metric.after.id",
        "baselineTimeFact": "metric.before.time", "observedTimeFact": "metric.after.time"}
    values = {"metric.before": 3, "metric.after": 8, "metric.before.unit": "count", "metric.after.unit": "count",
              "metric.before.id": "failed-signins", "metric.after.id": "failed-signins",
              "metric.before.time": "2026-10-01T10:10:00Z", "metric.after.time": "2026-10-01T10:40:00Z"}
    c["primary"]["records"][0]["facts"].update({k: fact(v) for k, v in values.items()})


def retention(c, node_id="focus-assessment", answer="yes"):
    row = {**assessment(c), "nodeId": node_id, "answer": answer, "rationale": "This named assessment was retained.",
           "limitations": ["Only this supplied bounded observation was examined."]}
    c["retention"] = {"subjects": deepcopy(c["bindings"]), "interval": deepcopy(c["interval"]),
        "graphVersion": CRITERIA["graphVersion"], "closesInvestigation": False,
        "focusDispositions": {FOCUS: "assessed"}, "assessments": [row]}
    if "hypothesis" in c["analysis"]:
        c["retention"]["hypothesis"] = deepcopy(c["analysis"]["hypothesis"])


class SemanticBaseTests(unittest.TestCase):
    def test_primary_classification_cannot_borrow_an_inherited_independent_witness(self):
        criteria = deepcopy(CRITERIA)
        criteria['nodes']['independent-classification'] = {**criteria['nodes']['classification'], 'nodeId': 'independent-classification'}
        criteria['nodes']['classification']['nodeId'] = 'classification'
        criteria['domains']['Identity']['classification'] = ['classification', 'independent-classification']
        c = case(); c['primary']['accessible'] = False
        c['independent']['records'] = [record('record:witness', 'origin:separate')]
        c.update(_selectedGroup='independent', _selectedRecordId='record:witness')
        self.assertEqual('unknown', restored.answer(criteria['nodes']['classification'], c, criteria)[0])
        self.assertEqual('yes', restored.answer(criteria['nodes']['independent-classification'], c, criteria)[0])

    def test_clock_membership_uses_entire_finite_nonnegative_bound(self):
        c = case()
        r = c["primary"]["records"][0]
        for when, uncertainty, expected in [
            (INTERVAL["start"], 0, "yes"), (INTERVAL["end"], 0, "no"),
            (INTERVAL["start"], 1, "unknown"), (INTERVAL["end"], 1, "unknown"),
            ("2026-10-01T09:59:58Z", 1, "no"), ("2026-10-01T09:59:59Z", 1, "unknown"),
            ("2026-10-01T11:00:01Z", 1, "no"), ("2026-10-01T10:30:00Z", 1, "yes")]:
            r.update(eventTime=when, clockUncertaintySeconds=uncertainty)
            with self.subTest(when=when, uncertainty=uncertainty):
                self.assertEqual(expected, base.match_answer(c, DOMAIN)[0])
        for bad in (True, -1, float("inf"), float("nan"), "0", None):
            r.update(eventTime="2026-10-01T10:30:00Z", clockUncertaintySeconds=bad)
            self.assertEqual("unknown", base.match_answer(c, DOMAIN)[0])
        r.pop("clockUncertaintySeconds")
        self.assertEqual("unknown", base.match_answer(c, DOMAIN)[0])

    def test_criteria_opt_in_preserves_caller_and_rejects_missing_clock(self):
        c = case(); c.pop("semanticReview")
        c["primary"]["records"][0].pop("clockUncertaintySeconds")
        self.assertEqual("unknown", restored.answer({"domain": "Identity", "role": "primaryValidation"}, c, CRITERIA)[0])
        self.assertNotIn("semanticReview", c)

    def test_selection_is_explicit_unique_and_permutation_invariant(self):
        c = case(); c["primary"]["records"].append(record("record:second"))
        for reverse in (False, True):
            if reverse: c["primary"]["records"].reverse()
            self.assertEqual("unknown", base.match_answer(c, DOMAIN)[0])
            c["primary"]["selectedRecordId"] = "record:second"
            self.assertEqual("record:second", base.match_answer(c, DOMAIN)[2]["id"])
            c["primary"].pop("selectedRecordId")
        c["primary"]["records"][1]["id"] = c["primary"]["records"][0]["id"]
        c["primary"]["selectedRecordId"] = c["primary"]["records"][0]["id"]
        self.assertEqual("unknown", base.match_answer(c, DOMAIN)[0])

    def test_independence_compares_every_actual_primary_identity_and_origin(self):
        c = case(); c["primaryOrigin"] = "origin:mistaken-claim"
        c["primary"]["records"].append(record("record:other", "origin:other"))
        c["independent"]["records"] = [record("record:witness", "origin:other")]
        self.assertEqual("unknown", base.match_answer(c, DOMAIN, True)[0])
        c["independent"]["records"][0].update(id="record:other", origin="origin:separate")
        self.assertEqual("unknown", base.match_answer(c, DOMAIN, True)[0])
        c["independent"]["records"][0]["id"] = "record:witness"
        self.assertEqual("yes", base.match_answer(c, DOMAIN, True)[0])
        c["primary"]["records"][1].pop("origin")
        self.assertEqual("unknown", base.match_answer(c, DOMAIN, True)[0])

    def test_independent_validation_and_later_roles_keep_selected_witness(self):
        c = case(); c["primary"]["records"][0]["provenanceAssessment"] = "rejected"
        c["independent"]["records"] = [record("record:independent", "origin:separate")]
        card = {"domain": "Identity", "role": "independentValidation"}
        self.assertEqual("yes", restored.answer(card, c, CRITERIA)[0])
        c.update(_selectedGroup="independent", _selectedRecordId="record:independent")
        self.assertEqual("yes", restored.answer({"domain": "Identity", "role": "primaryValidation"}, c, CRITERIA)[0])
        self.assertEqual("yes", restored.answer(CRITERIA["nodes"]["classification"], c, CRITERIA)[0])
        c["independent"]["records"][0]["facts"]["signal"]["value"] = "absent"
        self.assertEqual("no", restored.answer(CRITERIA["nodes"]["classification"], c, CRITERIA)[0])

    def test_direct_independent_classification_and_scope_variants_recheck_witness(self):
        # Read the declared question identities; the evidence and expected answers
        # below are authored here, independently of scenario/fixture generators.
        criteria = json.loads((Path(__file__).resolve().parents[2] / "drafts/core/entry-evidence-criteria.json").read_text())
        for domain, declared in criteria["domains"].items():
            if len(declared["classification"]) < 2:
                continue
            c = case(); c["domain"] = domain
            c["bindings"] = {field: "manual:" + field for field in declared["bindings"]}
            c["analysis"]["hypothesis"]["subjects"] = deepcopy(c["bindings"])
            c["primary"]["records"][0]["subjects"] = deepcopy(c["bindings"])
            c["analysis"]["scope"] = {**assessment(c), "claimsCompletePopulation": False,
                "entities": [{"domain": domain, "subjectId": c["bindings"][declared["bindings"][0]],
                    "subjects": deepcopy(c["bindings"]), "disposition": "included", "evidenceRefs": ["evidence:source"]}]}
            c["analysis"]["scope"]["evidenceRefs"].append("record:witness")
            for role in ("classification", "scope"):
                card = criteria["nodes"][declared[role][1]]
                with self.subTest(domain=domain, role=role, question=declared[role][1]):
                    for unavailable in ("accessible", "searched"):
                        c["independent"] = {"accessible": True, "searched": True, "records": []}
                        c["independent"][unavailable] = False
                        self.assertEqual("unknown", restored.answer(card, c, criteria)[0])
                    witness = record("record:witness", "origin:independent", c["bindings"])
                    c["independent"] = {"accessible": True, "searched": True, "records": [witness]}
                    c.update(_selectedGroup="primary", _selectedRecordId="record:primary")
                    self.assertEqual("yes", restored.answer(card, c, criteria)[0])
                    if role == "classification":
                        witness["facts"]["signal"]["value"] = "absent"
                        self.assertEqual("no", restored.answer(card, c, criteria)[0])

    def test_direct_independent_variant_carries_witness_to_later_path_question(self):
        criteria = deepcopy(CRITERIA)
        criteria["domains"]["Identity"]["classification"] = ["classification", "independent-classification"]
        criteria["nodes"]["independent-classification"] = {"domain": "Identity", "role": "classification",
            "predicate": "Does the separately originating record satisfy the declared technical criterion?"}
        criteria["nodes"]["terminal"] = {"domain": "Identity", "role": "assessed"}
        c = case(); metric(c)
        witness = record("record:witness", "origin:independent")
        witness["facts"].update(deepcopy(c["primary"]["records"][0]["facts"]))
        witness["facts"]["metric.after"]["value"] = 3  # Independent metric is unchanged; primary changed.
        c["independent"]["records"] = [witness]
        c["primary"]["records"][0]["facts"]["signal"]["value"] = "absent"
        retention(c, "classification")
        c["retention"]["assessments"] = [{**deepcopy(c["retention"]["assessments"][0]),
            "nodeId": node, "answer": outcome, "focus": FOCUS} for node, outcome in
            (("independent-classification", "yes"), ("effect", "no"))]
        graph = {"version": criteria["graphVersion"], "nodes": [
            {"id": "independent-classification", "archetype": "classify"}, {"id": "effect", "archetype": "impact"},
            {"id": "terminal", "archetype": "terminal"}], "edges": [
                {"source": "independent-classification", "decision": "yes", "target": "effect"},
                {"source": "effect", "decision": "no", "target": "terminal"}]}
        path = {"id": "direct-independent-path", "entry": "independent-classification",
            "evidenceByNode": {node["id"]: {"evidenceRef": "manual"} for node in graph["nodes"]},
            "expectedTrace": [["independent-classification", "yes"], ["effect", "no"], ["terminal", "yes"]]}
        suite = {"graphVersion": criteria["graphVersion"], "restoredCases": [], "restoredFixtures": {"manual": c},
                 "restoredPaths": [path]}
        self.assertTrue(restored.run_cases(graph, criteria, suite)[0]["passed"])

    def test_exclusion_requires_real_complete_search_and_no_ambiguous_records(self):
        c = case(); c["primary"]["records"] = []
        c["coverage"] = {"subjects": deepcopy(SUBJECTS), "interval": deepcopy(INTERVAL),
                         "evidenceRefs": ["evidence:coverage"], **{k: True for k in base.COVERAGE_FLAGS}}
        self.assertEqual("yes", base.exclusion_answer(c, DOMAIN)[0])
        for group, field in (("primary", "accessible"), ("independent", "searched")):
            c[group][field] = False
            self.assertEqual("unknown", base.exclusion_answer(c, DOMAIN)[0])
            c[group][field] = True
        c["primary"]["records"] = [record()]
        self.assertEqual("no", base.exclusion_answer(c, DOMAIN)[0])
        c["primary"]["records"][0].update(eventTime=INTERVAL["start"], clockUncertaintySeconds=1)
        self.assertEqual("unknown", base.exclusion_answer(c, DOMAIN)[0])
        c["primary"]["records"][0]["eventTime"] = "unparseable"
        self.assertEqual("unknown", base.exclusion_answer(c, DOMAIN)[0])

    def test_scope_requires_full_composite_identity(self):
        c = case(); scope(c)
        self.assertEqual("yes", restored.answer(CRITERIA["nodes"]["scope"], c, CRITERIA)[0])
        c["analysis"]["scope"]["entities"][0].pop("subjects")
        self.assertEqual("unknown", restored.answer(CRITERIA["nodes"]["scope"], c, CRITERIA)[0])
        scope(c)
        c["analysis"]["scope"]["entities"].append({"domain": "Identity", "subjectId": SUBJECTS["principalId"],
            "disposition": "excluded", "evidenceRefs": ["evidence:partial-exclusion"]})
        self.assertEqual("unknown", restored.answer(CRITERIA["nodes"]["scope"], c, CRITERIA)[0])

    def test_fact_led_scope_source_relation_effect_need_no_affirmative_hypothesis(self):
        for hypothesis_state in ("absent", "no", "unknown"):
            c = case(hypothesis_state != "absent"); scope(c); metric(c)
            r = c["primary"]["records"][0]
            if hypothesis_state == "no": r["facts"]["signal"]["value"] = "absent"
            if hypothesis_state == "unknown": r["facts"].pop("signal")
            c["analysis"]["attribution"] = {**assessment(c), "claimKind": "technical-source", "sourceEntityId": "service:idp",
                "alternatives": ["A different technical source produced this record."],
                "criterion": {"method": "test named technical source", "fact": "source", "equals": "service:idp"}}
            target = record("record:target", "origin:server", {"fileId": "file:17", "systemId": "host:alpha"})
            c["analysis"]["correlation"] = {**assessment(c), "sourceRecordId": r["id"], "targetDomain": "File",
                "targetSubjects": deepcopy(target["subjects"]), "targetRecord": target, "relationKind": "shared-identifier",
                "sourceFact": "relation.key", "targetFact": "relation.key"}
            for role in ("scope", "attribution", "correlation", "impact"):
                with self.subTest(hypothesis=hypothesis_state, role=role):
                    self.assertEqual("yes", restored.answer({"domain": "Identity", "role": role}, c, CRITERIA)[0])

    def test_explicit_prior_baseline_interval_is_comparable_and_ordered(self):
        c = case(False); metric(c)
        c["primary"]["records"][0]["facts"]["metric.before.time"]["value"] = "2026-10-01T09:30:00Z"
        self.assertEqual("unknown", restored.answer(CRITERIA["nodes"]["effect"], c, CRITERIA)[0])
        c["analysis"]["impact"]["baselineInterval"] = {"start": "2026-10-01T09:00:00Z", "end": INTERVAL["start"]}
        self.assertEqual("yes", restored.answer(CRITERIA["nodes"]["effect"], c, CRITERIA)[0])
        c["analysis"]["impact"]["baselineInterval"]["start"] = "2026-10-01T09:40:00Z"
        self.assertEqual("unknown", restored.answer(CRITERIA["nodes"]["effect"], c, CRITERIA)[0])

    def test_target_interval_can_be_separate_but_cannot_be_inferred(self):
        c = case(False); r = c["primary"]["records"][0]
        target = record("record:target", "origin:server", {"fileId": "file:17", "systemId": "host:alpha"})
        target["eventTime"] = "2026-10-01T11:30:00Z"
        a = {**assessment(c), "sourceRecordId": r["id"], "targetDomain": "File", "targetSubjects": target["subjects"],
            "targetRecord": target, "relationKind": "shared-identifier", "sourceFact": "relation.key", "targetFact": "relation.key"}
        c["analysis"]["correlation"] = a
        card = {"domain": "Identity", "role": "correlation"}
        self.assertEqual("unknown", restored.answer(card, c, CRITERIA)[0])
        a["targetInterval"] = {"start": INTERVAL["end"], "end": "2026-10-01T12:00:00Z"}
        self.assertEqual("yes", restored.answer(card, c, CRITERIA)[0])
        a["targetSubjects"].pop("systemId")
        self.assertEqual("unknown", restored.answer(card, c, CRITERIA)[0])

    def test_named_dependency_relation_must_match_both_endpoint_facts(self):
        c = case(False); scope(c); r = c["primary"]["records"][0]
        target = record("record:target", "origin:server", {"fileId": "file:17", "systemId": "host:alpha"})
        c["analysis"]["scope"]["entities"].append({"domain": "File", "subjectId": "file:17",
            "subjects": deepcopy(target["subjects"]), "disposition": "included", "evidenceRefs": ["evidence:target"]})
        c["analysis"]["dependency"] = {**assessment(c), "sourceRecordId": r["id"], "targetDomain": "File",
            "targetSubjects": deepcopy(target["subjects"]), "targetRecord": target,
            "claimKind": "documented-dependency", "direction": "downstream", "relationId": "relation:declared"}
        r["facts"]["dependency.source"] = fact(SUBJECTS["principalId"])
        target["facts"]["dependency.target"] = fact("file:17")
        for endpoint, prefix, subjects in ((r, "source", SUBJECTS), (target, "target", target["subjects"])):
            endpoint["facts"]["dependency.relationId"] = fact("relation:actual")
            endpoint["facts"]["dependency.direction"] = fact("downstream")
            endpoint["facts"].update({"dependency." + prefix + "." + k: fact(v) for k, v in subjects.items()})
        card = {"domain": "Identity", "role": "restored", "stage": "scope", "assessmentKind": "dependencies", "sourceFacet": FOCUS}
        self.assertEqual("no", restored.answer(card, c, CRITERIA)[0])
        c["analysis"]["dependency"]["relationId"] = "relation:actual"
        self.assertEqual("yes", restored.answer(card, c, CRITERIA)[0])

    def test_restored_temporal_relation_uses_separately_declared_target_interval(self):
        c = case(False); r = c["primary"]["records"][0]
        target = record("record:target", "origin:server", {"fileId": "file:17", "systemId": "host:alpha"})
        target["eventTime"] = "2026-10-01T11:30:00Z"
        c["analysis"]["correlation"] = {**assessment(c), "sourceRecordId": r["id"], "targetDomain": "File",
            "targetSubjects": deepcopy(target["subjects"]), "targetRecord": target,
            "targetInterval": {"start": INTERVAL["end"], "end": "2026-10-01T12:00:00Z"},
            "relationKind": "bounded-time-coincidence", "toleranceSeconds": 3600}
        card = {"domain": "Identity", "role": "restored", "stage": "correlate", "assessmentKind": "temporal", "sourceFacet": FOCUS}
        self.assertEqual("yes", restored.answer(card, c, CRITERIA)[0])

    def test_declared_corroboration_does_not_compare_local_record_identifiers(self):
        c = case(); witness = record("record:witness", "origin:server")
        witness["facts"]["event.id"]["value"] = "server-local:99"
        c["independent"]["records"] = [witness]
        card = {"domain": "Identity", "role": "restored", "stage": "validate", "assessmentKind": "corroboration", "sourceFacet": FOCUS}
        self.assertEqual("unknown", restored.answer(card, c, CRITERIA)[0])
        c["analysis"]["corroboration"] = {**assessment(c), "sourceRecordId": "record:primary",
            "sourceFact": "relation.key", "targetFact": "relation.key", "identifierNamespace": "bounded-session-id"}
        self.assertEqual("yes", restored.answer(card, c, CRITERIA)[0])
        witness["evidenceFacet"] = "other material"
        self.assertEqual("unknown", restored.answer(card, c, CRITERIA)[0])

    def test_terminal_retains_actual_answers_and_supplied_source_focus(self):
        c = case(False); retention(c, answer="unknown")
        c["retainedTrace"] = [{"nodeId": "focus-assessment", "answer": "unknown"}]
        card = {"domain": "Identity", "role": "assessed", "sourceFacet": "unrelated historical target facet"}
        self.assertEqual("yes", restored.answer(card, c, CRITERIA)[0])
        c["retention"]["assessments"][0]["answer"] = "yes"
        self.assertEqual("no", restored.answer(card, c, CRITERIA)[0])
        c.pop("retainedTrace"); c["retention"]["assessments"][0]["nodeId"] = "other-focus"
        self.assertEqual("unknown", restored.answer(card, c, CRITERIA)[0])
        c["retention"]["focusDispositions"][FOCUS] = "open"
        self.assertEqual("yes", restored.answer(card, c, CRITERIA)[0])

    def test_fixed_facet_retained_row_cannot_relabel_itself_as_current_focus(self):
        c = case(False); retention(c)
        c["focus"] = "artifact provenance"
        c["retention"]["focusDispositions"] = {"artifact provenance": "assessed"}
        c["retention"]["assessments"][0]["focus"] = c["focus"]
        card = {"domain": "Identity", "role": "restored", "stage": "terminal", "assessmentKind": "retention",
            "sourceFacet": "historical terminal label", "focusBinding": "supplied-investigation-focus"}
        self.assertEqual("unknown", restored.answer(card, c, CRITERIA)[0])

    def test_every_assessed_focus_needs_its_own_nonterminal_row(self):
        c = case(False); retention(c)
        card = {"domain": "Identity", "role": "assessed"}
        c["retention"]["focusDispositions"]["other material"] = "assessed"
        self.assertEqual("unknown", restored.answer(card, c, CRITERIA)[0])
        c["retention"]["focusDispositions"]["other material"] = "open"
        self.assertEqual("yes", restored.answer(card, c, CRITERIA)[0])

    def test_generic_retained_rows_preserve_explicit_visited_focuses(self):
        c = case(False); retention(c, "classification")
        row = c["retention"]["assessments"][0]
        row["focus"] = FOCUS
        c["retention"]["focusDispositions"]["other material"] = "assessed"
        other = {**deepcopy(row), "nodeId": "effect", "focus": "other material", "answer": "unknown"}
        c["retention"]["assessments"].append(other)
        c["retainedTrace"] = [{"nodeId": "classification", "answer": "yes", "focus": FOCUS},
                              {"nodeId": "effect", "answer": "unknown", "focus": "other material"}]
        card = {"domain": "Identity", "role": "assessed"}
        self.assertEqual("yes", restored.answer(card, c, CRITERIA)[0])
        other["focus"] = FOCUS
        self.assertEqual("unknown", restored.answer(card, c, CRITERIA)[0])

    def test_retention_preserves_full_original_hypothesis_not_reused_id(self):
        c = case(); retention(c)
        card = {"domain": "Identity", "role": "assessed"}
        self.assertEqual("yes", restored.answer(card, c, CRITERIA)[0])
        for field, value in (("statement", "A different proposition."), ("alternatives", ["Different alternative."]),
                             ("criterion", {"fact": "other", "equals": "observed", "method": "different test"})):
            changed = deepcopy(c); changed["retention"]["hypothesis"][field] = value
            self.assertEqual("unknown", restored.answer(card, changed, CRITERIA)[0])
        c["retention"]["assessments"][0]["hypothesisStatement"] = "A changed statement under the same ID."
        self.assertEqual("unknown", restored.answer(card, c, CRITERIA)[0])

    def test_unresolved_terminal_names_gap_without_requiring_absent_event(self):
        c = case(); retention(c, "classification", "unknown")
        c["retention"]["focusDispositions"][FOCUS] = "open"
        self.assertEqual("yes", restored.answer({"domain": "Identity", "role": "unresolved"}, c, CRITERIA)[0])
        self.assertEqual("yes", base.match_answer(c, DOMAIN)[0])


if __name__ == "__main__":
    unittest.main()
