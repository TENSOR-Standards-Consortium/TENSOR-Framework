"""Proof that current acceptance rejects unsafe packages, not low proxy scores."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_entry_scenarios import expand_suite
from graph_assurance_policy import assess_evidence, build_acceptance, DIAGNOSTIC_IDS
from review_topology_gates import experiments, snapshot


class AssurancePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (ROOT / "drafts/core/tensor.core.graph.json").read_bytes()
        cls.graph = json.loads(raw)
        cls.sha = hashlib.sha256(raw).hexdigest()
        cls.criteria = json.loads((ROOT / "drafts/core/entry-evidence-criteria.json").read_bytes())
        cls.suite = json.loads((ROOT / "drafts/core/scenarios/entry-evidence-cases.json").read_bytes())
        historical = json.loads((ROOT / "drafts/core/reviews/2026-10-11-topology-policy/reviewed-graph.graph.json").read_bytes())
        cls.experiments = experiments(historical, cls.criteria, cls.suite)
        cls.reference = snapshot(cls.graph)["reference"]

    def assess(self, graph=None, criteria=None, suite=None):
        return assess_evidence(graph or self.graph, self.sha, criteria or self.criteria, suite or self.suite)

    def test_low_diagnostics_cannot_fail_valid_evidence_acceptance(self):
        reference = copy.deepcopy(self.reference)
        for item in reference["gates"]:
            if item["id"] in DIAGNOSTIC_IDS:
                item["passed"] = False
        reference["allPassed"] = False
        report = build_acceptance([], reference, self.assess())
        self.assertTrue(report["allPassed"], report)
        self.assertFalse(DIAGNOSTIC_IDS & {g["id"] for g in report["gates"]})

    def test_missing_evidence_checks_are_not_passes(self):
        report = build_acceptance([], self.reference)
        self.assertFalse(report["allPassed"])
        self.assertEqual(4, sum(g.get("status") == "notRun" for g in report["gates"]))

    def test_unknown_gate_or_structural_failure_cannot_be_waived(self):
        reference = copy.deepcopy(self.reference)
        reference["gates"].append({"id": "unreviewed_gate", "passed": True})
        self.assertIn("policy_catalog", build_acceptance([], reference, self.assess())["failedGateIds"])
        self.assertIn("graph_authoring", build_acceptance(["Invalid reference"], self.reference, self.assess())["failedGateIds"])
        reference = copy.deepcopy(self.reference)
        next(g for g in reference["gates"] if g["id"] == "dag_pass")["passed"] = False
        self.assertIn("dag_pass", build_acceptance([], reference, self.assess())["failedGateIds"])

    def test_hash_predicate_rule_and_role_edits_are_rejected(self):
        for fault in ("hash", "predicate", "rules", "role", "bindings", "missing-card", "annotation"):
            criteria = copy.deepcopy(self.criteria)
            graph = copy.deepcopy(self.graph)
            if fault == "hash":
                criteria["graphSha256"] = "changed"
            elif fault == "predicate":
                criteria["nodes"]["Q233"]["predicate"] = "Does this prove maliciousness?"
            elif fault == "rules":
                criteria["rules"]["hypothesis-test"]["unknown"] = ""
            elif fault == "role":
                criteria["nodes"]["Q233"]["role"] = "impact"
            elif fault == "bindings":
                criteria["nodes"]["Q233"]["boundSubjectFields"] = ["arbitrary-subject"]
            elif fault == "missing-card":
                criteria["nodes"].pop("Q233")
            else:
                next(n for n in graph["nodes"] if n["id"] == "Q233")["extensions"] = {}
            with self.subTest(fault=fault):
                self.assertFalse(next(g for g in self.assess(graph, criteria) if g["id"] == "evidence_cards")["passed"])

    def test_every_unsafe_transition_is_blocked_even_if_scenarios_omit_it(self):
        for source, answer, target in (("Q1", "unknown", "Q233"), ("Q155", "no", "Q233"),
                                       ("Q233", "unknown", "Q253"), ("Q233", "no", "Q253"),
                                       ("Q253", "unknown", "Q379"), ("Q379", "unknown", "Q558")):
            graph = copy.deepcopy(self.graph)
            for edge in graph["edges"]:
                if (edge["source"], edge["decision"]) == (source, answer):
                    edge.update({"target": target, "id": f"{source}-{answer}-{target}"})
            with self.subTest(source=source, answer=answer):
                self.assertFalse(next(g for g in self.assess(graph) if g["id"] == "evidence_transitions")["passed"])

    def test_wrong_expectation_fails_scenario_agreement(self):
        suite = copy.deepcopy(self.suite)
        suite["cases"][0]["expectedState"] = "bounded-findings"
        self.assertFalse(next(g for g in self.assess(suite=suite) if g["id"] == "scenario_agreement")["passed"])

    def test_only_positive_fixtures_cannot_claim_coverage(self):
        suite = expand_suite(self.suite)
        suite["cases"] = [c for c in suite["cases"] if not any(n in self.criteria["domains"][c["domain"]]["classification"] and a != "yes" for n, a in c["expectedTrace"])]
        checks = {g["id"]: g for g in self.assess(suite=suite)}
        self.assertTrue(checks["scenario_agreement"]["passed"])
        self.assertFalse(checks["scenario_coverage"]["passed"])

    def test_victim_evidence_unknown_cases_cannot_be_silently_removed(self):
        suite = expand_suite(self.suite)
        suite["cases"] = [c for c in suite["cases"] if c.get("evidenceKind") != "public-report-only"]
        self.assertFalse(next(g for g in self.assess(suite=suite) if g["id"] == "scenario_coverage")["passed"])

    def test_empty_or_cyclic_fixture_suite_is_rejected(self):
        for cases in ([], [{"id": "cycle", "extends": "cycle", "patch": {}, "expectedState": "unresolved", "expectedTrace": []}]):
            suite = {**self.suite, "cases": cases}
            self.assertFalse(build_acceptance([], self.reference, self.assess(suite=suite))["allPassed"])

    def test_historical_values_match_the_preserved_receipt(self):
        old = json.loads((ROOT / "drafts/core/reviews/2026-10-11-positive-evidence/structural/math-assurance.json").read_bytes())
        snapshot_raw = (ROOT / "drafts/core/reviews/2026-10-11-topology-policy/reviewed-graph.graph.json").read_bytes()
        self.assertEqual(old["provenance"]["inputs"][0]["sha256"], hashlib.sha256(snapshot_raw).hexdigest())
        self.assertEqual(old["monitoring"]["publishGates"], self.experiments["baseline"]["reference"])
        for key, value in self.experiments["baseline"]["scores"].items():
            self.assertEqual(old["summary"][key], value)

    def test_counterexamples_show_scores_are_not_semantic_acceptance(self):
        r = self.experiments
        self.assertTrue(r["meaninglessPredicates"]["scoresUnchanged"])
        self.assertIn("evidence_cards", r["meaninglessPredicates"]["failedEvidenceChecks"])
        self.assertEqual(100, r["scatteredDomainLabels"]["metrics"]["scores"]["routingScore"])
        self.assertGreater(len(r["scatteredDomainLabels"]["metrics"]["authoringErrors"]), 0)
        self.assertGreater(r["baseline"]["maximumBetweennessShare"], .02)
        self.assertLess(r["identicalRouteReplication"]["metrics"]["maximumBetweennessShare"], .02)
        self.assertAlmostEqual(r["baseline"]["maximumBetweennessShare"] / 2, r["identicalRouteReplication"]["metrics"]["maximumBetweennessShare"])
        self.assertEqual(.5, r["deletedPrerequisiteToy"]["remainingReachabilityWithoutBypass"])
        self.assertEqual(1, r["deletedPrerequisiteToy"]["remainingReachabilityWithUnsafeBypass"])
        self.assertEqual(r["duplicateFailure"]["robustnessScore"], r["duplicateFailure"]["100TimesTargetedReachability"])

    def test_noncanonical_graph_without_evidence_inputs_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            graph = Path(directory) / "graph.json"
            graph.write_bytes((ROOT / "drafts/core/tensor.core.graph.json").read_bytes())
            run = subprocess.run([sys.executable, "scripts/lint_core_graph_quality.py", "--graph-path", str(graph), "--output-dir", str(Path(directory) / "report")], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(0, run.returncode)
            report = json.loads((Path(directory) / "report/math-assurance.json").read_bytes())
            self.assertIn("evidence_cards", report["monitoring"]["publishGates"]["failedGateIds"])

    def test_noncanonical_exact_graph_with_explicit_evidence_can_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            graph = Path(directory) / "graph.json"
            graph.write_bytes((ROOT / "drafts/core/tensor.core.graph.json").read_bytes())
            run = subprocess.run([sys.executable, "scripts/lint_core_graph_quality.py", "--graph-path", str(graph),
                                  "--criteria-path", "drafts/core/entry-evidence-criteria.json",
                                  "--scenarios-path", "drafts/core/scenarios/entry-evidence-cases.json",
                                  "--output-dir", str(Path(directory) / "report")], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, run.returncode, run.stdout + run.stderr)

    def test_missing_criteria_file_is_not_a_diagnostic_waiver(self):
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run([sys.executable, "scripts/lint_core_graph_quality.py", "--graph-path", "drafts/core/tensor.core.graph.json",
                                  "--criteria-path", str(Path(directory) / "missing.json"), "--output-dir", directory],
                                 cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(0, run.returncode)
            report = json.loads((Path(directory) / "math-assurance.json").read_bytes())
            self.assertTrue(any(g.get("status") == "notRun" for g in report["monitoring"]["publishGates"]["gates"]))

    def test_evidence_and_policy_digests_are_in_every_json_report(self):
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run([sys.executable, "scripts/lint_core_graph_quality.py", "--graph-path", "drafts/core/tensor.core.graph.json", "--entry-path", "drafts/core/source/entry_nodes.json", "--output-dir", directory], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, run.returncode, run.stderr)
            for name in ("math-assurance.json", "graph-quality.json", "coverage-matrix.json"):
                report = json.loads((Path(directory) / name).read_bytes())
                inputs = {i["path"]: i["sha256"] for i in report["provenance"]["inputs"]}
                for path in ("drafts/core/scenarios/entry-evidence-cases.json", "standards/graph-assurance-policy.md", "scripts/graph_assurance_policy.py"):
                    self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), inputs[path])


if __name__ == "__main__":
    unittest.main()
