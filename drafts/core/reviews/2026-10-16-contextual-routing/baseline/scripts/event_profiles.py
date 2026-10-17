"""Explicit public event-profile interpretations of the unchanged working graph.

Profile-qualified questions are distinct definitions, never silent replacements
for the base questions. Supplied assessed observations are not verified truth.
"""
from copy import deepcopy
import json
from pathlib import Path

from evaluate_entry_scenarios import (context_ready, fact, named, references,
    validation_answer, bound_assessment, equality_answer, downstream_answer, instant, exclusion_answer,
    finite_nonnegative, record_group)

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0-draft.2'
BASELINE = '78a275b127d2f24933c3ec16d9a2b0b1c38fb0af'
ROLE_STAGE = {'entry':'detect','alternate':'detect','primaryValidation':'validate',
    'independentValidation':'validate','classification':'classify','scope':'scope',
    'correlation':'correlate','attribution':'attribute','impact':'impact',
    'exclusion':'terminal','unresolved':'terminal','refuted':'terminal','assessed':'terminal'}
ROLE_PROMPTS = {
    'entry':'Does the examined evidence contain a record of {event} matching every declared subject and the bound interval?',
    'alternate':'Does separately originating evidence contain a record of {event} matching every declared subject and the bound interval?',
    'primaryValidation':'Does the selected record of {event} have a cited acceptable provenance and interpretation basis?',
    'independentValidation':'Does the separately originating record of {event} have a cited acceptable provenance and interpretation basis?',
    'classification':'Does the validated record of {event} satisfy the declared falsifiable technical hypothesis, with alternatives assessed?',
    'scope':'Does the exact context of {event} retain evidenced inclusions, exclusions and unknowns alongside any separately declared technical hypothesis?',
    'correlation':'Do separately validated observations of {event} and the named target share the declared assessed identifier?',
    'attribution':'Does the assessed discriminator for {event} support the named technical source, with alternatives retained?',
    'impact':'Does {event} show the named observed technical metric change against a comparable bounded baseline?',
    'exclusion':'Does the explicit logging and search coverage basis exclude {event} within every declared subject and the entire interval?',
    'unresolved':'Were the unresolved or rejected prerequisites for {event} retained separately with their evidence and limitations?',
    'refuted':'Was the contradicted technical hypothesis for {event} retained without refuting the event or proving alternatives?',
    'assessed':'Were the actual bounded answers for {event}, including any declared hypothesis answer and open questions, retained with their evidence and limitations without closing the investigation?',
}
OBSERVATION_PROMPTS = {
    'event-match':'Does the examined {facet} material contain a record of {event} matching every declared subject and the bound interval?',
    'provenance':'Does the selected record of {event}, examined under the {facet} evidence focus, have a cited acceptable provenance and interpretation basis?',
    'corroboration':'Do separately originating validated records of {event}, examined under the {facet} evidence focus, agree on the explicitly declared discriminator within its assessed namespace or mapping and exact subject/time bounds?',
    'baseline':'Does the validated record of {event}, examined under the {facet} evidence focus, satisfy the declared operational comparator criterion with its applicability and evidence basis retained?',
    'hypothesis':'Does the validated record of {event}, examined under the {facet} evidence focus, satisfy the declared criterion for one named technical hypothesis, with competing explanations assessed?',
    'scope-bound':'Were evidence-backed full entity inclusions, exclusions and unknown dispositions for {event}, examined under the {facet} evidence focus, recorded within exact subject/time bounds without claiming population completeness?',
    'additional-entities':'Were additional named full entity contexts included in the bounded scope of {event}, examined under the {facet} evidence focus, using cited evidence with exclusions and unknowns retained?',
    'dependencies':'Does the bounded scope of {event}, examined under the {facet} evidence focus, include an evidenced documented dependency with full named validated endpoints, relation identifier and direction?',
    'identifier-relation':'Do separately validated records of {event} and the named target, examined under the {facet} evidence focus, share the declared assessed identifier within their explicit endpoint contexts?',
    'temporal':'Do separately validated records of {event} and the named target, examined under the {facet} evidence focus, meet the declared temporal-coincidence tolerance within their own bounded contexts after accounting for both clock uncertainties?',
    'technical-source':'Does the assessed discriminator for {event} in the examined {facet} material support the named technical source under its declared criterion, with competing explanations retained?',
    'behavior-pattern':'Does the validated record of {event}, examined under the {facet} evidence focus, satisfy the declared technical behavior-pattern discriminator with alternative explanations retained?',
    'metric-change':'Did the named technical metric for the bound effect subjects of {event}, examined under the {facet} evidence focus, change between separately declared comparable baseline and observation contexts with the same metric and units?',
    'additional-impact':'Did the named technical metric for the explicitly bound additional effect subject related to {event}, examined under the {facet} evidence focus, change between its own separately declared comparable baseline and observation contexts with the same metric and units?',
}


