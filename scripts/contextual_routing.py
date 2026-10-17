"""Answer-specific working routes and explicit, separately evidenced discovery.

The October 13 review remains a historical receipt. This is an author repair,
not a second independent or institutional sign-off. No Core schema is changed.
"""
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'drafts/core/reviews/2026-10-16-contextual-routing'
VERSION = '0.20261016a'
PROFILE = 'tensor-contextual-routing/1'


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + '\n').encode()


def baseline(name):
    return json.loads((REVIEW / 'baseline' / name).read_text())


def shared_pairs(graph):
    grouped = defaultdict(list)
    for edge in graph['edges']:
        grouped[edge['source'], edge['target']].append(edge)
    return {pair: edges for pair, edges in grouped.items() if len(edges) > 1}


def eligible_discoveries(graph, source, answer, context):
    """Offline new-lead readiness; identities returned here are not transitions.

    Source history is checked, never copied into the target. A separately cited
    discovery may change subjects, interval or profile within the same domain.
    """
    from evaluate_entry_scenarios import named, references
    from semantic_graph_review import interval_ready
    from event_profiles import VERSION as profile_version, definition_id
    if not isinstance(context,dict) or answer not in ('yes','no','unknown'):return []
    criteria=json.loads((ROOT/'drafts/core/entry-evidence-criteria.json').read_text())
    catalog=json.loads((ROOT/'drafts/core/event-profiles/catalog.source.json').read_text())['profiles']
    card=criteria['nodes'].get(source)
    original=context.get('_source',{})
    if (not card or not isinstance(original,dict) or original.get('nodeId')!=source or
        original.get('answer')!=answer or original.get('graphVersion')!=graph['version'] or
        original.get('domain')!=card['domain'] or not references(original.get('evidenceRefs')) or
        not named(original.get('rationale')) or not isinstance(original.get('bindings'),dict)):return []
    def profile_for(value,card):
        pid=value.get('eventProfile')
        if pid is None:
            return (None,card['boundSubjectFields'],card['nodeId']) if value.get('profileVersion') is None else None
        profile=catalog.get(pid)
        if (not profile or profile['domain']!=card['domain'] or value.get('profileVersion')!=profile_version or
            (card['role']=='restored' and card.get('stage')!='terminal' and card['sourceFacet'] not in profile['facets'])):return None
        return pid,profile['bindings'],definition_id(pid,card['nodeId'])
    source_profile=profile_for(original,card)
    if not source_profile or original.get('questionId')!=source_profile[2]:return []
    missing=[field for field in source_profile[1] if not named(original['bindings'].get(field))]
    if not interval_ready(original.get('interval')):missing.append('interval')
    declared=original.get('missingContextFields',[])
    if (not isinstance(declared,list) or not all(named(v) for v in declared) or
        len(declared)!=len(set(declared)) or set(declared)!=set(missing) or (missing and answer!='unknown')):return []
    options=next((n.get('extensions',{}).get('tensor:discoveryOptions',[]) for n in graph['nodes'] if n['id']==source),[])
    result=[]
    for option in options:
        target=context.get(option['target'])
        target_card=criteria['nodes'][option['target']]
        if not isinstance(target,dict):continue
        target_profile=profile_for(target,target_card)
        if (not target_profile or target.get('graphVersion')!=graph['version'] or
            target.get('questionId')!=target_profile[2] or target.get('domain')!=target_card['domain'] or
            not isinstance(target.get('bindings'),dict) or not interval_ready(target.get('interval')) or
            not all(named(target['bindings'].get(f)) for f in target_profile[1])):continue
        own_context=(target.get('bindings')!=original.get('bindings') or target.get('interval')!=original.get('interval') or
                     target_profile[0]!=source_profile[0] or card['domain']!=target_card['domain'])
        discovery=references(target.get('discoveryEvidenceRefs')) and named(target.get('discoveryRationale'))
        assessment=references(target.get('evidenceRefs')) and named(target.get('method'))
        if discovery or (not own_context and assessment):result.append(option['id'])
    return result


