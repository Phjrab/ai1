#!/usr/bin/env python3
"""Verify game assets; recover only missing matching assets, never overwrite edits."""
from pathlib import Path
import gzip
import hashlib
import json
import os
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    expected = json.loads((ROOT / 'MODEL_PROVENANCE.json').read_text())['assets']
    manifest_path = ROOT.parent / 'asset-parts/manifest.json'
    packed = json.loads(manifest_path.read_text())['assets'] if manifest_path.exists() else []
    packed = {entry['path']: entry for entry in packed}
    restored = 0
    for name, metadata in expected.items():
        path = ROOT / 'dist/assets' / name
        if not path.exists():
            entry = packed.get('game/dist/assets/' + name)
            if not entry or entry['sha256'] != metadata['sha256']:
                raise SystemExit(f'Missing current game asset: {name}. Restore this revision’s asset package; no local files were overwritten.')
            compressed = bytearray()
            for part in entry['parts']:
                source = (ROOT.parent / part['path']).resolve()
                if not source.is_relative_to((ROOT.parent / 'asset-parts').resolve()):
                    raise ValueError('Unsafe asset part path')
                data = source.read_bytes()
                if digest(data) != part['sha256']:
                    raise ValueError('Corrupt asset part: ' + part['path'])
                compressed.extend(data)
            data = gzip.decompress(compressed)
            if len(data) != metadata['bytes'] or digest(data) != metadata['sha256']:
                raise ValueError('Restored asset hash mismatch: ' + name)
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
                file.write(data)
                temporary = file.name
            os.replace(temporary, path)
            restored += 1
        data = path.read_bytes()
        if len(data) != metadata['bytes'] or digest(data) != metadata['sha256']:
            raise SystemExit(f'Current asset differs from MODEL_PROVENANCE.json: {name}. If this is an intended model update, record its provenance before testing. Nothing was overwritten.')
    print(f'Game assets verified: {len(expected)} total; {restored} missing assets restored.')

if __name__ == '__main__':
    main()