def load_package():
    graph = json.loads((ROOT/'drafts/core/tensor.core.graph.json').read_text())
    criteria = json.loads((ROOT/'drafts/core/entry-evidence-criteria.json').read_text())
    catalog = json.loads((ROOT/'drafts/core/event-profiles/catalog.json').read_text())
    return graph, criteria, catalog


def profile_for(catalog, domain, profile_id):
    profile = catalog['profiles'].get(profile_id)
    return profile if profile and profile['domain'] == domain else None


def definition_id(profile_id, node_id):
    return f'urn:tensor:event-profile:{profile_id}:{VERSION}:{node_id}'


def definitions(graph, criteria, catalog):
    result = {}
    for pid, profile in catalog['profiles'].items():
        rows = {}
        for node in graph['nodes']:
            card = criteria['nodes'][node['id']]
            if card['domain'] != profile['domain']:
                continue
            if card['role'] == 'restored' and card.get('stage') != 'terminal' and card['sourceFacet'] not in profile['facets']:
                continue
            prompt = card['predicate'] if card['role'] == 'restored' else ROLE_PROMPTS[card['role']].format(event=profile['proposition'])
            if card['role'] == 'classification' and len(criteria['domains'][card['domain']]['classification']) > 1:
                witness = 'primary' if node['id'] == criteria['domains'][card['domain']]['classification'][0] else 'separately originating'
                prompt = prompt.replace('validated record', f'validated {witness} record')
            if card['role'] == 'restored' and card.get('stage') == 'terminal':
                prompt = f"Were the bounded assessments of {profile['proposition']} and open evidence-focus questions retained separately with references and limitations, without investigation closure?"
            elif card['role'] == 'restored' and profile.get('observationMode') == 'observation':
                prompt = OBSERVATION_PROMPTS[card['assessmentKind']].format(event=profile['proposition'],facet=card['sourceFacet'])
                prompt += ' This profile assesses an observation; the evidence-focus label alone does not establish a historical change, action, execution or access.'
            rows[node['id']] = {'id':definition_id(pid,node['id']), 'graphNodeId':node['id'],
                'profileId':pid, 'profileVersion':VERSION, 'predicate':prompt,
                'boundSubjectFields':profile['bindings'], 'rule':card['rule'],
                'requiredInterpretationDependency':f'urn:tensor:event-profile:{pid}:{VERSION}'}
        result[pid] = rows
    return result


def event_domain(profile):
    return {'bindings':profile['bindings']}


def assessment_criteria(criteria, case, profile):
    """Use this qualified identity for fact checks without changing Core bindings."""
    domains = dict(criteria.get('domains',{}))
    domains[case['domain']] = {**domains.get(case['domain'],{}),**event_domain(profile)}
    return {**criteria,'domains':domains}


def exact_context(value, case):
    return (isinstance(value,dict) and value.get('eventProfile') == case.get('eventProfile')
            and value.get('profileVersion') == VERSION and value.get('subjects') == case.get('bindings')
            and value.get('interval') == case.get('interval'))


def assessed_context(value, case):
    hypothesis = case.get('analysis',{}).get('hypothesis')
    if hypothesis is not None and (not exact_context(hypothesis,case)
            or not named(hypothesis.get('hypothesisId')) or not named(hypothesis.get('statement'))):
        return False
    hid = hypothesis.get('hypothesisId') if isinstance(hypothesis,dict) else None
    return (exact_context(value,case) and bound_assessment(value,case,hid)
            and named(value.get('method')) and references(value.get('evidenceRefs')))


