#!/usr/bin/env python3
"""Check that the review ZIP contains the exact sibling guides and frozen source."""
import argparse
from pathlib import Path
from zipfile import ZipFile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parents[1] / 'review/2026-10-11.1')
folder = parser.parse_args().package
expected = {p.name: p for p in folder.iterdir() if p.name != 'review-package.zip'}
if not expected or any(not p.is_file() or p.is_symlink() for p in expected.values()):
    raise SystemExit('Review package must contain regular files only')
with ZipFile(folder / 'review-package.zip') as archive:
    names = archive.namelist()
    if len(names) != len(expected) or set(names) != set(expected):
        raise SystemExit('Review ZIP member inventory differs from package')
    for name, source in expected.items():
        if archive.getinfo(name).file_size != source.stat().st_size or archive.read(name) != source.read_bytes():
            raise SystemExit(f'Review ZIP member differs from package: {name}')
print(f'Verified review ZIP: {len(expected)} exact package files')
