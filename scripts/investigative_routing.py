"""Versioned draft routing profile: explicit choices and bounded new leads.

This authoring profile is not a new Core schema or an execution engine. Its
optional edge metadata explains the context an investigator must supply. Core
outcome guards alone do not evaluate these additional readiness conditions.
"""
from copy import deepcopy
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'drafts/core/reviews/2026-10-13-routing'
VERSION = '0.20261013a'
PROFILE = 'tensor-investigative-routing/1'
PRIOR_SHA = '1a32d33c3ffbc6068b64a19c102ec4a85ca2914b206d96eb78cafd4173e169d0'

# Reviewed topic relationships, not a complete graph or a target-count quota.
# Every target opens a new independently bound event assessment at its root.
DOMAIN_LEADS = {
    'Identity': [('Email', 'A session or principal identifies a named mailbox event'), ('Cloud', 'A credential or principal identifies a named resource operation')],
    'Email': [('File', 'A message identifies a separately acquired attachment on a named system'), ('Identity', 'A mailbox event identifies a named authentication or session action')],
    'File': [('Host', 'An artifact identifies a named process execution on a named host'), ('Email', 'Artifact provenance identifies a named delivery to a named mailbox')],
    'Host': [('Network', 'Process/socket evidence identifies a named endpoint communication'), ('Application', 'A process/connection identifies a named application request')],
    'Application': [('Identity', 'An authenticated request identifies a named principal action'), ('Cloud', 'A request identifies a named resource operation in a named tenant')],
    'Cloud': [('Network', 'Runtime or resource telemetry identifies a named endpoint communication'), ('Application', 'Resource audit evidence identifies a named application request')],
    'Network': [('Host', 'Socket and endpoint discrimination identifies a named process on a host'), ('Identity', 'Authenticated connection evidence identifies a named principal action')],
}
FACET_DOMAINS = {
    'control-plane actions': ['Cloud', 'Identity'], 'content lineage': ['File', 'Email'],
    'process ancestry': ['Host', 'Application'], 'execution lineage': ['Host', 'File'],
    'collaboration artifacts': ['Email', 'File'], 'session anomalies': ['Identity', 'Application'],
    'privileged access events': ['Identity', 'Cloud'], 'transport metadata': ['Network', 'Host'],
    'data access traces': ['Cloud', 'File'], 'authentication pathways': ['Identity', 'Application'],
    'workload identity context': ['Identity', 'Cloud'], 'message delivery paths': ['Email', 'Network'],
    'artifact provenance': ['File', 'Email'], 'endpoint state changes': ['Host', 'File'],
    'network pivots': ['Network', 'Host'], 'api invocation patterns': ['Application', 'Cloud'],
}


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True)+'\n').encode()


def continuation_edges(graph):
    """Only the explicitly retained historical single-path fixtures use this.

    Do not collapse a current investigation into a source/outcome dictionary.
    New route selection uses edge identities and explicit target instances.
    """
    return [e for e in graph['edges'] if 'tensor:investigativeLead' not in e.get('extensions', {})]


