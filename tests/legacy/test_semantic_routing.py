"""Independent v2 routing challenges using hand-authored investigation contexts.

No graph builder or generated scenario fixture constructs these expectations.
The inputs are normalized supplied claims, not authenticated incident evidence.
Readiness permits an explicitly selected assessment; it never supplies a finding,
a causal relation, an execution instruction, or organizational authority.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from investigative_routing import eligible_leads
from contextual_routing import eligible_discoveries

PROFILE_VERSION = '0.1.0-draft.2'
SOURCE_INTERVAL = {'start': '2026-10-13T08:00:00Z', 'end': '2026-10-13T08:30:00Z'}
TARGET_INTERVAL = {'start': '2026-10-13T08:20:00Z', 'end': '2026-10-13T09:00:00Z'}

# Each tuple is independently specified from the published seven event families.
# The first target is a concrete plausible lead, rather than a graph-count quota.
DOMAINS = {
    'Identity': {'entry': 'Q1', 'alternate': 'Q8', 'primary': 'Q155', 'independent': 'Q150', 'gap': 'Q596',
        'relation': 'Q379', 'classification': 'Q233', 'scope': 'Q253',
        'bindings': {'principalId': 'principal:morgan', 'identityAction': 'signin:42'},
        'target': 'Email', 'profile': 'identity-credential-state',
        'profileBindings': {'principalId': 'principal:morgan', 'credentialId': 'credential:42'}},
    'Host': {'entry': 'Q2', 'alternate': 'Q9', 'primary': 'Q156', 'independent': 'Q151', 'gap': 'Q597',
        'relation': 'Q348', 'classification': 'Q214', 'scope': 'Q268',
        'bindings': {'hostId': 'host:alpha', 'processId': 'process:204'},
        'target': 'Network', 'profile': 'host-state',
        'profileBindings': {'hostId': 'host:alpha', 'stateKey': 'state:autorun'}},
    'Network': {'entry': 'Q3', 'alternate': 'Q10', 'primary': 'Q152', 'independent': 'Q82', 'gap': 'Q598',
        'relation': 'Q356', 'classification': 'Q159', 'scope': 'Q303',
        'bindings': {'sourceEndpoint': 'host:alpha:41000', 'destinationEndpoint': '203.0.113.7:443', 'communicationId': 'flow:8'},
        'target': 'Host', 'profile': 'network-configuration',
        'profileBindings': {'deviceId': 'gateway:alpha', 'configurationId': 'configuration:42'}},
    'Cloud': {'entry': 'Q4', 'alternate': 'Q11', 'primary': 'Q153', 'independent': 'Q83', 'gap': 'Q599',
        'relation': 'Q364', 'classification': 'Q223', 'scope': 'Q256',
        'bindings': {'tenantId': 'tenant:7', 'resourceId': 'object:9', 'operationId': 'operation:42'},
        'target': 'Application', 'profile': 'cloud-resource-state',
        'profileBindings': {'tenantId': 'tenant:7', 'resourceId': 'object:9', 'stateKey': 'state:policy'}},
    'Email': {'entry': 'Q5', 'alternate': 'Q12', 'primary': 'Q154', 'independent': 'Q147', 'gap': 'Q600',
        'relation': 'Q323', 'classification': 'Q161', 'scope': 'Q299',
        'bindings': {'messageId': 'message:31', 'mailboxId': 'mailbox:morgan'},
        'target': 'File', 'profile': 'email-mailbox-access',
        'profileBindings': {'mailboxId': 'mailbox:morgan', 'principalId': 'principal:morgan', 'operationId': 'access:42'}},
    'Application': {'entry': 'Q6', 'alternate': 'Q13', 'primary': 'Q85', 'independent': 'Q148', 'gap': 'Q601',
        'relation': 'Q345', 'classification': 'Q190', 'scope': 'Q279',
        'bindings': {'applicationId': 'application:reports', 'requestId': 'request:42'},
        'target': 'Identity', 'profile': 'application-session',
        'profileBindings': {'applicationId': 'application:reports', 'sessionId': 'session:42'}},
    'File': {'entry': 'Q7', 'alternate': 'Q14', 'primary': 'Q86', 'independent': 'Q149', 'gap': 'Q602',
        'relation': 'Q346', 'classification': 'Q184', 'scope': 'Q245',
        'bindings': {'fileId': 'sha256:artifact31', 'systemId': 'host:alpha'},
        'target': 'Email', 'profile': 'file-deletion',
        'profileBindings': {'fileId': 'sha256:artifact31', 'systemId': 'host:alpha', 'operationId': 'delete:42'}},
}


def question(node_id, profile=None):
    return f'urn:tensor:event-profile:{profile}:{PROFILE_VERSION}:{node_id}' if profile else node_id


class SemanticRoutingChallenge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = json.loads((ROOT / 'drafts/core/tensor.core.graph.json').read_text())

    def source(self, domain, node_id=None, answer='yes', profiled=False):
        row = DOMAINS[domain]
        value = {'nodeId': node_id or row['entry'], 'answer': answer,
            'questionId': question(node_id or row['entry'], row['profile'] if profiled else None),
            'graphVersion': self.graph['version'], 'domain': domain,
            'bindings': deepcopy(row['profileBindings'] if profiled else row['bindings']),
            'interval': deepcopy(SOURCE_INTERVAL), 'evidenceRefs': [f'evidence:{domain}:examined-source'],
            'method': 'Examine the declared evidence and retain its exact context.',
            'rationale': 'The source answer is retained independently of every proposed target assessment.',
            'materialOrigins': [f'origin:{domain}:primary'], 'recordIds': [f'record:{domain}:primary']}
        if profiled:
            value.update(eventProfile=row['profile'], profileVersion=PROFILE_VERSION)
        return value

    def same_context(self, domain, kind, profiled=False):
        row = DOMAINS[domain]
        outcome, target_id = {'independent-validation': ('yes', row['independent']),
            'independent-search': ('no', row['alternate']),
            'bounded-handoff': ('unknown', row['gap'])}[kind]
        original = self.source(domain, answer=outcome, profiled=profiled)
        target = {'questionId': question(target_id, row['profile'] if profiled else None),
            'graphVersion': self.graph['version'], 'domain': domain,
            'bindings': deepcopy(original['bindings']), 'interval': deepcopy(original['interval']),
            'evidenceRefs': [f'evidence:{domain}:independent-material'],
            'method': 'Examine separately originating material within these exact declared bounds.',
            'materialOrigin': f'origin:{domain}:independent', 'recordId': f'record:{domain}:independent',
            'materialDescription': 'A separately originating observation or explicitly identified source to search.',
            'gapDescription': 'The original examined material is incomplete; preserve that gap without changing findings.'}
        if profiled:
            target.update(eventProfile=row['profile'], profileVersion=PROFILE_VERSION)
        return original['nodeId'], outcome, target_id, {'_source': original, target_id: target}

    def cross_context(self, domain, answer='yes', profiled=False, source_role='relation'):
        row = DOMAINS[domain]
        target_domain = row['target']
        destination = DOMAINS[target_domain]
        source_id, target_id = row[source_role], destination['entry']
        original = self.source(domain, node_id=source_id, answer=answer)
        target = {'questionId': question(target_id, destination['profile'] if profiled else None),
            'graphVersion': self.graph['version'], 'domain': target_domain,
            'bindings': deepcopy(destination['profileBindings'] if profiled else destination['bindings']),
            'interval': deepcopy(TARGET_INTERVAL),
            'discoveryEvidenceRefs': [f'evidence:{domain}:named-{target_domain}-reference'],
            'discoveryRationale': f'An examined {domain} observation names this {target_domain} context; its proposition still needs independent assessment.'}
        if profiled:
            target.update(eventProfile=destination['profile'], profileVersion=PROFILE_VERSION)
        return source_id, answer, target_id, {'_source': original, target_id: target}

    def eligible(self, source, answer, target, context):
        return (f'{source}-{answer}-{target}' in eligible_leads(self.graph,source,answer,context) or
                f'{source}-discover-{target}' in eligible_discoveries(self.graph,source,answer,context))

    def test_all_seven_domains_support_each_same_domain_lead_kind(self):
        for domain in DOMAINS:
            for kind in ('independent-validation', 'independent-search', 'bounded-handoff'):
                with self.subTest(domain=domain, kind=kind):
                    self.assertTrue(self.eligible(*self.same_context(domain, kind)))

    def test_each_same_domain_kind_preserves_qualified_profile_meaning(self):
        for domain in DOMAINS:
            for kind in ('independent-validation', 'independent-search', 'bounded-handoff'):
                with self.subTest(domain=domain, kind=kind):
                    self.assertTrue(self.eligible(*self.same_context(domain, kind, profiled=True)))

    def test_independent_search_does_not_require_a_discovered_target_record(self):
        for domain in DOMAINS:
            source, answer, target, context = self.same_context(domain, 'independent-search')
            context[target].pop('recordId')
            context['_source']['recordIds'] = []  # The examined material contained no matching record.
            with self.subTest(domain=domain):
                self.assertTrue(self.eligible(source, answer, target, context))

    def test_each_same_domain_kind_rejects_changed_source_context(self):
        for domain in DOMAINS:
            for kind in ('independent-validation', 'independent-search', 'bounded-handoff'):
                for fault in ('domain', 'bindings', 'interval', 'profile', 'version', 'question', 'evidence', 'method'):
                    source, answer, target, context = self.same_context(domain, kind)
                    value = context[target]
                    if fault == 'domain': value['domain'] = 'wrong-domain'
                    if fault == 'bindings': value['bindings'][next(iter(value['bindings']))] += ':other'
                    if fault == 'interval': value['interval'] = deepcopy(TARGET_INTERVAL)
                    if fault == 'profile': value.update(eventProfile='unsupported-profile', profileVersion=PROFILE_VERSION)
                    if fault == 'version': value['graphVersion'] = 'wrong-graph-version'
                    if fault == 'question': value['questionId'] = 'wrong-question'
                    if fault == 'evidence': value['evidenceRefs'] = []
                    if fault == 'method': value['method'] = ''
                    with self.subTest(domain=domain, kind=kind, fault=fault):
                        self.assertFalse(self.eligible(source, answer, target, context))

    def test_all_same_domain_kinds_reject_bare_readiness(self):
        for domain in DOMAINS:
            for kind in ('independent-validation', 'independent-search', 'bounded-handoff'):
                source, answer, target, context = self.same_context(domain, kind)
                context[target] = {'ready': True}
                with self.subTest(domain=domain, kind=kind):
                    self.assertFalse(self.eligible(source, answer, target, context))

    def test_independent_material_rejects_same_origin_or_record_identity(self):
        for domain in DOMAINS:
            for kind in ('independent-validation', 'independent-search'):
                for fault in ('same-origin', 'same-record', 'missing-origin', 'missing-source-origins'):
                    source, answer, target, context = self.same_context(domain, kind)
                    if fault == 'same-origin': context[target]['materialOrigin'] = context['_source']['materialOrigins'][0]
                    if fault == 'same-record': context[target]['recordId'] = context['_source']['recordIds'][0]
                    if fault == 'missing-origin': context[target].pop('materialOrigin')
                    if fault == 'missing-source-origins': context['_source'].pop('materialOrigins')
                    with self.subTest(domain=domain, kind=kind, fault=fault):
                        self.assertFalse(self.eligible(source, answer, target, context))

    def test_independent_validation_requires_actual_source_and_target_records(self):
        for domain in DOMAINS:
            for fault in ('source-records', 'target-record'):
                source, answer, target, context = self.same_context(domain, 'independent-validation')
                if fault == 'source-records': context['_source'].pop('recordIds')
                else: context[target].pop('recordId')
                with self.subTest(domain=domain, fault=fault):
                    self.assertFalse(self.eligible(source, answer, target, context))

    def test_cross_domain_yes_no_unknown_open_only_separately_bound_questions(self):
        for domain in DOMAINS:
            for outcome in ('yes', 'no', 'unknown'):
                for profiled in (False, True):
                    source, answer, target, context = self.cross_context(domain, outcome, profiled)
                    before = deepcopy(context)
                    with self.subTest(domain=domain, outcome=outcome, profiled=profiled):
                        self.assertTrue(self.eligible(source, answer, target, context))
                        self.assertEqual(context, before)
                        self.assertNotIn('answer', context[target])
                        self.assertNotIn('authorized', context[target])

    def test_validated_event_can_open_discovered_lead_before_hypothesis_support(self):
        for domain in DOMAINS:
            with self.subTest(domain=domain):
                # No hypothesis, scope, relation finding or action is supplied.
                self.assertTrue(self.eligible(*self.cross_context(domain, source_role='primary')))

    def test_cross_domain_needs_own_discovery_context(self):
        for domain in DOMAINS:
            for fault in ('bindings', 'interval', 'discovery', 'rationale', 'question', 'version', 'profile'):
                source, answer, target, context = self.cross_context(domain)
                value = context[target]
                if fault == 'bindings': value['bindings'].pop(next(iter(value['bindings'])))
                if fault == 'interval': value['interval']['end'] = value['interval']['start']
                if fault == 'discovery': value['discoveryEvidenceRefs'] = []
                if fault == 'rationale': value['discoveryRationale'] = ''
                if fault == 'question': value['questionId'] = 'wrong-question'
                if fault == 'version': value['graphVersion'] = 'wrong-version'
                if fault == 'profile': value.update(eventProfile='unsupported-profile', profileVersion=PROFILE_VERSION)
                with self.subTest(domain=domain, fault=fault):
                    self.assertFalse(self.eligible(source, answer, target, context))

    def test_source_definition_answer_version_and_evidence_cannot_be_substituted(self):
        for domain in DOMAINS:
            for fault in ('missing', 'node', 'answer', 'graph', 'domain', 'evidence', 'rationale', 'profile', 'orphan-profile-version'):
                source, answer, target, context = self.cross_context(domain)
                original = context['_source']
                if fault == 'missing': context.pop('_source')
                if fault == 'node': original['nodeId'] = DOMAINS[domain]['entry']
                if fault == 'answer': original['answer'] = 'unknown'
                if fault == 'graph': original['graphVersion'] = 'wrong-version'
                if fault == 'domain': original['domain'] = 'wrong-domain'
                if fault == 'evidence': original['evidenceRefs'] = []
                if fault == 'rationale': original['rationale'] = ''
                if fault == 'profile': original.update(eventProfile='unsupported-profile', profileVersion=PROFILE_VERSION)
                if fault == 'orphan-profile-version': original['profileVersion'] = PROFILE_VERSION
                with self.subTest(domain=domain, fault=fault):
                    self.assertFalse(self.eligible(source, answer, target, context))

    def test_target_profile_version_and_qualified_question_are_exact(self):
        for domain in DOMAINS:
            for fault in ('version', 'base-question', 'missing-profile', 'orphan-version'):
                source, answer, target, context = self.cross_context(domain, profiled=True)
                value = context[target]
                if fault == 'version': value['profileVersion'] = '0.1.0-draft.UNKNOWN'
                if fault == 'base-question': value['questionId'] = target
                if fault == 'missing-profile': value.pop('eventProfile')
                if fault == 'orphan-version':
                    value.pop('eventProfile'); value['questionId'] = target
                with self.subTest(domain=domain, fault=fault):
                    self.assertFalse(self.eligible(source, answer, target, context))

    def test_unknown_partial_source_can_open_fully_bound_independent_cross_domain_lead(self):
        for domain in DOMAINS:
            source, answer, target, context = self.cross_context(domain, 'unknown', source_role='entry')
            field = next(iter(context['_source']['bindings']))
            context['_source']['bindings'].pop(field)
            context['_source'].pop('interval')
            context['_source']['missingContextFields'] = [field, 'interval']
            with self.subTest(domain=domain):
                self.assertTrue(self.eligible(source, answer, target, context))
                self.assertNotIn(field, context['_source']['bindings'])

    def test_partial_context_does_not_invent_full_same_domain_handoff_bounds(self):
        for domain in DOMAINS:
            source, answer, target, context = self.same_context(domain, 'bounded-handoff')
            field = next(iter(context['_source']['bindings']))
            for value in (context['_source'], context[target]):
                value['bindings'].pop(field)
                value.pop('interval')
                value['missingContextFields'] = [field, 'interval']
            with self.subTest(domain=domain):
                self.assertTrue(self.eligible(source, answer, target, context))
                self.assertNotIn('interval', context[target])
                self.assertNotIn('answer', context[target])

    def test_partial_unknown_context_must_enumerate_each_actual_missing_field(self):
        for domain in DOMAINS:
            for fault in ('undeclared-field', 'extra-field', 'yes-source', 'handoff-drift'):
                source, answer, target, context = self.same_context(domain, 'bounded-handoff')
                field = next(iter(context['_source']['bindings']))
                for value in (context['_source'], context[target]):
                    value['bindings'].pop(field)
                    value['missingContextFields'] = [field]
                if fault == 'undeclared-field': context['_source']['missingContextFields'] = []
                if fault == 'extra-field': context['_source']['missingContextFields'].append('nonexistent-field')
                if fault == 'yes-source': context['_source']['answer'] = 'yes'
                if fault == 'handoff-drift': context[target]['missingContextFields'] = []
                with self.subTest(domain=domain, fault=fault):
                    self.assertFalse(self.eligible(source, answer, target, context))

    def test_declared_missing_source_fields_cannot_contradict_complete_bindings(self):
        for domain in DOMAINS:
            source, answer, target, context = self.cross_context(domain, 'unknown', source_role='entry')
            context['_source']['missingContextFields'] = [next(iter(context['_source']['bindings']))]
            with self.subTest(domain=domain):
                self.assertFalse(self.eligible(source, answer, target, context))

    def test_malformed_missing_context_declarations_are_unready_without_exceptions(self):
        for domain in DOMAINS:
            for malformed in (None, 'interval', {'interval': True}, ['interval', 7]):
                source, answer, target, context = self.cross_context(domain, 'unknown', source_role='entry')
                context['_source'].pop('interval')
                context['_source']['missingContextFields'] = malformed
                with self.subTest(domain=domain, malformed=malformed):
                    self.assertFalse(self.eligible(source, answer, target, context))

    def test_partial_handoff_target_missing_field_declaration_is_typed_and_exact(self):
        for domain in DOMAINS:
            for malformed in (None, 'interval', {'interval': True}, ['interval', 7]):
                source, answer, target, context = self.same_context(domain, 'bounded-handoff')
                for value in (context['_source'], context[target]):
                    value.pop('interval')
                    value['missingContextFields'] = ['interval']
                context[target]['missingContextFields'] = malformed
                with self.subTest(domain=domain, malformed=malformed):
                    self.assertFalse(self.eligible(source, answer, target, context))

    def test_fixed_source_question_must_exist_in_its_declared_profile(self):
        # These named source predicates have fixed facets outside the declared
        # profile. A known profile in the right domain is insufficient.
        cases = [('Email', 'Q309', 'File'), ('Application', 'Q310', 'Host'),
            ('File', 'Q311', 'Host'), ('Identity', 'Q312', 'Cloud'),
            ('Host', 'Q313', 'Identity'), ('Network', 'Q314', 'Cloud'),
            ('Cloud', 'Q315', 'Application')]
        for domain, source, destination in cases:
            target = DOMAINS[destination]['entry']
            original = self.source(domain, source, profiled=True)
            context = {'_source': original, target: {
                'questionId': target, 'graphVersion': self.graph['version'], 'domain': destination,
                'bindings': deepcopy(DOMAINS[destination]['bindings']), 'interval': deepcopy(TARGET_INTERVAL),
                'discoveryEvidenceRefs': ['evidence:separately-identified-target'],
                'discoveryRationale': 'Separate discovery evidence names the target, but cannot define an incompatible source question.'}}
            with self.subTest(domain=domain, source=source, profile=original['eventProfile']):
                self.assertFalse(self.eligible(source, 'yes', target, context))

    def test_compatible_fixed_source_profile_can_preserve_its_defined_question(self):
        cases = [
            ('Email', 'Q309', 'File', 'email-collaboration-artifact',
                {'workspaceId': 'workspace:42', 'artifactId': 'artifact:31', 'operationId': 'share:42'}),
            ('Application', 'Q310', 'Host', 'application-agent-action',
                {'applicationId': 'application:reports', 'agentId': 'agent:42', 'actionId': 'action:42'}),
            ('Identity', 'Q312', 'Cloud', 'identity-workload-binding',
                {'principalId': 'principal:morgan', 'workloadId': 'workload:42'}),
            ('Cloud', 'Q315', 'Application', 'cloud-data-access',
                {'tenantId': 'tenant:7', 'resourceId': 'object:9', 'operationId': 'read:42'})]
        for domain, source, destination, profile, bindings in cases:
            target = DOMAINS[destination]['entry']
            original = self.source(domain, source)
            original.update(eventProfile=profile, profileVersion=PROFILE_VERSION,
                questionId=question(source, profile), bindings=bindings)
            context = {'_source': original, target: {
                'questionId': target, 'graphVersion': self.graph['version'], 'domain': destination,
                'bindings': deepcopy(DOMAINS[destination]['bindings']), 'interval': deepcopy(TARGET_INTERVAL),
                'discoveryEvidenceRefs': ['evidence:separately-identified-target'],
                'discoveryRationale': 'The source profile defines this question and independent evidence identifies the exact target search context.'}}
            with self.subTest(domain=domain, source=source, profile=profile):
                self.assertTrue(self.eligible(source, 'yes', target, context))

    def test_qualified_source_question_identity_and_profile_version_are_exact(self):
        for domain in DOMAINS:
            for fault in ('base-question', 'wrong-qualified-question', 'profile-version'):
                source, answer, target, context = self.same_context(domain, 'independent-validation', profiled=True)
                original = context['_source']
                if fault == 'base-question': original['questionId'] = source
                if fault == 'wrong-qualified-question': original['questionId'] = question(DOMAINS[domain]['relation'], DOMAINS[domain]['profile'])
                if fault == 'profile-version': original['profileVersion'] = '0.1.0-draft.UNKNOWN'
                with self.subTest(domain=domain, fault=fault):
                    self.assertFalse(self.eligible(source, answer, target, context))

    def test_independent_assessment_can_keep_hypothesis_no_or_unknown_separate(self):
        for domain in DOMAINS:
            row = DOMAINS[domain]
            for outcome in ('no', 'unknown'):
                source, target = row['classification'], row['scope']
                context = {'_source': self.source(domain, source, outcome), target: {
                    'questionId': target, 'graphVersion': self.graph['version'], 'domain': domain,
                    'bindings': deepcopy(row['bindings']), 'interval': deepcopy(SOURCE_INTERVAL),
                    'method': 'Assess evidenced entity dispositions without inheriting hypothesis support.',
                    'evidenceRefs': [f'evidence:{domain}:scope-observation']}}
                with self.subTest(domain=domain, outcome=outcome):
                    self.assertTrue(self.eligible(source, outcome, target, context))
                    self.assertNotIn('hypothesisAnswer', context[target])


if __name__ == '__main__':
    unittest.main(verbosity=2)