def repair(graph, criteria, suite):
    graph, criteria, suite = deepcopy(graph), deepcopy(criteria), deepcopy(suite)
    before = deepcopy(graph)
    cards = criteria['nodes']
    edges, discovery = [], {}
    for old in graph['edges']:
        edge = deepcopy(old)
        source, target = cards[edge['source']], cards[edge['target']]
        roles = criteria['domains'][source['domain']]
        lead = edge.get('extensions', {}).get('tensor:investigativeLead')
        # Independent discoveries are not logical consequences of every answer.
        # Publish one new-lead option, with its own context, rather than three
        # answer arrows. Positive, evidence-motivated pivots remain real routes.
        if lead and (lead['kind'] == 'cross-domain-lead' or lead['kind'] == 'independent-assessment'):
            key = (edge['source'], edge['target'])
            discovery[key] = {'id': f"{key[0]}-discover-{key[1]}", 'source': key[0], 'target': key[1],
                'sourceDomain': source['domain'], 'targetDomain': target['domain'],
                'basis': lead['basis'], 'origin': 'newLead', 'answerGuard': None,
                'requirements': ['Exact target question and graph/profile version', 'Full target subjects and interval',
                    'Separately cited discovery evidence and rationale', 'Retained source assessment and context'],
                'meaning': 'A separate discovery can open this question after any source answer. It is not an answer route, finding, permission, or automatic selection.'}
            if edge['decision'] != 'yes':
                continue
        if not lead:
            kind, role, outcome = source.get('assessmentKind'), source['role'], edge['decision']
            if role == 'restored' and outcome != 'yes':
                if outcome == 'unknown':
                    edge['target'] = roles['unresolved']
                elif kind == 'hypothesis':
                    edge['target'] = roles['refuted']
                elif kind in ('provenance', 'corroboration', 'scope-bound'):
                    edge['target'] = roles['unresolved']
                elif kind not in ('baseline', 'metric-change', 'additional-impact'):
                    edge['target'] = roles['assessed']
            elif role in ('correlation', 'attribution') and outcome != 'yes':
                edge['target'] = roles['assessed'] if outcome == 'no' else roles['unresolved']
            elif role == 'impact' and outcome == 'unknown':
                edge['target'] = roles['unresolved']
            if edge['target'] != old['target'] and target.get('stage') != 'terminal' and target['role'] not in ('assessed','unresolved','refuted','exclusion'):
                discovery.setdefault((old['source'],old['target']),{
                    'id':f"{old['source']}-discover-{old['target']}",'source':old['source'],'target':old['target'],
                    'sourceDomain':source['domain'],'targetDomain':target['domain'],'origin':'newLead','answerGuard':None,
                    'basis':'Independent evidence can support the separate target question while this source remains negative or unknown. Retain the source result and recheck the target context and criterion.',
                    'requirements':['Exact target question and graph/profile version','Full target subjects and interval',
                        'Separately cited assessment evidence and method','Retained source assessment and context'],
                    'meaning':'An independently evidenced new lead, not a source-answer implication or automatic selection.'})
            edge['id'] = f"{edge['source']}-{outcome}-{edge['target']}"
            target = cards[edge['target']]
            # An adapter is needed only for a continuation into a generic
            # nonterminal question. Terminal retention preserves the input focus.
            if target.get('stage') == 'terminal' or target['role'] in ('assessed','unresolved','refuted','exclusion'):
                edge.setdefault('extensions', {}).pop('tensor:contextAdapter', None)
            edge.setdefault('extensions', {})['tensor:routeBasis'] = rationale(source, target, outcome)
        target = cards[edge['target']]
        edge.setdefault('extensions', {})['tensor:routeContext'] = {
            'profile': PROFILE, 'preserve': ['definitionIdentity','questionIdentity','subjectBindings','timeContext',
                'parameterBindings','eventProfile','evidenceReferences','assessmentHistory','originDecision'],
            'targetInstance': 'fresh', 'targetAssessment': 'independent',
            'sameDomain': source['domain'] == target['domain'], 'targetContext':'bind-explicitly',
            'meaning': rationale(source, target, edge['decision']),
        }
        edges.append(edge)
    # Multiple routes per answer are explicit list entries, never a source/answer dictionary.
    if len({e['id'] for e in edges}) != len(edges):
        raise ValueError('Repair produced duplicate route identities')
    graph['edges'] = edges
    graph['version'] = VERSION
    graph['generatedAt'] = '2026-10-16T00:00:00Z'
    graph['extensions']['tensor:contextualRouting'] = PROFILE
    for node in graph['nodes']:
        options = [option for (source,_),option in discovery.items() if source == node['id']]
        if options:
            node['extensions']['tensor:discoveryOptions'] = options
    incoming = {edge['target'] for edge in edges}
    # A retained-record question can be resumed with its own supplied record;
    # no fabricated transition is added to satisfy a connectivity count.
    graph['entryNodeIds'] = sorted(set(graph['entryNodeIds']) | {n['id'] for n in graph['nodes'] if n['id'] not in incoming}, key=lambda value:int(value[1:]))
    for node in graph['nodes']:
        node['extensions']['tensor:evidenceCriteria']['version'] = VERSION
    from core_graph_pipeline import build_graph_payload
    graph = build_graph_payload(VERSION,graph['nodes'],graph['edges'],graph['entryNodeIds'],graph['schemaVersion'])
    criteria['graphVersion'] = VERSION
    criteria['graphSha256'] = sha256(encoded(graph)).hexdigest()
    criteria['contextualRouting'] = {'id': PROFILE, 'document': 'reviews/2026-10-16-contextual-routing/README.md',
        'scope': 'Author answer-route repairs and all shared-destination dispositions; independent external review pending.'}
    def repin(value):
        if isinstance(value,dict):
            return {key:VERSION if key=='graphVersion' else repin(item) for key,item in value.items()}
        if isinstance(value,list):return [repin(item) for item in value]
        return value
    suite = repin(suite)
    # Re-author the finite fixture plans from their explicit assessment answers.
    # No answer is learned from the evaluator. The independent challenges below
    # also assert concrete target roles, not this generated plan.
    continuation = {(e['source'],e['decision']):e['target'] for e in edges if 'tensor:investigativeLead' not in e.get('extensions',{})}
    def trace_plan(old_trace):
        answers = dict(old_trace)
        current = old_trace[0][0]
        trace = []
        while True:
            if current in {n for n,_ in trace}: raise ValueError('A linear fixture requires an explicit return-instance plan')
            answer = answers.get(current,'yes')
            trace.append([current,answer])
            card = cards[current]
            if card.get('stage') == 'terminal' or card['role'] in ('assessed','unresolved','refuted','exclusion'):break
            current = continuation[current,answer]
        return trace
    for case in suite['cases']:
        case['expectedTrace'] = trace_plan(case['expectedTrace'])
        trace = case['expectedTrace'];role = cards[trace[-1][0]]['role']
        case['expectedState'] = 'unresolved' if role=='unresolved' or trace[-1][1]!='yes' else {
            'exclusion':'bounded-exclusion','refuted':'hypothesis-refuted'}.get(role,
                'bounded-findings' if all(a=='yes' for n,a in trace if cards[n]['role'] in ('classification','scope','correlation','attribution','impact')) else 'partial-findings')
    from restored_evidence import case_evidence
    for case in suite['restoredPaths']:
        old_trace = case['expectedTrace']
        new_trace = trace_plan(old_trace)
        old_terminal = case_evidence(suite,case['evidenceByNode'][old_trace[-1][0]])
        terminal = new_trace[-1][0]
        retained = old_terminal['retention']
        retained['assessments'] = [row for row in retained['assessments'] if [row['nodeId'],row['answer']] in new_trace[:-1]]
        key = 'contextual-route:'+case['id']
        suite['restoredFixtures'][key] = old_terminal
        case['evidenceByNode'][terminal] = {'evidenceRef':key}
        case['expectedTrace'] = new_trace
    ledger = []
    current = {e['id']: e for e in edges}
    for (source, target), originals in shared_pairs(before).items():
        replacements = []
        for old in originals:
            matches = [e for e in edges if e['source'] == source and e['decision'] == old['decision'] and
                       (e['id'] == old['id'] or ('tensor:investigativeLead' not in old.get('extensions', {}) and
                        'tensor:investigativeLead' not in e.get('extensions', {})))]
            replacements.append({'oldRoute': old['id'], 'answer': old['decision'],
                'currentRoutes': [e['id'] for e in matches],
                'disposition': 'retained' if old['id'] in current else 'separate-discovery' if (source,target) in discovery else 'rerouted',
                'rationale': rationale(cards[source], cards[matches[0]['target']], old['decision']) if matches else
                    'Independent discovery is available with separately supplied target context and cited discovery material. It is not a consequence of this source answer.'})
        ledger.append({'source':source, 'target':target, 'domain':cards[source]['domain'],
            'sourcePredicate':cards[source]['predicate'], 'targetPredicate':cards[target]['predicate'], 'outcomes':replacements})
    review = {'format':'tensor-shared-destination-review','version':1,'status':'author-repaired-external-review-pending',
        'institutionalApproval':False, 'graphVersion':VERSION,'graphSha256':criteria['graphSha256'],
        'baselineGraphSha256':sha256(encoded(before)).hexdigest(), 'reviewedSharedPairs':ledger,
        'currentSharedPairs':[{'source':s,'target':t,'answers':[e['decision'] for e in es],
            'rationales':{e['decision']:rationale(cards[s],cards[t],e['decision']) for e in es}}
            for (s,t),es in shared_pairs(graph).items()],
        'counts':{'questions':len(graph['nodes']),'routes':len(edges),'reviewedSharedDestinations':len(ledger),
                  'remainingSharedDestinations':len(shared_pairs(graph)), 'discoveryOptions':len(discovery)},
        'scope':'Every previously shared destination has an explicit answer-by-answer disposition. Context-preserving convergence is retained for independent search, bounded gap retention, baseline comparisons and measured-result retention. No new independent sign-off is claimed.'}
    return graph, criteria, suite, review


