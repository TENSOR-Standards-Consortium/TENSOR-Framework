"""Explicit public event-profile interpretations of the unchanged working graph.

Profile-qualified questions are distinct definitions, never silent replacements
for the base questions. Supplied assessed observations are not verified truth.
"""
from copy import deepcopy
import math
import json
from pathlib import Path

from evaluate_entry_scenarios import (context_ready, fact, named, references,
    validation_answer, bound_assessment, equality_answer, downstream_answer, instant, exclusion_answer)

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0-draft.1'
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
    'scope':'Does the hypothesis for {event} retain evidenced inclusions, exclusions and unknowns in the exact profile, subjects and interval?',
    'correlation':'Do separately validated observations of {event} and the named target share the declared assessed identifier?',
    'attribution':'Does the assessed discriminator for {event} support the named technical source, with alternatives retained?',
    'impact':'Does {event} show the named observed technical metric change against a comparable bounded baseline?',
    'exclusion':'Does the explicit logging and search coverage basis exclude {event} within every declared subject and the entire interval?',
    'unresolved':'Were the unresolved or rejected prerequisites for {event} retained separately with their evidence and limitations?',
    'refuted':'Was the contradicted technical hypothesis for {event} retained without refuting the event or proving alternatives?',
    'assessed':'Were the supported hypothesis and scope for {event}, with separate relation, source and effect answers and limitations, retained without closing the investigation?',
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
            if card['role'] == 'restored' and card.get('stage') == 'terminal':
                prompt = f"Were the bounded assessments of {profile['proposition']} and open evidence-focus questions retained separately with references and limitations, without investigation closure?"
            rows[node['id']] = {'id':definition_id(pid,node['id']), 'graphNodeId':node['id'],
                'profileId':pid, 'profileVersion':VERSION, 'predicate':prompt,
                'boundSubjectFields':profile['bindings'], 'rule':card['rule'],
                'requiredInterpretationDependency':f'urn:tensor:event-profile:{pid}:{VERSION}'}
        result[pid] = rows
    return result


def event_domain(profile):
    return {'bindings':profile['bindings']}


def exact_context(value, case):
    return (isinstance(value,dict) and value.get('eventProfile') == case.get('eventProfile')
            and value.get('profileVersion') == VERSION and value.get('subjects') == case.get('bindings')
            and value.get('interval') == case.get('interval'))


def assessed_context(value, case):
    hid = case.get('analysis',{}).get('hypothesis',{}).get('hypothesisId')
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
        if not all(record.get('subjects',{}).get(f) == case['bindings'][f] for f in profile['bindings']):
            continue
        when = instant(record.get('eventTime'))
        if not when:
            unresolved = True
            continue
        uncertainty = record.get('clockUncertaintySeconds')
        if type(uncertainty) not in (int,float) or not math.isfinite(uncertainty) or uncertainty < 0:
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
    result = validation_answer(record,case)
    if result[0] != 'yes':
        return result
    if not named(record.get('id')) or not named(record.get('assessmentMethod')):
        return 'unknown','The selected profile observation needs an identity and cited assessment method'
    for field in profile['requiredFacts']:
        if fact(record,field) is None:
            return 'unknown',f'The profile requires an assessed {field} with method and references'
    if profile.get('observationMode') == 'historical-lineage':
        if fact(record,'lineage.parentRevisionId') == case['bindings']['revisionId']:
            return 'unknown','A revision cannot establish its own historical parent'
    return result


def safe_record(record, profile):
    value = deepcopy(record)
    if profile.get('contentAvailabilityFact') and fact(record,profile['contentAvailabilityFact']) != 'available':
        value['facts'] = {k:v for k,v in value.get('facts',{}).items() if not k.startswith(('content.', 'payload.')) or k == profile['contentAvailabilityFact']}
    return value