def match_profile(case, profile, group):
    if not context_ready(case,event_domain(profile)) or case.get('materialConflict'):
        return 'unknown','Subject/time bounds or counterevidence are unresolved',None
    if group.get('accessible') is not True or group.get('searched') is not True:
        return 'unknown','Evidence is unavailable or the declared search is incomplete',None
    unresolved = False
    candidates = []
    for record in group.get('records',[]):
        if not isinstance(record,dict):
            unresolved = True
            continue
        subjects = record.get('subjects',{})
        if not isinstance(subjects,dict):
            unresolved = True
            continue
        if any(named(subjects.get(f)) and subjects[f] != case['bindings'][f] for f in profile['bindings']):
            continue
        if any(not named(subjects.get(f)) for f in profile['bindings']):
            unresolved = True
            continue
        when = instant(record.get('eventTime'))
        if not when:
            unresolved = True
            continue
        uncertainty = record.get('clockUncertaintySeconds')
        if not finite_nonnegative(uncertainty):
            unresolved = True
            continue
        # Compare seconds, rather than constructing an unbounded timedelta.
        start,end = (instant(case['interval'][k]) for k in ('start','end'))
        before_start,after_end = (when-start).total_seconds(),(end-when).total_seconds()
        if before_start < -uncertainty or after_end <= -uncertainty:
            continue
        if before_start < uncertainty or after_end <= uncertainty:
            unresolved = True
            continue
        kind = fact(record,'event.kind')
        if record.get('eventProfile') != case['eventProfile'] or record.get('profileVersion') != VERSION or kind is None:
            unresolved = True
            continue
        if kind != profile['eventKind']:
            continue
        candidates.append(record)
    selected_id = group.get('selectedRecordId')
    if selected_id is not None:
        candidates = [r for r in candidates if r.get('id') == selected_id]
        if len(candidates) != 1:
            return 'unknown','The explicitly selected observation is not one unique matching profile record',None
    if len(candidates) > 1:
        return 'unknown','Multiple matching observations need an explicit selectedRecordId; list order is not an assessment',None
    if candidates:
        return 'yes','A profile-discriminated record matches all declared subjects and the interval',candidates[0]
    return ('unknown','Matching material lacks a resolved profile, event kind or event time',None) if unresolved else (
        'no','The completed search found no matching profile event in the examined material; absence is unproved',None)


def validate_record(record, case, profile):
    record = safe_record(record,profile) if isinstance(record,dict) else record
    result = validation_answer(record,case)
    if result[0] != 'yes':
        return result
    if not named(record.get('id')) or not named(record.get('origin')) or not named(record.get('assessmentMethod')):
        return 'unknown','The selected profile observation needs an identity and cited assessment method'
    for field in profile['requiredFacts']:
        value = fact(record,field)
        types = profile.get('requiredFactTypes',{}).get(field,[])
        value_type = {str:'string',bool:'boolean',int:'integer',float:'number'}.get(type(value))
        if value is None or value_type not in types:
            return 'unknown',f'The profile requires an assessed {field} of its declared value type with method and references'
    if profile.get('observationMode') == 'historical-lineage':
        if fact(record,'lineage.parentRevisionId') == case['bindings']['revisionId']:
            return 'unknown','A revision cannot establish its own historical parent'
    return result


def safe_record(record, profile):
    value = deepcopy(record)
    if profile.get('contentAvailabilityFact'):
        available = fact(record,profile['contentAvailabilityFact']) == 'available'
        # Names cannot establish whether a fact was measured from bytes or from
        # a manifest. Every usable fact in this profile declares that dependency.
        def usable(item):
            dependency = item.get('evidenceDependency',{}) if isinstance(item,dict) else {}
            return (isinstance(dependency,dict) and references(dependency.get('evidenceRefs'))
                    and (dependency.get('kind') == 'metadata'
                         or (available and dependency.get('kind') == 'content')))
        value['facts'] = {k:v for k,v in value.get('facts',{}).items() if usable(v)}
    return value


def criterion_basis_ready(record, criterion):
    """A claim may require a particular declared evidence basis, never infer it."""
    if not isinstance(criterion,dict) or 'requiredEvidenceDependency' not in criterion:
        return True
    required = criterion['requiredEvidenceDependency']
    item = record.get('facts',{}).get(criterion.get('fact'),{})
    dependency = item.get('evidenceDependency',{}) if isinstance(item,dict) else {}
    return (required in ('metadata','content') and isinstance(dependency,dict)
            and dependency.get('kind') == required and references(dependency.get('evidenceRefs')))


def profile_equality_answer(record, criterion):
    if not criterion_basis_ready(record,criterion):
        return 'unknown','The criterion needs its explicitly required evidence dependency and cited fact basis'
    return equality_answer(record,criterion)


def independent_record(record, case):
    """Separation is from every actual primary record, not an optional label."""
    if not named(record.get('id')) or not named(record.get('origin')):
        return False
    for primary in case.get('primary',{}).get('records',[]):
        if (not isinstance(primary,dict) or not named(primary.get('id')) or not named(primary.get('origin'))
                or record['id'] == primary['id'] or record['origin'] == primary['origin']):
            return False
    return not (named(case.get('primaryOrigin')) and record['origin'] == case['primaryOrigin'])


