#!/usr/bin/env python3
"""Reproduce the public event-profile scenario review without network access."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from event_profiles import ROOT,load_package,evaluate_route


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Optional receipt path; public artifacts are not overwritten')
    args=parser.parse_args()
    graph,criteria,catalog=load_package()
    for path,digest in catalog['inputPins'].items():
        if sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise SystemExit(f'Input pin differs: {path}; rebuild/review the profile package')
    suite=json.loads((ROOT/'drafts/core/event-profiles/scenarios.json').read_text())
    results=[]
    for case in suite['cases']:
        result=evaluate_route(graph,criteria,catalog,case)
        result['passed']=[[r['nodeId'],r['answer']] for r in result['trace']]==case['expectedTrace']
        results.append(result)
    receipt={'format':'tensor-event-profile-evaluation','profileVersion':catalog['version'],
        'graphSha256':catalog['graphSha256'],'cases':len(results),'passed':sum(r['passed'] for r in results),
        'scope':'Author-side supplied-evidence scenarios, not authenticated incidents, institutional approval or Core conformance',
        'results':results}
    if args.output:
        args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(f'{receipt["passed"]}/{receipt["cases"]} event-profile scenarios passed across {len(catalog["profiles"])} profiles')
    if receipt['passed']!=receipt['cases']:raise SystemExit(1)

if __name__=='__main__':main()