def target_record(assessment, case, selected, catalog):
    profile = profile_for(catalog,assessment.get('targetDomain'),assessment.get('targetEventProfile'))
    if not profile or assessment.get('targetProfileVersion') != VERSION or assessment.get('sourceRecordId') != selected.get('id'):
        return None,None,None
    target = assessment.get('targetRecord')
    target_case = {'domain':assessment['targetDomain'],'eventProfile':assessment['targetEventProfile'],
        'profileVersion':VERSION,'bindings':assessment.get('targetSubjects',{}),'interval':case['interval']}
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
                any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in [tolerance,*clocks])):
            return 'unknown','A bounded coincidence method and finite nonnegative clock uncertainties are required'
        start,end = (instant(case['interval'][k]) for k in ('start','end'))
        for record,uncertainty in zip((selected,target),clocks):
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
        dispositions = [e['disposition'] for e in case['analysis']['scope']['entities'] if
            e['domain'] == tc['domain'] and e['eventProfile'] == tc['eventProfile'] and e['subjects'] == tc['bindings']]
        if 'excluded' in dispositions:
            return 'no','The additional effect subject is explicitly excluded'
        if 'included' not in dispositions:
            return 'unknown','The additional effect subject needs an evidenced scope inclusion'
        metric_case = deepcopy(tc)
        metric_case['analysis'] = deepcopy(a.get('targetAnalysis',{}))
        metric = metric_case['analysis'].get('impact',{})
        hypothesis = metric_case['analysis'].get('hypothesis',{})
        if (not assessed_context(metric,metric_case) or not exact_context(hypothesis,metric_case)):
            return 'unknown','The additional subject needs its own profile-bound hypothesis and metric assessment'
        return downstream_answer('impact',metric_case,target,{'domains':{}})
    return 'yes','Validated endpoints share the assessed identifier; this does not establish causation'


def terminal_answer(card, case, criteria, catalog):
    ledger = case.get('retention',{})
    if (not exact_context(ledger,case) or ledger.get('graphVersion') != criteria['graphVersion']
            or ledger.get('hypothesis') != case.get('analysis',{}).get('hypothesis')
            or ledger.get('closesInvestigation') is not False):
        return 'unknown','Retain the exact profile/version, graph version, subjects and interval without closure'
    if ledger.get('knownMissing') is True:
        return 'no','A required assessment is known missing from this exact retained context'
    rows = ledger.get('assessments',[])+ledger.get('prerequisiteAssessments',[])
    if not rows:
        return 'unknown','No separate qualified question assessments were retained'
    seen,stages = {},{}
    pid = case['eventProfile']
    for row in rows:
        previous = criteria['nodes'].get(row.get('nodeId'))
        if (not previous or previous['domain'] != case['domain'] or not assessed_context(row,case)
                or row.get('questionId') != definition_id(pid,row['nodeId'])
                or row.get('answer') not in ('yes','no','unknown') or not named(row.get('rationale'))
                or not references(row.get('limitations'))
                or (previous.get('sourceFacet') and previous['sourceFacet'] not in catalog['profiles'][pid]['facets'])):
            return 'unknown','Every retained row needs its exact qualified question, profile context, method, references and limitations'
        nid = row['nodeId']
        if nid in seen and seen[nid] != row['answer']:
            return 'unknown','Conflicting qualified question answers require an explicit assessment history'
        seen[nid] = row['answer']
        if previous.get('assessmentKind') not in ('additional-entities','dependencies','behavior-pattern','additional-impact'):
            stages.setdefault(previous.get('stage',ROLE_STAGE.get(previous['role'])),[]).append(row['answer'])
    for prior in case.get('retainedTrace',[]):
        if seen.get(prior['nodeId']) != prior['answer']:
            return 'no','The retained record drops or changes a preceding qualified assessment'
    role = card['role']
    if role == 'assessed' and ('yes' not in stages.get('classify',[]) or 'yes' not in stages.get('scope',[])
            or not all(s in stages for s in ('correlate','attribute','impact'))):
        return 'unknown','A handoff needs separate hypothesis, mandatory scope, relation, source and effect answers'
    if role == 'refuted' and 'no' not in stages.get('classify',[]):
        return 'unknown','No retained assessment refutes this exact hypothesis'
    if role == 'unresolved' and not any(r['answer']=='unknown' or (r['answer']=='no' and
            criteria['nodes'][r['nodeId']].get('role') in ('primaryValidation','independentValidation','scope')) for r in rows):
        return 'unknown','An unresolved ending needs an actual retained uncertainty or rejected prerequisite'
    if role == 'restored' and ledger.get('focusDispositions',{}).get(case.get('focus')) not in ('open','assessed'):
        return 'unknown','Retain the terminal focus as assessed or explicitly open'
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
    group_name = 'independent' if card['role'] in ('alternate','independentValidation') else case.get('_selectedGroup','primary')
    group = case.get(group_name,{})
    matched,reason,record = match_profile(case,profile,group)
    if stage == 'detect':
        if card['role']=='alternate' and record and (not named(case.get('primaryOrigin')) or record.get('origin')==case['primaryOrigin']
                or any(record.get('origin')==r.get('origin') for r in case.get('primary',{}).get('records',[]))):
            return 'unknown','The alternate needs a separately declared origin; a copy is not independent'
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
            return equality_answer(selected,a.get('criterion')) if assessed_context(a,case) and named(a.get('comparatorId')) else (
                'unknown','Comparator applicability and evidence must retain the exact profile context')
        if kind == 'corroboration':
            group = case.get('independent',{})
            if group.get('accessible') is not True or group.get('searched') is not True:
                return 'unknown','Independent examination is incomplete'
            candidates = []
            for r in group.get('records',[]):
                matched,_,_ = match_profile(case,profile,{'accessible':True,'searched':True,'records':[r]})
                if matched == 'yes' and validate_record(r,case,profile)[0]=='yes' and r.get('origin') != selected.get('origin') and r.get('id') != selected.get('id'):
                    candidates.append(r)
            values = [fact(r,'event.id') for r in candidates]
            own = fact(selected,'event.id')
            if not values or own is None or any(v is None or type(v) is not type(own) for v in values):
                return 'unknown','Separate accepted origins need an assessed event discriminator'
            agree = [v==own for v in values]
            if any(agree) and not all(agree):
                return 'unknown','Accepted independent observations conflict'
            return ('yes','Separate accepted origins agree on the event discriminator') if all(agree) else ('no','Separate accepted origins contradict corroboration')
    if valid[0] != 'yes':
        return 'unknown','A validated profile event is a prerequisite'
    hypothesis = case.get('analysis',{}).get('hypothesis',{})
    if not exact_context(hypothesis,case):
        return 'unknown','The hypothesis must retain its explicit event profile/version and bounds'
    classified = downstream_answer('classification',case,selected,criteria)
    if stage == 'classify':
        return classified
    if classified[0] != 'yes':
        return 'unknown','A supported bound technical hypothesis is a prerequisite'
    scoped = scope_answer(case,selected,catalog)
    if stage == 'scope':
        if scoped[0] != 'yes' or kind in (None,'scope-bound'):
            return scoped
        if kind == 'additional-entities':
            extra = [e for e in case['analysis']['scope']['entities'] if e['disposition']=='included' and
                (e['domain'],e['eventProfile'],e['subjects']) != (case['domain'],case['eventProfile'],case['bindings'])]
            return ('yes','Additional complete profile identities have evidenced inclusions') if extra else ('no','No additional entity is included; source scope remains valid')
        return relation_answer(case,selected,catalog,'dependency','dependencies')
    if scoped[0] != 'yes':
        return 'unknown','An evidence-backed profile scope is a prerequisite'
    if stage == 'correlate':
        return relation_answer(case,selected,catalog,kind=kind or 'identifier-relation')
    if stage == 'attribute' and kind == 'behavior-pattern':
        a = case.get('analysis',{}).get('pattern',{})
        if (not assessed_context(a,case) or a.get('claimKind') != 'technical-behavior-pattern'
                or not named(a.get('patternId')) or not references(a.get('alternatives'))
                or a.get('criterion',{}).get('equals') != a['patternId']):
            return 'unknown','A profile-bound technical pattern discriminator and alternatives are required'
        return equality_answer(selected,a.get('criterion'))
    if stage == 'impact' and kind == 'additional-impact':
        return relation_answer(case,selected,catalog,'additionalEffect','additional-impact')
    role = 'attribution' if stage=='attribute' else 'impact'
    if not assessed_context(case.get('analysis',{}).get(role,{}),case):
        return 'unknown','The assessment must retain the exact profile context and basis'
    return downstream_answer(role,case,selected,criteria)