def target_record(assessment, case, selected, catalog):
    profile = profile_for(catalog,assessment.get('targetDomain'),assessment.get('targetEventProfile'))
    if not profile or assessment.get('targetProfileVersion') != VERSION or assessment.get('sourceRecordId') != selected.get('id'):
        return None,None,None
    target = assessment.get('targetRecord')
    target_case = {'domain':assessment['targetDomain'],'eventProfile':assessment['targetEventProfile'],
        'profileVersion':VERSION,'bindings':assessment.get('targetSubjects',{}),
        'interval':assessment.get('targetInterval',case['interval'])}
    result,_,_ = match_profile(target_case,profile,{'accessible':True,'searched':True,'records':[target]})
    if (result != 'yes' or validate_record(target,target_case,profile)[0] != 'yes'
            or target.get('id') == selected.get('id') or target.get('origin') == selected.get('origin')):
        return None,None,None
    return safe_record(target,profile),target_case,profile


def scope_answer(case, selected, catalog):
    a = case.get('analysis',{}).get('scope',{})
    if not assessed_context(a,case) or selected.get('id') not in a.get('evidenceRefs',[]) or a.get('claimsCompletePopulation') is not False:
        return 'unknown','Scope needs its exact profile context, selected evidence and explicit incomplete-population boundary'
    entities = a.get('entities')
    if not isinstance(entities,list) or not entities:
        return 'unknown','No evidenced entity dispositions were supplied'
    source_key = None
    seen = {}
    for entity in entities:
        if not isinstance(entity,dict):
            return 'unknown','Scope entities must be structured profile contexts'
        profile = profile_for(catalog,entity.get('domain'),entity.get('eventProfile'))
        subjects = entity.get('subjects',{})
        if (not profile or entity.get('profileVersion') != VERSION or not isinstance(subjects,dict)
                or not all(named(subjects.get(f)) for f in profile['bindings'])
                or entity.get('disposition') not in ('included','excluded','unknown')
                or (entity['disposition'] != 'unknown' and not references(entity.get('evidenceRefs')))):
            return 'unknown','Each entity needs a known profile, full declared identity, disposition and evidence basis'
        key = (entity['domain'],entity['eventProfile'],tuple(subjects[f] for f in profile['bindings']))
        if key in seen and seen[key] != entity['disposition']:
            return 'unknown','Conflicting dispositions for one full profile identity need reassessment'
        seen[key] = entity['disposition']
        if entity['domain'] == case['domain'] and entity['eventProfile'] == case['eventProfile'] and subjects == case['bindings']:
            source_key = key
    if source_key is None or seen[source_key] == 'unknown':
        return 'unknown','The exact source profile context has no evidenced inclusion'
    if seen[source_key] == 'excluded':
        return 'no','The source profile context is explicitly excluded'
    return 'yes','Full profile identities and evidence-backed dispositions are retained; population completeness remains open'


