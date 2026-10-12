"""Behavioral proof for restored predicates and resumption, not effectiveness."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import restored_evidence as evaluator
from graph_assurance_policy import assess_evidence


class RestoredEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "drafts/core/tensor.core.graph.json").read_bytes()
        cls.graph = json.loads(cls.raw)
        cls.criteria = json.loads((ROOT / "drafts/core/entry-evidence-criteria.json").read_bytes())
        cls.suite = json.loads((ROOT / "drafts/core/scenarios/entry-evidence-cases.json").read_bytes())
        cls.ids = set(cls.criteria["restoration"]["restoredNodeIds"])

    def fixture(self, kind):
        nid = next(n for n in sorted(self.ids) if self.criteria["nodes"][n]["assessmentKind"] == kind)
        case = next(c for c in self.suite["restoredCases"] if c["id"] == nid+"-yes")
        return self.criteria["nodes"][nid], evaluator.case_evidence(self.suite, case)

    def test_every_source_and_repair_id_is_active_and_source_is_immutable(self):
        original = json.loads((ROOT / "releases/core/graphs/v0.20260206e/tensor.core.graph.json").read_bytes())
        self.assertEqual({n["id"] for n in self.graph["nodes"]}, {n["id"] for n in original["nodes"]} | {f"Q{i}" for i in range(589, 610)})
        self.assertEqual((609, 1554), (len(self.graph["nodes"]), len(self.graph["edges"])))
        self.assertEqual(506, len(self.ids))
        analysis = json.loads((ROOT / "drafts/core/reviews/2026-10-12-restoration/analysis.json").read_bytes())
        self.assertEqual(588, len(analysis["questions"]))
        self.assertEqual(479, analysis["summary"]["distinctSourcePrompts"])
        self.assertEqual(0, analysis["summary"]["independentlyApprovedDispositions"])

    def test_all_restored_answers_and_domain_paths_agree(self):
        results = evaluator.run_cases(self.graph, self.criteria, self.suite)
        self.assertEqual(1539, len(results))
        for result in results:
            self.assertTrue(result["passed"], result)

    def test_missing_focus_and_material_conflict_fail_closed_for_every_kind(self):
        for kind in {self.criteria["nodes"][n]["assessmentKind"] for n in self.ids}:
            card, case = self.fixture(kind)
            for change in ("focus", "counterevidence", "subject", "time"):
                c = deepcopy(case)
                if change == "focus":
                    c.pop("focus")
                elif change == "counterevidence":
                    c["materialConflict"] = True
                elif change == "subject":
                    c["bindings"][card["boundSubjectFields"][0]] = "unrelated-subject"
                else:
                    c["interval"]["end"] = "not-a-time"
                with self.subTest(kind=kind, change=change):
                    expected = "no" if change == "subject" and card["stage"] == "detect" else "unknown"
                    self.assertEqual(expected, evaluator.answer(card, c, self.criteria)[0])

    def test_resumption_rechecks_record_provenance_hypothesis_and_scope(self):
        for stage in ("classify", "scope", "correlate", "attribute", "impact"):
            nid = next(n for n in sorted(self.ids) if self.criteria["nodes"][n]["stage"] == stage)
            card = self.criteria["nodes"][nid]
            raw = next(c for c in self.suite["restoredCases"] if c["id"] == nid+"-yes")
            case = evaluator.case_evidence(self.suite, raw)
            changes = ["provenance", "time", "record-subject", "facet"]
            if stage != "classify":
                changes += ["hypothesis"]
            if stage not in ("classify", "scope"):
                changes += ["scope"]
            for change in changes:
                c = deepcopy(case)
                record = c["primary"]["records"][0]
                if change == "provenance":
                    record["assessmentEvidenceRefs"] = []
                elif change == "time":
                    record["eventTime"] = c["interval"]["end"]
                elif change == "record-subject":
                    record["subjects"][card["boundSubjectFields"][0]] = "unrelated-subject"
                elif change == "facet":
                    record["evidenceFacet"] = "unrelated-material"
                else:
                    c["analysis"].pop(change)
                with self.subTest(stage=stage, change=change):
                    self.assertEqual("unknown", evaluator.answer(card, c, self.criteria)[0])

    def test_copied_origin_cannot_corroborate(self):
        card, c = self.fixture("corroboration")
        c["independent"]["records"][0]["origin"] = c["primary"]["records"][0]["origin"]
        self.assertEqual("unknown", evaluator.answer(card, c, self.criteria)[0])

    def test_baseline_requires_applicable_comparator_and_typed_assessed_fact(self):
        card, case = self.fixture("baseline")
        for change in ("comparator", "bound-subject", "fact", "type"):
            c = deepcopy(case)
            a = c["analysis"]["baseline"]
            if change == "comparator":
                a.pop("comparatorId")
            elif change == "bound-subject":
                a["subjects"] = {}
            elif change == "fact":
                c["primary"]["records"][0]["facts"][a["criterion"]["fact"]]["assessment"] = "unknown"
            else:
                a["criterion"]["equals"] = 1
            self.assertEqual("unknown", evaluator.answer(card, c, self.criteria)[0], change)

    def test_temporal_coincidence_uses_clock_intervals_and_typed_tolerance(self):
        card, case = self.fixture("temporal")
        self.assertEqual("yes", evaluator.answer(card, case, self.criteria)[0])
        for tolerance in (True, -1, float("nan"), "5", None):
            c = deepcopy(case)
            c["analysis"]["correlation"]["toleranceSeconds"] = tolerance
            self.assertEqual("unknown", evaluator.answer(card, c, self.criteria)[0])
        c = deepcopy(case)
        c["analysis"]["correlation"]["targetRecord"]["clockUncertaintySeconds"] = 10
        self.assertEqual("unknown", evaluator.answer(card, c, self.criteria)[0])
        c["analysis"]["correlation"]["targetRecord"]["eventTime"] = "2026-10-01T10:40:00Z"
        self.assertEqual("no", evaluator.answer(card, c, self.criteria)[0])
        c["analysis"]["correlation"]["targetRecord"]["origin"] = c["primary"]["records"][0]["origin"]
        self.assertEqual("unknown", evaluator.answer(card, c, self.criteria)[0])

    def test_dependency_requires_direction_and_endpoint_evidence(self):
        card, case = self.fixture("dependencies")
        for change in ("direction", "endpoint", "basis"):
            c = deepcopy(case)
            a = c["analysis"]["dependency"]
            if change == "direction":
                a["direction"] = "maybe"
            elif change == "endpoint":
                a["targetRecord"]["assessmentEvidenceRefs"] = []
            else:
                a["evidenceRefs"] = []
            self.assertEqual("unknown", evaluator.answer(card, c, self.criteria)[0])

    def test_metric_and_additional_subject_do_not_inherit_source_impact(self):
        for kind in ("metric-change", "additional-impact"):
            card, case = self.fixture(kind)
            for change in ("baseline", "units", "context"):
                c = deepcopy(case)
                record = c["primary"]["records"][0]
                a = c["analysis"]["impact"]
                if kind == "additional-impact":
                    extra = c["analysis"]["additionalEffect"]
                    record = extra["targetRecord"]
                    a = extra["assessment"]["analysis"]["impact"]
                if change == "baseline":
                    record["facts"].pop(a["baselineFact"])
                elif change == "units":
                    record["facts"][a["observedUnitFact"]]["value"] = "incompatible-unit"
                elif kind == "additional-impact":
                    extra["assessment"]["bindings"] = {}
                else:
                    a["subjects"] = {}
                self.assertEqual("unknown", evaluator.answer(card, c, self.criteria)[0], (kind, change))

    def test_terminal_cannot_drop_unknown_answers_or_assert_closure(self):
        card, case = self.fixture("retention")
        c = deepcopy(case)
        c["retainedTrace"] = [{"nodeId": "Q1", "answer": "no"}]
        self.assertEqual("no", evaluator.answer(card, c, self.criteria)[0])
        c = deepcopy(case)
        c["retention"]["closesInvestigation"] = True
        self.assertEqual("unknown", evaluator.answer(card, c, self.criteria)[0])

    def test_restored_cards_unsafe_routes_and_missing_negative_cases_are_blocked(self):
        card, _ = self.fixture("hypothesis")
        nid = next(n for n in self.ids if self.criteria["nodes"][n] == card)
        for fault in ("rule", "source", "predicate", "route", "coverage"):
            graph, criteria, suite = deepcopy(self.graph), deepcopy(self.criteria), deepcopy(self.suite)
            if fault == "rule":
                criteria["rules"][card["rule"]]["unknown"] = "Proceed as supported"
            elif fault == "source":
                criteria["nodes"][nid]["sourceFacet"] = "arbitrary"
            elif fault == "predicate":
                next(n for n in graph["nodes"] if n["id"] == nid)["text"] = "Does this establish malicious intent?"
            elif fault == "route":
                next(e for e in graph["edges"] if e["source"] == nid and e["decision"] == "unknown")["target"] = self.criteria["domains"][card["domain"]]["impact"]
            else:
                suite["restoredCases"] = [c for c in suite["restoredCases"] if c["id"] != nid+"-no"]
            gates = assess_evidence(graph, sha256(self.raw).hexdigest(), criteria, suite)
            self.assertTrue(any(not g["passed"] for g in gates), fault)

    def test_all_author_review_outputs_are_reproducible(self):
        run = subprocess.run([sys.executable, "scripts/restore_original_questions.py", "--check"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, run.returncode, run.stdout+run.stderr)


if __name__ == "__main__":
    unittest.main()
