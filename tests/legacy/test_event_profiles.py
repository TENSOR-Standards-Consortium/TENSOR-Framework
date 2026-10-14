"""Counterexamples for explicit event contexts; no original-generator fixtures."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from event_profiles import (load_package,answer_profile,evaluate_route,definition_id,definitions,VERSION,expand_scenarios)


class EventProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph,cls.criteria,cls.catalog=load_package()
        cls.scenarios=expand_scenarios(json.loads((ROOT/'drafts/core/event-profiles/scenarios.json').read_text()))
        cls.positive={c['eventProfile']:c for c in cls.scenarios if c['id'].endswith('-supported')}

    def card(self,case,role):
        nid=self.criteria['domains'][case['domain']][role]
        return self.criteria['nodes'][nid[0] if isinstance(nid,list) else nid]

    def answer(self,case,role):
        return answer_profile(self.card(case,role),case,self.criteria,self.catalog)[0]

    def test_authored_routes_all_seven_domains_positive_negative_unknown_and_absence(self):
        self.assertEqual({'Identity','Host','Network','Cloud','Email','Application','File'},{c['domain'] for c in self.positive.values()})
        self.assertEqual(16,len(self.positive))
        self.assertEqual(144,len(self.scenarios))
        for case in self.scenarios:
            with self.subTest(case=case['id']):
                result=evaluate_route(self.graph,self.criteria,self.catalog,case)
                self.assertEqual(case['expectedTrace'],[[s['nodeId'],s['answer']] for s in result['trace']])
                self.assertTrue(all(s['questionId']==definition_id(case['eventProfile'],s['nodeId']) for s in result['trace']))

    def test_exact_catalog_definitions_and_input_pins(self):
        self.assertEqual(self.criteria['graphSha256'],self.catalog['graphSha256'])
        for path,digest in self.catalog['inputPins'].items():
            self.assertEqual(digest,sha256((ROOT/path).read_bytes()).hexdigest(),path)
        actual=json.loads((ROOT/'drafts/core/event-profiles/definitions.json').read_text())['profiles']
        self.assertEqual(actual,definitions(self.graph,self.criteria,self.catalog))
        for pid,rows in actual.items():
            self.assertTrue(rows)
            for nid,row in rows.items():
                self.assertEqual(definition_id(pid,nid),row['id'])
                self.assertEqual(self.catalog['profiles'][pid]['bindings'],row['boundSubjectFields'])
                self.assertIn(self.catalog['profiles'][pid]['proposition'],row['predicate']) if self.criteria['nodes'][nid]['role']!='restored' else None

    def test_profile_subjects_do_not_require_invented_old_event_identifiers(self):
        for case in self.positive.values():
            self.assertEqual(set(self.catalog['profiles'][case['eventProfile']]['bindings']),set(case['bindings']))
            self.assertEqual('yes',self.answer(case,'classification'))
        for pid,absent in [('host-state','processId'),('network-configuration','communicationId'),
            ('cloud-resource-state','operationId'),('email-mailbox-rule','messageId'),
            ('application-state','requestId'),('application-agent-action','requestId')]:
            self.assertNotIn(absent,self.positive[pid]['bindings'])

    def test_missing_binding_unknown_profile_wrong_domain_or_version_is_unknown(self):
        for seed in self.positive.values():
            for variation in ('binding','profile','domain','version'):
                case=deepcopy(seed)
                if variation=='binding':case['bindings'].pop(next(iter(case['bindings'])))
                elif variation=='profile':case['eventProfile']='unregistered-profile'
                elif variation=='domain':case['domain']='Host' if case['domain']!='Host' else 'File'
                else:case['profileVersion']='different'
                with self.subTest(profile=seed['eventProfile'],variation=variation):
                    self.assertEqual('unknown',answer_profile(self.card(seed,'entry'),case,self.criteria,self.catalog)[0])

    def test_event_kind_full_secondary_subject_and_time_are_discriminated(self):
        for seed in self.positive.values():
            for variation in ('kind','subject','time','unassessed-kind','record-profile'):
                case=deepcopy(seed)
                record=case['primary']['records'][0]
                if variation=='kind':record['facts']['event.kind']['value']='unrelated-event'
                elif variation=='subject':record['subjects'][list(case['bindings'])[-1]]='other-subject'
                elif variation=='time':
                    record['eventTime']=case['interval']['end'];record['clockUncertaintySeconds']=0
                elif variation=='unassessed-kind':record['facts']['event.kind']['assessment']='unresolved'
                else:record['eventProfile']='different-profile'
                with self.subTest(profile=seed['eventProfile'],variation=variation):
                    self.assertEqual('unknown' if variation in ('unassessed-kind','record-profile') else 'no',self.answer(case,'entry'))

    def test_required_facts_provenance_and_hypothesis_context_cannot_be_assumed(self):
        for seed in self.positive.values():
            for variation in ('required','provenance','hypothesis-profile','hypothesis-subject','hypothesis-interval'):
                case=deepcopy(seed)
                if variation=='required':case['primary']['records'][0]['facts'].pop(self.catalog['profiles'][case['eventProfile']]['requiredFacts'][-1])
                elif variation=='provenance':case['primary']['records'][0]['provenanceAssessment']='rejected'
                elif variation=='hypothesis-profile':case['analysis']['hypothesis']['eventProfile']='different-profile'
                elif variation=='hypothesis-subject':case['analysis']['hypothesis']['subjects']={}
                else:case['analysis']['hypothesis']['interval']['end']='2026-10-13T10:00:00Z'
                with self.subTest(profile=seed['eventProfile'],variation=variation):
                    self.assertEqual('unknown',self.answer(case,'classification'))

    def test_attempted_or_queued_operations_do_not_prove_success(self):
        for pid,factname,failed in [('cloud-data-access','access.outcome','attempted'),
            ('email-mailbox-rule','rule.outcome','failed'),('email-mailbox-access','access.outcome','denied'),
            ('application-agent-action','action.outcome','queued'),('file-deletion','deletion.outcome','failed')]:
            case=deepcopy(self.positive[pid])
            case['primary']['records'][0]['facts'][factname]['value']=failed
            self.assertEqual('yes',self.answer(case,'entry'))
            self.assertEqual('yes',self.answer(case,'primaryValidation'))
            self.assertEqual('no',self.answer(case,'classification'))

    def test_state_snapshots_do_not_become_historical_changes_or_coverage(self):
        for pid in ('identity-credential-state','host-state','network-configuration','network-sensor-coverage',
                    'cloud-resource-state','application-state','application-session'):
            case=deepcopy(self.positive[pid])
            case['analysis']['hypothesis']['criterion']['fact']='state.previousValue'
            case['analysis']['hypothesis']['criterion']['equals']='previously-enabled'
            self.assertEqual('unknown',self.answer(case,'classification'))
            case=deepcopy(self.positive[pid])
            case['coverage'].pop('evidenceRefs')
            self.assertEqual('unknown',self.answer(case,'exclusion'))
            case=deepcopy(self.positive[pid])
            case['coverage']['eventProfile']='different-profile'
            self.assertEqual('unknown',self.answer(case,'exclusion'))

    def test_file_deletion_and_lineage_are_not_inferred_from_presence_or_manifest_cycles(self):
        case=deepcopy(self.positive['file-deletion'])
        case['primary']['records'][0]['facts']['event.kind']['value']='directory-listing'
        self.assertEqual('no',self.answer(case,'entry'))
        case=deepcopy(self.positive['file-historical-lineage'])
        case['primary']['records'][0]['facts']['lineage.parentRevisionId']['value']=case['bindings']['revisionId']
        self.assertEqual('unknown',self.answer(case,'primaryValidation'))

    def test_unavailable_content_metadata_never_proves_payload_facts(self):
        seed=self.positive['file-unavailable-content']
        for status in ('encrypted','withheld','missing','unavailable'):
            case=deepcopy(seed)
            record=case['primary']['records'][0]
            record['facts']['content.availability']['value']=status
            record['facts']['content.hash']=deepcopy(record['facts']['event.id'])
            record['facts']['content.hash']['value']='claimed-content-hash'
            record['facts']['content.hash']['evidenceDependency']={'kind':'content','evidenceRefs':['authored:byte-examination']}
            case['analysis']['hypothesis']['criterion'].update(fact='content.hash',equals='claimed-content-hash')
            self.assertEqual('unknown',self.answer(case,'classification'))
        case=deepcopy(case)
        record=case['primary']['records'][0]
        record['facts']['content.availability']['value']='available'
        self.assertEqual('yes',self.answer(case,'classification'))

    def test_full_profile_scope_identity_and_counterevidence(self):
        for seed in self.positive.values():
            for variation in ('incomplete','excluded','conflict','profile','complete-population'):
                case=deepcopy(seed)
                entity=case['analysis']['scope']['entities'][0]
                if variation=='incomplete':entity['subjects'].pop(list(entity['subjects'])[-1])
                elif variation=='excluded':entity['disposition']='excluded'
                elif variation=='conflict':
                    extra=deepcopy(entity);extra['disposition']='excluded';case['analysis']['scope']['entities'].append(extra)
                elif variation=='profile':entity['eventProfile']='different-profile'
                else:case['analysis']['scope']['claimsCompletePopulation']=True
                with self.subTest(profile=seed['eventProfile'],variation=variation):
                    self.assertEqual('no' if variation=='excluded' else 'unknown',self.answer(case,'scope'))

    def test_relation_endpoints_require_their_own_profile_bindings_and_provenance(self):
        for seed in self.positive.values():
            for variation in ('target-profile','target-subject','target-provenance','copied-origin','discriminator','missing-discriminator'):
                case=deepcopy(seed)
                a=case['analysis']['correlation']
                if variation=='target-profile':a['targetEventProfile']='different-profile'
                elif variation=='target-subject':a['targetSubjects'][list(a['targetSubjects'])[-1]]='wrong'
                elif variation=='target-provenance':a['targetRecord']['provenanceAssessment']='rejected'
                elif variation=='copied-origin':a['targetRecord']['origin']=case['primary']['records'][0]['origin']
                elif variation=='discriminator':a['targetRecord']['facts']['relation.key']['value']='different'
                else:a['targetRecord']['facts'].pop('relation.key')
                self.assertEqual('no' if variation=='discriminator' else 'unknown',self.answer(case,'correlation'))

    def test_same_domain_cross_profile_relation_preserves_distinct_subjects(self):
        for sourcepid,targetpid in [('email-mailbox-rule','email-mailbox-access'),('cloud-resource-state','cloud-data-access'),
                                    ('application-state','application-agent-action'),('file-deletion','file-historical-lineage')]:
            case=deepcopy(self.positive[sourcepid]);target=deepcopy(self.positive[targetpid])
            relation=case['analysis']['correlation']
            relation.update(targetEventProfile=targetpid,targetDomain=target['domain'],targetSubjects=target['bindings'],targetRecord=target['primary']['records'][0])
            relation['targetRecord']['facts']['relation.key']=deepcopy(case['primary']['records'][0]['facts']['relation.key'])
            self.assertEqual('yes',self.answer(case,'correlation'))
            case['analysis']['scope']['entities'].append(deepcopy(target['analysis']['scope']['entities'][0]))
            self.assertEqual('yes',self.answer(case,'scope'))
            self.assertEqual(sourcepid,case['eventProfile'])

    def test_retention_requires_qualified_id_context_and_separate_answers(self):
        for seed in self.positive.values():
            for variation in ('question-id','profile','subject','hypothesis','missing-scope','closure','conflict','hypothesis-definition'):
                case=deepcopy(seed);rows=case['retention']['assessments']
                if variation=='question-id':rows[0]['questionId']=rows[0]['nodeId']
                elif variation=='profile':case['retention']['eventProfile']='different-profile'
                elif variation=='subject':rows[0]['subjects']={}
                elif variation=='hypothesis':rows[0]['hypothesisId']='different-hypothesis'
                elif variation=='missing-scope':
                    case['retainedTrace']=[{'nodeId':r['nodeId'],'answer':r['answer']} for r in rows]
                    case['retention']['assessments']=[r for r in rows if self.criteria['nodes'][r['nodeId']]['role']!='scope']
                elif variation=='closure':case['retention']['closesInvestigation']=True
                elif variation=='hypothesis-definition':case['analysis']['hypothesis']['statement']='A different proposition under the same ID'
                else:extra=deepcopy(rows[0]);extra['answer']='no';rows.append(extra)
                self.assertEqual('no' if variation=='missing-scope' else 'unknown',self.answer(case,'assessed'))
            case=deepcopy(seed);case['retainedTrace']=[{'nodeId':case['retention']['assessments'][0]['nodeId'],'answer':'no'}]
            self.assertEqual('no',self.answer(case,'assessed'))

    def restored_card(self,case,kind):
        profile=self.catalog['profiles'][case['eventProfile']]
        return next((c for c in self.criteria['nodes'].values() if c['domain']==case['domain']
            and c.get('assessmentKind')==kind and c.get('sourceFacet') in profile['facets']),None)

    def test_alternate_selection_and_multiple_observation_order_are_explicit(self):
        for seed in self.positive.values():
            case=deepcopy(seed)
            other=deepcopy(case['primary']['records'][0]);other['id']+='-other'
            case['primary']['records'].append(other)
            self.assertEqual('unknown',self.answer(case,'entry'))
            case['primary']['records'].reverse()
            self.assertEqual('unknown',self.answer(case,'entry'))
            case['primary']['selectedRecordId']=other['id']
            self.assertEqual('yes',self.answer(case,'entry'))
            case['primary']['selectedRecordId']='missing'
            self.assertEqual('unknown',self.answer(case,'entry'))
            case=deepcopy(seed)
            case['independent']['records'][0]['origin']=case['primaryOrigin']
            self.assertEqual('unknown',self.answer(case,'alternate'))
            case.pop('primaryOrigin')
            self.assertEqual('unknown',self.answer(case,'alternate'))

    def test_restored_profile_facets_recheck_context_and_preserve_optional_answers(self):
        for seed in self.positive.values():
            for kind in ('event-match','provenance','baseline','additional-entities','dependencies'):
                case=deepcopy(seed);card=self.restored_card(case,kind)
                if card is None:continue
                case['focus']=card['sourceFacet']
                case['primary']['records'][0]['evidenceFacet']=case['focus']
                result=answer_profile(card,case,self.criteria,self.catalog)[0]
                expected='yes' if kind in ('event-match','provenance') else ('no' if kind=='additional-entities' else 'unknown')
                self.assertEqual(expected,result,(seed['eventProfile'],kind))
                if kind in ('baseline','additional-entities','dependencies'):
                    nid=next(n for n,c in self.criteria['nodes'].items() if c is card)
                    targets={e['target'] for e in self.graph['edges'] if e['source']==nid}
                    self.assertEqual(1,len(targets))
                    self.assertNotEqual('terminal',next(n['archetype'] for n in self.graph['nodes'] if n['id']==next(iter(targets))))
                case['primary']['records'][0]['evidenceFacet']='unrelated-facet'
                self.assertEqual('unknown',answer_profile(card,case,self.criteria,self.catalog)[0])

    def test_profile_temporal_relations_preserve_clock_uncertainty(self):
        tested=0
        for seed in self.positive.values():
            case=deepcopy(seed);card=self.restored_card(case,'temporal')
            if card is None:continue
            tested+=1;case['focus']=card['sourceFacet']
            case['primary']['records'][0]['evidenceFacet']=case['focus']
            a=case['analysis']['correlation'];a.update(relationKind='bounded-time-coincidence',toleranceSeconds=4)
            self.assertEqual('yes',answer_profile(card,case,self.criteria,self.catalog)[0])
            a['toleranceSeconds']=0
            self.assertEqual('unknown',answer_profile(card,case,self.criteria,self.catalog)[0])
            a['targetRecord']['eventTime']='2026-10-12T09:30:00Z'
            self.assertEqual('no',answer_profile(card,case,self.criteria,self.catalog)[0])
            a['targetRecord']['eventTime']='2026-10-12T09:59:59Z'
            self.assertEqual('unknown',answer_profile(card,case,self.criteria,self.catalog)[0])
        self.assertGreater(tested,0)

    def test_profile_dependency_full_endpoints_direction_and_target_inclusion(self):
        tested=0
        for seed in self.positive.values():
            case=deepcopy(seed);card=self.restored_card(case,'dependencies')
            if card is None:continue
            tested+=1;case['focus']=card['sourceFacet'];selected=case['primary']['records'][0]
            selected['evidenceFacet']=case['focus']
            relation=deepcopy(case['analysis']['correlation'])
            relation.update(claimKind='documented-dependency',direction='downstream',relationId='dependency-17')
            target=relation['targetRecord']
            for record,prefix in ((selected,'source'),(target,'target')):
                template=deepcopy(record['facts']['event.id'])
                for f,v in case['bindings'].items():record['facts'][f'dependency.{prefix}.{f}']={**deepcopy(template),'value':v}
                record['facts']['dependency.relationId']={**deepcopy(template),'value':'dependency-17'}
                record['facts']['dependency.direction']={**deepcopy(template),'value':'downstream'}
            case['analysis']['dependency']=relation
            self.assertEqual('yes',answer_profile(card,case,self.criteria,self.catalog)[0])
            target['facts']['dependency.direction']['value']='upstream'
            self.assertEqual('no',answer_profile(card,case,self.criteria,self.catalog)[0])
            target['facts'].pop('dependency.direction')
            self.assertEqual('unknown',answer_profile(card,case,self.criteria,self.catalog)[0])
        self.assertGreater(tested,0)

    def test_profile_corroboration_witness_order_cannot_resolve_conflicts(self):
        tested=0
        for seed in self.positive.values():
            case=deepcopy(seed);card=self.restored_card(case,'corroboration')
            if card is None:continue
            tested+=1;case['focus']=card['sourceFacet'];case['primary']['records'][0]['evidenceFacet']=case['focus']
            case['independent']['records'][0]['evidenceFacet']=case['focus']
            good=case['independent']['records'][0]
            bad=deepcopy(good);bad.update(id='other-observation',origin='other-origin')
            bad['facts']['event.id']['value']='different-event'
            case['independent']['records']=[bad,good]
            self.assertEqual('unknown',answer_profile(card,case,self.criteria,self.catalog)[0])
            case['independent']['records'].reverse()
            self.assertEqual('unknown',answer_profile(card,case,self.criteria,self.catalog)[0])
            bad['provenanceAssessment']='rejected'
            self.assertEqual('yes',answer_profile(card,case,self.criteria,self.catalog)[0])
        self.assertGreater(tested,0)

    def test_compiled_profiles_are_reproducible(self):
        import subprocess
        result=subprocess.run([sys.executable,str(ROOT/'scripts/build_event_profiles.py'),'--check'],capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)

    def test_source_clock_bounds_cannot_silently_assign_event_membership(self):
        for seed in self.positive.values():
            for uncertainty,time in ((None,'2026-10-12T09:20:00Z'),(float('nan'),'2026-10-12T09:20:00Z'),
                (float('inf'),'2026-10-12T09:20:00Z'),(-1,'2026-10-12T09:20:00Z'),
                (2,'2026-10-12T09:00:01Z'),(2,'2026-10-12T09:59:59Z'),(2,'2026-10-12T10:00:01Z')):
                case=deepcopy(seed);record=case['primary']['records'][0]
                record.update(eventTime=time,clockUncertaintySeconds=uncertainty)
                self.assertEqual('unknown',self.answer(case,'entry'))
            case=deepcopy(seed);case['primary']['records'][0].update(eventTime='2026-10-12T10:01:00Z',clockUncertaintySeconds=2)
            self.assertEqual('no',self.answer(case,'entry'))

    def test_exclusion_needs_examined_material_and_cannot_overlook_ambiguous_records(self):
        for seed in self.positive.values():
            case=deepcopy(seed);case['primary']['records']=case['independent']['records']=[]
            self.assertEqual('yes',self.answer(case,'exclusion'))
            case['primary']['accessible']=False
            self.assertEqual('unknown',self.answer(case,'exclusion'))
            case=deepcopy(seed);case['primary']['records'][0]['facts']['event.kind']['assessment']='unresolved'
            self.assertEqual('unknown',self.answer(case,'exclusion'))

    def test_complete_restored_facet_paths_use_profile_definitions_and_keep_prerequisites_separate(self):
        from build_event_profiles import declare_expected,retained_row
        for seed in self.positive.values():
            case=deepcopy(seed);card=self.restored_card(case,'event-match')
            self.assertIsNotNone(card,seed['eventProfile'])
            case['entry']=next(n for n,c in self.criteria['nodes'].items() if c is card)
            case['focus']=card['sourceFacet']
            for group in ('primary','independent'):
                for record in case[group]['records']:record['evidenceFacet']=case['focus']
            case['analysis']['correlation']['targetRecord']['evidenceFacet']=case['focus']
            declare_expected(case,self.criteria,self.graph,{'restored-baseline':'unknown','restored-additional-entities':'no',
                'restored-dependencies':'unknown','restored-temporal':'unknown','restored-behavior-pattern':'unknown'})
            visited={row['nodeId'] for row in case['retention']['assessments']}
            domain=self.criteria['domains'][case['domain']]
            case['retention']['prerequisiteAssessments']=[retained_row(case,nid,'yes') for nid in
                (domain['classification'][0],domain['scope'][0]) if nid not in visited]
            result=evaluate_route(self.graph,self.criteria,self.catalog,case)
            self.assertEqual(case['expectedTrace'],[[r['nodeId'],r['answer']] for r in result['trace']],case['eventProfile'])
            for row in result['trace']:
                self.assertIn(row['nodeId'],definitions(self.graph,self.criteria,self.catalog)[case['eventProfile']])

    def test_additional_effect_requires_own_profile_baseline_units_and_scope_inclusion(self):
        tested=0
        for seed in self.positive.values():
            case=deepcopy(seed);card=self.restored_card(case,'additional-impact')
            if card is None:continue
            tested+=1;case['focus']=card['sourceFacet'];case['primary']['records'][0]['evidenceFacet']=case['focus']
            target=deepcopy(next(c for c in self.positive.values() if c['domain']!=case['domain']))
            a=deepcopy(case['analysis']['correlation'])
            a.update(targetDomain=target['domain'],targetEventProfile=target['eventProfile'],targetSubjects=target['bindings'],
                targetRecord=target['primary']['records'][0],targetAnalysis=target['analysis'])
            a['targetRecord']['facts']['relation.key']=deepcopy(case['primary']['records'][0]['facts']['relation.key'])
            case['analysis']['additionalEffect']=a
            self.assertEqual('unknown',answer_profile(card,case,self.criteria,self.catalog)[0])
            case['analysis']['scope']['entities'].append(deepcopy(target['analysis']['scope']['entities'][0]))
            self.assertEqual('yes',answer_profile(card,case,self.criteria,self.catalog)[0])
            a['targetRecord']['facts']['metric.baselineUnit']['value']='incomparable'
            self.assertEqual('unknown',answer_profile(card,case,self.criteria,self.catalog)[0])
        self.assertGreater(tested,0)

    def test_profile_pattern_and_technical_source_remain_separate_propositions(self):
        tested=0
        for seed in self.positive.values():
            case=deepcopy(seed);card=self.restored_card(case,'behavior-pattern')
            if card is None:continue
            tested+=1;case['focus']=card['sourceFacet'];record=case['primary']['records'][0];record['evidenceFacet']=case['focus']
            a=deepcopy(case['analysis']['attribution'])
            a.update(claimKind='technical-behavior-pattern',patternId='pattern-17',
                criterion={'fact':'pattern.identifier','equals':'pattern-17','method':'Compare a declared technical pattern'})
            case['analysis']['pattern']=a
            self.assertEqual('unknown',answer_profile(card,case,self.criteria,self.catalog)[0])
            record['facts']['pattern.identifier']={**deepcopy(record['facts']['event.id']),'value':'pattern-17'}
            self.assertEqual('yes',answer_profile(card,case,self.criteria,self.catalog)[0])
            record['facts']['pattern.identifier']['value']='different-pattern'
            self.assertEqual('no',answer_profile(card,case,self.criteria,self.catalog)[0])
            self.assertEqual('yes',self.answer(case,'attribution'))
        self.assertGreater(tested,0)

    def test_profile_graph_schema_releases_and_frozen_review_are_byte_unchanged(self):
        receipt=json.loads((ROOT/'drafts/core/reviews/2026-10-12-independent-review/review.json').read_text())
        for path,digest in receipt['preservedArtifacts'].items():
            self.assertEqual(digest,sha256((ROOT/path).read_bytes()).hexdigest(),path)
        self.assertEqual('1a32d33c3ffbc6068b64a19c102ec4a85ca2914b206d96eb78cafd4173e169d0',sha256((ROOT/'drafts/core/reviews/2026-10-13-routing/prior-draft.graph.json').read_bytes()).hexdigest())
        self.assertEqual(609,len(self.graph['nodes']))
        from investigative_routing import continuation_edges
        self.assertEqual(1554,len(continuation_edges(self.graph)))
        self.assertGreater(len(self.graph['edges']),1554)

if __name__=='__main__':unittest.main()
