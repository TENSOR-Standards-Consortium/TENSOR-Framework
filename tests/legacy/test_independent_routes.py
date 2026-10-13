"""Review invariants independent of generated scenario expectations."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from graph_assurance_policy import assess_evidence
from investigative_routing import continuation_edges, PRIOR_SHA
from core_graph_pipeline import validate_and_measure, GENERIC_HUB_LIMITS

class IndependentRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT/'drafts/core/tensor.core.graph.json').read_bytes()
        cls.graph = json.loads(cls.raw)
        cls.criteria = json.loads((ROOT/'drafts/core/entry-evidence-criteria.json').read_text())
        cls.suite = json.loads((ROOT/'drafts/core/scenarios/entry-evidence-cases.json').read_text())
        cls.nodes = {n['id']: n for n in cls.graph['nodes']}

    def test_all_routes_preserve_facet_or_declare_parameterized_adapter(self):
        cards = self.criteria['nodes']
        for e in continuation_edges(self.graph):
            source, target = cards[e['source']], cards[e['target']]
            if source['role'] != 'restored' or self.nodes[e['target']]['archetype'] == 'terminal':
                continue
            with self.subTest(edge=e['id']):
                self.assertEqual(source['domain'], target['domain'])
                if target['role'] == 'restored':
                    self.assertEqual(source['sourceFacet'], target['sourceFacet'])
                    self.assertNotIn('tensor:contextAdapter', e['extensions'])
                else:
                    adapter = e['extensions']['tensor:contextAdapter']
                    self.assertEqual(source['sourceFacet'], adapter['focus'])
                    self.assertIs(True, adapter['recheckPrerequisites'])
                    self.assertEqual({'domain','bindings','interval','hypothesisId','priorAnswers'}, set(adapter['preserve']))

    def test_optional_negative_and_unknown_answers_do_not_end_other_assessments(self):
        for nid, card in self.criteria['nodes'].items():
            if card.get('assessmentKind') not in {'baseline','corroboration','additional-entities','dependencies'}:
                continue
            targets = {e['target'] for e in self.graph['edges'] if e['source'] == nid}
            with self.subTest(node=nid):
                self.assertEqual(1, len(targets))
                self.assertNotEqual('terminal', self.nodes[next(iter(targets))]['archetype'])

    def test_existing_seven_path_edges_are_unchanged(self):
        prior = json.loads((ROOT/'drafts/core/reviews/2026-10-12-restoration/prior-draft.graph.json').read_text())
        base = {n['id'] for n in prior['nodes']}
        self.assertEqual(prior['edges'], [e for e in continuation_edges(self.graph) if e['source'] in base])
        receipt = json.loads((ROOT/'drafts/core/reviews/2026-10-12-independent-review/review.json').read_text())
        self.assertEqual(PRIOR_SHA, receipt['graphSha256'])
        import subprocess
        for item in receipt['inputs']:
            historical = subprocess.check_output(['git','show',f"986841b8d977a80a532a297f36b2aad49afe2cba:{item['path']}"],cwd=ROOT)
            self.assertEqual(item['sha256'],sha256(historical).hexdigest(),item['path'])
        for path, digest in receipt['preservedArtifacts'].items():
            self.assertEqual(digest, sha256((ROOT/path).read_bytes()).hexdigest(), path)

    def test_missing_adapter_or_changed_focus_blocks_acceptance(self):
        original = next(e for e in self.graph['edges'] if 'tensor:contextAdapter' in e.get('extensions', {}))
        for variation in ('missing','focus','prerequisites','hub-capacity'):
            graph = deepcopy(self.graph)
            edge = next(e for e in graph['edges'] if e['id'] == original['id'])
            if variation == 'missing':
                edge['extensions'].pop('tensor:contextAdapter')
            elif variation == 'focus':
                edge['extensions']['tensor:contextAdapter']['focus'] = 'unrelated evidence'
            elif variation == 'prerequisites':
                edge['extensions']['tensor:contextAdapter']['recheckPrerequisites'] = False
            else:
                node = next(n for n in graph['nodes'] if n['id'] in GENERIC_HUB_LIMITS)
                node['extensions']['tensor:genericEvidenceHub']['maxFanIn'] += 1
            gates = assess_evidence(graph, sha256(self.raw).hexdigest(), self.criteria, self.suite)
            self.assertTrue(any(not g['passed'] for g in gates), variation)

    def test_unreviewed_hub_cannot_raise_its_own_capacity(self):
        graph = deepcopy(self.graph)
        node = next(n for n in graph['nodes'] if n['id'] == 'Q15')
        node['extensions']['tensor:genericEvidenceHub'] = {'profile':'tensor-restored-evidence/2','maxFanIn':1000,
            'basis':'Explicit same-domain context adapters; target prerequisites are re-evaluated'}
        errors, _, _ = validate_and_measure(graph['nodes'], graph['edges'], graph['entryNodeIds'], set())
        self.assertTrue(any('unrecognized generic evidence hub' in e for e in errors))

    def test_pattern_cannot_substitute_a_separate_technical_source_assessment(self):
        from test_independent_investigations import investigation, retained_row
        from restored_evidence import answer
        for domain, bindings in self.criteria['domains'].items():
            pattern_id, pattern = next((nid, c) for nid, c in self.criteria['nodes'].items()
                                       if c['domain'] == domain and c.get('assessmentKind') == 'behavior-pattern')
            case = investigation(domain, pattern, self.criteria)
            case['analysis'].pop('attribution')
            case['retention']['assessments'] = [retained_row(nid, case) for nid in
                (bindings['classification'][0], bindings['scope'][0], bindings['correlation'], pattern_id, bindings['impact'])]
            terminal = self.criteria['nodes'][bindings['assessed']]
            with self.subTest(domain=domain):
                self.assertEqual('unknown', answer(terminal, case, self.criteria)[0])
                source_unknown = retained_row(bindings['attribution'], case, 'unknown')
                source_unknown['limitations'] = ['No technical-source discriminator; pattern does not identify its source']
                case['retention']['assessments'].append(source_unknown)
                self.assertEqual('yes', answer(terminal, case, self.criteria)[0])