def relation_answer(case, selected, catalog, field='correlation', kind='identifier-relation'):
    a = case.get('analysis',{}).get(field,{})
    if not assessed_context(a,case):
        return 'unknown','The relation lacks its exact profile, subject, time, hypothesis and assessment basis'
    target,tc,tp = target_record(a,case,selected,catalog)
    if target is None:
        return 'unknown','Both relation endpoints need their own explicit profiles and separately validated records'
    if kind == 'temporal':
        tolerance = a.get('toleranceSeconds')
        clocks = [r.get('clockUncertaintySeconds') for r in (selected,target)]
        if (a.get('relationKind') != 'bounded-time-coincidence' or
                any(not finite_nonnegative(v) for v in [tolerance,*clocks])):
            return 'unknown','A bounded coincidence method and finite nonnegative clock uncertainties are required'
        for record,uncertainty,record_case in zip((selected,target),clocks,(case,tc)):
            start,end = (instant(record_case['interval'][k]) for k in ('start','end'))
            when = instant(record['eventTime'])
            if (when-start).total_seconds() < uncertainty or (end-when).total_seconds() <= uncertainty:
                return 'unknown','A source clock bound crosses the declared interval'
        distance = abs((instant(selected['eventTime'])-instant(target['eventTime'])).total_seconds())
        low,high = max(0,distance-sum(clocks)),distance+sum(clocks)
        return ('yes','Outer clock bounds meet the coincidence tolerance; no causation is inferred') if high <= tolerance else (
            ('no','Closest clock bounds contradict coincidence') if low > tolerance else ('unknown','Clock uncertainty overlaps the coincidence threshold'))
    if kind == 'dependencies':
        if a.get('claimKind') != 'documented-dependency' or a.get('direction') not in ('upstream','downstream'):
            return 'unknown','A documented dependency and direction are required'
        for record,prefix,subjects,pid in ((selected,'source',case['bindings'],case['eventProfile']),
                                           (target,'target',tc['bindings'],tc['eventProfile'])):
            profile = catalog['profiles'][pid]
            for binding in profile['bindings']:
                actual = fact(record,f'dependency.{prefix}.{binding}')
                if actual is None:
                    return 'unknown','A declared dependency endpoint discriminator is unassessed'
                if actual != subjects[binding]:
                    return 'no','The assessed dependency endpoint contradicts the full named context'
        ids = [fact(r,'dependency.relationId') for r in (selected,target)]
        directions = [fact(r,'dependency.direction') for r in (selected,target)]
        if None in ids+directions or not named(a.get('relationId')):
            return 'unknown','The dependency relation ID and direction need assessments on both endpoints'
        if ids != [a['relationId']]*2 or directions != [a['direction']]*2:
            return 'no','The assessed dependency relation or direction contradicts the claim'
        dispositions = [e['disposition'] for e in case['analysis']['scope']['entities'] if
            e['domain'] == tc['domain'] and e['eventProfile'] == tc['eventProfile'] and e['subjects'] == tc['bindings']]
        if 'excluded' in dispositions:
            return 'no','The dependency target is explicitly excluded'
        return ('yes','A separately validated documented dependency target is included') if 'included' in dispositions else (
            'unknown','The dependency target has no evidenced inclusion')
    if a.get('relationKind') != 'shared-identifier':
        return 'unknown','This profile tests an explicit shared identifier, not causal inference'
    left,right = fact(selected,a.get('sourceFact')),fact(target,a.get('targetFact'))
    if left is None or right is None or type(left) is not type(right):
        return 'unknown','The relation discriminator is unassessed or incompatible'
    if left != right:
        return 'no','The endpoint discriminators contradict the shared identifier'
    if kind == 'additional-impact':
        if tc['eventProfile'] == case['eventProfile'] and tc['bindings'] == case['bindings'] and tc['domain'] == case['domain']:
            return 'no','The proposed effect subject is the same complete profile identity'
        if scope_answer(case,selected,catalog)[0] == 'unknown':
            return 'unknown','The additional effect subject needs its own bounded evidenced scope disposition'
        dispositions = [e['disposition'] for e in case['analysis']['scope']['entities'] if
            e['domain'] == tc['domain'] and e['eventProfile'] == tc['eventProfile'] and e['subjects'] == tc['bindings']]
        if 'excluded' in dispositions:
            return 'no','The additional effect subject is explicitly excluded'
        if 'included' not in dispositions:
            return 'unknown','The additional effect subject needs an evidenced scope inclusion'
        metric_case = deepcopy(tc)
        metric_case['analysis'] = deepcopy(a.get('targetAnalysis',{}))
        metric = metric_case['analysis'].get('impact',{})
        if not assessed_context(metric,metric_case):
            return 'unknown','The additional subject needs its own profile-bound hypothesis and metric assessment'
        return downstream_answer('impact',metric_case,target,assessment_criteria({},metric_case,tp))
    return 'yes','Validated endpoints share the assessed identifier; this does not establish causation'


