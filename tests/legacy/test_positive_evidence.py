"""Downstream behavior checks using evidence mutations and real graph traversal."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import evaluate_entry_scenarios as evaluator


class PositiveEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = json.loads((ROOT / "drafts/core/tensor.core.graph.json").read_text())
        cls.criteria = json.loads((ROOT / "drafts/core/entry-evidence-criteria.json").read_text())
        cls.suite = evaluator.expand_suite(json.loads((ROOT / "drafts/core/scenarios/entry-evidence-cases.json").read_text()))

    def case(self, case_id):
        return copy.deepcopy(next(c for c in self.suite["cases"] if c["id"] == case_id))

    def result(self, case):
        return evaluator.evaluate_case(self.graph, self.criteria, case)

    def answer(self, result, role):
        return next(t["answer"] for t in result["trace"] if self.criteria["nodes"][t["nodeId"]]["role"] == role)

    def test_every_classification_route_exercises_all_three_answers(self):
        seen = {}
        for case in self.suite["cases"]:
            for item in self.result(case)["trace"]:
                if self.criteria["nodes"][item["nodeId"]]["role"] == "classification":
                    seen.setdefault(item["nodeId"], set()).add(item["answer"])
        self.assertEqual(13, len(seen))
        self.assertTrue(all(answers == {"yes", "no", "unknown"} for answers in seen.values()))

    def test_independent_scope_can_be_contradicted_without_losing_event(self):
        for domain in self.criteria["domains"]:
            case = self.case(domain.lower() + "-independent-recovery")
            case["analysis"]["scope"]["entities"][0]["disposition"] = "excluded"
            result = self.result(case)
            self.assertEqual("no", self.answer(result, "scope"))
            self.assertEqual("yes", self.answer(result, "classification"))
            self.assertEqual("unresolved", result["state"])

    def test_missing_relation_or_attribution_does_not_block_observed_effect(self):
        for domain in self.criteria["domains"]:
            for role in ("correlation", "attribution"):
                case = self.case(domain.lower() + "-supported-record")
                case["analysis"].pop(role)
                result = self.result(case)
                self.assertEqual("unknown", self.answer(result, role))
                self.assertEqual("yes", self.answer(result, "impact"))
                self.assertEqual("partial-findings", result["state"])

    def test_correlation_requires_target_context_and_validated_lineage(self):
        for fault in ("wrong-source", "unknown-provenance", "causation", "missing-fact", "no-ref", "duplicate-record"):
            case = self.case("host-independent-cross-domain-relation")
            relation = case["analysis"]["correlation"]
            target = relation["targetRecord"]
            if fault == "wrong-source":
                relation["sourceRecordId"] = "unrelated-event"
            elif fault == "unknown-provenance":
                target["provenanceAssessment"] = "unknown"
            elif fault == "causation":
                relation["relationKind"] = "caused-by"
            elif fault == "missing-fact":
                target["facts"].clear()
            elif fault == "no-ref":
                target["facts"]["relation.id"]["evidenceRefs"] = []
            else:
                target["id"] = relation["sourceRecordId"]
            with self.subTest(fault=fault):
                result = self.result(case)
                self.assertEqual("unknown", self.answer(result, "correlation"))
                self.assertEqual("yes", self.answer(result, "impact"))

    def test_metric_effect_requires_comparable_units_identity_times_and_numbers(self):
        for fault in ("units", "metric", "reversed-time", "outside-window", "missing-time", "bool", "nan", "unassessed-baseline"):
            case = self.case("cloud-supported-record")
            facts = case["primary"]["records"][0]["facts"]
            if fault == "units":
                facts["effect.baseline-unit"]["value"] = "unrelated-unit"
            elif fault == "metric":
                facts["effect.baseline-metric"]["value"] = "other-population"
            elif fault == "reversed-time":
                facts["effect.baseline-time"]["value"] = "2026-10-01T10:50:00Z"
            elif fault == "outside-window":
                facts["effect.observed-time"]["value"] = case["interval"]["end"]
            elif fault == "missing-time":
                facts.pop("effect.baseline-time")
            elif fault == "bool":
                facts["effect.observed"]["value"] = True
            elif fault == "nan":
                facts["effect.observed"]["value"] = float("nan")
            else:
                facts["effect.baseline"]["assessment"] = "unknown"
            with self.subTest(fault=fault):
                self.assertEqual("unknown", self.answer(self.result(case), "impact"))

    def test_positive_route_cannot_silently_change_domain(self):
        graph = copy.deepcopy(self.graph)
        for edge in graph["edges"]:
            if (edge["source"], edge["decision"]) == ("Q233", "yes"):
                edge["target"] = "Q261"
        with self.assertRaisesRegex(ValueError, "changed domain"):
            evaluator.evaluate_case(graph, self.criteria, self.case("identity-supported-record"))

    def test_refuted_classification_cannot_be_promoted_by_a_bad_edge(self):
        graph = copy.deepcopy(self.graph)
        for edge in graph["edges"]:
            if (edge["source"], edge["decision"]) == ("Q233", "no"):
                edge["target"] = "Q253"
        result = evaluator.evaluate_case(graph, self.criteria, self.case("identity-hypothesis-refuted"))
        self.assertEqual("unresolved", result["state"])
        self.assertEqual("unknown", result["trace"][-1]["answer"])

    def test_exact_prior_draft_and_detached_material_are_retained(self):
        folder = ROOT / "drafts/core/reviews/2026-10-11-positive-evidence"
        manifest = json.loads((folder / "prior-draft-manifest.json").read_text())
        raw = (folder / manifest["snapshot"]).read_bytes()
        self.assertEqual(manifest["sourceSha256"], hashlib.sha256(raw).hexdigest())
        old = json.loads(raw)
        before, after = {n["id"] for n in old["nodes"]}, {n["id"] for n in self.graph["nodes"]}
        self.assertEqual(before - after, set(manifest["detachedNodeIds"]))
        self.assertEqual(88, len(before - after))
        old_by_id = {n["id"]: n for n in old["nodes"]}
        for node in self.graph["nodes"]:
            if self.criteria["nodes"][node["id"]]["role"] in ("entry", "alternate", "primaryValidation", "independentValidation", "exclusion", "unresolved"):
                self.assertEqual(old_by_id[node["id"]]["text"], node["text"])

    def test_protected_files_match_pre_change_receipt(self):
        receipt = json.loads((ROOT / "drafts/core/reviews/2026-10-11-entry-evidence/preservation.json").read_text())
        for path, expected in receipt["sha256ByPath"].items():
            with self.subTest(path=path):
                self.assertEqual(expected, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())

    def test_fixture_inheritance_preserves_independent_expectations(self):
        base = self.case("host-supported-record")
        bad = {"id": "derived", "extends": base["id"], "patch": {}}
        with self.assertRaisesRegex(ValueError, "explicit independent expectations"):
            evaluator.expand_suite({"cases": [base, bad]})
        for variant in ({**bad, "extends": "missing"}, {**bad, "id": base["id"]}):
            with self.assertRaises(ValueError):
                evaluator.expand_suite({"cases": [base, variant]})
        bad.update({"expectedTrace": [], "expectedState": "unresolved", "patch": {"expectedState": "bounded-findings"}})
        with self.assertRaisesRegex(ValueError, "evidence only"):
            evaluator.expand_suite({"cases": [base, bad]})

    def test_strict_release_authoring_keeps_cross_domain_quota_blocking(self):
        from core_graph_pipeline import validate_and_measure
        errors, _, _ = validate_and_measure(self.graph["nodes"], self.graph["edges"], self.graph["entryNodeIds"], [])
        self.assertTrue(any("Cross-domain edge ratio" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
