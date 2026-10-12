"""Independent normalized investigation examples, never a raw-log truth oracle.

These examples are written without importing restoration generators or generated
scenario fixtures. Accepted facts/provenance are supplied analyst assertions;
passing these tests establishes only evaluator behavior, not incident truth,
external approval, authorization, or equivalent investigative coverage.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import restored_evidence as evaluator


# A separate bounded investigation in each domain. IDs are fictitious.
INVESTIGATIONS = {
    "Identity": ({"principalId": "svc-payroll", "identityAction": "token.exchange"},
                 "Unexpected service-account token exchange", "workload-identity-proxy", "token-count", "tokens"),
    "Host": ({"hostId": "build-runner-07", "processId": "pid:2411:start:20261012T120400Z"},
             "Build runner launched a shell from the package installer", "package-installer", "child-processes", "processes"),
    "Network": ({"sourceEndpoint": "10.70.0.7:49210", "destinationEndpoint": "203.0.113.12:443", "communicationId": "tls-flow-902"},
                "Build runner established an unexpected TLS session", "build-runner-07", "transferred-bytes", "bytes"),
    "Cloud": ({"tenantId": "lab-tenant", "resourceId": "storage/payroll-archive", "operationId": "op:policy-403"},
              "Storage policy update enabled anonymous reads", "deployment-role", "anonymous-reads", "requests"),
    "Email": ({"messageId": "<training-778@example.invalid>", "mailboxId": "payroll@example.invalid"},
              "Delivered message contained a credential collection link", "mail-relay-4", "link-visits", "requests"),
    "Application": ({"applicationId": "payroll-api", "requestId": "req:export-445"},
                    "Export request returned records beyond the requested page", "export-handler-v3", "returned-records", "records"),
    "File": ({"fileId": "sha256:training-export-02", "systemId": "finance-share"},
             "Payroll export was present in the shared staging directory", "export-worker", "download-count", "downloads"),
}
INTERVAL = {"start": "2026-10-12T12:00:00Z", "end": "2026-10-12T12:20:00Z"}
BASE_KINDS = {"entry": "event-match", "alternate": "event-match", "primaryValidation": "provenance",
              "independentValidation": "provenance", "classification": "hypothesis", "scope": "scope-bound",
              "correlation": "identifier-relation", "attribution": "technical-source", "impact": "metric-change",
              "assessed": "retention", "refuted": "retention", "unresolved": "retention", "exclusion": "retention"}


def route_card(card, focus, stage):
    """Supply evidence for an explicit generic adapter without changing the facet."""
    return {**card, "sourceFacet": focus, "stage": stage,
            "assessmentKind": card.get("assessmentKind", BASE_KINDS.get(card["role"]))}


def assessed(record_id, value):
    return {"value": value, "assessment": "accepted", "method": "analyst compared supplied normalized observations",
            "evidenceRefs": [record_id]}


def record(record_id, origin, subjects, facet, facts, event_time="2026-10-12T12:05:00Z"):
    return {"id": record_id, "origin": origin, "subjects": deepcopy(subjects),
            "eventTime": event_time, "clockUncertaintySeconds": 1, "evidenceFacet": facet,
            "provenanceAssessment": "accepted", "interpretationAssessment": "accepted",
            "assessmentEvidenceRefs": [origin + ":export-manifest", origin + ":interpretation-note"],
            "facts": {key: assessed(record_id, value) for key, value in facts.items()}}


def metric_facts(metric_id, unit, before=4, after=11):
    return {"metric.baseline": before, "metric.observed": after,
            "metric.baseline-unit": unit, "metric.observed-unit": unit,
            "metric.baseline-id": metric_id, "metric.observed-id": metric_id,
            "metric.baseline-time": "2026-10-12T12:01:00Z", "metric.observed-time": "2026-10-12T12:08:00Z"}


def metric_assessment(bound, record_id, metric_id, unit):
    return {**deepcopy(bound), "method": "compare own-subject before and after observations",
            "evidenceRefs": [record_id], "claimKind": "observed-metric-change", "metricId": metric_id, "unit": unit,
            "baselineFact": "metric.baseline", "observedFact": "metric.observed",
            "baselineUnitFact": "metric.baseline-unit", "observedUnitFact": "metric.observed-unit",
            "baselineMetricFact": "metric.baseline-id", "observedMetricFact": "metric.observed-id",
            "baselineTimeFact": "metric.baseline-time", "observedTimeFact": "metric.observed-time"}


def retained_row(node_id, case, answer="yes"):
    return {"nodeId": node_id, "answer": answer,
            "subjects": deepcopy(case["bindings"]), "interval": deepcopy(case["interval"]),
            "hypothesisId": case["analysis"]["hypothesis"]["hypothesisId"],
            "method": "retain separate normalized analyst assessment", "evidenceRefs": [case["primary"]["records"][0]["id"]],
            "rationale": "Retained bounded technical finding; alternative explanations remain recorded",
            "limitations": ["Supplied assertions; raw exports have not been independently authenticated"]}


def investigation(domain, card, criteria):
    subjects, statement, source, metric_id, unit = INVESTIGATIONS[domain]
    facet = card["sourceFacet"]
    first = criteria["domains"][domain]["bindings"][0]
    target_subjects = deepcopy(subjects)
    target_subjects[first] += ":dependent"
    primary_id, target_id = domain.lower() + ":primary", domain.lower() + ":target"
    source_subject, target_subject = subjects[first], target_subjects[first]
    hypothesis_id = domain.lower() + ":hypothesis:1"
    bound = {"subjects": deepcopy(subjects), "interval": deepcopy(INTERVAL), "hypothesisId": hypothesis_id}
    endpoint_facts = {**{"dependency.source." + key: value for key, value in subjects.items()},
                      **{"dependency.target." + key: value for key, value in target_subjects.items()},
                      "dependency.relationId": domain.lower() + ":documented-service-dependency:1"}
    facts = {"event.id": domain.lower() + ":event:1", "hypothesis.kind": statement,
             "technical.source": source, "behavior.pattern": "bounded-export-chain", "request.link": "workflow:42",
             # A genuine relation is a pair plus direction, not two unrelated self-identities.
             "dependency.source": source_subject, "dependency.target": target_subject, "dependency.direction": "upstream", **endpoint_facts,
             **metric_facts(metric_id, unit)}
    primary = record(primary_id, domain.lower() + ":sensor-a", subjects, facet, facts)
    independent = record(domain.lower() + ":witness", domain.lower() + ":sensor-b", subjects, facet, facts)
    target = record(target_id, domain.lower() + ":service-inventory", target_subjects, facet,
                    {"request.link": "workflow:42", "dependency.source": source_subject,
                     "dependency.target": target_subject, "dependency.direction": "upstream", **endpoint_facts,
                     **metric_facts(metric_id + ":dependent", unit, before=2, after=5)})
    criterion = {"fact": "hypothesis.kind", "equals": statement, "method": "compare declared technical event discriminator"}
    relation = {**deepcopy(bound), "method": "compare independently assessed shared workflow identifier",
                "evidenceRefs": [primary_id, target_id], "sourceRecordId": primary_id,
                "targetDomain": domain, "targetSubjects": deepcopy(target_subjects), "targetRecord": deepcopy(target),
                "relationKind": "shared-identifier", "sourceFact": "request.link", "targetFact": "request.link"}
    analysis = {
        "hypothesis": {**deepcopy(bound), "statement": statement, "alternatives": ["Authorized maintenance", "Sensor interpretation error"],
                       "criterion": deepcopy(criterion)},
        "baseline": {**deepcopy(bound), "comparatorId": domain.lower() + ":approved-operating-profile",
                     "evidenceRefs": [primary_id, "analyst:comparator-applicability"], "criterion": deepcopy(criterion)},
        "scope": {**deepcopy(bound), "method": "record individual entity inclusion and unresolved neighbors",
                  "evidenceRefs": [primary_id, target_id], "claimsCompletePopulation": False,
                  "entities": [{"domain": domain, "subjectId": source_subject, "subjects": deepcopy(subjects),
                                "disposition": "included", "evidenceRefs": [primary_id]},
                               {"domain": domain, "subjectId": target_subject, "subjects": deepcopy(target_subjects),
                                "disposition": "included", "evidenceRefs": [target_id]},
                               {"domain": domain, "subjectId": source_subject + ":unresolved-neighbor", "disposition": "unknown"}]},
        "correlation": deepcopy(relation),
        "dependency": {**deepcopy(relation), "claimKind": "documented-dependency", "direction": "upstream",
                       "method": "compare documented directed endpoint pair on both normalized sources"},
        "attribution": {**deepcopy(bound), "method": "evaluate technical source discriminator",
                        "evidenceRefs": [primary_id], "claimKind": "technical-source", "sourceEntityId": source,
                        "alternatives": ["Proxy-mediated execution", "Reused account"],
                        "criterion": {"fact": "technical.source", "equals": source, "method": "compare source identity"}},
        "pattern": {**deepcopy(bound), "method": "compare observed sequence discriminator", "evidenceRefs": [primary_id],
                    "claimKind": "technical-behavior-pattern", "patternId": "bounded-export-chain",
                    "alternatives": ["Authorized batch export"],
                    "criterion": {"fact": "behavior.pattern", "equals": "bounded-export-chain", "method": "compare bounded technical pattern"}},
        "impact": metric_assessment(bound, primary_id, metric_id, unit),
    }
    target_bound = {**deepcopy(bound), "subjects": deepcopy(target_subjects)}
    additional = {"domain": domain, "bindings": deepcopy(target_subjects), "interval": deepcopy(INTERVAL),
                  "analysis": {"hypothesis": {**deepcopy(analysis["hypothesis"]), "subjects": deepcopy(target_subjects)},
                               "impact": metric_assessment(target_bound, target_id, metric_id + ":dependent", unit)}}
    analysis["additionalEffect"] = {**deepcopy(relation), "assessment": additional}
    if card["assessmentKind"] == "temporal":
        analysis["correlation"].update(relationKind="bounded-time-coincidence", toleranceSeconds=5)
    case = {"domain": domain, "bindings": deepcopy(subjects), "interval": deepcopy(INTERVAL), "focus": facet,
            "evidenceKind": "independently-authored-normalized-investigation", "primaryOrigin": primary["origin"],
            "primary": {"accessible": True, "searched": True, "records": [primary]},
            "independent": {"accessible": True, "searched": True, "records": [independent]}, "analysis": analysis}
    case["retention"] = {"subjects": deepcopy(subjects), "interval": deepcopy(INTERVAL),
                         "graphVersion": criteria["graphVersion"], "closesInvestigation": False,
                         "focusDispositions": {facet: "open"},
                         "assessments": [retained_row(criteria["domains"][domain]["entry"], case)]}
    return case


class IndependentInvestigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.criteria = json.loads((ROOT / "drafts/core/entry-evidence-criteria.json").read_text())
        cls.graph = json.loads((ROOT / "drafts/core/tensor.core.graph.json").read_text())
        cls.cards = {}
        for node_id, card in cls.criteria["nodes"].items():
            if "assessmentKind" in card:
                cls.cards.setdefault((card["domain"], card["assessmentKind"]), (node_id, card))

    def cases(self, kind=None):
        for (domain, available_kind), (node_id, card) in self.cards.items():
            if kind is None or kind == available_kind:
                yield domain, node_id, card, investigation(domain, card, self.criteria)

    def expect(self, expected, card, case):
        answer, reason = evaluator.answer(card, case, self.criteria)
        self.assertEqual(expected, answer, reason)

    def test_independent_positive_examples_cover_every_available_domain_and_kind(self):
        self.assertEqual(set(INVESTIGATIONS), set(self.criteria["domains"]))
        for domain, node_id, card, case in self.cases():
            with self.subTest(domain=domain, kind=card["assessmentKind"], node=node_id):
                self.expect("yes", card, case)

    def test_operational_counterexamples_do_not_generalize_beyond_question(self):
        for domain, node_id, card, case in self.cases():
            kind, a = card["assessmentKind"], case["analysis"]
            source = case["primary"]["records"][0]
            if kind == "event-match":
                case["primary"]["records"] = []  # searched material only; event absence remains unproved
            elif kind == "provenance":
                source["provenanceAssessment"] = "rejected"
            elif kind in ("baseline", "hypothesis"):
                role = "baseline" if kind == "baseline" else "hypothesis"
                source["facts"][a[role]["criterion"]["fact"]]["value"] = "different technical observation"
            elif kind == "corroboration":
                case["independent"]["records"][0]["facts"]["event.id"]["value"] = "different event"
            elif kind == "scope-bound":
                a["scope"]["entities"][0]["disposition"] = "excluded"
            elif kind == "additional-entities":
                a["scope"]["entities"] = [a["scope"]["entities"][0], a["scope"]["entities"][2]]
            elif kind == "dependencies":
                target = a["dependency"]["targetRecord"]
                target["facts"]["dependency.target"]["value"] = "different dependent service"
                first = self.criteria["domains"][domain]["bindings"][0]
                target["facts"]["dependency.target." + first]["value"] = "different dependent service"
            elif kind == "temporal":
                a["correlation"]["targetRecord"]["eventTime"] = "2026-10-12T12:10:00Z"
            elif kind == "identifier-relation":
                a["correlation"]["targetRecord"]["facts"]["request.link"]["value"] = "workflow:unrelated"
            elif kind in ("technical-source", "behavior-pattern"):
                key = "technical.source" if kind == "technical-source" else "behavior.pattern"
                source["facts"][key]["value"] = "different technical discriminator"
            elif kind == "metric-change":
                source["facts"]["metric.observed"]["value"] = source["facts"]["metric.baseline"]["value"]
            elif kind == "additional-impact":
                target = a["additionalEffect"]["targetRecord"]
                target["facts"]["metric.observed"]["value"] = target["facts"]["metric.baseline"]["value"]
            elif kind == "retention":
                case["retention"]["knownMissing"] = True
            else:
                self.fail("Unhandled independent investigation kind: " + kind)
            with self.subTest(domain=domain, kind=kind, node=node_id):
                self.expect("no", card, case)

    def test_unavailable_or_conflicting_evidence_remains_unknown(self):
        for domain, node_id, card, case in self.cases():
            case["materialConflict"] = True
            with self.subTest(domain=domain, node=node_id):
                self.expect("unknown", card, case)

    def test_endpoint_self_identities_do_not_prove_a_dependency_pair(self):
        for domain, node_id, card, case in self.cases("dependencies"):
            source, target = case["primary"]["records"][0], case["analysis"]["dependency"]["targetRecord"]
            source["facts"].pop("dependency.target")
            target["facts"].pop("dependency.source")
            for endpoint in (source, target):
                endpoint["facts"].pop("dependency.direction")
                for name in list(endpoint["facts"]):
                    if name.startswith(("dependency.source.", "dependency.target.")) or name == "dependency.relationId":
                        endpoint["facts"].pop(name)
            with self.subTest(domain=domain, node=node_id):
                self.expect("unknown", card, case)

    def test_dependency_direction_cannot_be_reversed_without_assessed_support(self):
        for domain, node_id, card, case in self.cases("dependencies"):
            case["analysis"]["dependency"]["direction"] = "downstream"
            with self.subTest(domain=domain, node=node_id):
                self.expect("no", card, case)

    def test_rejected_independent_export_does_not_hide_a_valid_corroborating_record(self):
        for domain, node_id, card, case in self.cases("corroboration"):
            rejected = deepcopy(case["independent"]["records"][0])
            rejected["id"] += ":rejected-copy"
            rejected["origin"] += ":corrupt-export"
            rejected["provenanceAssessment"] = "rejected"
            # The next independent export remains accepted and agrees on event.id.
            case["independent"]["records"].insert(0, rejected)
            with self.subTest(domain=domain, node=node_id):
                self.expect("yes", card, case)

    def test_accepted_contradictory_corroborating_witnesses_remain_unknown_in_either_order(self):
        for domain, node_id, card, original in self.cases("corroboration"):
            for reverse in (False, True):
                case = deepcopy(original)
                contradiction = deepcopy(case["independent"]["records"][0])
                contradiction["id"] += ":different-event"
                contradiction["origin"] += ":third-sensor"
                contradiction["facts"]["event.id"]["value"] = "a-different-bound-event"
                case["independent"]["records"].append(contradiction)
                if reverse:
                    case["independent"]["records"].reverse()
                with self.subTest(domain=domain, node=node_id, reverse=reverse):
                    self.expect("unknown", card, case)

    def test_same_cloud_tenant_cannot_substitute_a_different_dependency_resource(self):
        _, card = self.cards[("Cloud", "dependencies")]
        case = investigation("Cloud", card, self.criteria)
        dependency = case["analysis"]["dependency"]
        dependency["targetSubjects"]["resourceId"] = "storage/unrelated-resource"
        dependency["targetRecord"]["subjects"]["resourceId"] = "storage/unrelated-resource"
        # The accepted dependency.target.resourceId still names payroll-archive.
        self.expect("no", card, case)

    def test_dependency_cannot_claim_target_inclusion_when_scope_excludes_it(self):
        for domain, node_id, card, case in self.cases("dependencies"):
            case["analysis"]["scope"]["entities"][1]["disposition"] = "excluded"
            with self.subTest(domain=domain, node=node_id):
                self.expect("no", card, case)

    def test_clock_bounds_crossing_the_investigation_interval_are_unresolved(self):
        for domain, node_id, card, case in self.cases("temporal"):
            case["primary"]["records"][0]["eventTime"] = INTERVAL["start"]
            case["analysis"]["correlation"]["targetRecord"]["eventTime"] = INTERVAL["start"]
            # Coincidence is numerically certain, but event membership in [start,end) is not.
            with self.subTest(domain=domain, node=node_id):
                self.expect("unknown", card, case)

    def test_conflicting_entity_dispositions_are_not_a_supported_scope(self):
        for domain, node_id, card, case in self.cases():
            if card["assessmentKind"] not in ("scope-bound", "additional-entities"):
                continue
            contradicted = deepcopy(case["analysis"]["scope"]["entities"][1])
            contradicted["disposition"] = "excluded"
            contradicted["evidenceRefs"] = [domain.lower() + ":conflicting-inventory"]
            case["analysis"]["scope"]["entities"].append(contradicted)
            with self.subTest(domain=domain, kind=card["assessmentKind"], node=node_id):
                self.expect("unknown", card, case)

    def test_mixed_composite_and_legacy_rows_cannot_hide_a_scope_conflict(self):
        for domain, node_id, card, case in self.cases():
            if card["assessmentKind"] not in ("scope-bound", "additional-entities"):
                continue
            contradicted = deepcopy(case["analysis"]["scope"]["entities"][0])
            contradicted.pop("subjects")
            contradicted["disposition"] = "excluded"
            case["analysis"]["scope"]["entities"].append(contradicted)
            with self.subTest(domain=domain, node=node_id):
                self.expect("unknown", card, case)

    def test_distinct_composite_entity_exclusion_does_not_refute_source_inclusion(self):
        for domain, node_id, card, case in self.cases("scope-bound"):
            fields = self.criteria["domains"][domain]["bindings"]
            sibling = case["analysis"]["scope"]["entities"][1]
            sibling["subjectId"] = case["bindings"][fields[0]]
            sibling["subjects"] = deepcopy(case["bindings"])
            sibling["subjects"][fields[1]] += ":different-context"
            sibling["disposition"] = "excluded"
            with self.subTest(domain=domain, node=node_id):
                self.expect("yes", card, case)

    def test_unrelated_retention_ledger_cannot_refute_this_bound_retention(self):
        for domain, node_id, card, case in self.cases("retention"):
            first = self.criteria["domains"][domain]["bindings"][0]
            case["retention"]["subjects"][first] = "unrelated-investigation"
            case["retention"]["knownMissing"] = True
            with self.subTest(domain=domain, node=node_id):
                self.expect("unknown", card, case)

    def test_retention_row_cannot_silently_name_another_hypothesis(self):
        for domain, node_id, card, case in self.cases("retention"):
            case["retention"]["assessments"][0]["hypothesisId"] = "unrelated:hypothesis"
            with self.subTest(domain=domain, node=node_id):
                self.expect("unknown", card, case)

    def test_additional_subject_needs_its_own_baseline_and_link(self):
        for domain, node_id, card, original in self.cases("additional-impact"):
            for variation in ("missing-own-baseline", "different-link", "different-units", "different-subject"):
                case = deepcopy(original)
                extra = case["analysis"]["additionalEffect"]
                target = extra["targetRecord"]
                if variation == "missing-own-baseline":
                    target["facts"].pop("metric.baseline")
                elif variation == "different-link":
                    target["facts"]["request.link"]["value"] = "unrelated:workflow"
                elif variation == "different-units":
                    target["facts"]["metric.observed-unit"]["value"] = "incompatible-unit"
                else:
                    extra["assessment"]["bindings"] = {}
                with self.subTest(domain=domain, variation=variation, node=node_id):
                    self.expect("unknown", card, case)

    def test_same_file_on_a_different_system_can_have_its_own_additional_effect(self):
        _, card = self.cards[("File", "additional-impact")]
        case = investigation("File", card, self.criteria)
        extra = case["analysis"]["additionalEffect"]
        target_subjects = {"fileId": case["bindings"]["fileId"], "systemId": "offsite-backup-share"}
        extra["targetSubjects"] = deepcopy(target_subjects)
        extra["targetRecord"]["subjects"] = deepcopy(target_subjects)
        extra["assessment"]["bindings"] = deepcopy(target_subjects)
        extra["assessment"]["analysis"]["hypothesis"]["subjects"] = deepcopy(target_subjects)
        extra["assessment"]["analysis"]["impact"]["subjects"] = deepcopy(target_subjects)
        self.expect("yes", card, case)

    def test_undeclared_display_labels_cannot_manufacture_an_additional_entity(self):
        for domain, node_id, card, case in self.cases("additional-entities"):
            source = case["analysis"]["scope"]["entities"][0]
            alias = deepcopy(source)
            alias["subjects"]["displayLabel"] = "Another display name for the same declared identity"
            case["analysis"]["scope"]["entities"] = [source, alias]
            with self.subTest(domain=domain, node=node_id):
                self.expect("no", card, case)

    def test_undeclared_display_label_cannot_manufacture_an_additional_effect_subject(self):
        _, card = self.cards[("File", "additional-impact")]
        case = investigation("File", card, self.criteria)
        extra = case["analysis"]["additionalEffect"]
        alias = {**case["bindings"], "displayLabel": "Presentation alias for the same file and system"}
        extra["targetSubjects"] = deepcopy(alias)
        extra["targetRecord"]["subjects"] = deepcopy(alias)
        extra["assessment"]["bindings"] = deepcopy(alias)
        extra["assessment"]["analysis"]["hypothesis"]["subjects"] = deepcopy(alias)
        extra["assessment"]["analysis"]["impact"]["subjects"] = deepcopy(alias)
        self.expect("unknown", card, case)

    def test_generic_assessed_terminal_requires_retained_relationship_source_and_effect_answers(self):
        for domain in INVESTIGATIONS:
            node_id = self.criteria["domains"][domain]["assessed"]
            card = self.criteria["nodes"][node_id]
            focus = self.cards[(domain, "event-match")][1]["sourceFacet"]
            case = investigation(domain, route_card(card, focus, "terminal"), self.criteria)
            # Only the entry assessment is retained: none of the separate downstream answers is present.
            with self.subTest(domain=domain, node=node_id):
                self.expect("unknown", card, case)

    def test_generic_unresolved_terminal_cannot_relabel_an_all_positive_ledger(self):
        for domain in INVESTIGATIONS:
            node_id = self.criteria["domains"][domain]["unresolved"]
            card = self.criteria["nodes"][node_id]
            focus = self.cards[(domain, "event-match")][1]["sourceFacet"]
            case = investigation(domain, route_card(card, focus, "terminal"), self.criteria)
            case["retention"]["focusDispositions"][focus] = "assessed"
            positive_entry = self.cards[(domain, "event-match")][0]
            case["retention"]["assessments"] = [retained_row(positive_entry, case)]
            with self.subTest(domain=domain, node=node_id):
                self.expect("unknown", card, case)

    def test_same_file_on_another_system_dependency_needs_its_own_scope_inclusion(self):
        _, card = self.cards[("File", "dependencies")]
        case = investigation("File", card, self.criteria)
        dependency = case["analysis"]["dependency"]
        target_subjects = {"fileId": case["bindings"]["fileId"], "systemId": "offsite-backup-share"}
        dependency["targetSubjects"] = deepcopy(target_subjects)
        dependency["targetRecord"]["subjects"] = deepcopy(target_subjects)
        for endpoint in (case["primary"]["records"][0], dependency["targetRecord"]):
            endpoint["facts"]["dependency.target"]["value"] = target_subjects["fileId"]
            for field, value in target_subjects.items():
                endpoint["facts"]["dependency.target." + field]["value"] = value
        case["analysis"]["scope"]["entities"].pop(1)
        # The only included file entity is on finance-share, not offsite-backup-share.
        self.expect("unknown", card, case)

    def route_suite(self, domain, entry=None, optional_kind=None, optional_answer=None, singleton=False):
        edges = {(edge["source"], edge["decision"]): edge["target"] for edge in self.graph["edges"]}
        if entry is None:
            entry = min((node_id for (d, kind), (node_id, _) in self.cards.items() if d == domain and kind == "event-match"),
                        key=lambda value: int(value[1:]))
        current, rows, fixtures, by_node, expected = entry, [], {}, {}, []
        focus = self.criteria["nodes"][entry]["sourceFacet"]
        stages = {node["id"]: node["archetype"] for node in self.graph["nodes"]}
        while True:
            card = self.criteria["nodes"][current]
            stage = stages[current]
            case = investigation(domain, route_card(card, focus, stage), self.criteria)
            if singleton:
                case["analysis"]["scope"]["entities"] = case["analysis"]["scope"]["entities"][:1]
            if optional_kind == "dependencies":
                dependency = case["analysis"]["dependency"]
                if optional_answer == "no":
                    dependency["direction"] = "downstream"  # assessed sources document upstream instead
                elif optional_answer == "unknown":
                    dependency["evidenceRefs"] = []  # entity scope is supported; this proposed relation remains open
            outcome = optional_answer if optional_kind is not None and card.get("assessmentKind") == optional_kind else "yes"
            if stage == "terminal":
                case["retention"]["assessments"] = deepcopy(rows)
                mandatory_scope = self.criteria["domains"][domain]["scope"][0]
                case["retention"]["prerequisiteAssessments"] = [retained_row(mandatory_scope, case)]
                if not any(self.criteria["nodes"][row["nodeId"]].get("stage") == "classify"
                           or self.criteria["nodes"][row["nodeId"]].get("role") == "classification" for row in rows):
                    classification = self.criteria["domains"][domain]["classification"][0]
                    case["retention"]["prerequisiteAssessments"].append(retained_row(classification, case))
            fixtures[current] = case
            by_node[current] = {"evidenceRef": current}
            expected.append([current, outcome])
            rows.append(retained_row(current, case, outcome))
            if stage == "terminal":
                break
            current = edges[current, outcome]
        path = {"id": domain.lower() + ":independent-route", "entry": entry,
                "evidenceByNode": by_node, "expectedTrace": expected}
        return {"graphVersion": self.graph["version"], "restoredCases": [], "restoredFixtures": fixtures, "restoredPaths": [path]}

    def test_complete_independent_routes_retain_bounded_answers_in_all_domains(self):
        for domain in INVESTIGATIONS:
            with self.subTest(domain=domain):
                results = evaluator.run_cases(self.graph, self.criteria, self.route_suite(domain))
                self.assertEqual(1, len(results))
                self.assertTrue(results[0]["passed"], results[0])

    def test_singleton_route_retains_optional_additional_entities_no_and_reaches_qualified_handoff(self):
        suite = self.route_suite("Identity", entry="Q15", optional_kind="additional-entities", optional_answer="no", singleton=True)
        expected = suite["restoredPaths"][0]["expectedTrace"]
        self.assertIn(["Q288", "no"], expected)
        self.assertEqual([self.criteria["domains"]["Identity"]["assessed"], "yes"], expected[-1])
        results = evaluator.run_cases(self.graph, self.criteria, suite)
        self.assertTrue(results[0]["passed"], results[0])
        self.assertIn({"nodeId": "Q288", "answer": "no"}, results[0]["trace"])
        terminal = suite["restoredFixtures"][expected[-1][0]]
        self.assertEqual(1, len(terminal["retention"]["prerequisiteAssessments"]))
        self.assertEqual(self.criteria["domains"]["Identity"]["scope"][0], terminal["retention"]["prerequisiteAssessments"][0]["nodeId"])

    def test_dependency_no_or_unknown_is_retained_separately_from_supported_mandatory_scope(self):
        for domain, node_id, _, _ in self.cases("dependencies"):
            for optional_answer in ("no", "unknown"):
                suite = self.route_suite(domain, entry=node_id, optional_kind="dependencies", optional_answer=optional_answer)
                expected = suite["restoredPaths"][0]["expectedTrace"]
                with self.subTest(domain=domain, node=node_id, optional_answer=optional_answer):
                    self.assertEqual([node_id, optional_answer], expected[0])
                    self.assertEqual([self.criteria["domains"][domain]["assessed"], "yes"], expected[-1])
                    results = evaluator.run_cases(self.graph, self.criteria, suite)
                    self.assertTrue(results[0]["passed"], results[0])
                    terminal = suite["restoredFixtures"][expected[-1][0]]
                    self.assertIn(retained_row(node_id, terminal, optional_answer), terminal["retention"]["assessments"])
                    scope_rows = [row for row in terminal["retention"]["prerequisiteAssessments"]
                                  if row["nodeId"] == self.criteria["domains"][domain]["scope"][0]]
                    self.assertEqual(1, len(scope_rows))
                    self.assertEqual("yes", scope_rows[0]["answer"])

    def test_route_rejects_silent_subject_or_time_drift(self):
        for domain in INVESTIGATIONS:
            for drift in ("subject", "time"):
                suite = self.route_suite(domain)
                node = suite["restoredPaths"][0]["expectedTrace"][2][0]
                case = suite["restoredFixtures"][node]
                if drift == "subject":
                    key = self.criteria["domains"][domain]["bindings"][0]
                    case["bindings"][key] = "unrelated-investigation"
                else:
                    case["interval"]["end"] = "2026-10-12T12:30:00Z"
                with self.subTest(domain=domain, drift=drift):
                    with self.assertRaises(ValueError):
                        evaluator.run_cases(self.graph, self.criteria, suite)

    def test_route_rejects_silent_hypothesis_drift(self):
        for domain in INVESTIGATIONS:
            suite = self.route_suite(domain)
            after_classification = False
            for node, _ in suite["restoredPaths"][0]["expectedTrace"]:
                case = suite["restoredFixtures"][node]
                card = self.criteria["nodes"][node]
                if after_classification:
                    for assessment in case["analysis"].values():
                        if isinstance(assessment, dict) and "hypothesisId" in assessment:
                            assessment["hypothesisId"] = domain.lower() + ":replacement-hypothesis"
                    for row in case["retention"]["assessments"]:
                        row["hypothesisId"] = domain.lower() + ":replacement-hypothesis"
                if card.get("stage") == "classify" or card.get("role") == "classification":
                    after_classification = True
            with self.subTest(domain=domain):
                with self.assertRaises(ValueError):
                    evaluator.run_cases(self.graph, self.criteria, suite)

    def test_route_rejects_changed_hypothesis_meaning_under_the_same_id(self):
        for domain in INVESTIGATIONS:
            suite = self.route_suite(domain)
            after_classification = False
            for node, _ in suite["restoredPaths"][0]["expectedTrace"]:
                case = suite["restoredFixtures"][node]
                card = self.criteria["nodes"][node]
                if after_classification:
                    replacement = "A different technical hypothesis under a reused identifier"
                    case["analysis"]["hypothesis"]["statement"] = replacement
                    case["analysis"]["hypothesis"]["criterion"]["equals"] = replacement
                    case["primary"]["records"][0]["facts"]["hypothesis.kind"]["value"] = replacement
                if card.get("stage") == "classify" or card.get("role") == "classification":
                    after_classification = True
            with self.subTest(domain=domain):
                with self.assertRaises(ValueError):
                    evaluator.run_cases(self.graph, self.criteria, suite)


if __name__ == "__main__":
    unittest.main()
