import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('coverage_audit', ROOT / 'scripts/audit_graph_coverage.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class CoverageInventoryTests(unittest.TestCase):
    def test_inventory_accounts_for_every_source_without_equivalence_claims(self):
        data = audit.build()
        self.assertEqual(json.loads((ROOT / 'drafts/core/coverage-inventory.json').read_text()), data)
        rows = data['originalQuestions']
        self.assertEqual(len({r['sourceId'] for r in rows}), 588)
        self.assertEqual(data['summary']['lineage'], {'restored-with-evidence-repair': 506, 'same-id-rewritten': 82})
        from collections import Counter
        self.assertEqual(Counter(r['firstRemovedAt'] for r in rows), {None: 82, 'entry-evidence-repair': 49, 'positive-evidence-repair': 88, 'technical-reduction': 369})
        self.assertEqual(len(data['newQuestionIds']), 21)
        self.assertEqual(sum(data['summary']['absentByDomain'].values()), 0)
        self.assertEqual(data['summary']['authorReviewedDispositions'], 588)
        self.assertEqual(data['summary']['approvedSemanticDispositions'], 0)
        self.assertTrue(all(r['semanticReview'] == 'author-reviewed-independent-review-pending' and r['disposition'] and r['issues'] and r['scenarioRefs'] for r in rows))
        self.assertTrue(all(r['textChanged'] for r in rows if r['activeId']))