def terminal_answer(card, case, criteria, catalog):
    ledger = case.get('retention',{})
    if (not exact_context(ledger,case) or ledger.get('graphVersion') != criteria['graphVersion']
            or ledger.get('hypothesis') != case.get('analysis',{}).get('hypothesis')
            or ledger.get('closesInvestigation') is not False):
        return 'unknown','Retain the exact profile/version, graph version, subjects and interval without closure'
    if ledger.get('knownMissing') is True:
        return 'no','A required assessment is known missing from this exact retained context'
    retained = ledger.get('assessments',[])
    prerequisites = ledger.get('prerequisiteAssessments',[])
    if not isinstance(retained,list) or not isinstance(prerequisites,list):
        return 'unknown','Retained assessments must be structured lists'
    rows = retained+prerequisites
    if not rows or any(not isinstance(row,dict) for row in rows):
        return 'unknown','No separate qualified question assessments were retained'
    seen,stages = {},{}
    pid = case['eventProfile']
    dispositions = ledger.get('focusDispositions',{})
    if (not isinstance(dispositions,dict) or case.get('focus') not in catalog['profiles'][pid]['facets']
            or dispositions.get(case['focus']) not in ('open','assessed')):
        return 'unknown','Retain the supplied source focus as assessed or explicitly open'
    if any(focus not in catalog['profiles'][pid]['facets'] or disposition not in ('open','assessed')
            for focus,disposition in dispositions.items()):
        return 'unknown','Every retained evidence focus needs an applicable profile and explicit disposition'
    for row in rows:
        previous = criteria['nodes'].get(row.get('nodeId'))
        previous_stage = previous.get('stage',ROLE_STAGE.get(previous['role'])) if previous else None
        fixed_focus = previous.get('sourceFacet') if previous and previous_stage != 'terminal' else None
        retained_focus = row.get('focus',fixed_focus or case.get('focus'))
        hypothesis = case.get('analysis',{}).get('hypothesis')
        retained_meaning = {'hypothesis':hypothesis,**{'hypothesis'+field.title():
            hypothesis.get(field) if isinstance(hypothesis,dict) else None
            for field in ('statement','criterion','alternatives')}}
        if (not previous or previous['domain'] != case['domain'] or not assessed_context(row,case)
                or row.get('questionId') != definition_id(pid,row['nodeId'])
                or row.get('answer') not in ('yes','no','unknown') or not named(row.get('rationale'))
                or not references(row.get('limitations'))
                or (fixed_focus and (fixed_focus not in catalog['profiles'][pid]['facets']
                    or retained_focus != fixed_focus))
                or (previous_stage == 'terminal' and not named(row.get('focus')))
                or retained_focus not in dispositions
                or any(field in row and row[field] != value for field,value in retained_meaning.items())):
            return 'unknown','Every retained row needs its exact qualified question, profile context, method, references and limitations'
        key = (row['nodeId'],retained_focus)
        if key in seen and seen[key] != row['answer']:
            return 'unknown','Conflicting qualified question answers require an explicit assessment history'
        seen[key] = row['answer']
        if previous.get('assessmentKind') not in ('additional-entities','dependencies','behavior-pattern','additional-impact'):
            stages.setdefault(previous.get('stage',ROLE_STAGE.get(previous['role'])),[]).append(row['answer'])
    for prior in case.get('retainedTrace',[]):
        previous = criteria['nodes'].get(prior['nodeId'],{})
        fixed_focus = previous.get('sourceFacet') if previous.get('stage') != 'terminal' else None
        focus = prior.get('focus',fixed_focus or case.get('focus'))
        if seen.get((prior['nodeId'],focus)) != prior['answer']:
            return 'no','The retained record drops or changes a preceding qualified assessment'
    role = card['role']
    if role == 'refuted' and 'no' not in stages.get('classify',[]):
        return 'unknown','No retained assessment refutes this exact hypothesis'
    if role == 'unresolved' and not any(r['answer']=='unknown' or (r['answer']=='no' and
            criteria['nodes'][r['nodeId']].get('role') in ('primaryValidation','independentValidation','scope')) for r in rows):
        return 'unknown','An unresolved ending needs an actual retained uncertainty or rejected prerequisite'
    for focus,disposition in dispositions.items():
        if disposition == 'assessed' and not any(
                row.get('focus',criteria['nodes'][row['nodeId']].get('sourceFacet')) == focus
                and criteria['nodes'][row['nodeId']].get('stage',ROLE_STAGE.get(
                    criteria['nodes'][row['nodeId']]['role'])) != 'terminal' for row in rows):
            return 'unknown','A focus marked assessed needs its own retained applicable nonterminal assessment'
    return 'yes','Separate profile-qualified assessments and limitations are retained; this route does not close the investigation'


