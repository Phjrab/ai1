#!/usr/bin/env python3
"""Restore content-addressed compressed assets using Python's standard library."""
from pathlib import Path
import gzip, hashlib, json, os, tempfile
ROOT = Path(__file__).resolve().parents[1]

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def main():
    manifest = json.loads((ROOT / 'asset-parts/manifest.json').read_text())
    restored = skipped = 0
    for asset in manifest['assets']:
        target = (ROOT / asset['path']).resolve()
        if not target.is_relative_to(ROOT):
            raise ValueError('Unsafe destination: ' + asset['path'])
        if target.exists() and sha256(target.read_bytes()) == asset['sha256']:
            skipped += 1
            continue
        compressed = bytearray()
        for part in asset['parts']:
            path = (ROOT / part['path']).resolve()
            if not path.is_relative_to(ROOT / 'asset-parts'):
                raise ValueError('Unsafe part path')
            data = path.read_bytes()
            if sha256(data) != part['sha256']:
                raise ValueError('Corrupt asset part: ' + part['path'])
            compressed.extend(data)
        data = gzip.decompress(compressed)
        if len(data) != asset['bytes'] or sha256(data) != asset['sha256']:
            raise ValueError('Restored asset hash mismatch: ' + asset['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as f:
            f.write(data)
            tmp = f.name
        os.replace(tmp, target)
        restored += 1
    print(f'Assets verified: {restored} restored, {skipped} already present.')

if __name__ == '__main__':
    main()
