"""Authored semantic witnesses; expectations do not come from graph builders.

All observations below are synthetic supplied assessments, not acquired logs.
Read the authored catalog so these tests can run before artifact regeneration.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from event_profiles import (VERSION, answer_profile, definition_id, definitions,
    evaluate_route, relation_answer, safe_record)

INTERVAL = {'start':'2026-10-13T10:00:00Z','end':'2026-10-13T11:00:00Z'}


def observation(value, dependency=None):
    result = {'value':value,'assessment':'accepted','method':'Manually examine the named synthetic observation',
        'evidenceRefs':['review:fact-basis']}
    if dependency is not None:
        result['evidenceDependency'] = {'kind':dependency,'evidenceRefs':['review:dependency-basis']}
    return result


class SemanticProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = json.loads((ROOT/'drafts/core/tensor.core.graph.json').read_text())
        cls.criteria = json.loads((ROOT/'drafts/core/entry-evidence-criteria.json').read_text())
        cls.catalog = json.loads((ROOT/'drafts/core/event-profiles/catalog.source.json').read_text())

    def card(self, case, role):
        node_id = self.criteria['domains'][case['domain']][role]
        return self.criteria['nodes'][node_id[0] if isinstance(node_id,list) else node_id]

    def node_id(self, card):
        return next(n for n,c in self.criteria['nodes'].items() if c is card)

    def restored(self, case, kind):
        return next(c for c in self.criteria['nodes'].values() if c['domain'] == case['domain']
            and c.get('assessmentKind') == kind and c.get('sourceFacet') in self.catalog['profiles'][case['eventProfile']]['facets'])

    def answer(self, case, role):
        return answer_profile(self.card(case,role),case,self.criteria,self.catalog)[0]

    def context(self, case):
        return {'eventProfile':case['eventProfile'],'profileVersion':VERSION,
            'subjects':deepcopy(case['bindings']),'interval':deepcopy(case['interval']),
            'hypothesisId':'review:hypothesis','method':'Bound the named synthetic assessment',
            'evidenceRefs':['review:primary','review:assessment-basis']}

    def case(self, pid='host-state', bindings=None, values=None):
        profile = self.catalog['profiles'][pid]
        if bindings is None:
            bindings = {'hostId':'review:host','stateKey':'service.enabled'}
        if values is None:
            values = {'state.value':False}
        case = {'id':'review:profile-case','domain':profile['domain'],'eventProfile':pid,
            'profileVersion':VERSION,'bindings':deepcopy(bindings),'interval':deepcopy(INTERVAL),
            'focus':profile['facets'][0]}
        facts = {'event.kind':profile['eventKind'],'event.id':'review:event',
            'relation.key':'review:shared','technical.source':'review:service',
            'metric.before':0,'metric.after':2,'metric.before.unit':'events','metric.after.unit':'events',
            'metric.before.id':'review:metric','metric.after.id':'review:metric',
            'metric.before.time':'2026-10-13T10:10:00Z','metric.after.time':'2026-10-13T10:30:00Z',**values}
        primary = {'id':'review:primary','origin':'review:origin-primary',
            'eventProfile':pid,'profileVersion':VERSION,'subjects':deepcopy(bindings),
            'eventTime':'2026-10-13T10:30:00Z','clockUncertaintySeconds':0,
            'evidenceFacet':case['focus'],'provenanceAssessment':'accepted','interpretationAssessment':'accepted',
            'assessmentMethod':'Manually examine the synthetic origin and interpretation',
            'assessmentEvidenceRefs':['review:provenance'],'facts':{k:observation(v,'metadata') for k,v in facts.items()}}
        independent = deepcopy(primary)
        independent.update(id='review:independent',origin='review:origin-independent',eventTime='2026-10-13T10:31:00Z')
        case.update(primary={'accessible':True,'searched':True,'records':[primary]},
            independent={'accessible':True,'searched':True,'records':[independent]})
        context = self.context(case)
        criterion_field = next(iter(values))
        case['analysis'] = {
            'hypothesis':{**deepcopy(context),'statement':'The named technical discriminator equals the declared value.',
                'alternatives':['The named technical discriminator has another value.'],
                'criterion':{'fact':criterion_field,'equals':values[criterion_field],'method':'Compare the explicit discriminator'}},
            'scope':{**deepcopy(context),'claimsCompletePopulation':False,'entities':[{
                'domain':case['domain'],'eventProfile':pid,'profileVersion':VERSION,'subjects':deepcopy(bindings),
                'disposition':'included','evidenceRefs':['review:scope-basis']}]},
            'corroboration':{**deepcopy(context),'sourceRecordId':primary['id'],
                'sourceFact':'event.id','targetFact':'event.id','identifierNamespace':'review:normalized-observation'},
            'correlation':{**deepcopy(context),'targetDomain':case['domain'],'targetEventProfile':pid,
                'targetProfileVersion':VERSION,'targetSubjects':deepcopy(bindings),'sourceRecordId':primary['id'],
                'targetRecord':deepcopy(independent),'relationKind':'shared-identifier',
                'sourceFact':'relation.key','targetFact':'relation.key'},
            'attribution':{**deepcopy(context),'claimKind':'technical-source','sourceEntityId':'review:service',
                'alternatives':['Another service emitted the observation.'],
                'criterion':{'fact':'technical.source','equals':'review:service','method':'Compare named technical source'}},
            'impact':{**deepcopy(context),'claimKind':'observed-metric-change','metricId':'review:metric','unit':'events',
                'baselineFact':'metric.before','observedFact':'metric.after','baselineUnitFact':'metric.before.unit',
                'observedUnitFact':'metric.after.unit','baselineMetricFact':'metric.before.id',
                'observedMetricFact':'metric.after.id','baselineTimeFact':'metric.before.time',
                'observedTimeFact':'metric.after.time'},
        }
        return case

    def retained(self, case, card, answer):
        return {**self.context(case),'nodeId':self.node_id(card),
            'questionId':definition_id(case['eventProfile'],self.node_id(card)),
            'focus':case['focus'],'answer':answer,'rationale':'Retain this exact bounded answer.',
            'limitations':['Only supplied synthetic evidence was examined.']}

    def retain(self, case, rows, disposition='open'):
        case['retention'] = {'eventProfile':case['eventProfile'],'profileVersion':VERSION,
            'subjects':deepcopy(case['bindings']),'interval':deepcopy(case['interval']),
            'graphVersion':self.criteria['graphVersion'],'closesInvestigation':False,
            'hypothesis':deepcopy(case['analysis'].get('hypothesis')),
            'focusDispositions':{case['focus']:disposition},'assessments':rows}

    def test_new_qualified_version_keeps_core_bindings(self):
        self.assertEqual('0.1.0-draft.2',VERSION)
        self.assertEqual(VERSION,self.catalog['version'])
        self.assertEqual(['hostId','processId'],self.criteria['domains']['Host']['bindings'])
        case = self.case()
        self.assertEqual('yes',self.answer(case,'classification'))
        row = definitions(self.graph,self.criteria,self.catalog)['host-state'][self.node_id(self.card(case,'classification'))]
        self.assertIn(VERSION,row['id'])
        self.assertEqual(['hostId','stateKey'],row['boundSubjectFields'])

    def test_extreme_clock_bounds_remain_unknown_without_overflow(self):
        case = self.case();case['primary']['records'][0]['clockUncertaintySeconds']=10**400
        self.assertEqual('unknown',self.answer(case,'entry'))
        case = self.case();card=self.restored(case,'temporal');case['focus']=card['sourceFacet']
        case['primary']['records'][0]['evidenceFacet']=case['focus']
        case['analysis']['correlation'].update(relationKind='bounded-time-coincidence',toleranceSeconds=10**400)
        self.assertEqual('yes',answer_profile(card,case,self.criteria,self.catalog)[0])

    def test_partial_record_subjects_are_unknown_and_known_mismatches_are_no(self):
        case = self.case('network-sensor-coverage',{'sensorId':'review:sensor','collectionId':'review:collection'},
            {'collection.status':'running'})
        for subjects in ({'sensorId':'review:sensor'}, {'sensorId':'review:sensor','collectionId':None},
                {'sensorId':'review:sensor','collectionId':False}, {'sensorId':'review:sensor','collectionId':7},
                {'sensorId':'review:sensor','collectionId':''}, None, []):
            case['primary']['records'][0]['subjects']=subjects
            with self.subTest(subjects=subjects):self.assertEqual('unknown',self.answer(case,'entry'))
        for subjects in ({'sensorId':'review:other'},
                {'sensorId':'review:other','collectionId':None},
                {'sensorId':'review:sensor','collectionId':'review:other'}):
            case['primary']['records'][0]['subjects']=subjects
            with self.subTest(subjects=subjects):self.assertEqual('no',self.answer(case,'entry'))
        self.assertEqual({'sensorId':'review:sensor','collectionId':'review:collection'},case['bindings'])

    def test_direct_independent_validation_rejects_copies_of_any_primary(self):
        for change in ('same-origin','same-id','missing-origin','wrong-label','second-primary'):
            case = self.case(); primary = case['primary']['records'][0]; independent = case['independent']['records'][0]
            if change == 'same-origin': independent['origin'] = primary['origin']
            elif change == 'same-id': independent['id'] = primary['id']
            elif change == 'missing-origin': independent.pop('origin')
            elif change == 'wrong-label':
                case['primaryOrigin'] = 'review:misleading-label'; independent['origin'] = primary['origin']
            else:
                extra = deepcopy(primary);extra.update(id='review:second-primary',origin=independent['origin'])
                case['primary']['records'].append(extra)
            with self.subTest(change=change):
                self.assertEqual('unknown',self.answer(case,'independentValidation'))
        self.assertEqual('yes',self.answer(self.case(),'independentValidation'))

    def test_independent_validation_preserves_group_and_record_through_route(self):
        case = self.case()
        case['entry'] = self.node_id(self.card(case,'independentValidation'))
        case['primary']['records'][0]['facts']['state.value']['value'] = True
        selected = case['independent']['records'][0]
        case['analysis']['scope']['evidenceRefs'] = [selected['id']]
        relation = case['analysis']['correlation']
        relation.update(sourceRecordId=selected['id'],targetRecord=deepcopy(case['primary']['records'][0]))
        second = deepcopy(selected);second['id']='review:other-independent';second['facts']['state.value']['value']=True
        case['independent']['records'].append(second)
        case['independent']['selectedRecordId'] = selected['id']
        trace = evaluate_route(self.graph,self.criteria,self.catalog,case)['trace']
        self.assertEqual(['yes','yes','yes'],[r['answer'] for r in trace[:3]])
        self.assertEqual('scope',self.criteria['nodes'][trace[2]['nodeId']]['role'])

    def test_unavailable_content_uses_declared_dependency_not_fact_name(self):
        case = self.case('file-unavailable-content',{'fileId':'review:file','systemId':'review:store'},
            {'content.availability':'encrypted'})
        record = case['primary']['records'][0]
        criterion = case['analysis']['hypothesis']['criterion']
        for field in ('metadata.digest','customDigest','content.hash','payload.signature'):
            for dependency,expected in ((None,'unknown'),('content','unknown'),('metadata','yes')):
                record['facts'][field] = observation('digest:claimed',dependency)
                criterion.update(fact=field,equals='digest:claimed')
                with self.subTest(field=field,dependency=dependency):
                    self.assertEqual(expected,self.answer(case,'classification'))
        record['facts']['customDigest'] = observation('digest:claimed','content')
        criterion.update(fact='customDigest',equals='digest:claimed')
        record['facts']['content.availability']['value'] = 'available'
        self.assertEqual('yes',self.answer(case,'classification'))
        record['facts']['customDigest']['evidenceDependency']['evidenceRefs'] = []
        self.assertEqual('unknown',self.answer(case,'classification'))

    def test_content_dependency_declaration_also_applies_to_required_facts(self):
        case = self.case('file-unavailable-content',{'fileId':'review:file','systemId':'review:store'},
            {'content.availability':'encrypted'})
        record = case['primary']['records'][0]
        record['facts']['content.availability'].pop('evidenceDependency')
        self.assertEqual('unknown',self.answer(case,'primaryValidation'))
        self.assertNotIn('content.availability',safe_record(record,self.catalog['profiles'][case['eventProfile']])['facts'])

    def test_criterion_declares_byte_verification_or_manifest_comparison_basis(self):
        case = self.case('file-unavailable-content',{'fileId':'review:file','systemId':'review:store'},
            {'content.availability':'encrypted'})
        record=case['primary']['records'][0]
        record['facts']['metadata.reportedDigest']=observation('digest:manifest','metadata')
        criterion=case['analysis']['hypothesis']['criterion']
        criterion.update(fact='metadata.reportedDigest',equals='digest:manifest',requiredEvidenceDependency='metadata')
        self.assertEqual('yes',self.answer(case,'classification'))
        criterion['requiredEvidenceDependency']='content'
        self.assertEqual('unknown',self.answer(case,'classification'))
        record['facts']['content.hash']=observation('digest:manifest','metadata')
        criterion['fact']='content.hash'
        self.assertEqual('unknown',self.answer(case,'classification'))
        record['facts']['content.availability']['value']='available'
        self.assertEqual('unknown',self.answer(case,'classification'))
        record['facts']['content.hash']['evidenceDependency']['kind']='content'
        self.assertEqual('yes',self.answer(case,'classification'))
        for invalid in ('unexamined',None,True,[]):
            criterion['requiredEvidenceDependency']=invalid
            with self.subTest(basis=invalid):self.assertEqual('unknown',self.answer(case,'classification'))

    def test_required_outcomes_and_lineage_have_declared_string_types(self):
        samples = [
            ('file-historical-lineage',{'fileId':'review:file','systemId':'review:store','revisionId':'review:r2'},'lineage.parentRevisionId','review:r1'),
            ('file-deletion',{'fileId':'review:file','systemId':'review:store','operationId':'review:delete'},'deletion.outcome','failed'),
            ('application-agent-action',{'applicationId':'review:app','agentId':'review:agent','actionId':'review:action'},'action.outcome','queued'),
        ]
        for pid,bindings,field,valid in samples:
            case = self.case(pid,bindings,{field:valid})
            self.assertEqual('yes',self.answer(case,'primaryValidation'))
            for bad in (True,2,2.5,'',None):
                case['primary']['records'][0]['facts'][field]['value'] = bad
                with self.subTest(profile=pid,bad=bad):
                    self.assertEqual('unknown',self.answer(case,'primaryValidation'))
        case = self.case('file-historical-lineage',samples[0][1],{'lineage.parentRevisionId':'review:r2'})
        self.assertEqual('unknown',self.answer(case,'primaryValidation'))

    def test_declared_state_and_configuration_scalars_remain_valid(self):
        for pid,bindings,field in [
            ('host-state',{'hostId':'review:host','stateKey':'review:key'},'state.value'),
            ('network-configuration',{'deviceId':'review:device','configurationId':'review:config'},'configuration.value')]:
            for scalar in (False,0,2.5,'enabled'):
                case = self.case(pid,bindings,{field:scalar})
                with self.subTest(profile=pid,scalar=scalar):
                    self.assertEqual('yes',self.answer(case,'primaryValidation'))
                    self.assertEqual('yes',self.answer(case,'classification'))

    def test_rule_operations_and_deletion_attempts_have_distinct_bound_identity(self):
        for pid,bindings,values in [
            ('file-deletion',{'fileId':'review:file','systemId':'review:store','operationId':'review:delete-a'},{'deletion.outcome':'failed'}),
            ('email-mailbox-rule',{'mailboxId':'review:mailbox','ruleId':'review:rule','operationId':'review:create-a'},
                {'rule.operation':'create','rule.outcome':'failed'})]:
            case = self.case(pid,bindings,values)
            self.assertIn('operationId',self.catalog['profiles'][pid]['bindings'])
            case['independent']['records'][0]['subjects']['operationId'] = 'review:other-operation'
            self.assertEqual('unknown',self.answer(case,'independentValidation'))
            case['bindings'].pop('operationId')
            self.assertEqual('unknown',self.answer(case,'entry'))

    def test_independent_fact_assessments_survive_refuted_or_open_hypothesis(self):
        for value in (True,None):
            case = self.case()
            if value is None:case['analysis']['hypothesis']['criterion']['fact']='review:unobserved'
            else:case['analysis']['hypothesis']['criterion']['equals']=value
            self.assertEqual('unknown' if value is None else 'no',self.answer(case,'classification'))
            for role in ('scope','correlation','attribution','impact'):
                with self.subTest(hypothesis=value,role=role):
                    self.assertEqual('yes',self.answer(case,role))
        case = self.case();case['analysis']['scope']['entities'][0]['disposition']='excluded'
        self.assertEqual('no',self.answer(case,'scope'))
        for role in ('correlation','attribution','impact'):
            self.assertEqual('yes',self.answer(case,role))

    def test_independent_fact_assessments_preserve_absent_hypothesis(self):
        case = self.case();case['analysis'].pop('hypothesis')
        for assessment in case['analysis'].values():assessment.pop('hypothesisId')
        self.assertEqual('unknown',self.answer(case,'classification'))
        for role in ('scope','correlation','attribution','impact'):
            with self.subTest(role=role):self.assertEqual('yes',self.answer(case,role))
        self.assertNotIn('hypothesis',case['analysis'])

    def test_independent_assessment_still_needs_own_evidence_and_exact_supplied_hypothesis(self):
        for role in ('scope','correlation','attribution','impact'):
            case = self.case();case['analysis'][role]['evidenceRefs']=[]
            self.assertEqual('unknown',self.answer(case,role))
            case = self.case();case['analysis']['hypothesis']['subjects']={}
            self.assertEqual('unknown',self.answer(case,role))

    def test_relation_target_can_have_its_own_explicit_bound_interval(self):
        case = self.case();a=case['analysis']['correlation']
        a['targetInterval']={'start':'2026-10-12T10:00:00Z','end':'2026-10-12T11:00:00Z'}
        a['targetRecord']['eventTime']='2026-10-12T10:30:00Z'
        self.assertEqual('yes',self.answer(case,'correlation'))
        a['targetInterval']['end']='2026-10-12T10:29:00Z'
        self.assertEqual('unknown',self.answer(case,'correlation'))

    def test_metric_baseline_can_have_its_own_explicit_bound_interval(self):
        case = self.case();metric=case['analysis']['impact']
        case['primary']['records'][0]['facts']['metric.before.time']['value']='2026-10-12T10:30:00Z'
        self.assertEqual('unknown',self.answer(case,'impact'))
        metric['baselineInterval']={'start':'2026-10-12T10:00:00Z','end':'2026-10-12T11:00:00Z'}
        self.assertEqual('yes',self.answer(case,'impact'))
        metric['baselineInterval']['end']='2026-10-12T10:29:00Z'
        self.assertEqual('unknown',self.answer(case,'impact'))

    def test_additional_effect_uses_targets_own_metric_answer(self):
        case = self.case();selected=case['primary']['records'][0]
        target_case = self.case(bindings={'hostId':'review:other-host','stateKey':'service.enabled'})
        target = target_case['primary']['records'][0]
        target.update(id='review:target',origin='review:target-origin')
        case['analysis']['scope']['entities'].append(deepcopy(target_case['analysis']['scope']['entities'][0]))
        a = deepcopy(case['analysis']['correlation'])
        a.update(targetSubjects=deepcopy(target_case['bindings']),targetRecord=target)
        case['analysis']['additionalEffect']=a
        result = lambda: relation_answer(case,selected,self.catalog,'additionalEffect','additional-impact')[0]
        self.assertEqual('unknown',result())
        a['targetAnalysis']={'impact':deepcopy(target_case['analysis']['impact'])}
        a['targetAnalysis']['impact'].pop('hypothesisId')
        self.assertEqual('yes',result())
        target['facts']['metric.after']['value']=0
        self.assertEqual('no',result())

    def test_fixed_facet_corroboration_cannot_use_other_facet_witness(self):
        case = self.case();card=self.restored(case,'corroboration');case['focus']=card['sourceFacet']
        case['primary']['records'][0]['evidenceFacet']=case['focus']
        case['independent']['records'][0]['evidenceFacet']='review:unrelated-facet'
        self.assertEqual('unknown',answer_profile(card,case,self.criteria,self.catalog)[0])
        case['independent']['records'][0]['evidenceFacet']=case['focus']
        self.assertEqual('yes',answer_profile(card,case,self.criteria,self.catalog)[0])
        case['independent']['records'][0]['facts']['event.id']['value']=False
        self.assertEqual('unknown',answer_profile(card,case,self.criteria,self.catalog)[0])

    def test_corroboration_uses_declared_fields_and_namespace_not_local_ids(self):
        case = self.case('network-sensor-coverage',{'sensorId':'review:sensor','collectionId':'review:collection'},
            {'collection.status':'running'})
        card=self.restored(case,'corroboration');case['focus']=card['sourceFacet']
        primary=case['primary']['records'][0];independent=case['independent']['records'][0]
        primary['evidenceFacet']=independent['evidenceFacet']=case['focus']
        primary['facts']['event.id']['value']='review:sensor-local-id'
        independent['facts']['event.id']['value']='review:archive-local-id'
        primary['facts']['sensor.sampleId']=observation(123)
        independent['facts']['archive.normalizedSample']=observation(123)
        a=case['analysis']['corroboration']
        a.update(sourceFact='sensor.sampleId',targetFact='archive.normalizedSample',identifierNamespace='review:normalized-sample-namespace')
        answer=lambda:answer_profile(card,case,self.criteria,self.catalog)[0]
        self.assertEqual('yes',answer())
        a.pop('identifierNamespace')
        self.assertEqual('unknown',answer())
        a['mappingEvidenceRefs']=['review:explicit-sample-mapping']
        self.assertEqual('yes',answer())
        independent['facts']['archive.normalizedSample']['value']='123'
        self.assertEqual('unknown',answer())
        independent['facts']['archive.normalizedSample']['value']=124
        self.assertEqual('no',answer())
        a['sourceRecordId']='review:unselected-record'
        self.assertEqual('unknown',answer())

    def test_corroboration_preserves_witness_lineage_clock_bounds_and_conflicts(self):
        case = self.case();card=self.restored(case,'corroboration');case['focus']=card['sourceFacet']
        primary=case['primary']['records'][0];independent=case['independent']['records'][0]
        primary['evidenceFacet']=independent['evidenceFacet']=case['focus']
        answer=lambda:answer_profile(card,case,self.criteria,self.catalog)[0]
        independent['eventTime']=case['interval']['start'];independent['clockUncertaintySeconds']=1
        self.assertEqual('unknown',answer())
        independent.update(eventTime='2026-10-13T10:31:00Z',clockUncertaintySeconds=0,origin=primary['origin'])
        self.assertEqual('unknown',answer())
        independent['origin']='review:origin-independent'
        rejected=deepcopy(primary);rejected.update(id='review:copied-rejected',provenanceAssessment='rejected')
        case['independent']['records'].append(rejected)
        self.assertEqual('yes',answer())
        conflicting=deepcopy(independent);conflicting.update(id='review:conflict',origin='review:third-origin')
        conflicting['facts']['event.id']['value']='review:contradicting-event'
        case['independent']['records'].append(conflicting)
        self.assertEqual('unknown',answer())
        case['independent']['records'].reverse()
        self.assertEqual('unknown',answer())

    def test_observation_definitions_do_not_infer_actions_from_evidence_focus(self):
        rows=definitions(self.graph,self.criteria,self.catalog)
        for pid,profile in self.catalog['profiles'].items():
            if profile['observationMode']!='observation':continue
            for node_id,row in rows[pid].items():
                card=self.criteria['nodes'][node_id]
                if card['role']!='restored' or card.get('stage')=='terminal':continue
                with self.subTest(profile=pid,node=node_id):
                    self.assertIn(profile['proposition'],row['predicate'])
                    self.assertIn('evidence-focus label alone does not establish a historical change, action, execution or access',row['predicate'])
                    self.assertEqual(definition_id(pid,node_id),row['id'])
        for node_id in ['Q25','Q90','Q97','Q146','Q195','Q357','Q386','Q434']:
            self.assertIn('the observed named cloud resource state',rows['cloud-resource-state'][node_id]['predicate'])

    def test_assessed_focus_requires_applicable_retained_nonterminal_assessment(self):
        case = self.case();row=self.retained(case,self.card(case,'entry'),'yes')
        row.pop('focus')
        self.retain(case,[row],'assessed')
        self.assertEqual('unknown',self.answer(case,'assessed'))
        case['retention']['focusDispositions'][case['focus']]='open'
        self.assertEqual('yes',self.answer(case,'assessed'))
        card=self.restored(case,'event-match');case['focus']=card['sourceFacet']
        self.retain(case,[self.retained(case,card,'no')],'assessed')
        self.assertEqual('yes',self.answer(case,'assessed'))

    def test_explicitly_focused_generic_nonterminal_rows_can_retain_assessed_focus(self):
        case = self.case('network-sensor-coverage',{'sensorId':'review:sensor','collectionId':'review:collection'},
            {'collection.status':'running'})
        case['focus']='transport metadata';case['analysis'].pop('hypothesis')
        rows=[self.retained(case,self.card(case,role),'yes')for role in ['entry','primaryValidation','impact']]
        for row in rows:row.pop('hypothesisId')
        self.retain(case,rows,'assessed')
        self.assertEqual('yes',self.answer(case,'assessed'))
        fixed=self.restored(case,'event-match');fixed_row=self.retained(case,fixed,'yes')
        fixed_row.pop('hypothesisId')
        fixed_row['focus']=next(f for f in self.catalog['profiles'][case['eventProfile']]['facets'] if f!=fixed['sourceFacet'])
        case['retention']['assessments'].append(fixed_row)
        self.assertEqual('unknown',self.answer(case,'assessed'))

    def test_generic_terminal_history_uses_qualified_supplied_focus(self):
        case = self.case();card=self.restored(case,'event-match');case['focus']=card['sourceFacet']
        self.retain(case,[self.retained(case,card,'no')],'assessed')
        terminal = next(c for c in self.criteria['nodes'].values() if c['domain']==case['domain']
            and c['role']=='restored' and c.get('stage')=='terminal'
            and c.get('sourceFacet') not in self.catalog['profiles']['host-state']['facets'])
        self.assertEqual('yes',answer_profile(terminal,case,self.criteria,self.catalog)[0])
        history = self.retained(case,terminal,'yes');case['retention']['assessments'].append(history)
        case['retainedTrace']=[{'nodeId':history['nodeId'],'answer':'yes','focus':case['focus']}]
        self.assertEqual('yes',self.answer(case,'assessed'))
        original_focus = history.pop('focus')
        self.assertEqual('unknown',self.answer(case,'assessed'))
        history['focus']=original_focus
        history['focus']='review:changed-focus'
        self.assertEqual('unknown',self.answer(case,'assessed'))

    def test_handoff_preserves_distinct_focus_history_without_rebinding(self):
        case = self.case();event_card=self.restored(case,'event-match');case['focus']=event_card['sourceFacet']
        first = self.retained(case,event_card,'no')
        self.retain(case,[first],'assessed')
        terminal = next(c for c in self.criteria['nodes'].values() if c['domain']==case['domain']
            and c['role']=='restored' and c.get('stage')=='terminal')
        first_terminal = self.retained(case,terminal,'yes')
        case['retention']['assessments'].append(first_terminal)
        new_focus = next(f for f in self.catalog['profiles'][case['eventProfile']]['facets'] if f!=case['focus'])
        case['focus']=new_focus
        case['retention']['focusDispositions'][new_focus]='open'
        second_terminal = self.retained(case,terminal,'unknown')
        case['retention']['assessments'].append(second_terminal)
        case['retainedTrace']=[{'nodeId':first_terminal['nodeId'],'focus':first_terminal['focus'],'answer':'yes'},
            {'nodeId':second_terminal['nodeId'],'focus':new_focus,'answer':'unknown'}]
        self.assertEqual('yes',self.answer(case,'assessed'))
        case['retention']['assessments'].remove(first_terminal)
        self.assertEqual('no',self.answer(case,'assessed'))

    def test_handoff_retains_actual_answers_without_all_stages_or_support(self):
        case = self.case();classification=self.card(case,'classification')
        self.retain(case,[self.retained(case,classification,'no')])
        self.assertEqual('yes',self.answer(case,'assessed'))
        case['retainedTrace']=[{'nodeId':self.node_id(classification),'answer':'no'}]
        self.assertEqual('yes',self.answer(case,'assessed'))
        case['retention']['assessments'][0]['answer']='yes'
        self.assertEqual('no',self.answer(case,'assessed'))
        case['retention']['assessments'][0]['answer']='no'
        case['retention']['assessments'][0]['hypothesisStatement']='A changed proposition under the same ID.'
        self.assertEqual('unknown',self.answer(case,'assessed'))


if __name__ == '__main__':
    unittest.main()
