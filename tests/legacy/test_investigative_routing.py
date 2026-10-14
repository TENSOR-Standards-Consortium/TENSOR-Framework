"""Challenge the routing model independently of the restoration generator."""
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from core_graph_pipeline import validate_and_measure
from investigative_routing import eligible_leads, assess_routes, continuation_edges, PROFILE

# SOC chains authored here independently of the route generator. The source
# finding concerns only a named relationship; target events have their own
# observations. These are normalized fictional facts, not authenticated logs.
CASES = [
    ('Identity', 'Issuer session s42', 'Email', {'messageId':'m42','mailboxId':'morgan'}, 'Cloud', {'tenantId':'tenant7','resourceId':'key17','operationId':'create-key17'}),
    ('Email', 'Mailbox delivery m31', 'File', {'fileId':'sha256:artifact31','systemId':'h17'}, 'Identity', {'principalId':'morgan','identityAction':'signin-s42'}),
    ('File', 'Attachment digest f31', 'Host', {'hostId':'h17','processId':'p204'}, 'Email', {'messageId':'m31','mailboxId':'morgan'}),
    ('Host', 'Process/socket p204', 'Network', {'sourceEndpoint':'h17:41000','destinationEndpoint':'203.0.113.7:443','communicationId':'flow8'}, 'Application', {'applicationId':'report-api','requestId':'req42'}),
    ('Application', 'Gateway request req42', 'Identity', {'principalId':'workload17','identityAction':'issue-token71'}, 'Cloud', {'tenantId':'tenant7','resourceId':'object9','operationId':'set-object-policy9'}),
    ('Cloud', 'Control-plane operation op9', 'Network', {'sourceEndpoint':'runtime17:43000','destinationEndpoint':'203.0.113.9:443','communicationId':'flow9'}, 'Application', {'applicationId':'object-api','requestId':'req91'}),
    ('Network', 'Gateway flow flow8', 'Host', {'hostId':'h17','processId':'p204'}, 'Identity', {'principalId':'workload17','identityAction':'use-token71'}),
]


class InvestigativeRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(ROOT/'drafts/core/tensor.core.graph.json').read_bytes()
        cls.graph=json.loads(cls.raw)
        cls.criteria=json.loads((ROOT/'drafts/core/entry-evidence-criteria.json').read_text())
        cls.nodes={n['id']:n for n in cls.graph['nodes']}

    def test_all_seven_domains_have_multiple_yes_no_unknown_cross_domain_choices(self):
        for domain, description, left, left_bindings, right, right_bindings in CASES:
            source=self.criteria['domains'][domain]['correlation']
            context={self.criteria['domains'][target]['entry']:{'domain':target,'bindings':bindings,
                'interval':{'start':'2026-10-13T08:35:00Z','end':'2026-10-13T09:00:00Z'},
                'questionId':self.criteria['domains'][target]['entry'],'graphVersion':self.graph['version'],
                'discoveryEvidenceRefs':['independent:'+description+':'+target],
                'discoveryRationale':'Separately acquired endpoint evidence identifies this exact target event, with competing explanations retained.'}
                for target,bindings in [(left,left_bindings),(right,right_bindings)]}
            for answer in ('yes','no','unknown'):
                with self.subTest(domain=domain,answer=answer):
                    context['_source']={'nodeId':source,'answer':answer,'graphVersion':self.graph['version'],'domain':domain,
                        'bindings':{f:'source:'+f for f in self.criteria['domains'][domain]['bindings']},
                        'interval':{'start':'2026-10-13T08:00:00Z','end':'2026-10-13T08:30:00Z'},
                        'evidenceRefs':['source:'+description],'rationale':'Retain the independently assessed source proposition.'}
                    eligible=eligible_leads(self.graph,source,answer,context)
                    self.assertEqual({f'{source}-{answer}-{self.criteria["domains"][d]["entry"]}' for d in (left,right)},set(eligible))
                    # One or both can be explicitly selected. Readiness does not
                    # manufacture target answers or require selecting everything.
                    selected=[eligible[0]]
                    self.assertEqual(1,len(selected))
                    self.assertEqual(2,len(eligible))
                    self.assertTrue(set(selected)<=set(eligible))
                    self.assertTrue(all('answer' not in v for k,v in context.items() if k!='_source'))
            for fault in ('binding','interval','domain','discovery','rationale'):
                broken=deepcopy(context)
                for key,target in broken.items():
                    if key=='_source':continue
                    if fault=='binding':target['bindings'].pop(next(iter(target['bindings'])))
                    if fault=='interval':target['interval']['end']=target['interval']['start']
                    if fault=='domain':target['domain']='unrelated'
                    if fault=='discovery':target['discoveryEvidenceRefs']=[]
                    if fault=='rationale':target['discoveryRationale']=''
                self.assertEqual([],eligible_leads(self.graph,source,'yes',broken),(domain,fault))

    def test_source_negatives_and_uncertainty_never_supply_discovery_evidence(self):
        for domain in self.criteria['domains']:
            for answer in ('yes','no','unknown'):
                self.assertEqual([],eligible_leads(self.graph,self.criteria['domains'][domain]['correlation'],answer,{}))

    def test_graph_allows_parallel_routes_lower_ids_and_cycles_without_weakening_references(self):
        errors,_,metrics=validate_and_measure(self.graph['nodes'],self.graph['edges'],self.graph['entryNodeIds'],set())
        self.assertEqual([],errors)
        self.assertGreater(metrics['branchDeterminism']['multiRouteSourceCount'],7)
        self.assertFalse(metrics['dagPass'])
        self.assertTrue(metrics['allNodesReachable'])
        self.assertEqual(0,metrics['branchDeterminism']['violations'])
        for fault in ('duplicate','missing-target','missing-outcome','terminal-route'):
            graph=deepcopy(self.graph)
            if fault=='duplicate':graph['edges'].append(deepcopy(graph['edges'][0]))
            if fault=='missing-target':graph['edges'][0]['target']='Q99999'
            if fault=='missing-outcome':graph['edges']=[e for e in graph['edges'] if not(e['source']=='Q1' and e['decision']=='unknown')]
            if fault=='terminal-route':graph['edges'].append({'id':'Q609-yes-Q1','source':'Q609','target':'Q1','decision':'yes'})
            self.assertTrue(validate_and_measure(graph['nodes'],graph['edges'],graph['entryNodeIds'],set())[0],fault)

    def test_every_added_edge_is_bound_to_its_reviewed_context(self):
        self.assertEqual([],assess_routes(self.graph,self.criteria))
        edge=next(e for e in self.graph['edges'] if e.get('extensions',{}).get('tensor:investigativeLead',{}).get('kind')=='cross-domain-lead')
        for fault in ('binding','domain','guard','target','basis','missing'):
            graph=deepcopy(self.graph);changed=next(e for e in graph['edges'] if e['id']==edge['id'])
            if fault=='binding':changed['extensions']['tensor:investigativeLead']['targetBindingFields']=['borrowed-source-id']
            elif fault=='domain':changed['extensions']['tensor:investigativeLead']['targetDomain']='unrelated'
            elif fault=='guard':changed['decision']='unknown' if changed['decision']=='yes' else 'yes'
            elif fault=='target':changed['target']='Q609'
            elif fault=='basis':changed['extensions']['tensor:investigativeLead']['basis']='Because the nodes are nearby'
            else:graph['edges'].remove(changed)
            self.assertTrue(assess_routes(graph,self.criteria),fault)

    def test_schema_runtime_releases_and_frozen_reviews_are_byte_preserved(self):
        head='986841b8d977a80a532a297f36b2aad49afe2cba'
        paths=subprocess.check_output(['git','ls-tree','-r','--name-only',head,'releases','review','core/v0.1.0-draft.1'],cwd=ROOT,text=True).splitlines()
        paths+=['drafts/core/tensor.core.schema.json']
        for path in paths:
            self.assertEqual(subprocess.check_output(['git','show',f'{head}:{path}'],cwd=ROOT),(ROOT/path).read_bytes(),path)
        original=json.loads((ROOT/'releases/core/graphs/v0.20260206e/tensor.core.graph.json').read_text())
        self.assertEqual({n['id'] for n in original['nodes']}|{f'Q{i}' for i in range(589,610)},set(self.nodes))
        self.assertEqual(1554,len(continuation_edges(self.graph)))
        report=json.loads((ROOT/'drafts/core/reviews/2026-10-13-routing/review.json').read_text())
        self.assertEqual('4943feee2af28d414fcfd98194e63d196bee529ce8f85117aed4932d977e4d5e',report['graphSha256'])
        self.assertEqual(subprocess.check_output(['git','show','e6ced17:'+ 'drafts/core/reviews/2026-10-13-routing/review.json'],cwd=ROOT),(ROOT/'drafts/core/reviews/2026-10-13-routing/review.json').read_bytes())

if __name__=='__main__':unittest.main()
