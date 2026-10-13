"""Regression tests for real legacy input binding and non-destructive preparation."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import inventory_legacy_graph as inventory
import lint_core_graph_quality as quality
import validate_release_contract as contract
from core_graph_pipeline import ValidationError, build_graph_payload, load_entry_config, load_jsonl

DRAFT = Path("drafts/core/tensor.core.graph.json")
STABLE = Path("releases/core/graphs/v0.20260206e/tensor.core.graph.json")
SOURCE_ID = "https://tensorframework.org/legacy/core"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LegacyPreservationTests(unittest.TestCase):
    def graph_args(self, path, version=None, entry=None):
        return argparse.Namespace(graph_path=path, version=version, entry_path=entry, nodes_path=None, edges_path=None)

    def test_released_contract_and_checksums_remain_valid(self):
        manifest = contract.load_json(ROOT / "releases/manifest.json")
        self.assertEqual([], contract.validate_manifest(manifest))
        self.assertEqual([], contract.validate_release_graph_semantics(manifest))
        self.assertEqual([], contract.validate_release_report_artifacts(manifest))
        self.assertEqual([], contract.validate_checksums())

    def test_stable_and_draft_are_distinct_exact_inputs(self):
        stable = quality.load_inputs(self.graph_args(STABLE), ROOT)
        draft = quality.load_inputs(self.graph_args(DRAFT), ROOT)
        self.assertEqual("0.20260206e", stable[0])
        self.assertEqual(588, len(stable[1]))
        draft_graph = json.loads((ROOT / DRAFT).read_text())
        self.assertEqual(draft_graph["version"], draft[0])
        self.assertEqual(len(draft_graph["nodes"]), len(draft[1]))
        self.assertEqual(sha(ROOT / STABLE), stable[5]["inputs"][0]["sha256"])
        self.assertNotEqual(stable[5]["inputs"][0]["sha256"], draft[5]["inputs"][0]["sha256"])
        with self.assertRaisesRegex(ValidationError, "exact graph declares"):
            quality.load_inputs(self.graph_args(DRAFT, version=stable[0]), ROOT)

    def test_draft_graph_matches_current_structured_sources(self):
        graph = json.loads((ROOT / DRAFT).read_text())
        source = ROOT / "drafts/core/source"
        entries, _ = load_entry_config(source / "entry_nodes.json")
        rebuilt = build_graph_payload(graph["version"], load_jsonl(source / "nodes.jsonl"), load_jsonl(source / "edges.jsonl"), entries, graph["schemaVersion"])
        self.assertEqual(graph,rebuilt)

    def test_quality_run_does_not_rewrite_releases(self):
        before = {str(p): sha(p) for p in (ROOT / "releases").rglob("*") if p.is_file()}
        with tempfile.TemporaryDirectory() as output:
            run = subprocess.run([sys.executable, "scripts/lint_core_graph_quality.py", "--graph-path", str(DRAFT),
                "--entry-path", "drafts/core/source/entry_nodes.json", "--draft-review", "--output-dir", output], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(0, run.returncode, run.stdout + run.stderr)
            for name in ("graph-quality.json", "coverage-matrix.json", "math-assurance.json"):
                report = json.loads((Path(output) / name).read_text())
                self.assertEqual(json.loads((ROOT / DRAFT).read_text())["version"], report["version"])
                self.assertEqual(sha(ROOT / DRAFT), report["provenance"]["inputs"][0]["sha256"])
        after = {str(p): sha(p) for p in (ROOT / "releases").rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_quality_rejects_implicit_sources_and_release_output(self):
        commands = [
            ["--version", "0.20260206e", "--output-dir", "/tmp/unused-tensor-quality"],
            ["--graph-path", str(DRAFT), "--output-dir", "releases/core/reports/latest"],
        ]
        for flags in commands:
            run = subprocess.run([sys.executable, "scripts/lint_core_graph_quality.py", *flags], cwd=ROOT, text=True, capture_output=True)
            self.assertNotEqual(0, run.returncode)

    def test_inventory_is_deterministic_pinned_and_loss_explicit(self):
        raw = (ROOT / STABLE).read_bytes()
        first = inventory.build_inventory(raw, SOURCE_ID)
        second = inventory.build_inventory(raw, SOURCE_ID)
        self.assertEqual(first, second)
        self.assertEqual(sha(ROOT / STABLE), first["source"]["digest"]["value"])
        self.assertFalse(first["migrationPerformed"])
        self.assertEqual("notAssessed", first["candidateConformance"])
        self.assertEqual(588, first["summary"]["questionsNeedingReview"])
        self.assertEqual(1554, first["summary"]["transitionsNeedingReview"])
        original = json.loads(raw)
        self.assertEqual({n["id"]: n for n in original["nodes"]}, {n["legacyId"]: n["legacyItem"] for n in first["questionMappings"]})
        self.assertEqual({e["id"]: e for e in original["edges"]}, {e["legacyId"]: e["legacyItem"] for e in first["transitionMappings"]})
        self.assertTrue(first["losses"])
        self.assertIn("evidence-and-observations", first["notReconstructableFromGraphAlone"])
        self.assertNotIn("records", first)
        question_ids = {n["proposedId"] for n in first["questionMappings"]}
        self.assertEqual(588, len(question_ids))
        self.assertTrue(all(e["sourceProposedId"] in question_ids and e["targetProposedId"] in question_ids for e in first["transitionMappings"]))

    def test_inventory_ids_are_scoped_to_source_and_exact_artifact(self):
        raw = (ROOT / DRAFT).read_bytes()
        base = inventory.build_inventory(raw, SOURCE_ID)["questionMappings"][0]["proposedId"]
        changed_bytes = inventory.build_inventory(raw + b"\n", SOURCE_ID)["questionMappings"][0]["proposedId"]
        changed_id = inventory.build_inventory(raw, "https://example.org/other")["questionMappings"][0]["proposedId"]
        self.assertEqual(3, len({base, changed_bytes, changed_id}))

    def test_inventory_reports_missing_refs_and_rejects_ambiguous_ids(self):
        graph = {"version": "legacy-1", "nodes": [{"id": "Q1", "text": "Question?"}],
                 "edges": [{"id": "e1", "source": "Q1", "target": "Q2", "decision": "yes"}]}
        report = inventory.build_inventory(json.dumps(graph).encode(), SOURCE_ID)
        self.assertEqual(1, report["summary"]["unresolvedReferences"])
        self.assertIsNone(report["transitionMappings"][0]["targetProposedId"])
        graph["nodes"].append(graph["nodes"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate question"):
            inventory.build_inventory(json.dumps(graph).encode(), SOURCE_ID)

    def test_inventory_cli_preserves_input_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "graph.json", Path(tmp) / "inventory.json"
            source.write_bytes((ROOT / DRAFT).read_bytes())
            before = source.read_bytes()
            command = [sys.executable, str(ROOT / "scripts/inventory_legacy_graph.py"), "--graph-path", str(source), "--source-id", SOURCE_ID]
            run = subprocess.run([*command, "--output", str(output)], text=True, capture_output=True)
            self.assertEqual(0, run.returncode, run.stderr)
            self.assertEqual(before, source.read_bytes())
            for target in (source, output):
                run = subprocess.run([*command, "--output", str(target)], text=True, capture_output=True)
                self.assertNotEqual(0, run.returncode)
            self.assertEqual(before, source.read_bytes())

    def run_builder(self, root, version, *flags):
        return subprocess.run([sys.executable, str(ROOT / "scripts/build_core_graph_from_source.py"),
            "--repo-root", str(root), "--version", version, *flags], text=True, capture_output=True)

    def prepare_builder_repository(self, root):
        shutil.copytree(ROOT / "drafts/core/source", root / "drafts/core/source")
        graph = root / STABLE
        graph.parent.mkdir(parents=True)
        graph.write_bytes((ROOT / STABLE).read_bytes())
        latest = root / "releases/core/graphs/latest/tensor.core.graph.json"
        latest.parent.mkdir(parents=True)
        latest.write_bytes(graph.read_bytes())
        for name in ("manifest.json", "checksums.json"):
            (root / "releases" / name).write_bytes((ROOT / "releases" / name).read_bytes())
        return {str(p.relative_to(root)): p.read_bytes() for p in (root / "releases").rglob("*") if p.is_file()}

    def test_builder_defaults_to_draft_and_preserves_all_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = self.prepare_builder_repository(root)
            for flags in ((), ("--draft-only",)):
                run = self.run_builder(root, "0.20260206e", *flags)
                self.assertEqual(0, run.returncode, run.stderr)
                self.assertTrue((root / DRAFT).is_file())
                after = {str(p.relative_to(root)): p.read_bytes() for p in (root / "releases").rglob("*") if p.is_file()}
                self.assertEqual(before, after)

    def test_builder_prepare_release_is_new_only_and_never_promotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = self.prepare_builder_repository(root)
            # A frozen, authoring-valid graph isolates new-directory safety.
            stable = json.loads((ROOT / "drafts/core/reviews/2026-10-11-positive-evidence/prior-draft.graph.json").read_text())
            for key, filename in (("nodes", "nodes.jsonl"), ("edges", "edges.jsonl")):
                (root / "drafts/core/source" / filename).write_text("".join(json.dumps(v) + "\n" for v in stable[key]))
            (root / "drafts/core/source/entry_nodes.json").write_text(json.dumps({"entryNodeIds": stable["entryNodeIds"], "fanInExceptionNodeIds": ["Q467", "Q492", "Q493", "Q494", "Q506", "Q507", "Q508", "Q509", "Q581"]}))
            # Even if a historical artifact is missing, its catalog version is reserved.
            (root / STABLE).unlink()
            refused = self.run_builder(root, "0.20260206e", "--prepare-release")
            self.assertNotEqual(0, refused.returncode)
            self.assertIn("already recorded", refused.stderr)
            self.assertFalse((root / DRAFT).exists())
            (root / STABLE).write_bytes(before[str(STABLE)])
            version = "0.20990101"
            created = root / f"releases/core/graphs/v{version}/tensor.core.graph.json"
            run = self.run_builder(root, version, "--prepare-release")
            self.assertEqual(0, run.returncode, run.stderr)
            self.assertEqual(version, json.loads(created.read_text())["version"])
            self.assertFalse((root / DRAFT).exists())
            for name, content in before.items():
                self.assertEqual(content, (root / name).read_bytes())
            first = created.read_bytes()
            refused = self.run_builder(root, version, "--prepare-release")
            self.assertNotEqual(0, refused.returncode)
            self.assertEqual(first, created.read_bytes())
            created.unlink()
            refused = self.run_builder(root, version, "--prepare-release")
            self.assertNotEqual(0, refused.returncode, "An existing empty version directory must be reserved too.")
            self.assertFalse(created.exists())

    def test_builder_rejects_draft_symlink_into_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare_builder_repository(root)
            draft = root / DRAFT
            draft.symlink_to(root / STABLE)
            before = (root / STABLE).read_bytes()
            run = self.run_builder(root, "0.20990101")
            self.assertNotEqual(0, run.returncode)
            self.assertEqual(before, (root / STABLE).read_bytes())

    def test_release_preparation_is_not_evidence_acceptance_or_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = self.prepare_builder_repository(root)
            run = self.run_builder(root, "0.20990101", "--prepare-release")
            self.assertEqual(0, run.returncode, run.stderr)
            prepared = root / "releases/core/graphs/v0.20990101/tensor.core.graph.json"
            self.assertTrue(prepared.is_file())
            self.assertIn("Unpromoted release graph", run.stdout)
            for path, raw in before.items():
                self.assertEqual(raw, (root / path).read_bytes())
            payload = json.loads(prepared.read_text())
            from core_graph_pipeline import validate_and_measure
            from core_graph_math_assurance import build_math_assurance_payload
            _, _, metrics = validate_and_measure(payload["nodes"], payload["edges"], payload["entryNodeIds"], [])
            report = build_math_assurance_payload(payload["version"], payload["nodes"], payload["edges"], payload["entryNodeIds"], metrics)
            self.assertFalse(report["monitoring"]["publishGates"]["allPassed"])
            self.assertIn("evidence_cards", report["monitoring"]["publishGates"]["failedGateIds"])

    def test_legacy_manifest_positive_and_negative_fixtures(self):
        # Historical fixture latest pointers are isolated from today's latest release.
        fixture_dir = ROOT / "standards/conformance/fixtures"
        valid = json.loads((fixture_dir / "valid/release-manifest.valid.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for release in valid["releases"]:
                for field, kind, filename in (("graphPath", "graphs", "tensor.core.graph.json"), ("schemaPath", "schemas", "tensor.core.schema.json")):
                    target = root / release[field]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((ROOT / release[field]).read_bytes())
                    latest = root / "releases/core" / kind / "latest" / filename
                    latest.parent.mkdir(parents=True, exist_ok=True)
                    latest.write_bytes(target.read_bytes())
            with patch.object(contract, "REPO_ROOT", root), patch.object(contract, "RELEASES_DIR", root / "releases"):
                self.assertEqual([], contract.validate_manifest(valid))
                for fixture in sorted((fixture_dir / "invalid").glob("*.json")):
                    with self.subTest(fixture=fixture.name):
                        self.assertTrue(contract.validate_manifest(json.loads(fixture.read_text())))


if __name__ == "__main__":
    unittest.main()
