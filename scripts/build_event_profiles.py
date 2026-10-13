#!/usr/bin/env python3
"""Compile explicit public profile definitions and authored scenario variants.

Expected answers are declared below, not learned from evaluator results.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from event_profiles import ROOT, VERSION, definition_id, definitions, evaluate_route, ROLE_STAGE
from evaluate_entry_scenarios import COVERAGE_FLAGS

DIRECTORY = ROOT/'drafts/core/event-profiles'

def encoded(value):
    return (json.dumps(value,indent=2)+'\n').encode()


def assessed(value,ref):
    return {'value':value,'assessment':'accepted','method':'Compare the separately cited normalized observation','evidenceRefs':[ref]}


def fixture(seed,profile,criteria):
    case = deepcopy(seed)
    case['focus'] = profile['facets'][0]
    hid = 'hypothesis-'+case['eventProfile']
    ref = 'observation-'+case['eventProfile']
    context = {'subjects':deepcopy(case['bindings']),'interval':deepcopy(case['interval']),
        'eventProfile':case['eventProfile'],'profileVersion':VERSION,'hypothesisId':hid,
        'method':'Bounded authored evidence assessment','evidenceRefs':[ref]}
    facts = {'event.kind':profile['eventKind'],'event.id':ref,
        **case['requiredFactValues'],'relation.key':'relation-'+case['eventProfile'],
        'source.entity':case['technicalSource'],'metric.baseline':case['baseline'],'metric.observed':case['observed'],
        'metric.baselineUnit':case['metricUnit'],'metric.observedUnit':case['metricUnit'],
        'metric.baselineId':case['metricId'],'metric.observedId':case['metricId'],
        'metric.baselineTime':'2026-10-12T09:05:00Z','metric.observedTime':'2026-10-12T09:25:00Z'}
    record = {'id':ref,'origin':'origin-primary-'+case['eventProfile'],'eventProfile':case['eventProfile'],
        'profileVersion':VERSION,'subjects':deepcopy(case['bindings']),'eventTime':'2026-10-12T09:20:00Z',
        'clockUncertaintySeconds':1,'evidenceFacet':case['focus'],
        'provenanceAssessment':'accepted','interpretationAssessment':'accepted',
        'assessmentMethod':'Review acquisition manifest and event-kind interpretation',
        'assessmentEvidenceRefs':[ref+'-manifest'],'facts':{k:assessed(v,ref+'-'+k) for k,v in facts.items()}}
    target = deepcopy(record)
    target.update(id=ref+'-independent',origin='origin-independent-'+case['eventProfile'],eventTime='2026-10-12T09:20:01Z')
    criterion = {'fact':case['hypothesisFact'],'equals':case['hypothesisValue'],'method':'Test the single explicit technical discriminator'}
    case.update(primaryOrigin=record['origin'],primary={'accessible':True,'searched':True,'records':[record]},
        independent={'accessible':True,'searched':True,'records':[target]})
    case['analysis'] = {
        'hypothesis':{**deepcopy(context),'statement':case['hypothesisStatement'],'alternatives':['An attempted operation rather than the stated outcome','An observation of a different full subject context'],'criterion':criterion},
        'scope':{**deepcopy(context),'claimsCompletePopulation':False,'entities':[{'domain':case['domain'],
            'eventProfile':case['eventProfile'],'profileVersion':VERSION,'subjects':deepcopy(case['bindings']),
            'disposition':'included','evidenceRefs':[ref]}]},
        'correlation':{**deepcopy(context),'targetDomain':case['domain'],'targetEventProfile':case['eventProfile'],
            'targetProfileVersion':VERSION,'targetSubjects':deepcopy(case['bindings']),'targetRecord':target,
            'sourceRecordId':ref,'relationKind':'shared-identifier','sourceFact':'relation.key','targetFact':'relation.key'},
        'attribution':{**deepcopy(context),'claimKind':'technical-source','sourceEntityId':case['technicalSource'],
            'alternatives':['A relay or copied origin rather than this technical source'],
            'criterion':{'fact':'source.entity','equals':case['technicalSource'],'method':'Compare assessed technical source discriminator'}},
        'impact':{**deepcopy(context),'claimKind':'observed-metric-change','metricId':case['metricId'],'unit':case['metricUnit'],
            **{k:'metric.'+v for k,v in {'baselineFact':'baseline','observedFact':'observed',
                'baselineUnitFact':'baselineUnit','observedUnitFact':'observedUnit','baselineMetricFact':'baselineId',
                'observedMetricFact':'observedId','baselineTimeFact':'baselineTime','observedTimeFact':'observedTime'}.items()}},
    }
    case['coverage'] = {**deepcopy(context),'eventKind':profile['eventKind'],'method':'Review complete applicable event logging and acquisition coverage',
        **{f:True for f in COVERAGE_FLAGS}}
    return case


def retained_row(case,node,answer):
    return {'nodeId':node,'questionId':definition_id(case['eventProfile'],node),'answer':answer,
        'eventProfile':case['eventProfile'],'profileVersion':VERSION,'subjects':deepcopy(case['bindings']),
        'interval':deepcopy(case['interval']),'hypothesisId':case['analysis']['hypothesis']['hypothesisId'],
        'method':'Retain the separate bounded authored assessment','evidenceRefs':['retained-basis-'+node],
        'rationale':'Retain this exact qualified proposition and its answer','limitations':case['limitations']}


def declare_expected(case,criteria,graph,overrides=None):
    overrides = overrides or {}
    from investigative_routing import continuation_edges
    edges = {(e['source'],e['decision']):e['target'] for e in continuation_edges(graph)}
    current = case.get('entry',criteria['domains'][case['domain']]['entry'])
    trace = []
    for _ in range(len(graph['nodes'])):
        card = criteria['nodes'][current]
        role = card['role']
        outcome = overrides.get(current,overrides.get(card['rule'],overrides.get(role,'yes')))
        trace.append([current,outcome])
        if card.get('stage',ROLE_STAGE.get(role)) == 'terminal':break
        current = edges[current,outcome]
    else:raise ValueError('Declared scenario route failed to terminate')
    case['expectedTrace'] = trace
    case['retention'] = {'eventProfile':case['eventProfile'],'profileVersion':VERSION,'graphVersion':graph['version'],
        'subjects':deepcopy(case['bindings']),'interval':deepcopy(case['interval']),'closesInvestigation':False,
        'hypothesis':deepcopy(case['analysis']['hypothesis']),
        'focusDispositions':{case['focus']:'assessed'},'assessments':[retained_row(case,n,a) for n,a in trace[:-1]]}
    return case


def build():
    graph_raw = (ROOT/'drafts/core/tensor.core.graph.json').read_bytes()
    criteria_raw = (ROOT/'drafts/core/entry-evidence-criteria.json').read_bytes()
    graph,criteria = json.loads(graph_raw),json.loads(criteria_raw)
    catalog = json.loads((DIRECTORY/'catalog.source.json').read_text())
    catalog.update(graphVersion=graph['version'],graphSha256=sha256(graph_raw).hexdigest(),criteriaSha256=sha256(criteria_raw).hexdigest(),
        baselineCommit='78a275b127d2f24933c3ec16d9a2b0b1c38fb0af')
    seeds = json.loads((DIRECTORY/'scenarios.source.json').read_text())['cases']
    cases = []
    for seed in seeds:
        p = catalog['profiles'][seed['eventProfile']]
        base = fixture(seed,p,criteria)
        cases.append(declare_expected(deepcopy(base),criteria,graph))
        refuted = deepcopy(base)
        refuted['id'] = seed['eventProfile']+'-refuted'
        refuted['primary']['records'][0]['facts'][seed['hypothesisFact']]['value'] = 'contradicting-observation'
        cases.append(declare_expected(refuted,criteria,graph,{'classification':'no'}))
        unknown = deepcopy(base)
        unknown['id'] = seed['eventProfile']+'-unresolved'
        unknown['analysis']['hypothesis']['alternatives'] = []
        cases.append(declare_expected(unknown,criteria,graph,{'classification':'unknown'}))
        unavailable = deepcopy(base)
        unavailable['id'] = seed['eventProfile']+'-unavailable'
        unavailable['primary']['accessible'] = unavailable['independent']['accessible'] = False
        cases.append(declare_expected(unavailable,criteria,graph,{'entry':'unknown','alternate':'unknown'}))
        absence = deepcopy(base)
        absence['id'] = seed['eventProfile']+'-covered-absence'
        absence['primary']['records'] = absence['independent']['records'] = []
        cases.append(declare_expected(absence,criteria,graph,{'entry':'no','alternate':'no'}))
        gap = deepcopy(absence)
        gap['id'] = seed['eventProfile']+'-coverage-gap'
        gap['coverage']['continuousCollection'] = False
        cases.append(declare_expected(gap,criteria,graph,{'entry':'no','alternate':'no','exclusion':'no'}))
        alternate = deepcopy(base)
        alternate['id'] = seed['eventProfile']+'-independent-fallback'
        alternate['primary']['accessible'] = False
        alternate['primary']['records'] = []
        alternate['analysis']['scope']['evidenceRefs'] = [alternate['independent']['records'][0]['id']]
        relation = alternate['analysis']['correlation']
        relation['sourceRecordId'] = alternate['independent']['records'][0]['id']
        relation['targetRecord'] = deepcopy(base['primary']['records'][0])
        cases.append(declare_expected(alternate,criteria,graph,{'entry':'unknown'}))
        unchanged = deepcopy(base)
        unchanged['id'] = seed['eventProfile']+'-unchanged-metric'
        unchanged['primary']['records'][0]['facts']['metric.observed']['value'] = seed['baseline']
        cases.append(declare_expected(unchanged,criteria,graph,{'impact':'no'}))
        metric_unknown = deepcopy(base)
        metric_unknown['id'] = seed['eventProfile']+'-incomparable-metric'
        metric_unknown['primary']['records'][0]['facts']['metric.observedUnit']['value'] = 'incompatible-unit'
        cases.append(declare_expected(metric_unknown,criteria,graph,{'impact':'unknown'}))
    defs = {'format':'tensor-event-profile-question-definitions','version':VERSION,
        'graphSha256':catalog['graphSha256'],'profiles':definitions(graph,criteria,catalog)}
    scenarios = {'format':'tensor-event-profile-scenarios','version':VERSION,'graphVersion':graph['version'],
        'graphSha256':catalog['graphSha256'],'cases':cases}
    return graph,criteria,catalog,defs,scenarios



def evidence_edits(base,value,path=()):
    if type(base) is not type(value):return [{'op':'set','path':list(path),'value':deepcopy(value)}]
    if isinstance(base,dict):
        edits=[]
        for key in sorted(base.keys()-value.keys()):edits.append({'op':'remove','path':list(path)+( [key] )})
        for key in sorted(value):
            if key not in base:edits.append({'op':'set','path':list(path)+[key],'value':deepcopy(value[key])})
            else:edits.extend(evidence_edits(base[key],value[key],(*path,key)))
        return edits
    if isinstance(base,list) and len(base)==len(value):
        return [edit for i,(left,right) in enumerate(zip(base,value)) for edit in evidence_edits(left,right,(*path,i))]
    return [] if base==value else [{'op':'set','path':list(path),'value':deepcopy(value)}]


def compact_scenarios(suite):
    fixtures={case['eventProfile']:deepcopy(case) for case in suite['cases'] if case['id'].endswith('-supported')}
    fixtures=json.loads(json.dumps(fixtures))  # JSON has no shared object identity.
    rows=[]
    for case in suite['cases']:
        base=deepcopy(fixtures[case['eventProfile']]);value=deepcopy(case)
        for field in ('id','expectedTrace'):base.pop(field);value.pop(field)
        rows.append({'id':case['id'],'eventProfile':case['eventProfile'],'evidenceRef':case['eventProfile'],
            'expectedTrace':case['expectedTrace'],'evidenceEdits':evidence_edits(base,value)})
    return {**suite,'encoding':'shared-fixtures-and-explicit-edits/1','fixtures':fixtures,'cases':rows}


def main():
    graph,criteria,catalog,defs,scenarios = build()
    failures=[]
    results=[]
    for case in scenarios['cases']:
        result=evaluate_route(graph,criteria,catalog,case)
        actual=[[r['nodeId'],r['answer']] for r in result['trace']]
        result['passed'] = actual == case['expectedTrace']
        results.append(result)
        if actual != case['expectedTrace']:failures.append({'caseId':case['id'],'expected':case['expectedTrace'],'actual':result['trace']})
    if failures:
        print(json.dumps(failures[:3],indent=2))
        raise SystemExit(f'{len(failures)} profile scenarios failed')
    inputs=['scripts/event_profiles.py','scripts/build_event_profiles.py','drafts/core/event-profiles/catalog.source.json',
        'drafts/core/event-profiles/scenarios.source.json','drafts/core/tensor.core.graph.json','drafts/core/entry-evidence-criteria.json',
        'scripts/evaluate_event_profiles.py','scripts/evaluate_entry_scenarios.py','tests/legacy/test_event_profiles.py']
    catalog['inputPins']={p:sha256((ROOT/p).read_bytes()).hexdigest() for p in inputs}
    packed=compact_scenarios(scenarios)
    from event_profiles import expand_scenarios
    if expand_scenarios(packed)!=scenarios['cases']:raise SystemExit('Scenario compaction changed evidence')
    outputs={'catalog.json':catalog,'definitions.json':defs,'scenarios.json':packed}
    previous = json.loads((ROOT/'drafts/core/reviews/2026-10-12-independent-review/review.json').read_text())
    outputs['validation.json']={'format':'tensor-public-event-profile-validation','version':VERSION,
        'reviewKind':'author-side-scenario-and-counterexample-review','independentInstitutionalApproval':False,
        'baseGraphUnchanged':True,'graphSha256':catalog['graphSha256'],'profiles':len(catalog['profiles']),
        'scenarioCount':len(results),'passed':sum(r['passed'] for r in results),
        'artifactPins':{name:sha256(encoded(value)).hexdigest() for name,value in outputs.items()},
        'preservedArtifacts':previous['preservedArtifacts'],'results':results}
    for name,value in outputs.items():
        data=encoded(value)
        path=DIRECTORY/name
        if '--check' in sys.argv:
            if not path.exists() or path.read_bytes()!=data:raise SystemExit(f'Stale profile artifact: {name}')
        else:path.write_bytes(data)
    print(f'{len(catalog["profiles"])} public event profiles, {len(scenarios["cases"])} authored scenario variants passed; base graph and schema unchanged')

if __name__=='__main__':main()
