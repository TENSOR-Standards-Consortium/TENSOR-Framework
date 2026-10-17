#!/usr/bin/env python3
"""Verify exact independent-review coverage and source pins, not evidence truth."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'drafts/core/reviews/2026-10-13-semantic'


def verify():
    review = json.loads((DIRECTORY / 'review.json').read_text())
    if review['status'] != 'separate-ai-review-complete' or review['institutionalApproval'] is not False:
        raise ValueError('Review status must distinguish complete AI review from institutional approval')
    for path, digest in review['inputPins'].items():
        if sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Current reviewed input differs: {path}')
    for path, digest in review['ledgerPins'].items():
        if sha256((DIRECTORY / path).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Review ledger or challenge receipt differs: {path}')
    for path, digest in review['preservedArtifacts'].items():
        if sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Historical protected artifact differs: {path}')
    graph = json.loads((ROOT / 'drafts/core/tensor.core.graph.json').read_text())
    definitions = json.loads((ROOT / 'drafts/core/event-profiles/definitions.json').read_text())['profiles']
    snapshot = DIRECTORY / 'reviewed-structure.json'
    if sha256(snapshot.read_bytes()).hexdigest() != review['reviewedStructureSha256']:
        raise ValueError('Reviewed structural snapshot differs')
    for row in review['domains']:
        ledger = json.loads((DIRECTORY / 'items' / (row['id'] + '.json')).read_text())
        expected = {
            'nodes': {n['id'] for n in graph['nodes'] if n['category'] == row['domain']},
            'edges': {e['id'] for e in graph['edges'] if next(n for n in graph['nodes'] if n['id'] == e['source'])['category'] == row['domain']},
            'profileDefinitions': {d['id'] for p in definitions.values() for d in p.values()
                                   if next(n for n in graph['nodes'] if n['id'] == d['graphNodeId'])['category'] == row['domain']},
        }
        for kind, ids in expected.items():
            items = ledger[kind]
            actual = [item.get('id', item.get('questionId')) for item in items]
            if len(actual) != len(set(actual)) or set(actual) != ids or any(item['verdict'] != 'accept' or not item.get('rationale') for item in items):
                raise ValueError(f'{row["domain"]}: incomplete, duplicate or unresolved {kind} review')
        # The item review must refer to these exact definitions, not an older draft.
        raw = json.dumps(ledger)
        for key in ('graphSha256', 'criteriaSha256', 'definitionsSha256'):
            if review[key] not in raw:
                raise ValueError(f'{row["domain"]}: missing exact {key} review pin')
    leads = {e['id'] for e in graph['edges'] if 'tensor:investigativeLead' in e.get('extensions', {})}
    cross = json.loads((DIRECTORY / 'items/cross-domain.json').read_text())
    items = cross.get('perCurrentLeadEdge', cross.get('perNewEdge', cross.get('edges', [])))
    if {r['id'] for r in items} != leads or len(items) != len(leads) or any(
            r['verdict'] not in ('accept', 'pass-with-declared-profile-and-evidence-bounds') or not r.get('rationale') for r in items):
        raise ValueError('The separate routing review must cover every current lead exactly once')
    return review['counts']


if __name__ == '__main__':
    print('Exact item review and preserved artifacts verified:', verify())
