#!/usr/bin/env python3
"""Bind a final native file and seal bounded lighting QA; never rerun full QA."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import runpy
import shutil

ROOT = Path(__file__).resolve().parents[1]
V = runpy.run_path(str(ROOT / 'scripts/verify-lighting-release.py'))


def write_json(path, data):
    temporary = path.with_name(path.name + '.lighting-tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def finalize(root, inputs_name, binding_name, native_file, baseline_root=None):
    V['require'](binding_name and native_file,
                 'Explicit --native-binding and --native-file are required; final native is not inferred')
    # Stream the native bytes before archiving anything or replacing any release metadata.
    V['verify_native'](root, binding_name, native_file)
    inputs, baseline, _ = V['load_inputs'](root, inputs_name)
    for name in inputs['changedFiles']:
        preserved = V['local_path'](root, V['ORIGINAL'] + name)
        wanted = baseline['files'][name]
        if preserved.exists():
            V['bind'](root, V['ORIGINAL'] + name, wanted['sha256'])
            continue
        source_root = baseline_root if baseline_root is not None else root
        source = V['bind'](source_root, name, wanted['sha256'])
        preserved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, preserved)
        V['bind'](root, V['ORIGINAL'] + name, wanted['sha256'])
    checked = V['verify'](root, inputs_name, binding_name, native_file=None, finalized=False)
    old = checked['oldIndex']
    lighting = {'revision': 'street_lighting_v6', 'augmentedNativeSha256': checked['binding']['augmentedNativeSha256'],
                'nativeBinding': binding_name, 'nativeBindingSha256': V['sha'](V['local_path'](root, binding_name)),
                'fixtures': checked['fixtures'], 'originalCampusNativeSha256': V['BASE_NATIVE']}
    index = {
        'schema': 2, 'status': 'bounded_lighting_passed_with_preserved_a65_limits',
        'createdUTC': datetime.now(timezone.utc).isoformat(),
        'nativeSourceSha256': V['BASE_NATIVE'], 'rawGLBSha256': old['rawGLBSha256'],
        'exportManifestSha256': old['exportManifestSha256'],
        'lightingRevision': lighting, 'browserWebGLVerified': False, 'iPhoneVerified': False,
        'original362ChecksRerun': False, 'fullSceneRerun': False,
        'baselineValidation': {'path': V['ORIGINAL'] + 'tests/FINAL_VALIDATION.json',
                               'sha256': baseline['files']['tests/FINAL_VALIDATION.json']['sha256']},
        'releaseInputs': inputs_name, 'releaseInputsSha256': V['sha'](V['local_path'](root, inputs_name)),
        'boundedReports': inputs['reports'], 'knownLimits': old['knownLimits'],
        'scope': 'Addition-only street-lighting unit and placement checks on exact current inputs. '
                 'All a65 source/evidence files are unchanged or preserved byte-for-byte. '
                 'The original 362 checks and full-scene suites were not rerun. '
                 'Baseline tyre, shuttle, grounding and browser/device limits remain applicable. '
                 'Unchanged campus/building GLBs retain a65 provenance; the separately bound augmented native adds lighting.',
        'lightingLimits': ['Node checks do not establish browser/WebGL/GPU/iPhone performance or pixel night readability.',
                           'Native lamp spotlights are excluded from the lighting GLB; runtime realtime lamps are capped at four.'],
    }
    release = V['read'](root, V['ORIGINAL'] + 'dist/release-manifest.json')
    release.update({'schema': 2, 'files': checked['runtimeFiles'],
                    'runtimeTreeSha256': checked['runtimeTreeSha256'], 'lightingRevision': lighting})
    paths = [V['local_path'](root, name) for name in sorted(V['GENERATED'])]
    before = {path: path.read_bytes() for path in paths}
    try:
        write_json(root / 'tests/FINAL_VALIDATION.json', index)
        release['validationIndexSha256'] = V['sha'](root / 'tests/FINAL_VALIDATION.json')
        write_json(root / 'dist/release-manifest.json', release)
        V['verify'](root, inputs_name, binding_name)
    except BaseException:
        for path, content in before.items():
            path.write_bytes(content)
        raise
    return {'status': index['status'], 'augmentedNativeSha256': lighting['augmentedNativeSha256'],
            'fixtures': checked['fixtures'], 'validationIndexSha256': release['validationIndexSha256'],
            'releaseManifestSha256': V['sha'](root / 'dist/release-manifest.json'),
            'original362ChecksRerun': False, 'fullSceneRerun': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--inputs', default=V['INPUTS'])
    parser.add_argument('--native-binding')
    parser.add_argument('--native-file', type=Path)
    parser.add_argument('--baseline-root', type=Path, help='Verified immutable a65 source for any missing originals')
    args = parser.parse_args()
    print(json.dumps(finalize(args.root.resolve(), args.inputs, args.native_binding, args.native_file,
                              args.baseline_root.resolve() if args.baseline_root else None)))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise SystemExit('Lighting finalization blocked: ' + str(error))