def answer_profile(card, case, criteria, catalog):
    profile = profile_for(catalog,case.get('domain'),case.get('eventProfile'))
    if (not profile or case.get('profileVersion') != VERSION or card['domain'] != case.get('domain')
            or not context_ready(case,event_domain(profile)) or case.get('materialConflict')):
        return 'unknown','A known domain/profile/version, full subjects and bounded interval are required'
    stage = card.get('stage',ROLE_STAGE.get(card['role']))
    kind = card.get('assessmentKind')
    if kind and stage != 'terminal' and (case.get('focus') != card['sourceFacet'] or card['sourceFacet'] not in profile['facets']):
        return 'unknown','This fixed evidence facet is outside the selected profile or bound focus'
    if stage == 'terminal':
        if card['role'] == 'exclusion':
            coverage = case.get('coverage',{})
            if not exact_context(coverage,case) or not references(coverage.get('evidenceRefs')) or coverage.get('eventKind') != profile['eventKind']:
                return 'unknown','Exclusion needs its own profile-specific coverage method and references, not a state snapshot'
            if not named(coverage.get('method')):
                return 'unknown','The profile-specific coverage basis needs a declared assessment method'
            from evaluate_entry_scenarios import COVERAGE_FLAGS
            if any(coverage.get(flag) is False for flag in COVERAGE_FLAGS):
                return 'no','A known full-interval coverage gap prevents this exclusion'
            examined = deepcopy(case)
            for name in ('primary','independent'):
                group = case.get(name,{})
                if group.get('accessible') is not True or group.get('searched') is not True:
                    return 'unknown','Exclusion cannot use unavailable or incompletely examined declared material'
                relevant = []
                for r in group.get('records',[]):
                    matched,_,_ = match_profile(case,profile,{'accessible':True,'searched':True,'records':[r]})
                    if matched == 'unknown':
                        return 'unknown','Unresolved profile event context prevents a bounded exclusion'
                    if matched == 'yes':
                        relevant.append(r)
                examined[name]['records'] = relevant
            return exclusion_answer(examined,event_domain(profile))
        return terminal_answer(card,case,criteria,catalog)
    group_name = record_group(card,case,criteria)
    if group_name not in ('primary','independent'):
        return 'unknown','The exact question identity is needed to select its declared witness context'
    group = case.get(group_name,{})
    if group_name == case.get('_selectedGroup') and named(case.get('_selectedRecordId')):
        group = {**group,'selectedRecordId':case['_selectedRecordId']}
    matched,reason,record = match_profile(case,profile,group)
    if group_name == 'independent' and record and not independent_record(record,case):
        return 'unknown','The independent observation needs an identity and origin separate from every primary record'
    if stage == 'detect':
        if kind and record and record.get('evidenceFacet') != case.get('focus'):
            return 'unknown','The selected observation is not bound to this evidence facet'
        return matched,reason
    if matched != 'yes':
        return 'unknown','Resumption needs an independently matched profile event record'
    selected = safe_record(record,profile)
    if kind and selected.get('evidenceFacet') != case.get('focus'):
        return 'unknown','The selected observation is not bound to this evidence facet'
    valid = validate_record(selected,case,profile)
    if stage == 'validate':
        if kind in (None,'provenance'):
            return valid
        if valid[0] != 'yes':
            return 'unknown','Comparator and corroboration need accepted profile event provenance'
        if kind == 'baseline':
            a = case.get('analysis',{}).get('baseline',{})
            return profile_equality_answer(selected,a.get('criterion')) if assessed_context(a,case) and named(a.get('comparatorId')) else (
                'unknown','Comparator applicability and evidence must retain the exact profile context')
        if kind == 'corroboration':
            group = case.get('independent',{})
            if group.get('accessible') is not True or group.get('searched') is not True:
                return 'unknown','Independent examination is incomplete'
            assessment = case.get('analysis',{}).get('corroboration',{})
            if (not assessed_context(assessment,case) or assessment.get('sourceRecordId') != selected.get('id')
                    or not named(assessment.get('sourceFact')) or not named(assessment.get('targetFact'))
                    or not (named(assessment.get('identifierNamespace')) or references(assessment.get('mappingEvidenceRefs')))):
                return 'unknown','Corroboration needs its exact profile context, source record, declared fact fields, namespace or mapping, method and evidence basis'
            candidates = []
            for r in group.get('records',[]):
                matched,_,_ = match_profile(case,profile,{'accessible':True,'searched':True,'records':[r]})
                if (matched == 'yes' and validate_record(r,case,profile)[0]=='yes'
                        and independent_record(r,case) and r.get('origin') != selected.get('origin')
                        and r.get('id') != selected.get('id')
                        and (not kind or r.get('evidenceFacet') == card['sourceFacet'])):
                    candidates.append(r)
            values = [fact(safe_record(r,profile),assessment['targetFact']) for r in candidates]
            own = fact(selected,assessment['sourceFact'])
            if not values or own is None or any(v is None or type(v) is not type(own) for v in values):
                return 'unknown','Separate accepted origins need an assessed event discriminator'
            agree = [v==own for v in values]
            if any(agree) and not all(agree):
                return 'unknown','Accepted independent observations conflict'
            return ('yes','Separate accepted origins agree on the event discriminator') if all(agree) else ('no','Separate accepted origins contradict corroboration')
    if valid[0] != 'yes':
        return 'unknown','A validated profile event is a prerequisite'
    hypothesis = case.get('analysis',{}).get('hypothesis')
    if hypothesis is not None and (not exact_context(hypothesis,case)
            or not named(hypothesis.get('hypothesisId')) or not named(hypothesis.get('statement'))):
        return 'unknown','A supplied hypothesis must retain its explicit event profile/version and bounds'
    if stage == 'classify':
        if hypothesis is None:
            return 'unknown','Classification needs an explicit falsifiable hypothesis and alternatives'
        if not criterion_basis_ready(selected,hypothesis.get('criterion')):
            return 'unknown','The hypothesis criterion needs its explicitly required evidence dependency and cited fact basis'
        return downstream_answer('classification',case,selected,assessment_criteria(criteria,case,profile))
    if stage == 'scope':
        scoped = scope_answer(case,selected,catalog)
        if scoped[0] != 'yes' or kind in (None,'scope-bound'):
            return scoped
        if kind == 'additional-entities':
            extra = [e for e in case['analysis']['scope']['entities'] if e['disposition']=='included' and
                (e['domain'],e['eventProfile'],e['subjects']) != (case['domain'],case['eventProfile'],case['bindings'])]
            return ('yes','Additional complete profile identities have evidenced inclusions') if extra else ('no','No additional entity is included; source scope remains valid')
        return relation_answer(case,selected,catalog,'dependency','dependencies')
    if stage == 'correlate':
        return relation_answer(case,selected,catalog,kind=kind or 'identifier-relation')
    if stage == 'attribute' and kind == 'behavior-pattern':
        a = case.get('analysis',{}).get('pattern',{})
        if (not assessed_context(a,case) or a.get('claimKind') != 'technical-behavior-pattern'
                or not named(a.get('patternId')) or not references(a.get('alternatives'))
                or a.get('criterion',{}).get('equals') != a['patternId']):
            return 'unknown','A profile-bound technical pattern discriminator and alternatives are required'
        return profile_equality_answer(selected,a.get('criterion'))
    if stage == 'impact' and kind == 'additional-impact':
        return relation_answer(case,selected,catalog,'additionalEffect','additional-impact')
    role = 'attribution' if stage=='attribute' else 'impact'
    if not assessed_context(case.get('analysis',{}).get(role,{}),case):
        return 'unknown','The assessment must retain the exact profile context and basis'
    if role == 'attribution' and not criterion_basis_ready(selected,case['analysis'][role].get('criterion')):
        return 'unknown','The source criterion needs its explicitly required evidence dependency and cited fact basis'
    return downstream_answer(role,case,selected,assessment_criteria(criteria,case,profile))


