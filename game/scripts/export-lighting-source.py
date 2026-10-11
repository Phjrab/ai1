#!/usr/bin/env python3
"""Export only the explicit a65-plus-lighting allowlist after final native binding."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
V = runpy.run_path(str(ROOT / 'scripts/verify-lighting-release.py'))
PREFIX = 'Chosun_Campus_Walk/'
MANIFEST = 'LIGHTING_SOURCE_MANIFEST.json'


def put(archive, name, data):
    info = zipfile.ZipInfo(PREFIX + name, date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)


def export(root, output, inputs_name, binding_name, native_file=None):
    V['require'](binding_name, 'Explicit --native-binding is required; no ZIP before final native binding')
    output = output.resolve()
    V['require'](not output.is_relative_to(root.resolve()), 'ZIP output must be outside the source directory')
    V['require'](not output.exists(), 'Refusing to overwrite an existing output archive')
    checked = V['verify'](root, inputs_name, binding_name, native_file)
    names = checked['names']
    V['require'](MANIFEST not in names, 'Generated source manifest may not appear in the input allowlist')
    # No directory crawl: only the baseline + explicit changed/new files + their preserved originals.
    records = {name: V['entry'](V['local_path'](root, name)) for name in names}
    manifest = {'format': 1, 'revision': 'street_lighting_v6', 'baselineSourceManifestSha256': V['BASE_MANIFEST'],
                'augmentedNativeSha256': checked['binding']['augmentedNativeSha256'],
                'nativeBinding': binding_name, 'nativeBindingSha256': records[binding_name]['sha256'],
                'files': records}
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(prefix='.lighting-export-', suffix='.zip', dir=output.parent, delete=False)
    temporary = Path(handle.name)
    handle.close()
    try:
        with zipfile.ZipFile(temporary, 'w') as archive:
            for name, expected in records.items():
                content = V['local_path'](root, name).read_bytes()
                V['require'](len(content) == expected['bytes'] and hashlib.sha256(content).hexdigest() == expected['sha256'],
                             'Source changed during export: ' + name)
                put(archive, name, content)
            put(archive, MANIFEST, manifest_bytes)
        with zipfile.ZipFile(temporary) as archive:
            V['require'](archive.testzip() is None, 'ZIP CRC verification failed')
            expected_names = {PREFIX + name for name in records} | {PREFIX + MANIFEST}
            V['require'](set(archive.namelist()) == expected_names and len(archive.infolist()) == len(expected_names),
                         'ZIP file set differs or has duplicate entries')
            for name, expected in records.items():
                with archive.open(PREFIX + name) as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                V['require'](digest == expected['sha256'] and archive.getinfo(PREFIX + name).file_size == expected['bytes'],
                             'ZIP source hash/size differs: ' + name)
            V['require'](archive.read(PREFIX + MANIFEST) == manifest_bytes, 'ZIP manifest differs')
        V['require'](not output.exists(), 'Output appeared during export; refusing to overwrite')
        # Link creation is exclusive, so a concurrently appearing output is never replaced.
        import os
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {'archive': str(output), 'files': len(records) + 1, 'bytes': output.stat().st_size,
            'sha256': V['sha'](output), 'crcVerified': True,
            'augmentedNativeSha256': checked['binding']['augmentedNativeSha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, nargs='?', default=ROOT.parent / 'Chosun_Campus_Walk_Lighting_Source.zip')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--inputs', default=V['INPUTS'])
    parser.add_argument('--native-binding')
    parser.add_argument('--native-file', type=Path, help='Optionally recheck the external native bytes during export')
    args = parser.parse_args()
    print(json.dumps(export(args.root.resolve(), args.output, args.inputs, args.native_binding, args.native_file)))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as error:
        raise SystemExit('Lighting source export blocked: ' + str(error))
