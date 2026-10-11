#!/usr/bin/env python3
"""Read-only verification of an addition-only lighting release, never a QA rerun."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
BASE_NATIVE = 'a65c2ae19f02c59f655e0c7eedb2482a5c2f6a9c53bb94f2425769dbd4417fbd'
REJECTED_NATIVE = {'3579e68ad78ad6aa24f5379701b420ee8692b161cd3f760f4f5b78411c5889a7',
                   '94fae9cf88c03251d212162d3a2e2d7b4197263f681499a24d9b8697284b4228'}
BASE_MANIFEST = '27414f663cccd838ef84170ead0052b42523bd20a776af23fedf4dab491f2359'
INPUTS = 'revision/lighting-release-inputs.json'
ORIGINAL = 'revision/a65-original/'
GENERATED = {'tests/FINAL_VALIDATION.json', 'dist/release-manifest.json'}
CHANGEABLE = GENERATED | {'dist/game.js', 'dist/index.html', 'dist/style.css',
                         'MODEL_PROVENANCE.json', 'package.json', 'package-lock.json',
                         'tests/simulate.mjs', 'README.md', 'QA.md'}
FORBIDDEN = {'.git', '.openai', '.sites-runtime', 'node_modules', '__pycache__',
             '.cache', '.pytest_cache', '.mypy_cache', 'secrets', 'credentials'}
PRIVATE = {'credentials.json', 'secrets.json', 'token.json', 'tokens.json',
           'id_rsa', 'id_ed25519', '.npmrc', '.pypirc'}
REPORTS = {
    'tests/street-lighting-unit-results.json': 'PASS_LIGHTWEIGHT_LIGHTING_UNIT',
    'tests/street-lighting-placement-results.json': 'PASS_ADDITION_ONLY_LIGHTING_CHECKS',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_path(root, name):
    require(isinstance(name, str) and name and '\\' not in name, 'Invalid package path')
    path = PurePosixPath(name)
    require(not path.is_absolute() and path.as_posix() == name and
            all(part not in {'.', '..'} for part in path.parts), 'Unsafe path: ' + name)
    require(not any(part.lower() in FORBIDDEN or part.lower().startswith('.env') or
                    part.lower() in PRIVATE for part in path.parts), 'Excluded path: ' + name)
    require(path.suffix.lower() not in {'.pem', '.key', '.p12', '.pfx'} and
            not any(part.lower().startswith(('credentials.', 'secrets.', 'token.', 'tokens.'))
                    for part in path.parts), 'Credential/secret path excluded: ' + name)
    require(not any(part.startswith('.') for part in path.parts) or name == '.gitignore',
            'Hidden path: ' + name)
    result = root.joinpath(*path.parts)
    require(not any(root.joinpath(*path.parts[:i]).is_symlink()
                    for i in range(1, len(path.parts) + 1)), 'Symlink forbidden: ' + name)
    require(result.resolve().is_relative_to(root.resolve()), 'Path escapes package: ' + name)
    return result


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def entry(path):
    return {'bytes': path.stat().st_size, 'sha256': sha(path)}


def read(root, name):
    return json.loads(local_path(root, name).read_text(encoding='utf-8'))


def bind(root, name, wanted):
    require(isinstance(wanted, str) and len(wanted) == 64 and
            all(c in '0123456789abcdef' for c in wanted), 'Invalid SHA256: ' + name)
    path = local_path(root, name)
    require(path.is_file() and sha(path) == wanted, 'Hash mismatch or missing file: ' + name)
    return path


def binding_entry(root, record):
    return bind(root, record['path'], record['sha256'])


def load_inputs(root, inputs_name=INPUTS):
    inputs = read(root, inputs_name)
    require(inputs.get('schema') == 1 and inputs.get('baselineSourceManifestSha256') == BASE_MANIFEST,
            'Release inputs must identify the immutable a65 manifest')
    baseline = read(root, 'SOURCE_MANIFEST.json')
    bind(root, 'SOURCE_MANIFEST.json', BASE_MANIFEST)
    require(len(baseline['files']) == 460, 'Recovered a65 baseline must contain 460 entries')
    changed, new = inputs['changedFiles'], inputs['newFiles']
    require(isinstance(changed, list) and isinstance(new, list) and
            len(set(changed)) == len(changed) and len(set(new)) == len(new), 'Duplicate allowlist paths')
    require(set(changed) <= CHANGEABLE and set(changed) <= set(baseline['files']),
            'Changes exceed the bounded lighting revision')
    require(GENERATED <= set(changed), 'Final metadata must be declared as changed files')
    require(not set(new) & (set(baseline['files']) | {'SOURCE_MANIFEST.json'}),
            'New file collides with the baseline')
    require(all(PurePosixPath(name).parts[0] in {'revision', 'dist', 'tests', 'scripts', 'data'}
                for name in new), 'New files must use an explicit source/evidence directory')
    require(inputs_name in new and set(REPORTS) <= set(new), 'Inputs/results absent from explicit new-file allowlist')
    names = set(baseline['files']) | set(new) | {'SOURCE_MANIFEST.json'}
    names |= {ORIGINAL + name for name in changed}
    for name in names:
        local_path(root, name)
    return inputs, baseline, names


def verify_baseline(root, inputs, baseline):
    changed = set(inputs['changedFiles'])
    for name, wanted in baseline['files'].items():
        path = local_path(root, name)
        require(path.is_file(), 'Baseline file removed: ' + name)
        if name in changed:
            old = bind(root, ORIGINAL + name, wanted['sha256'])
            require(old.stat().st_size == wanted['bytes'], 'Original size differs: ' + name)
        else:
            bind(root, name, wanted['sha256'])
            require(path.stat().st_size == wanted['bytes'], 'Baseline size differs: ' + name)
    old_index = read(root, ORIGINAL + 'tests/FINAL_VALIDATION.json')
    require(old_index['nativeSourceSha256'] == BASE_NATIVE, 'Wrong preserved a65 validation')
    return old_index


def reverse_patches(root, inputs, baseline):
    """The patch journal is data only. Never execute a patch, test, or source module."""
    patch_name = inputs.get('gamePatches', 'revision/game-patches.json')
    journal = read(root, patch_name)
    require(journal.get('base') == 'a65c2ae1', 'Patch journal base differs')
    rows = journal['changed_files']
    require(isinstance(rows, list), 'Patch journal files must be a list')
    targets = {name for name in inputs['changedFiles'] if name in
               {'dist/game.js', 'dist/index.html', 'dist/style.css'}}
    require({row['path'] for row in rows} == targets and len(rows) == len(targets),
            'Patch journal must cover each changed game/UI file exactly once')
    for row in rows:
        name = row['path']
        require(row['before_sha256'] == baseline['files'][name]['sha256'], 'Patch baseline differs: ' + name)
        require(sha(local_path(root, name)) == row['after_sha256'], 'Patched source differs: ' + name)
        require(row['preserved'] == ORIGINAL + name, 'Preserved UI/source path differs: ' + name)
        bind(root, row['preserved'], row['before_sha256'])
        if name != 'dist/game.js':
            continue
        text = local_path(root, name).read_bytes().decode('utf-8')
        require(journal['patches'], 'Empty game patch journal')
        for edit in reversed(journal['patches']):
            require(isinstance(edit['before'], str) and isinstance(edit['after'], str) and edit['after'],
                    'Patch needs exact nonempty replacement text')
            require(text.count(edit['after']) == 1, 'Reverse patch is not unique: ' + name)
            text = text.replace(edit['after'], edit['before'], 1)
        require(hashlib.sha256(text.encode('utf-8')).hexdigest() == row['before_sha256'],
                'Reversed game/UI source is not exact a65: ' + name)


def permitted_auxiliary_bytes(name, original):
    """Construct only the two version edits or three lighting harness additions."""
    text = original.decode('utf-8')
    if name == 'package-lock.json':
        package_root = '\n    "": {\n      "name": "chosun-campus-walk",\n      "version": "1.0.0",\n'
        edits = [('\n  "version": "1.0.0",\n', '\n  "version": "1.1.0",\n'),
                 (package_root, package_root.replace('"1.0.0"', '"1.1.0"'))]
        lock = json.loads(text)
        require(lock['version'] == lock['packages']['']['version'] == '1.0.0',
                'Unexpected original lockfile versions')
    elif name == 'tests/simulate.mjs':
        source = "let source=await fs.readFile(path.join(root,'dist/game.js'),'utf8');"
        fetch = "const originalFetch=globalThis.fetch;globalThis.fetch=async(url,...args)=>url==='./street-lighting.json'?{ok:true,json:async()=>JSON.parse(await fs.readFile(path.join(root,'dist/street-lighting.json'),'utf8'))}:originalFetch(url,...args);\n"
        module_import = "source=source.replace(\"'./street-lighting.js'\",`'${moduleURL('dist/street-lighting.js')}'`).replace(\"'./street-lighting-native.js'\",`'${moduleURL('dist/street-lighting-native.js')}'`);"
        edits = [('setPointerCapture(){}}', 'setPointerCapture(){}setAttribute(){}}'),
                 (source, fetch + source + module_import)]
    else:
        raise ValueError('No bounded auxiliary edit is authorized for ' + name)
    for before, after in edits:
        require(text.count(before) == 1, 'Auxiliary edit anchor is not unique: ' + name)
        text = text.replace(before, after, 1)
    return text.encode('utf-8')


def verify_auxiliary_changes(root, inputs, baseline):
    for name in {'package-lock.json', 'tests/simulate.mjs'} & set(inputs['changedFiles']):
        original = bind(root, ORIGINAL + name, baseline['files'][name]['sha256']).read_bytes()
        expected = permitted_auxiliary_bytes(name, original)
        require(local_path(root, name).read_bytes() == expected,
                'Changes exceed exact permitted version/harness additions: ' + name)


def verify_composite_provenance(root, inputs, binding):
    require('MODEL_PROVENANCE.json' in inputs['changedFiles'], 'Composite model provenance must be explicit')
    current = read(root, 'MODEL_PROVENANCE.json')
    original = read(root, ORIGINAL + 'MODEL_PROVENANCE.json')
    revision = current.pop('lightingRevision', None)
    extra_asset = current['assets'].pop('lighting.glb', None)
    require(current == original, 'Original a65 model provenance changed beyond the lighting addition')
    require(extra_asset == {'bytes': local_path(root, 'dist/assets/lighting.glb').stat().st_size,
                           'sha256': binding['lightingGLB']['sha256'],
                           'source_path': 'street_lighting_v6/exports/lighting.glb',
                           'source_native_sha256': binding['augmentedNativeSha256']},
            'New lighting asset provenance differs')
    native_manifest = read(root, binding['nativeManifest']['path'])
    require(revision == {'revision': 'street_lighting_v6', 'originalCampusNativeSha256': BASE_NATIVE,
                         'augmentedNativeSha256': binding['augmentedNativeSha256'],
                         'nativeManifestSha256': binding['nativeManifest']['sha256'],
                         'placementSha256': binding['lightingContract']['sha256'],
                         'lightingGLBSha256': binding['lightingGLB']['sha256'],
                         'emitterOffset': native_manifest['native_light_emitter_offset_m']},
            'Composite lighting provenance differs from native binding')


def verify_results(root, inputs):
    source_hashes = inputs['inputSha256']
    require(isinstance(source_hashes, dict) and source_hashes, 'No current source bindings')
    require(not set(source_hashes) & GENERATED, 'Generated metadata cannot be a pre-final source input')
    for name, wanted in source_hashes.items():
        bind(root, name, wanted)
    essential = {'dist/street-lighting-native.js', 'dist/street-lighting.js', 'dist/street-lighting.json', 'dist/assets/lighting.glb',
                 'dist/game.js', 'dist/index.html', 'dist/style.css', inputs.get('gamePatches', 'revision/game-patches.json'),
                 'scripts/verify-lighting-release.py', 'scripts/finalize-lighting-release.py',
                 'scripts/export-lighting-source.py'}
    require(essential <= set(source_hashes), 'Missing required current source bindings')
    contract = read(root, 'dist/street-lighting.json')
    require(contract.get('schema_version') == 1 and contract.get('revision_id') == 'street_lighting_v6'
            and contract.get('source_native_sha256') == BASE_NATIVE, 'Wrong lighting contract identity')
    fixtures = contract['fixtures']
    require(isinstance(fixtures, list) and fixtures and
            len({f['id'] for f in fixtures}) == len(fixtures), 'Empty or duplicate lighting fixtures')
    records = inputs['reports']
    require(isinstance(records, dict) and set(records) == set(REPORTS), 'Require both bounded lighting results')
    for name, expected_status in REPORTS.items():
        report = json.loads(bind(root, name, records[name]).read_text(encoding='utf-8'))
        require(report.get('status') == expected_status and report.get('browserWebGLVerified') is False,
                'Lighting test failed or claims unverified browser execution: ' + name)
        require(report.get('mobilePerformanceVerified') is False and report.get('pixelNightReadabilityVerified') is False,
                'Unsupported mobile/pixel verification claim: ' + name)
        require(report.get('issues', []) == [], 'Lighting issues remain: ' + name)
        hashes = report.get('sourceSha256')
        require(isinstance(hashes, dict) and hashes, 'Test has no exact source hashes: ' + name)
        require('dist/street-lighting.js' in hashes, 'Test did not bind lighting implementation: ' + name)
        expected_test = 'tests/street-lighting.mjs' if name.endswith('unit-results.json') else 'tests/street-lighting-placement.mjs'
        require(expected_test in hashes, 'Test did not bind its own source: ' + name)
        for path, wanted in hashes.items():
            bind(root, path, wanted)
        if name.endswith('placement-results.json'):
            require({'dist/street-lighting-native.js', 'dist/street-lighting.json', 'dist/assets/lighting.glb', 'dist/game.js'} <= set(hashes),
                    'Placement test lacks actual runtime/asset bindings')
            require(report.get('fixtures') == len(fixtures), 'Test fixture count differs from contract')
            require(report.get('meshes', 0) > 0 and report.get('triangles', 0) > 0,
                    'Placement report contains no actual geometry')
            states = report.get('stateChecks')
            require(isinstance(states, list) and states and all(
                state.get('fixtures') == len(fixtures) and 0 <= state.get('realtimeLights', -1) <= 4
                and 0 < state.get('fixtureBatches', 0) <= 12 for state in states),
                'Placement state/fixture/light bounds differ')
        else:
            require(isinstance(report.get('checks'), int) and report['checks'] > 0 and
                    report.get('maxRealtimeLights') == 4, 'Unit checks or realtime lighting bound differ')
    return contract


def native_options_bytes(manifest_hash, native_hash, offset):
    require(isinstance(offset, list) and len(offset) == 3 and
            all(isinstance(v, (int, float)) and math.isfinite(v) for v in offset),
            'Missing finite native emitter offset')
    options = {'status': 'final_augmented_native_bound', 'emitterOffset': offset,
               'nativeManifestSha256': manifest_hash, 'augmentedNativeSha256': native_hash}
    return ('// Generated from the hash-bound final native lighting manifest.\n'
            'export const STREET_LIGHTING_NATIVE = Object.freeze(' +
            json.dumps(options, separators=(',', ':')) + ');\n').encode('utf-8')


def verify_native(root, binding_name, native_file=None):
    require(binding_name, 'Explicit --native-binding is required; final native is not inferred')
    binding = read(root, binding_name)
    require(binding.get('schema') == 1 and binding.get('status') == 'final_augmented_native_bound',
            'Native binding is not final')
    native = binding['augmentedNativeSha256']
    require(isinstance(native, str) and len(native) == 64 and native != BASE_NATIVE
            and all(c in '0123456789abcdef' for c in native), 'Missing augmented native identity')
    require(native not in REJECTED_NATIVE, 'Rejected read-side-effect native candidate cannot be released')
    require(binding.get('baselineNativeSha256') == BASE_NATIVE, 'Wrong native baseline')
    require(binding['nativeManifest']['path'] == 'revision/lighting-native-manifest.json', 'Wrong native manifest path')
    require(binding['lightingContract']['path'] == 'dist/street-lighting.json' and
            binding['lightingGLB']['path'] == 'dist/assets/lighting.glb', 'Wrong lighting input paths')
    for key in ('nativeManifest', 'lightingContract', 'lightingGLB', 'preservationReport', 'reopenReport'):
        binding_entry(root, binding[key])
    manifest = read(root, binding['nativeManifest']['path'])
    require(manifest.get('status') == 'PASS' and manifest.get('source_native_sha256') == BASE_NATIVE
            and manifest.get('augmented_native_sha256') == native, 'Authoritative native identity/status differs')
    require(local_path(root, 'dist/street-lighting-native.js').read_bytes() ==
            native_options_bytes(binding['nativeManifest']['sha256'], native,
                                 manifest.get('native_light_emitter_offset_m')),
            'Runtime native light options differ from the authoritative manifest')
    require(manifest.get('native_bytes') == binding['nativeBytes'] and binding['nativeBytes'] > 0,
            'Native byte count differs')
    require(manifest.get('placement_sha256') == binding['lightingContract']['sha256'], 'Native/contract hash differs')
    require(manifest.get('preservation_report_sha256') == binding['preservationReport']['sha256'],
            'Native preservation report differs')
    contract = read(root, binding['lightingContract']['path'])
    require(all(manifest.get(key) == value for key, value in contract.items()),
            'Native manifest does not contain the exact bound placement contract')
    preserved = read(root, binding['preservationReport']['path'])
    require(preserved.get('status') == 'PASS' and preserved.get('differences') == [] and
            preserved.get('disallowed_additions') == [] and preserved.get('source_native_bytes') == 'PASS' and
            preserved.get('source_script_bytes') == 'PASS', 'Native preservation was not fully checked or passed')
    require(preserved.get('original_state_sha256') and
            preserved.get('original_state_sha256') == preserved.get('observed_original_state_sha256'),
            'Original native state fingerprint differs')
    require(preserved.get('source_native_sha256') == BASE_NATIVE and
            preserved.get('placement_sha256') == binding['lightingContract']['sha256'] and
            preserved.get('fixture_count') == preserved.get('new_light_count') == len(contract['fixtures']),
            'Native preservation input/count differs')
    reopened = read(root, binding['reopenReport']['path'])
    require(reopened.get('status') == 'PASS' and reopened.get('native_sha256') == native and
            reopened.get('source_native_sha256') == BASE_NATIVE and reopened.get('read_only') is True and
            reopened.get('source_not_saved') is True and reopened.get('differences') == [] and
            reopened.get('disallowed_additions') == [] and
            reopened.get('original_state_sha256') == reopened.get('observed_original_state_sha256') ==
            preserved['original_state_sha256'] and
            reopened.get('original_objects_checked') == preserved['original_object_count'] and
            reopened.get('new_fixtures') == reopened.get('new_lights') == len(contract['fixtures']),
            'Saved final native was not reopened with exact original preservation')
    storage = reopened.get('loaded_native_deform_storage_guard', {})
    require(storage.get('status') == 'PASS' and storage.get('native_deform_storage_bytes') ==
            {'MDeformVert': 0, 'MDeformWeight': 0}, 'Unexpected added deform storage in saved native')
    require(manifest.get('native_spotlights_exported') is False, 'Native spotlights must not be exported')
    exports = [item for item in manifest['exports'] if PurePosixPath(item['file']).name == 'lighting.glb']
    require(len(exports) == 1 and exports[0]['sha256'] == binding['lightingGLB']['sha256']
            and exports[0]['bytes'] == local_path(root, 'dist/assets/lighting.glb').stat().st_size,
            'Native/runtime lighting GLB differs')
    if native_file is not None:
        path = Path(native_file)
        require(path.is_file() and not path.is_symlink(), 'Explicit native file is missing or a symlink')
        require(path.stat().st_size == binding['nativeBytes'] and sha(path) == native,
                'Final augmented native bytes/hash differ')
    return binding


def runtime_files(root, names):
    expected = {name[5:] for name in names if name.startswith('dist/') and name != 'dist/release-manifest.json'}
    actual = {path.relative_to(root / 'dist').as_posix() for path in (root / 'dist').rglob('*')
              if path.is_file() and path.name != 'release-manifest.json'}
    require(actual == expected, 'Runtime files differ from explicit allowlist')
    return {name: entry(local_path(root, 'dist/' + name)) for name in sorted(expected)}


def verify(root=ROOT, inputs_name=INPUTS, binding_name=None, native_file=None, finalized=True):
    # Reject a missing final binding before doing expensive reads or writing anything.
    require(binding_name, 'Explicit --native-binding is required; no FINAL_VALIDATION or ZIP without final native binding')
    binding = verify_native(root, binding_name, native_file)
    inputs, baseline, names = load_inputs(root, inputs_name)
    require(binding_name in names, 'Native binding absent from explicit source allowlist')
    for key in ('nativeManifest', 'preservationReport', 'reopenReport'):
        require(binding[key]['path'] in names, 'Native evidence absent from source allowlist')
    require(set(inputs['inputSha256']) <= names and set(inputs['reports']) <= names,
            'Bound inputs missing from source allowlist')
    required_hashes = (set(inputs['changedFiles']) - GENERATED) | (
        set(inputs['newFiles']) - {inputs_name} - set(REPORTS))
    require(required_hashes <= set(inputs['inputSha256']), 'Changed/new files lack exact source hashes')
    old_index = verify_baseline(root, inputs, baseline)
    reverse_patches(root, inputs, baseline)
    verify_auxiliary_changes(root, inputs, baseline)
    verify_composite_provenance(root, inputs, binding)
    contract = verify_results(root, inputs)
    for name in names:
        require(local_path(root, name).is_file(), 'Allowlisted source is missing: ' + name)
    files = runtime_files(root, names)
    tree = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if finalized:
        index, release = read(root, 'tests/FINAL_VALIDATION.json'), read(root, 'dist/release-manifest.json')
        require(index.get('status') == 'bounded_lighting_passed_with_preserved_a65_limits', 'Lighting release not finalized')
        require(index.get('original362ChecksRerun') is False and index.get('fullSceneRerun') is False,
                'Unsupported full-scene or original-check rerun claim')
        require(index.get('knownLimits') == old_index['knownLimits'], 'Preserved a65 limits changed')
        require(index.get('browserWebGLVerified') is False and index.get('iPhoneVerified') is False,
                'Unsupported browser/device verification claim')
        require(index.get('nativeSourceSha256') == BASE_NATIVE and release.get('nativeSourceSha256') == BASE_NATIVE,
                'Unchanged campus/building provenance was relabeled')
        require(index.get('lightingRevision') == release.get('lightingRevision'), 'Composite identity differs')
        revision = index['lightingRevision']
        require(revision.get('augmentedNativeSha256') == binding['augmentedNativeSha256'] and
                revision.get('nativeBindingSha256') == sha(local_path(root, binding_name)) and
                revision.get('nativeBinding') == binding_name and revision.get('fixtures') == len(contract['fixtures']),
                'Final lighting identity/count differs')
        require(index.get('releaseInputsSha256') == sha(local_path(root, inputs_name)) and
                index.get('boundedReports') == inputs['reports'], 'Final source/results binding differs')
        require(index.get('baselineValidation') == {'path': ORIGINAL + 'tests/FINAL_VALIDATION.json',
                'sha256': baseline['files']['tests/FINAL_VALIDATION.json']['sha256']}, 'Baseline QA binding differs')
        require(release.get('schema') == 2 and release.get('files') == files and
                release.get('runtimeTreeSha256') == tree, 'Schema2 runtime manifest differs')
        require(release.get('validationIndexSha256') == sha(local_path(root, 'tests/FINAL_VALIDATION.json')),
                'Release validation hash differs')
        for field in ('rawGLBSha256', 'exportManifestSha256', 'browserWebGLVerified'):
            old_release = read(root, ORIGINAL + 'dist/release-manifest.json')
            require(release.get(field) == old_release[field], 'Baseline release provenance changed: ' + field)
    return {'inputs': inputs, 'baseline': baseline, 'names': sorted(names), 'binding': binding,
            'oldIndex': old_index, 'fixtures': len(contract['fixtures']), 'runtimeFiles': files,
            'runtimeTreeSha256': tree}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--inputs', default=INPUTS)
    parser.add_argument('--native-binding')
    parser.add_argument('--native-file', type=Path)
    parser.add_argument('--pre-final', action='store_true', help='Verify bound inputs without requiring generated final metadata')
    args = parser.parse_args()
    result = verify(args.root.resolve(), args.inputs, args.native_binding, args.native_file, not args.pre_final)
    print(json.dumps({'status': 'VERIFIED_BOUNDED_LIGHTING_INPUTS' if args.pre_final else 'VERIFIED_BOUNDED_LIGHTING_RELEASE',
                      'baselineFiles': len(result['baseline']['files']), 'fixtures': result['fixtures'],
                      'sourceFiles': len(result['names']), 'original362ChecksRerun': False, 'fullSceneRerun': False}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise SystemExit('Lighting release verification blocked: ' + str(error))
