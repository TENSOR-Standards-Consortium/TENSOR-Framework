#!/usr/bin/env python3
"""Inventory ID lineage, not semantic equivalence. Never modifies graph artifacts."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
GRAPH = 'drafts/core/tensor.core.graph.json'
STAGES = [
    ('technical-reduction', '221e7d0542df6d51f882f1ab26689084dd976ea9'),
    ('entry-evidence-repair', '0404ca26e3dac628a64739c102a90683698f4ac2'),
    ('positive-evidence-repair', '3f480af9e67b09ac3ac39dfd103cdb0a00fd115f'),
]

def build():
    released_path = 'releases/core/graphs/v0.20260206e/tensor.core.graph.json'
    released_bytes = (ROOT / released_path).read_bytes()
    current_bytes = (ROOT / GRAPH).read_bytes()
    original, current = json.loads(released_bytes), json.loads(current_bytes)
    sources = []
    snapshots = []
    for name, commit in STAGES:
        data = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{commit}:{GRAPH}'])
        graph = json.loads(data)
        snapshots.append({n['id'] for n in graph['nodes']})
        sources.append(dict(stage=name, commit=commit, path=GRAPH, sha256=sha256(data).hexdigest(), version=graph['version'], questions=len(graph['nodes']), routes=len(graph['edges'])))
    active = {n['id']: n for n in current['nodes']}
    review_path = ROOT / 'drafts/core/reviews/2026-10-12-restoration/analysis.json'
    review = json.loads(review_path.read_text()) if review_path.exists() else {}
    # The source-predicate review remains historical. The routing revision does
    # not re-date its approval or pretend its old graph digest pins new edges.
    reviewed = {r['sourceId']: r for r in review.get('questions', [])}
    historical_bytes = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'e6ced17aeaa1cf1d8be31ba1fbd24bf96d0890e0:' + GRAPH]) if current.get('extensions', {}).get('tensor:semanticReview') else current_bytes
    historical = {n['id']: n for n in json.loads(historical_bytes)['nodes']}
    rows = []
    for node in original['nodes']:
        remaining = node['id'] in active
        removed = next((name for (name, _), ids in zip(STAGES, snapshots) if node['id'] not in ids), None)
        disposition = reviewed.get(node['id'], {})
        if disposition and (disposition['sourceText'] != node['text'] or not remaining or disposition['targetText'] != historical[node['id']]['text']):
            raise ValueError(f"{node['id']}: review no longer matches the source and target predicates")
        rows.append(dict(sourceId=node['id'], category=node['category'], archetype=node['archetype'], sourceLabel=node['label'], sourceText=node['text'], lineageStatus='restored-with-evidence-repair' if remaining and removed and disposition else 'same-id-rewritten' if remaining else removed,
            firstRemovedAt=removed, activeId=node['id'] if remaining else None, textChanged=active[node['id']]['text'] != node['text'] if remaining else None, historicalReviewedPredicate=historical[node['id']]['text'] if remaining else None, currentPredicate=active[node['id']]['text'] if remaining else None, currentReviewRef='reviews/2026-10-13-semantic/README.md',
            semanticReview=disposition.get('semanticReview', 'pending'), disposition=disposition.get('disposition'), rationale=disposition.get('meaningChange'),
            applicabilityLimitations=disposition.get('applicabilityLimitations', []), agentReviewRef=disposition.get('agentReviewRef'), sourceFacet=disposition.get('sourceFacet'), assessmentKind=disposition.get('assessmentKind'), issues=disposition.get('issues', []),
            sourceDuplicateIds=disposition.get('sourceDuplicateIds', []), targetDefinitionRefs=disposition.get('targetDefinitionRefs', []), scenarioRefs=disposition.get('scenarioRefs', [])))
    absent = [r for r in rows if r['activeId'] is None]
    originals = {n['id'] for n in original['nodes']}
    added = [n['id'] for n in current['nodes'] if n['id'] not in originals]
    return dict(format='tensor-graph-coverage-inventory', inventoryVersion=3, meaning='Every original ID has an author-reviewed disposition where recorded. Historical author dispositions remain pinned to their reviewed revision. Current item-level AI review is recorded separately in reviews/2026-10-13-semantic; institutional approval, equivalence and universal coverage remain unproved. Duplicate prompts are retained explicitly; no consolidation is approved.', published=dict(path=released_path, version=original['version'], sha256=sha256(released_bytes).hexdigest(), questions=len(original['nodes']), routes=len(original['edges'])), history=sources, working=dict(path=GRAPH, version=current['version'], sha256=sha256(current_bytes).hexdigest(), questions=len(current['nodes']), routes=len(current['edges'])), summary=dict(sameIdRewritten=len(rows)-len(absent), restoredOriginal=sum(r['lineageStatus']=='restored-with-evidence-repair' for r in rows), authorReviewedDispositions=len(reviewed), absentOriginal=len(absent), newQuestions=len(added), approvedSemanticDispositions=0, absentByDomain=dict(sorted(Counter(r['category'] for r in absent).items())), lineage=dict(sorted(Counter(r['lineageStatus'] for r in rows).items()))), originalQuestions=rows, newQuestionIds=added)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'drafts/core/coverage-inventory.json'
    data = json.dumps(build(), indent=2, ensure_ascii=False) + '\n'
    if args.check:
        if output.read_text() != data:
            raise SystemExit('Coverage inventory is stale; regenerate and review its diff.')
        print('Coverage inventory verified against published, historical, and working graph bytes.')
    else:
        output.write_text(data)
        print(f'Wrote {output.relative_to(ROOT)}; independent semantic approval remains pending.')

if __name__ == '__main__':
    main()