def lead_edges(graph, criteria):
    edges = []
    def add(source, target, outcomes, kind, basis, **extra):
        for outcome in outcomes:
            contract = {'profile': PROFILE, 'kind': kind, 'basis': basis,
                        'sourceDomain': criteria['nodes'][source]['domain'], 'targetDomain': criteria['nodes'][target]['domain'],
                        'targetBindingFields': criteria['nodes'][target]['boundSubjectFields'],
                        'preserveSourceAssessment': True, 'independentTargetAssessment': True,
                        'selection': 'Explicit transition ID and fresh target instance; eligible routes are not automatically selected.',
                        **extra}
            edges.append({'id': f'{source}-{outcome}-{target}', 'source': source, 'target': target, 'decision': outcome,
                          'label': kind.replace('-', ' '), 'extensions': {'tensor:investigativeLead': contract}})
    for domain, roles in criteria['domains'].items():
        add(roles['entry'], roles['independentValidation'], ['yes'], 'independent-validation',
            'A separately acquired matching record can be validated alongside the primary record. Copies of one origin are not independent.',
            readiness='A separately acquired matching record, with its own provenance basis, exact same source subjects and bounded interval.')
        add(roles['entry'], roles['alternate'], ['no'], 'independent-search',
            'No match in one examined source does not exclude a match in another independently acquired source.',
            readiness='Same source subject and interval; explicitly identify the independent material to examine. No event presence is inherited.')
        add(roles['entry'], roles['unresolved'], ['unknown'], 'bounded-handoff',
            'Retain the source uncertainty while an independent search may continue on a separate lead.',
            readiness='Record the evidence gap and the bound source context; this handoff does not close other leads.')
    for node in graph['nodes']:
        if node['archetype'] != 'correlate':
            continue
        card = criteria['nodes'][node['id']]
        facet = card.get('sourceFacet')
        targets = FACET_DOMAINS.get(facet, []) if facet else [d for d, _ in DOMAIN_LEADS[node['category']]]
        for domain in targets:
            if domain == node['category']:
                continue
            basis = next((text for d, text in DOMAIN_LEADS[node['category']] if d == domain),
                         f'Separately acquired {facet} evidence identifies a named {domain.lower()} event. Topic similarity alone is insufficient.')
            add(node['id'], criteria['domains'][domain]['entry'], ['yes', 'no', 'unknown'], 'cross-domain-lead', basis,
                sourceFacet=facet, readiness='Independently identified target event, complete target subject bindings, bounded target interval, and cited discovery evidence. Retain the source answer, including no/unknown; it establishes no target answer or relationship.',
                context='New lead: retain the original source context and separately declare the target context, discovery rationale and competing explanations. Never copy domain-specific bindings by position.')
    return edges


def apply(graph, criteria, suite):
    from core_graph_pipeline import build_graph_payload
    graph, criteria, suite = deepcopy(graph), deepcopy(criteria), deepcopy(suite)
    graph = build_graph_payload(VERSION, graph['nodes'], graph['edges']+lead_edges(graph, criteria), graph['entryNodeIds'], graph['schemaVersion'])
    for node in graph['nodes']:
        node['extensions']['tensor:evidenceCriteria']['version'] = VERSION
    graph['extensions'] = {'tensor:routingProfile': PROFILE}
    criteria['graphVersion'] = suite['graphVersion'] = VERSION
    criteria['graphSha256'] = sha256(encoded(graph)).hexdigest()
    criteria['routingProfile'] = {'id': PROFILE, 'document': 'reviews/2026-10-13-routing/README.md',
                                  'priorGraphSha256': PRIOR_SHA, 'semantics': 'One outcome can enable several routes; decisions explicitly select zero, one or multiple leads. Eligibility never asserts a target answer.'}
    # The retained fixture histories pin the active graph version. Their observed
    # facts and expected original continuation traces are otherwise unchanged.
    def repin(value):
        if isinstance(value, dict):
            return {k: VERSION if k == 'graphVersion' else repin(v) for k, v in value.items()}
        if isinstance(value, list): return [repin(v) for v in value]
        return value
    return graph, criteria, repin(suite)


def eligible_leads(graph, source, outcome, context):
    """Small offline profile evaluator; not normative Core interpretation.

    Missing bindings/clock/provenance leave a declared cross-domain option
    unready. No target event, authorization or evidence truth is inferred.
    """
    if graph.get('extensions', {}).get('tensor:semanticReview'):
        from semantic_graph_review import ready_leads
        return ready_leads(graph, source, outcome, context)
    result = []
    if not isinstance(context, dict): return result
    for edge in graph['edges']:
        lead = edge.get('extensions', {}).get('tensor:investigativeLead')
        if not lead or edge['source'] != source or edge['decision'] != outcome:
            continue
        target = context.get(edge['target'], {})
        if not isinstance(target, dict): continue
        if lead['kind'] == 'cross-domain-lead':
            from evaluate_entry_scenarios import instant
            interval = target.get('interval', {})
            if not isinstance(interval, dict) or not isinstance(target.get('bindings'), dict): continue
            start, end = instant(interval.get('start')), instant(interval.get('end'))
            refs = target.get('discoveryEvidenceRefs')
            if (target.get('domain') != lead['targetDomain'] or not start or not end or start >= end
                    or not all(isinstance(target.get('bindings', {}).get(k), str) and target['bindings'][k].strip() for k in lead['targetBindingFields'])
                    or not isinstance(refs, list) or not refs or not all(isinstance(ref,str) and ref.strip() for ref in refs)
                    or not isinstance(target.get('discoveryRationale'), str) or not target['discoveryRationale'].strip()):
                continue
        elif target.get('ready') is not True:
            continue
        result.append(edge['id'])
    return result