def rationale(source, target, answer):
    kind, role = source.get('assessmentKind'), target['role']
    subject = source.get('sourceFacet') or source['predicate']
    if role == 'unresolved':
        return f"Retain the {answer} assessment of {subject}, the exact missing or rejected basis and its bounds. Preserve established facts; no event absence, refutation, source attribution or closure is inferred."
    if role == 'refuted':
        return f"Retain only the explicitly contradicted technical hypothesis for {subject}; the observed event and other hypotheses remain separate."
    if role == 'assessed' or target.get('assessmentKind') == 'retention':
        return f"Retain the {answer} result for {subject}, its evidence, full context and open questions. No target finding or case closure is inherited; other leads remain open."
    if kind == 'baseline' and answer == 'no':
        return f"The declared baseline comparison for {subject} did not match. The separate technical hypothesis can still be tested on its own evidence, with this negative comparator result retained."
    if source['role'] == 'entry' and answer in ('no','unknown'):
        return f"Search separately originating material for the same exact proposition after a {answer} primary search. The missing-record result is not event absence; preserve the different search limitations."
    return f"After the {answer} assessment of {subject}, explicitly assess the separate target proposition ({target['predicate']}) on its own complete context and evidence. Retain the source answer unchanged; adjacency supplies no finding."


def assess(graph, graph_sha, criteria, suite):
    from graph_assurance_policy import EVIDENCE_IDS, gate
    from restored_evidence import answer, case_evidence
    expected_graph, expected_criteria, expected_suite, expected_review = repair(
        baseline('drafts/core/tensor.core.graph.json'), baseline('drafts/core/entry-evidence-criteria.json'),
        baseline('drafts/core/scenarios/entry-evidence-cases.json'))
    errors = [[], [], [], []]
    if graph['nodes'] != expected_graph['nodes'] or criteria != expected_criteria or graph_sha != criteria['graphSha256']:
        errors[0].append('Current graph or criteria differs from the exact answer-specific repair contract.')
    if graph != expected_graph:
        errors[1].append('Current routes or their context requirements differ from the exact repair contract.')
    review = json.loads((REVIEW / 'review.json').read_text())
    if review != expected_review:
        errors[1].append('Every historical and current shared destination requires its exact answer-specific disposition.')
    # All restored question evidence predicates are evaluated on current cards.
    for case in suite['restoredCases']:
        actual, _ = answer(criteria['nodes'][case['nodeId']], case_evidence(suite,case), criteria)
        if actual != case['expectedAnswer']:
            errors[2].append(f"{case['id']}: actual answer differs")
    from evaluate_entry_scenarios import run_cases
    from restored_evidence import run_cases as restored_cases
    if any(not case['passed'] for case in run_cases(graph,criteria,suite)+restored_cases(graph,criteria,suite)):
        errors[2].append('Current bounded evidence scenarios disagree with their explicitly authored answers and routes.')
    domains = {n['category'] for n in graph['nodes']}
    if domains != set(criteria['domains']) or len(domains) != 7 or len(review['reviewedSharedPairs']) != 602:
        errors[3].append('All seven domains and all 602 historical shared destinations must remain accounted for.')
    from evaluate_entry_scenarios import expand_suite
    if (expand_suite(suite)['cases'] != expand_suite(expected_suite)['cases'] or
        suite.get('restoredCases') != expected_suite['restoredCases'] or
        suite.get('restoredPaths') != expected_suite['restoredPaths']):
        errors[3].append('Current positive, negative, unknown, report-only and retained-context scenario coverage differs from the explicit repair package.')
    return [gate(gid, problem) for gid, problem in zip(EVIDENCE_IDS, errors)]