def evaluate_route(graph,criteria,catalog,case):
    """Traverse existing edges while retaining explicit qualified question identities."""
    profile = profile_for(catalog,case.get('domain'),case.get('eventProfile'))
    if not profile:
        raise ValueError('Unknown domain/event profile')
    current = case.get('entry',criteria['domains'][case['domain']]['entry'])
    from investigative_routing import continuation_edges
    edges = {(e['source'],e['decision']):e['target'] for e in continuation_edges(graph)}
    cards = criteria['nodes']
    trace,seen = [],set()
    supplied = deepcopy(case)
    supplied.pop('_selectedGroup',None)
    supplied.pop('_selectedRecordId',None)
    for _ in range(len(cards)):
        if current in seen or current not in cards or cards[current]['domain'] != case['domain']:
            raise ValueError('Profile route cycled or crossed its domain boundary')
        seen.add(current)
        supplied['retainedTrace'] = trace
        outcome,reason = answer_profile(cards[current],supplied,criteria,catalog)
        trace.append({'nodeId':current,'questionId':definition_id(case['eventProfile'],current),
            'focus':supplied.get('focus'),'answer':outcome,'reason':reason})
        stage = cards[current].get('stage',ROLE_STAGE.get(cards[current]['role']))
        if stage == 'terminal':
            return {'caseId':case['id'],'eventProfile':case['eventProfile'],'profileVersion':VERSION,'trace':trace}
        if outcome == 'yes':
            selected_group = record_group(cards[current],supplied,criteria)
            _,_,record = match_profile(supplied,profile,supplied.get(selected_group,{}))
            if record:
                supplied['_selectedGroup'] = selected_group
                supplied['_selectedRecordId'] = record['id']
        current = edges[(current,outcome)]
    raise ValueError('Profile route did not terminate')


def expand_scenarios(suite):
    """Expand bounded, explicit evidence edits; never execute case content."""
    cases=[]
    for item in suite['cases']:
        case=deepcopy(suite['fixtures'][item['evidenceRef']])
        for edit in item['evidenceEdits']:
            path=edit['path']
            if (not isinstance(path,list) or not 1<=len(path)<=20
                    or any(type(p) not in (str,int) or p in ('__proto__','constructor','prototype') for p in path)
                    or edit['op'] not in ('set','remove')):
                raise ValueError('Invalid public profile evidence edit')
            parent=case
            for part in path[:-1]:parent=parent[part]
            if edit['op']=='set':parent[path[-1]]=deepcopy(edit['value'])
            else:del parent[path[-1]]
        case['id']=item['id']
        case['expectedTrace']=deepcopy(item['expectedTrace'])
        cases.append(case)
    return cases