def assess_routes(graph, criteria):
    if graph.get('extensions', {}).get('tensor:contextualRouting'):
        from contextual_routing import repair, baseline
        expected, expected_criteria, _, _ = repair(baseline('drafts/core/tensor.core.graph.json'),
            baseline('drafts/core/entry-evidence-criteria.json'), baseline('drafts/core/scenarios/entry-evidence-cases.json'))
        return [] if graph == expected and criteria == expected_criteria else ['Current routes or context contracts differ from the reviewed repair.']
    if graph.get('extensions', {}).get('tensor:semanticReview'):
        from semantic_graph_review import REVIEW as SEMANTIC_REVIEW
        expected = json.loads((SEMANTIC_REVIEW/'reviewed-structure.json').read_text())
        return [] if graph['nodes'] == expected['nodes'] and graph['edges'] == expected['edges'] else ['Working definitions/routes differ from the independently reviewed semantic snapshot']
    errors = []
    prior_bytes = (REVIEW/'prior-draft.graph.json').read_bytes()
    if sha256(prior_bytes).hexdigest() != PRIOR_SHA:
        return ['Routing baseline does not match its immutable source pin']
    prior = json.loads(prior_bytes)
    if continuation_edges(graph) != prior['edges']:
        errors.append('Retained continuation routes changed without an explicit revised evidence review')
    expected = {e['id']: e for e in lead_edges(prior, criteria)}
    actual = {e['id']: e for e in graph['edges'] if 'tensor:investigativeLead' in e.get('extensions', {})}
    if expected != actual:
        errors.append('Added routes, readiness conditions or target contexts disagree with the reviewed routing profile')
    if graph.get('extensions') != {'tensor:routingProfile': PROFILE} or criteria.get('routingProfile', {}).get('id') != PROFILE:
        errors.append('The active draft must identify its routing profile explicitly')
    return errors


def review_payload(graph, criteria):
    by_source = defaultdict(lambda: defaultdict(list))
    nodes = {n['id']: n for n in graph['nodes']}
    for edge in graph['edges']: by_source[edge['source']][edge['decision']].append(edge['target'])
    return {'format': 'tensor-investigative-routing-review', 'profile': PROFILE, 'graphVersion': VERSION,
            'graphSha256': sha256(encoded(graph)).hexdigest(), 'priorGraphSha256': PRIOR_SHA,
            'scope': 'Author-side repair and scenario validation; external review and investigative effectiveness remain unproved.',
            'summary': {'questions': len(nodes), 'routes': len(graph['edges']),
                        'multipleRouteSources': sum(any(len(v)>1 for v in outcomes.values()) for outcomes in by_source.values()),
                        'crossDomainRoutes': sum(nodes[e['source']]['category'] != nodes[e['target']]['category'] for e in graph['edges']),
                        'retainedContinuationRoutes': len(continuation_edges(graph)),
                        'sameDestinationContinuations': 'Historical optional assessments retain their own answers on a common follow-up. They are not a rule for other routes.'},
            'inputs': [{'path': 'drafts/core/entry-evidence-criteria.json', 'sha256': sha256(encoded(criteria)).hexdigest()}],
            'decisions': ['Multiple targets per answer are legal; no automatic all-route traversal.',
                          'Cross-domain targets open a new bound event assessment; no target answer is inherited.',
                          'Question IDs and stage labels do not define chronology or evidence prerequisites.',
                          'Cycles are legal definitions. Revisit with a fresh instance; bound playback and selections prevent automatic recursion.',
                          'No numeric route quota or fan-in proxy determines investigative correctness.']}
