"""Independent answer/target challenges, not expectations copied from a builder."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from contextual_routing import shared_pairs
from investigative_routing import continuation_edges
from core_graph_pipeline import validate_and_measure


class ContextualRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=json.loads((ROOT/'drafts/core/tensor.core.graph.json').read_text())
        cls.criteria=json.loads((ROOT/'drafts/core/entry-evidence-criteria.json').read_text())
        cls.routes={(e['source'],e['decision']):e for e in continuation_edges(cls.graph)}

    def test_every_shared_destination_has_answer_specific_review_and_no_blanket_triple(self):
        review=json.loads((ROOT/'drafts/core/reviews/2026-10-16-contextual-routing/review.json').read_text())
        self.assertEqual(602,len(review['reviewedSharedPairs']))
        actual=shared_pairs(self.graph)
        self.assertEqual(set(actual),{(r['source'],r['target']) for r in review['currentSharedPairs']})
        for pair,edges in actual.items():
            self.assertLess(len(edges),3,pair)
            source,target=(self.criteria['nodes'][nid] for nid in pair)
            answers={e['decision'] for e in edges}
            # Allowed convergence has a concrete, falsifiable meaning. It is
            # not permission to proceed through all technical stages.
            if answers=={'yes','no'}:
                self.assertIn(source.get('assessmentKind',source['role']),{'baseline','metric-change','additional-impact','impact'})
            else:
                self.assertEqual({'no','unknown'},answers)
                self.assertTrue(target['role']=='unresolved' or source['role']=='entry')

    def test_each_domain_refutes_only_the_tested_hypothesis_and_retains_unknown_separately(self):
        for domain,roles in self.criteria['domains'].items():
            sources=[nid for nid,c in self.criteria['nodes'].items() if c['domain']==domain and
                     (c['role']=='classification' or c.get('assessmentKind')=='hypothesis')]
            for source in sources:
                with self.subTest(domain=domain,source=source):
                    self.assertEqual(roles['refuted'],self.routes[source,'no']['target'])
                    self.assertEqual(roles['unresolved'],self.routes[source,'unknown']['target'])
                    self.assertNotIn(self.routes[source,'yes']['target'],{roles['refuted'],roles['unresolved']})

    def test_rejected_relationship_and_source_do_not_imply_attribution_or_effect(self):
        kinds={'identifier-relation','temporal','technical-source','behavior-pattern'}
        for nid,card in self.criteria['nodes'].items():
            if card.get('assessmentKind') not in kinds and card['role'] not in ('correlation','attribution'):continue
            roles=self.criteria['domains'][card['domain']]
            self.assertEqual(roles['assessed'],self.routes[nid,'no']['target'],nid)
            self.assertEqual(roles['unresolved'],self.routes[nid,'unknown']['target'],nid)

    def test_negative_and_unknown_do_not_supply_cross_domain_discovery(self):
        for edge in self.graph['edges']:
            lead=edge.get('extensions',{}).get('tensor:investigativeLead',{})
            if lead.get('kind')=='cross-domain-lead':self.assertEqual('yes',edge['decision'])
        for node in self.graph['nodes']:
            for option in node.get('extensions',{}).get('tensor:discoveryOptions',[]):
                self.assertIsNone(option['answerGuard'])
                self.assertEqual('newLead',option['origin'])
                self.assertEqual(4,len(option['requirements']))

    def test_all_current_routes_retain_full_context_and_require_fresh_independent_targets(self):
        for edge in self.graph['edges']:
            context=edge['extensions']['tensor:routeContext']
            self.assertEqual('fresh',context['targetInstance'])
            self.assertEqual('independent',context['targetAssessment'])
            self.assertEqual({'definitionIdentity','questionIdentity','subjectBindings','timeContext','parameterBindings',
                              'eventProfile','evidenceReferences','assessmentHistory','originDecision'},set(context['preserve']))
        errors,_,metrics=validate_and_measure(self.graph['nodes'],self.graph['edges'],self.graph['entryNodeIds'],set())
        self.assertEqual([],errors)
        self.assertTrue(metrics['allNodesReachable'])
        self.assertFalse(metrics['dagPass'],'Definition loops are allowed; occurrences preserve each context')

    def test_seven_domain_case_keeps_old_identity_and_new_identity_distinct(self):
        bundle=json.loads((ROOT/'examples/investigations/v1/parallel-followup.bundle.json').read_text())
        entries=bundle['record']['entries'];by_id={e['id']:e for e in entries}
        definition=json.loads(bundle['definitions'][0]['content'])
        self.assertEqual(set(self.criteria['domains']),{q['metadata']['domain'] for q in definition['questions']})
        identities=[e for e in entries if e['type']=='QuestionInstance' and e['questionId'].endswith(':public:question-1')]
        self.assertEqual(2,len(identities))
        self.assertNotEqual(identities[0]['subjectBindings'],identities[1]['subjectBindings'])
        self.assertNotEqual(identities[0]['timeContext'],identities[1]['timeContext'])
        self.assertEqual('transition',identities[1]['origin']['kind'])
        last=by_id[bundle['record']['metadata']['walkthrough']['frames'][-1]['assessmentId']]
        cited={i['entryId'] for i in last['inputs']}
        actual=[e for e in entries if e['type']=='Assessment']
        self.assertTrue({e['id'] for e in actual[:-1]}<=cited)
        self.assertTrue(any(e['outcome']=='no' for e in actual))
        self.assertTrue(any(e['outcome']=='unknown' for e in actual))

    def test_same_domain_discovery_can_change_subject_and_time_only_with_its_own_basis(self):
        from contextual_routing import eligible_discoveries
        for domain,roles in self.criteria['domains'].items():
            source,target=roles['correlation'],roles['attribution']
            old={'start':'2026-10-13T08:00:00Z','end':'2026-10-13T08:30:00Z'}
            later={'start':'2026-10-13T10:00:00Z','end':'2026-10-13T10:30:00Z'}
            context={'_source':{'nodeId':source,'questionId':source,'answer':'unknown','domain':domain,
                'graphVersion':self.graph['version'],'bindings':{f:'old:'+f for f in roles['bindings']},
                'interval':old,'evidenceRefs':['retained:source'],'rationale':'The proposed relationship remains unresolved.'},
                target:{'questionId':target,'domain':domain,'graphVersion':self.graph['version'],
                    'bindings':{f:'new:'+f for f in roles['bindings']},'interval':later,
                    'discoveryEvidenceRefs':['separate:acquisition'],'discoveryRationale':'A later independent acquisition identifies this different target subject.'}}
            before=deepcopy(context)
            self.assertIn(f'{source}-discover-{target}',eligible_discoveries(self.graph,source,'unknown',context))
            self.assertEqual(before,context)
            context[target].pop('discoveryEvidenceRefs')
            context[target].update(evidenceRefs=['retained:source'],method='Copy the source answer')
            self.assertNotIn(f'{source}-discover-{target}',eligible_discoveries(self.graph,source,'unknown',context))
