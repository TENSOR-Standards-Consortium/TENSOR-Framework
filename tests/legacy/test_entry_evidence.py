"""Behavioral regressions for evidence-bound entry routes, not efficacy claims."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import evaluate_entry_scenarios as evaluator
import lint_core_graph_quality as quality_lint
from core_graph_pipeline import validate_and_measure, build_graph_payload


class EntryEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = json.loads((ROOT / "drafts/core/tensor.core.graph.json").read_text())
        cls.criteria = json.loads((ROOT / "drafts/core/entry-evidence-criteria.json").read_text())
        cls.suite = evaluator.expand_suite(json.loads((ROOT / "drafts/core/scenarios/entry-evidence-cases.json").read_text()))

    def case(self, case_id):
        return copy.deepcopy(next(c for c in self.suite["cases"] if c["id"] == case_id))

    def test_evidence_scenarios(self):
        results = evaluator.run_cases(self.graph, self.criteria, self.suite)
        self.assertEqual(252, len(results))
        for result in results:
            with self.subTest(case=result["caseId"]):
                self.assertTrue(result["passed"], result)

    def test_public_reports_do_not_invent_victim_evidence(self):
        public = [c for c in self.suite["cases"] if c["evidenceKind"] == "public-report-only"]
        self.assertEqual(set(self.criteria["domains"]), {c["domain"] for c in public})
        for case in public:
            with self.subTest(domain=case["domain"]):
                result = evaluator.evaluate_case(self.graph, self.criteria, case)
                self.assertEqual("unknown", result["trace"][0]["answer"])
                self.assertEqual("unresolved", result["state"])
                self.assertTrue(all(s in self.suite["sources"] for s in case["sourceIds"]))

    def test_every_reviewed_question_has_bound_public_criteria(self):
        raw = (ROOT / "drafts/core/tensor.core.graph.json").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.criteria["graphSha256"])
        self.assertEqual(self.graph["version"], self.criteria["graphVersion"])
        by_id = {n["id"]: n for n in self.graph["nodes"]}
        self.assertEqual(set(by_id), set(self.criteria["nodes"]))
        for node_id, card in self.criteria["nodes"].items():
            with self.subTest(node=node_id):
                node = by_id[node_id]
                self.assertEqual(node["text"], card["predicate"])
                self.assertEqual(card["domain"], node["category"])
                self.assertEqual(node_id, node["extensions"]["tensor:evidenceCriteria"]["nodeId"])
                self.assertEqual({"yes", "no", "unknown"}, set(self.criteria["rules"][card["rule"]]))
                self.assertTrue(card["boundSubjectFields"])

    def test_reviewed_routes_never_invent_cross_domain_links(self):
        by_id = {n["id"]: n for n in self.graph["nodes"]}
        cards = self.criteria["nodes"]
        for edge in self.graph["edges"]:
            if edge["source"] not in cards:
                continue
            with self.subTest(edge=edge["id"]):
                self.assertEqual(by_id[edge["source"]]["category"], by_id[edge["target"]]["category"])
                self.assertIn(edge["target"], cards)

    def test_original_unjustified_no_route_is_rejected(self):
        graph = copy.deepcopy(self.graph)
        for edge in graph["edges"]:
            if (edge["source"], edge["decision"]) == ("Q1", "no"):
                edge["target"] = "Q497"  # Original route eventually jumped to Application risk.
        with self.assertRaisesRegex(ValueError, "escaped the reviewed boundary"):
            evaluator.evaluate_case(graph, self.criteria, self.case("identity-bounded-absence"))

    def test_no_answer_does_not_exclude_activity_with_missing_logs(self):
        for domain in self.criteria["domains"]:
            case = self.case(domain.lower() + "-missing-logs")
            result = evaluator.evaluate_case(self.graph, self.criteria, case)
            self.assertEqual("no", result["trace"][0]["answer"])
            self.assertEqual("unresolved", result["state"])

    def test_corroborating_counterevidence_blocks_exclusion(self):
        case = self.case("identity-bounded-absence")
        case["independent"] = self.case("identity-independent-recovery")["independent"]
        result = evaluator.evaluate_case(self.graph, self.criteria, case)
        self.assertEqual("no", result["trace"][-1]["answer"])
        self.assertEqual("unresolved", result["state"])

    def test_unsupported_provenance_never_reaches_classification(self):
        for change in ("unknown-assessment", "missing-origin", "missing-basis", "wrong-basis-type"):
            case = self.case("host-supported-record")
            record = case["primary"]["records"][0]
            if change == "unknown-assessment":
                record["interpretationAssessment"] = "unknown"
            elif change == "missing-origin":
                record.pop("origin")
            else:
                record["assessmentEvidenceRefs"] = [] if change == "missing-basis" else "not-a-reference-list"
            with self.subTest(change=change):
                result = evaluator.evaluate_case(self.graph, self.criteria, case)
                self.assertEqual("unresolved", result["state"])
                self.assertEqual("unknown", result["trace"][1]["answer"])

    def test_time_and_subject_binding_limits(self):
        domain = self.criteria["domains"]["Network"]
        for value in (None, "", {}, ["endpoint"]):
            case = self.case("network-supported-record")
            case["bindings"][domain["bindings"][0]] = value
            self.assertEqual("unknown", evaluator.match_answer(case, domain)[0])
        case = self.case("network-supported-record")
        case["primary"]["records"][0]["eventTime"] = "2026-10-01T05:30:00-05:00"
        self.assertEqual("yes", evaluator.match_answer(case, domain)[0])
        for when in ("2026-10-01T10:30:00", "2026-10-01T10:30:00.1234567Z", "not-a-time"):
            case["primary"]["records"][0]["eventTime"] = when
            self.assertEqual("unknown", evaluator.match_answer(case, domain)[0])

    def test_graph_stays_acyclic_reachable_and_deterministic(self):
        config = json.loads((ROOT / "drafts/core/source/entry_nodes.json").read_text())
        errors, warnings, metrics = validate_and_measure(self.graph["nodes"], self.graph["edges"], self.graph["entryNodeIds"], set(config["fanInExceptionNodeIds"]))
        self.assertEqual([], errors)
        self.assertTrue(warnings, "The historical cross-domain quota must remain visible")
        self.assertTrue(metrics["allNodesReachable"])
        self.assertTrue(metrics["dagPass"])
        self.assertEqual(0, metrics["branchDeterminism"]["violations"])

    def test_schema_bytes_and_identity_are_preserved(self):
        digest = "6520f4cd90c26d72252c986e4db7e8639c76e30f2f5c865a7318101c2a513ad5"
        for path in ("drafts/core/tensor.core.schema.json", "releases/core/schemas/v0.20260206e/tensor.core.schema.json"):
            self.assertEqual(digest, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
        self.assertEqual("0.20260206e", self.graph["schemaVersion"])
        self.assertNotEqual(self.graph["version"], self.graph["schemaVersion"])
        payload = build_graph_payload(self.graph["version"], self.graph["nodes"], self.graph["edges"], self.graph["entryNodeIds"], self.graph["schemaVersion"])
        self.assertEqual(self.graph, payload)

    def test_detached_questions_are_preserved_without_fabricated_edges(self):
        archive = json.loads((ROOT / "drafts/core/reviews/2026-10-11-entry-evidence/detached-draft-material.json").read_text())
        self.assertEqual(49, len(archive["nodes"]))
        self.assertEqual(147, len(archive["edges"]))
        self.assertFalse({n["id"] for n in archive["nodes"]} & {n["id"] for n in self.graph["nodes"]})

    def test_draft_mode_keeps_failed_synthetic_gates_visible(self):
        for review in (False, True):
            with tempfile.TemporaryDirectory() as output:
                flags = ["--draft-review"] if review else []
                run = subprocess.run([sys.executable, "scripts/lint_core_graph_quality.py", "--graph-path", "drafts/core/tensor.core.graph.json", "--entry-path", "drafts/core/source/entry_nodes.json", "--output-dir", output, *flags], cwd=ROOT, capture_output=True, text=True)
                quality = json.loads((Path(output) / "graph-quality.json").read_text())
                math = json.loads((Path(output) / "math-assurance.json").read_text())
                self.assertEqual(0, run.returncode, run.stdout + run.stderr)
                self.assertTrue(math["monitoring"]["publishGates"]["allPassed"])
                self.assertFalse(math["monitoring"]["legacyReferenceThresholds"]["allPassed"])
                self.assertEqual({"cross_domain_pivots", "routing_score", "robustness_score", "targeted_resilience", "routing_centralization", "overall_score"}, set(math["monitoring"]["legacyReferenceThresholds"]["failedGateIds"]))
                self.assertTrue(quality["warnings"])
                self.assertFalse(quality["errors"])

    def test_draft_mode_refuses_released_graphs(self):
        with tempfile.TemporaryDirectory() as output:
            run = subprocess.run([sys.executable, "scripts/lint_core_graph_quality.py", "--graph-path", "releases/core/graphs/v0.20260206e/tensor.core.graph.json", "--draft-review", "--output-dir", output], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(0, run.returncode)
            self.assertIn("restricted to the canonical unpromoted draft", run.stderr)

    def test_draft_mode_does_not_waive_structural_errors(self):
        original = quality_lint.validate_and_measure
        def invalid(*args, **kwargs):
            errors, warnings, metrics = original(*args, **kwargs)
            errors.append("Injected structural reference error")
            return errors, warnings, metrics
        with tempfile.TemporaryDirectory() as output:
            argv = ["lint", "--graph-path", "drafts/core/tensor.core.graph.json", "--entry-path", "drafts/core/source/entry_nodes.json", "--draft-review", "--output-dir", output]
            with patch.object(sys, "argv", argv), patch.object(quality_lint, "validate_and_measure", invalid), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(1, quality_lint.main())
            report = json.loads((Path(output) / "graph-quality.json").read_text())
            self.assertIn("Injected structural reference error", report["errors"])

    def test_requested_action_is_not_executed_action(self):
        case = self.case("host-supported-record")
        case["primary"]["records"][0]["interpretationAssessment"] = "rejected"
        case["primary"]["records"][0]["eventInterpretation"] = "Only a tool request was recorded, with no execution observation"
        result = evaluator.evaluate_case(self.graph, self.criteria, case)
        self.assertEqual("no", result["trace"][1]["answer"])
        self.assertEqual("unresolved", result["state"])

    def test_scenario_receipts_do_not_overwrite_inputs(self):
        run = subprocess.run([sys.executable, "scripts/evaluate_entry_scenarios.py", "--output", "drafts/core/tensor.core.graph.json"], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(0, run.returncode)
        self.assertIn("FileExistsError", run.stderr)

    def test_scenario_cli_rejects_changed_graph_bytes_under_same_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = ["drafts/core/tensor.core.graph.json", "drafts/core/entry-evidence-criteria.json", "drafts/core/scenarios/entry-evidence-cases.json"]
            for name in relative:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            with (root / relative[0]).open("a") as handle:
                handle.write("\n")
            with patch.object(evaluator, "ROOT", root), patch.object(sys, "argv", ["evaluate"]), redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as failure:
                    evaluator.main()
                self.assertEqual(2, failure.exception.code)


if __name__ == "__main__":
    unittest.main()
