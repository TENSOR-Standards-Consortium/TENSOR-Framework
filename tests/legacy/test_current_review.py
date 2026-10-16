"""Review downloads must identify the same exact current dataset as their source."""
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('current_review_verifier', Path(__file__).resolve().parents[2] / 'scripts/verify_current_review.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CurrentReviewIntegrityTests(unittest.TestCase):
    def fixture(self, folder, bad_graph_pin=False, missing_dataset=False, duplicate=False, unsafe=False):
        graph = b'{"nodes":[],"edges":[]}'
        digest = lambda raw: hashlib.sha256(raw).hexdigest()
        dataset = {'id':'urn:example:current','counts':{'questions':0,'routes':0},'files':[
            {'source':'graph.json','bytes':len(graph),'sha256':'0'*64 if bad_graph_pin else digest(graph)}]}
        data = json.dumps(dataset).encode()
        files = [('graph.json',graph)]
        if not missing_dataset:
            files.append(('dataset/current.json',data))
        if unsafe:
            files.append(('../outside',b'not allowed'))
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer,mode='w') as tar:
            for name,raw in files + ([files[0]] if duplicate else []):
                member=tarfile.TarInfo(name);member.size=len(raw);tar.addfile(member,io.BytesIO(raw))
        archive=gzip.compress(buffer.getvalue(),mtime=0)
        manifest={'format':'tensor-current-review-package','manifestVersion':1,'sourceCommit':'a'*40,
            'dataset':{'id':dataset['id'],'counts':dataset['counts']},
            'archive':{'path':'source.tar.gz','bytes':len(archive),'sha256':digest(archive)},
            'files':[{'path':name,'bytes':len(raw),'sha256':digest(raw)} for name,raw in files]}
        (folder/'manifest.json').write_text(json.dumps(manifest))
        (folder/'dataset.json').write_bytes(data)
        (folder/'source.tar.gz').write_bytes(archive)
        return files

    def test_same_dataset_verifies_in_archive_and_extracted_source(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);files=self.fixture(folder);source=folder/'source';source.mkdir()
            for name,raw in files:
                target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            module.verify(folder,source)
            (source/'graph.json').write_bytes(b'changed graph')
            with self.assertRaisesRegex(ValueError,'Byte pin differs'):
                module.verify(folder,source)

    def test_an_alternate_downloaded_dataset_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);self.fixture(folder);(folder/'dataset.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'dataset.json'):
                module.verify(folder)

    def test_dataset_cannot_pin_another_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);self.fixture(folder,bad_graph_pin=True)
            with self.assertRaisesRegex(ValueError,'Dataset source pin differs'):
                module.verify(folder)

    def test_missing_current_dataset_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);self.fixture(folder,missing_dataset=True)
            with self.assertRaisesRegex(ValueError,'Current dataset is missing'):
                module.verify(folder)

    def test_duplicate_source_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);self.fixture(folder,duplicate=True)
            with self.assertRaisesRegex(ValueError,'Unexpected source member'):
                module.verify(folder)

    def test_source_paths_cannot_escape_the_package(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);self.fixture(folder,unsafe=True)
            with self.assertRaisesRegex(ValueError,'Unsafe source path'):
                module.verify(folder)
