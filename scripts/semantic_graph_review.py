"""Repairs accepted after separate, item-level AI review; working draft only.

This is an authoring/evidence profile, never a new Core binding or execution engine.
The prior restoration and routing review outputs stay reproducible and unchanged.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'e6ced17aeaa1cf1d8be31ba1fbd24bf96d0890e0'
VERSION = '0.20261013b'
PROFILE = 'tensor-semantic-review/1'
ROUTING_PROFILE = 'tensor-investigative-routing/2'
REVIEW = ROOT / 'drafts/core/reviews/2026-10-13-semantic'


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + '\n').encode()


def prepare_case(case, criteria):
    """Explicitly author missing fixture assumptions, never enrich imported evidence."""
    case = deepcopy(case)
    if not isinstance(case, dict):
        return case
    if 'bindings' in case and 'interval' in case:
        case['semanticReview'] = True
        if case.get('id', '').endswith('-bounded-absence'):
            for group in ('primary', 'independent'):
                case.setdefault(group, {}).update(accessible=True, searched=True)
        analysis = case.get('analysis', {})
        if isinstance(analysis, dict):
            scope = analysis.get('scope', {})
            for entity in scope.get('entities', []) if isinstance(scope, dict) else []:
                if not isinstance(entity, dict) or 'subjects' in entity:
                    continue
                domain = criteria['domains'].get(entity.get('domain'))
                if not domain:
                    continue
                if entity['domain'] == case.get('domain') and entity.get('subjectId') == case['bindings'].get(domain['bindings'][0]):
                    entity['subjects'] = deepcopy(case['bindings'])
                else:
                    for key in ('correlation', 'dependency', 'additionalEffect'):
                        relation = analysis.get(key, {})
                        subjects = relation.get('targetSubjects', {})
                        if relation.get('targetDomain') == entity['domain'] and subjects.get(domain['bindings'][0]) == entity.get('subjectId'):
                            entity['subjects'] = deepcopy(subjects)
            dependency = analysis.get('dependency', {})
            if isinstance(dependency, dict) and dependency.get('claimKind') == 'documented-dependency':
                dependency.setdefault('relationId', 'authored:documented-dependency:42')
            primary = case.get('primary', {}).get('records', [])
            if primary and isinstance(primary[0], dict):
                hypothesis = analysis.get('hypothesis', {})
                analysis.setdefault('corroboration', {
                    'subjects': deepcopy(case['bindings']), 'interval': deepcopy(case['interval']),
                    'hypothesisId': hypothesis.get('hypothesisId'), 'sourceRecordId': primary[0].get('id'),
                    'sourceFact': 'event.id', 'targetFact': 'event.id', 'identifierNamespace': 'authored:bounded-event-identifier',
                    'method': 'Compare explicitly supplied, assessed identifiers in the authored common namespace',
                    'evidenceRefs': [primary[0].get('id', 'authored:primary-discriminator')],
                })
            if isinstance(case.get('retention'), dict):
                case['retention']['hypothesis'] = deepcopy(analysis.get('hypothesis'))
    def clocks(value):
        if isinstance(value, dict):
            if 'eventTime' in value and 'subjects' in value:
                value.setdefault('clockUncertaintySeconds', 0)
            for item in value.values():
                clocks(item)
        elif isinstance(value, list):
            for item in value:
                clocks(item)
    clocks(case)
    return case


def apply(graph, criteria, suite):
    graph, criteria, suite = deepcopy(graph), deepcopy(criteria), deepcopy(suite)
    by_id = {n['id']: n for n in graph['nodes']}
    for nid, card in criteria['nodes'].items():
        card['nodeId'] = nid
        role, kind = card['role'], card.get('assessmentKind')
        if role == 'unresolved':
            card['predicate'] = 'Were the named unresolved investigation questions and evidence gaps retained separately with their bounds and limitations, preserving every established finding?'
        elif role == 'assessed':
            card['predicate'] = 'Have the completed assessments and any refuted hypotheses, unresolved questions and limitations been retained separately with their evidence and bounds, without asserting investigation closure?'
        elif role == 'scope':
            card['predicate'] = 'Were the investigation subjects and time bounds documented with evidence-backed full entity inclusions, exclusions and unknown dispositions, without claiming population completeness?'
        elif kind == 'scope-bound':
            card['predicate'] = f"Were evidence-backed full entity inclusions, exclusions and unknown dispositions for the supplied {card['sourceFacet']} investigation recorded within its declared subjects and time bounds, without claiming population completeness?"
        elif kind == 'retention':
            card['predicate'] = 'Were the bounded investigation assessments and open questions for the supplied evidence focus retained with separate answers, references and limitations, without asserting investigation closure?'
            card['focusBinding'] = 'supplied-investigation-focus'
            card['sourceFacetRole'] = 'historical-source-label-only'
        elif role == 'impact' or kind in ('metric-change', 'additional-impact'):
            card['predicate'] = ('Did the named technical metric for the explicitly bound additional effect subject change between its separately declared comparable baseline and observation contexts, with the same metric and units?'
                                 if kind == 'additional-impact' else
                                 'Did the named technical metric for the bound effect subjects change between separately declared comparable baseline and observation contexts, with the same metric and units?')
        if 'resumePrerequisites' in card:
            card['resumePrerequisites'] = [p for p in card['resumePrerequisites'] if p not in ('supported-hypothesis', 'bounded-scope')]
            if by_id[nid]['archetype'] in ('scope', 'correlate', 'attribute', 'impact'):
                card['resumePrerequisites'].append('own-bound-assessment-evidence')
        if role != 'classification' and kind != 'hypothesis':
            conditional = [f for f in card['requiredAssessmentRecord'] if f.startswith('hypothesis')]
            if conditional:
                card['requiredAssessmentRecord'] = [f for f in card['requiredAssessmentRecord'] if f not in conditional]
                card['conditionalAssessmentRecord'] = {'whenHypothesisSupplied': conditional,
                    'meaning': 'Retain the exact supplied hypothesis and its answer; independent factual assessments may omit a hypothesis.'}
        by_id[nid]['text'] = card['predicate']
        if by_id[nid]['archetype'] == 'terminal' and role != 'exclusion' and role != 'refuted':
            by_id[nid]['label'] = f"{card['domain']}: Retain bounded investigation assessments"
        by_id[nid]['extensions']['tensor:evidenceCriteria']['version'] = VERSION
    criteria['rules']['unresolved-stop'] = {
        'yes': 'The named unresolved or rejected assessment prerequisites and their evidence/limits are retained, while established event and other findings keep their original answers.',
        'no': 'The record demonstrably drops or changes a required unresolved assessment or misrepresents an established finding.',
        'unknown': 'The retained gap, its exact context or the basis for this handoff cannot be assessed; no event answer is inferred.'}
    criteria['rules']['findings-stop'] = {
        'yes': 'Actual completed assessments and explicitly open questions are retained with exact bounds, hypothesis meaning when supplied, references and limitations; a positive hypothesis or visit to every stage is not required.',
        'no': 'A required retained assessment or preceding answer is demonstrably omitted or changed.',
        'unknown': 'The completeness, exact context, hypothesis meaning or focus disposition of the retained record is unresolved.'}
    criteria['rules']['restored-retention'] = deepcopy(criteria['rules']['findings-stop'])
    for rule in ('scope-bound', 'restored-scope-bound'):
        criteria['rules'][rule]['yes'] = 'Exact declared composite subject identities, time bounds and evidence-backed inclusions/exclusions/unknowns are retained; no affirmative technical hypothesis or population completeness is inferred.'
        criteria['rules'][rule]['unknown'] = 'Full composite identities, own assessment method/evidence, time bounds or conflicting dispositions are unresolved.'
    for rule in ('restored-additional-entities', 'restored-dependencies', 'restored-identifier-relation',
                 'restored-temporal', 'restored-technical-source', 'restored-behavior-pattern',
                 'relationship-test', 'source-test'):
        criteria['rules'][rule]['unknown'] = 'The named assessment lacks its own full subject/time context, accepted evidence, operational discriminator or method; a supplied hypothesis must retain its exact meaning, but an affirmative unrelated hypothesis or scope is not required.'
    criteria['rules']['restored-additional-entities']['unknown'] = 'The own bounded scope, complete entity dispositions or inclusion evidence is unresolved. No affirmative technical hypothesis is required.'
    criteria['rules']['restored-dependencies']['unknown'] = 'The own bounded scope, full validated endpoint contexts, named dependency relation or direction is unresolved. No affirmative technical hypothesis is required.'
    criteria['rules']['restored-temporal']['yes'] = 'Both entire clock bounds lie within their separately declared source/target intervals and the greatest timestamp separation meets the declared tolerance; causation is separate.'
    criteria['rules']['restored-temporal']['no'] = 'Both entire clock bounds lie within their separately declared contexts and the smallest timestamp separation exceeds the declared tolerance.'
    for rule in ('effect-test', 'restored-metric-change', 'restored-additional-impact'):
        criteria['rules'][rule]['yes'] = 'Assessed comparable observations differ on the named metric and units over explicit baseline and observation intervals; the baseline may precede the event interval when separately bounded. Cause and business loss are not inferred.'
        criteria['rules'][rule]['unknown'] = 'Comparable values, metric/units, explicit baseline/observation bounds, subject identity, provenance or material counterevidence are unresolved.'
    for edge in graph['edges']:
        if by_id[edge['target']]['archetype'] == 'terminal' and criteria['nodes'][edge['target']]['role'] == 'restored':
            edge.setdefault('extensions', {})['tensor:routeBasis'] = 'Retain the incoming investigation focus, exact subjects/time and separate answers; the target historical source facet does not introduce a new question or end other leads.'
    from investigative_routing import DOMAIN_LEADS
    edges = graph['edges']
    def option(source, target, outcome, kind, basis):
        eid = f'{source}-{outcome}-{target}'
        if any(e['id'] == eid for e in edges):
            return
        edges.append({'id': eid, 'source': source, 'target': target, 'decision': outcome, 'label': kind.replace('-', ' '),
                      'extensions': {'tensor:investigativeLead': {'kind': kind, 'basis': basis}}})
    for domain, roles in criteria['domains'].items():
        # Fact-led investigations may retain a refutation/gap and continue with
        # another independently evidenced proposition in parallel.
        for source, target in zip(roles['classification'], roles['scope']):
            for outcome in ('no', 'unknown'):
                option(source, target, outcome, 'independent-assessment', 'A refuted or unresolved technical hypothesis does not decide independently evidenced investigation scope. Retain the hypothesis answer and assess scope on its own exact context.')
        for source in roles['scope']:
            for outcome in ('no', 'unknown'):
                option(source, roles['correlation'], outcome, 'independent-assessment', 'An unresolved or rejected scope does not decide a separately bound endpoint relationship. Preserve the scope answer and supply each relationship endpoint and its own evidence.')
        for source in (roles['entry'], roles['primaryValidation'], roles['independentValidation']):
            for target_domain, _ in DOMAIN_LEADS[domain]:
                for outcome in ('yes', 'no', 'unknown'):
                    option(source, criteria['domains'][target_domain]['entry'], outcome, 'cross-domain-lead', 'Separately acquired discovery material motivates the explicitly named target proposition. The source search or validation answer neither supplies nor excludes a target finding.')
    catalog = json.loads((ROOT / 'drafts/core/event-profiles/catalog.source.json').read_text())
    from event_profiles import VERSION as profile_version, definition_id
    for edge in edges:
        lead = edge.get('extensions', {}).get('tensor:investigativeLead')
        if not lead:
            continue
        source, target = criteria['nodes'][edge['source']], criteria['nodes'][edge['target']]
        alternatives = {pid: {'version': profile_version, 'questionId': definition_id(pid, edge['target']),
                             'bindings': p['bindings'], 'proposition': p['proposition']}
                        for pid, p in catalog['profiles'].items() if p['domain'] == target['domain']}
        lead.update(profile=ROUTING_PROFILE, sourceDomain=source['domain'], targetDomain=target['domain'],
                    targetBindingFields=target['boundSubjectFields'], preserveSourceAssessment=True,
                    independentTargetAssessment=True, targetQuestionId=edge['target'],
                    targetProposition=target['predicate'], targetProfiles=alternatives,
                    selection='Explicit transition identity and fresh target instance; no target answer or action is inherited.',
                    readiness='Supply the exact target question/profile/version, its own full bindings and interval, cited assessment/discovery basis, and the retained source context. Independent material must have distinct origins and identities; a bare ready flag is insufficient.')
        if lead['kind'] == 'cross-domain-lead':
            lead['basis'] = 'Evidence in the retained source context motivates a separately identified target proposition with its own subjects, interval and interpretation profile; topic similarity and source answers alone supply no finding.'
        lead.pop('sourceFacet', None)  # A fixed historical facet cannot fabricate a profile event.
    from core_graph_pipeline import build_graph_payload
    graph = build_graph_payload(VERSION, graph['nodes'], edges, graph['entryNodeIds'], graph['schemaVersion'])
    graph['extensions'] = {'tensor:routingProfile': ROUTING_PROFILE, 'tensor:semanticReview': PROFILE}
    criteria['graphVersion'] = suite['graphVersion'] = VERSION
    criteria['graphSha256'] = sha256(encoded(graph)).hexdigest()
    criteria['routingProfile'].update(id=ROUTING_PROFILE, document='reviews/2026-10-13-semantic/README.md')
    criteria['semanticReview'] = {'id': PROFILE, 'baselineCommit': BASELINE, 'reviewDocument': 'reviews/2026-10-13-semantic/README.md',
                                'scope': 'Separate AI item review and independently authored challenges; not institutional approval, authenticated logs or universal effectiveness.'}
    # Re-pin authored normalized scenarios. These explicit fixture assumptions
    # are documented as test inputs; imported records are never enriched.
    def repin(value):
        if isinstance(value, dict):
            return {k: VERSION if k == 'graphVersion' else repin(v) for k, v in value.items()}
        if isinstance(value, list):
            return [repin(v) for v in value]
        return value
    suite = repin(suite)
    from evaluate_entry_scenarios import expand_suite
    original_cases = suite['cases']
    expanded = {c['id']: prepare_case(c, criteria) for c in expand_suite(suite)['cases']}
    def patch(left, right):
        if not isinstance(left, dict) or not isinstance(right, dict):
            if right is None:
                raise ValueError('A null value needs an explicit fixture rather than merge-patch deletion')
            return deepcopy(right)
        result = {k: None for k in sorted(left.keys() - right.keys())}
        for key, value in right.items():
            if key not in left or left[key] != value:
                result[key] = patch(left.get(key), value)
        return result
    packed = []
    for raw in original_cases:
        case = expanded[raw['id']]
        if 'extends' in raw:
            try:
                evidence_patch = patch(expanded[raw['extends']], case)
                for key in ('id', 'expectedTrace', 'expectedState'):
                    evidence_patch.pop(key, None)
                packed.append({**{k: case[k] for k in ('id', 'expectedTrace', 'expectedState')},
                               'extends': raw['extends'], 'patch': evidence_patch})
                continue
            except ValueError:
                pass
        packed.append(case)
    suite['cases'] = packed
    if expand_suite(suite)['cases'] != list(expanded.values()):
        raise ValueError('Reviewed fixture compaction changed evidence or explicit expectations')
    suite['restoredFixtures'] = {key: prepare_case(c, criteria) for key, c in suite['restoredFixtures'].items()}
    return graph, criteria, suite


def interval_ready(value):
    from evaluate_entry_scenarios import instant
    if not isinstance(value, dict):
        return False
    start, end = instant(value.get('start')), instant(value.get('end'))
    return start is not None and end is not None and start < end


def ready_leads(graph, source, outcome, context):
    """Offline authoring-profile readiness, distinct from Core outcome guards."""
    from evaluate_entry_scenarios import named, references
    if not isinstance(context, dict):
        return []
    result = []
    original = context.get('_source', {})
    criteria = json.loads((ROOT / 'drafts/core/entry-evidence-criteria.json').read_text())
    from event_profiles import VERSION as profile_version, definition_id
    catalog = json.loads((ROOT / 'drafts/core/event-profiles/catalog.source.json').read_text())['profiles']
    if (not isinstance(original, dict) or original.get('nodeId') != source
            or original.get('answer') != outcome or original.get('graphVersion') != graph['version']
            or source not in criteria['nodes'] or original.get('domain') != criteria['nodes'][source]['domain']
            or not isinstance(original.get('bindings'), dict)
            or not references(original.get('evidenceRefs')) or not named(original.get('rationale'))):
        return []
    source_profile = catalog.get(original.get('eventProfile'))
    if original.get('eventProfile') is None and original.get('profileVersion') is not None:
        return []
    if original.get('eventProfile') is not None and (not source_profile
            or source_profile['domain'] != original['domain'] or original.get('profileVersion') != profile_version):
        return []
    source_card = criteria['nodes'][source]
    if source_profile and (original.get('questionId') != definition_id(original['eventProfile'], source)
            or (source_card.get('role') == 'restored' and source_card.get('stage') != 'terminal'
                and source_card.get('sourceFacet') not in source_profile['facets'])):
        return []
    source_fields = source_profile['bindings'] if source_profile else criteria['domains'][original['domain']]['bindings']
    missing = [f for f in source_fields if not named(original['bindings'].get(f))]
    if not interval_ready(original.get('interval')):
        missing.append('interval')
    def gaps_match(value):
        return (isinstance(value, list) and all(named(v) for v in value)
                and len(value) == len(set(value)) and set(value) == set(missing))
    if not gaps_match(original.get('missingContextFields', [])) or (missing and outcome != 'unknown'):
        return []
    for edge in graph['edges']:
        lead = edge.get('extensions', {}).get('tensor:investigativeLead')
        if not lead or edge['source'] != source or edge['decision'] != outcome:
            continue
        target = context.get(edge['target'])
        if not isinstance(target, dict) or target.get('domain') != lead['targetDomain']:
            continue
        pid = target.get('eventProfile')
        if pid is None and target.get('profileVersion') is not None:
            continue
        profile = lead['targetProfiles'].get(pid) if pid is not None else None
        if pid is not None and (not profile or target.get('profileVersion') != profile['version']):
            continue
        fields = profile['bindings'] if profile else lead['targetBindingFields']
        question = profile['questionId'] if profile else edge['target']
        handoff = lead['kind'] == 'bounded-handoff'
        if (target.get('questionId') != question or target.get('graphVersion') != graph['version']
                or not isinstance(target.get('bindings'), dict)):
            continue
        if not handoff and (not interval_ready(target.get('interval'))
                or not all(named(target['bindings'].get(f)) for f in fields)):
            continue
        if lead['kind'] == 'cross-domain-lead':
            if not references(target.get('discoveryEvidenceRefs')) or not named(target.get('discoveryRationale')):
                continue
        else:
            if (not isinstance(original, dict) or original.get('domain') != lead['sourceDomain']
                    or target.get('eventProfile') != original.get('eventProfile')
                    or target.get('profileVersion') != original.get('profileVersion')
                    or target['bindings'] != original.get('bindings') or target.get('interval') != original.get('interval')
                    or not references(target.get('evidenceRefs')) or not named(target.get('method'))):
                continue
            if lead['kind'] in ('independent-validation', 'independent-search'):
                if (not references(original.get('materialOrigins')) or not isinstance(original.get('recordIds'), list)
                        or not all(named(v) for v in original['recordIds'])
                        or not named(target.get('materialOrigin')) or target['materialOrigin'] in original['materialOrigins']
                        or target.get('recordId') in original['recordIds']
                        or not named(target.get('materialDescription'))):
                    continue
                if lead['kind'] == 'independent-validation' and (not references(original['recordIds'])
                        or not named(target.get('recordId'))):
                    continue
            if handoff and (not named(target.get('gapDescription'))
                    or not gaps_match(target.get('missingContextFields', []))):
                continue
        result.append(edge['id'])
    return result


def assess(graph, graph_sha, criteria, suite):
    """Structural/card coverage and independent challenge agreement, no truth claim."""
    from graph_assurance_policy import EVIDENCE_IDS, gate
    from evaluate_entry_scenarios import run_cases, expand_suite
    from restored_evidence import run_cases as restored_cases
    errors = [[], [], [], []]
    nodes = {n['id']: n for n in graph['nodes']}
    if (len(nodes) != len(graph['nodes']) or set(nodes) != set(criteria['nodes'])
            or criteria.get('graphSha256') != graph_sha or criteria.get('graphVersion') != graph['version']
            or criteria.get('schemaVersion') != graph['schemaVersion']):
        errors[0].append('Every exact current question and graph digest must be pinned by its evidence card.')
    expected = json.loads((REVIEW / 'reviewed-structure.json').read_text())
    if expected['criteria'] != criteria:
        errors[0].append('Evidence roles, rules, prerequisites or bindings differ from the separately reviewed criteria snapshot.')
    for nid, node in nodes.items():
        card = criteria['nodes'].get(nid)
        if not isinstance(card, dict):
            errors[0].append(f'{nid}: missing evidence card')
            continue
        if (card.get('predicate') != node['text'] or card.get('domain') != node['category']
                or card.get('rule') not in criteria['rules'] or card.get('boundSubjectFields') != criteria['domains'][node['category']]['bindings']
                or node.get('extensions', {}).get('tensor:evidenceCriteria') != {
                    'document': 'entry-evidence-criteria.json', 'version': graph['version'], 'nodeId': nid}):
            errors[0].append(f'{nid}: question, criterion, domain or complete subject contract disagree')
        if 'supported-hypothesis' in card.get('resumePrerequisites', []):
            errors[0].append(f'{nid}: an affirmative unrelated hypothesis cannot gate independent facts')
    if expected['nodes'] != graph['nodes'] or expected['edges'] != graph['edges']:
        errors[1].append('Current question or route differs from the exact separately reviewed snapshot; re-review is required.')
    if graph.get('extensions') != {'tensor:routingProfile': ROUTING_PROFILE, 'tensor:semanticReview': PROFILE}:
        errors[1].append('The working graph must declare its exact reviewed semantics profile.')
    results = run_cases(graph, criteria, suite) + restored_cases(graph, criteria, suite)
    if not results or any(not r['passed'] for r in results):
        errors[2].append('Explicitly authored bounded scenarios disagree with the reviewed current behavior.')
    expanded = expand_suite(suite)
    if not expanded['cases'] or {c['domain'] for c in expanded['cases']} != set(criteria['domains']):
        errors[3].append('Scenarios must exercise every public domain.')
    for domain, roles in criteria['domains'].items():
        cases = [c for c in expanded['cases'] if c['domain'] == domain]
        answers = {answer for c in cases for nid, answer in c['expectedTrace'] if nid in roles['classification']}
        if answers != {'yes', 'no', 'unknown'} or not any(c.get('evidenceKind') == 'public-report-only' for c in cases):
            errors[3].append(f'{domain}: positive, refuted, unknown and report-only evidence cases must remain explicit.')
        for role in ('entry', 'classification', 'scope', 'correlation', 'attribution', 'impact'):
            ids = roles[role] if isinstance(roles[role], list) else [roles[role]]
            outcomes = {a for c in cases for n, a in c['expectedTrace'] if n in ids}
            if outcomes != {'yes', 'no', 'unknown'}:
                errors[3].append(f'{domain}: {role} needs explicit positive, negative and unknown outcomes.')
    seen = {}
    for case in suite['restoredCases']:
        seen.setdefault(case['nodeId'], set()).add(case['expectedAnswer'])
    if any(seen.get(nid) != {'yes', 'no', 'unknown'} for nid in criteria['restoration']['restoredNodeIds']):
        errors[3].append('Every restored predicate needs explicit positive, negative and unknown scenarios.')
    return [gate(gid, problem) for gid, problem in zip(EVIDENCE_IDS, errors)]
