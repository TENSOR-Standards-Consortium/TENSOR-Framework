#!/usr/bin/env python3
"""Package the same current reference dataset used by the website and Lab."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile
from verify_current_review import verify

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'review/current'
def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args])
def sha(data):
    return hashlib.sha256(data).hexdigest()
def source_files(commit):
    names = git('ls-tree','-r','--name-only',commit).decode().splitlines()
    return [name for name in names if not name.startswith('review/current/')]

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', help='Clean committed source to package (default HEAD)')
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
if args.check:
    manifest = verify(OUTPUT)
    # Later commits may contain generated packaging only, never another dataset.
    for pin in manifest['files']:
        raw = (ROOT / pin['path']).read_bytes()
        if len(raw) != pin['bytes'] or sha(raw) != pin['sha256']:
            raise SystemExit(f'Current review source drifted: {pin["path"]}; rebuild the current package')
    if source_files('HEAD') != [p['path'] for p in manifest['files']]:
        raise SystemExit('Current source file inventory changed; rebuild the current package')
    print('Current review package matches the current checkout and dataset')
    raise SystemExit(0)

commit = git('rev-parse',args.source or 'HEAD').decode().strip()
names = source_files(commit)
dataset = json.loads(git('show',f'{commit}:dataset/current.json'))
pins = []
archive_buffer = io.BytesIO()
with tarfile.open(fileobj=archive_buffer, mode='w', format=tarfile.PAX_FORMAT) as tar:
    for name in names:
        raw = git('show',f'{commit}:{name}')
        pin = {'path':name,'bytes':len(raw),'sha256':sha(raw)}
        pins.append(pin)
        info = tarfile.TarInfo(name); info.size=len(raw); info.mode=0o644; info.mtime=0
        tar.addfile(info,io.BytesIO(raw))
archive = gzip.compress(archive_buffer.getvalue(),mtime=0)
manifest = {'format':'tensor-current-review-package','manifestVersion':1,
    'sourceRepository':'https://github.com/TENSOR-Standards-Consortium/TENSOR-Framework','sourceCommit':commit,
    'dataset':{'id':dataset['id'],'graphVersion':dataset['graphVersion'],'counts':dataset['counts'],'path':'dataset/current.json'},
    'scope':'The current public dataset, identical for implementers, visitors and reviewers. Generated review/current packaging is excluded from its own source archive.',
    'archive':{'path':'source.tar.gz','bytes':len(archive),'sha256':sha(archive)},'files':pins}
OUTPUT.mkdir(parents=True,exist_ok=True)
(OUTPUT/'source.tar.gz').write_bytes(archive)
(OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(OUTPUT/'verify-snapshot.py').write_bytes(git('show',f'{commit}:scripts/verify_current_review.py'))
(OUTPUT/'dataset.json').write_bytes(git('show',f'{commit}:dataset/current.json'))
for name in ['README.md','walkthrough.md','review-form.md']:
    raw=git('show',f'{commit}:review/templates/{name}').decode()
    replacements = {'SOURCE_COMMIT':commit,'DATASET_ID':dataset['id'],'GRAPH_VERSION':dataset['graphVersion'], **{name:str(dataset['counts'][key]) for name,key in [('QUESTIONS','questions'),('ROUTES','routes'),('DOMAINS','domains'),('PROFILES','eventProfiles'),('QUALIFIED','qualifiedDefinitions'),('REFERENCE_CASES','referenceCases')]}}
    for key,value in replacements.items():
        raw=raw.replace('{{'+key+'}}',value)
    (OUTPUT/name).write_text(raw)
# Validation evidence is recorded explicitly by the maintainer after execution.
(OUTPUT/'validation.json').write_bytes(git('show',f'{commit}:review/templates/validation.json'))
members=sorted(p for p in OUTPUT.iterdir() if p.is_file() and p.name!='review-package.zip')
with zipfile.ZipFile(OUTPUT/'review-package.zip','w',compression=zipfile.ZIP_DEFLATED) as zipped:
    for file in members:
        item=zipfile.ZipInfo(file.name,date_time=(2026,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED
        item.external_attr=0o100644<<16;zipped.writestr(item,file.read_bytes())
verify(OUTPUT)
print(f'Packaged the current dataset: {len(pins)} source files, {dataset["counts"]["questions"]} questions and {dataset["counts"]["routes"]} routes')