def evaluate_route(graph,criteria,catalog,case):
    """Traverse existing edges while retaining explicit qualified question identities."""
    profile = profile_for(catalog,case.get('domain'),case.get('eventProfile'))
    if not profile:
        raise ValueError('Unknown domain/event profile')
    current = case.get('entry',criteria['domains'][case['domain']]['entry'])
    edges = {(e['source'],e['decision']):e['target'] for e in graph['edges']}
    cards = criteria['nodes']
    trace,seen = [],set()
    supplied = deepcopy(case)
    supplied.pop('_selectedGroup',None)
    for _ in range(len(cards)):
        if current in seen or current not in cards or cards[current]['domain'] != case['domain']:
            raise ValueError('Profile route cycled or crossed its domain boundary')
        seen.add(current)
        supplied['retainedTrace'] = trace
        outcome,reason = answer_profile(cards[current],supplied,criteria,catalog)
        trace.append({'nodeId':current,'questionId':definition_id(case['eventProfile'],current),'answer':outcome,'reason':reason})
        stage = cards[current].get('stage',ROLE_STAGE.get(cards[current]['role']))
        if stage == 'terminal':
            return {'caseId':case['id'],'eventProfile':case['eventProfile'],'profileVersion':VERSION,'trace':trace}
        if cards[current]['role'] in ('entry','alternate') and outcome == 'yes':
            supplied['_selectedGroup'] = 'independent' if cards[current]['role']=='alternate' else 'primary'
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
