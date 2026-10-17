"""Historical review coverage remains a reproducible CI requirement."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('semantic_receipts', ROOT / 'scripts/verify_semantic_review.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SemanticReviewReceiptTests(unittest.TestCase):
    def test_each_archived_item_has_a_pinned_independent_verdict(self):
        counts = module.verify()
        self.assertEqual(609, counts['nodes'])
        self.assertEqual(567, counts['qualifiedDefinitions'])
