"""Read-only verification of shipped assets and the exact scoped QA evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_NATIVE = 'a1a2070f1c3c19d7f6f3af0b51af0563e947ba0a7278bc3236890ebbbc3b7e6c'
CURRENT_TESTS = {'export-contract', 'tyre-cache-runtime', 'site-closeout', 'car-grounding', 'parking-turns', 'road-grounding', 'garage-exterior-route', 'parking-clearance', 'realism', 'benchmark-car-grounding'}
BASELINE_TESTS = {'surface-conformity', 'final-repair-paths', 'functional-final', 'vehicle-grounding', 'shuttle-terminal-validation', 'parking-turns', 'road-grounding', 'garage-exterior-route', 'site-additions'}
UNIT_TESTS = {'tyre-footprint', 'tyre-contact-cache', 'bus-suspension-equivalence', 'known-tyre-limits', 'car-wheel-assembly'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_path(root, name):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe package path: ' + str(name))
    result = root / relative
    require(result.resolve().is_relative_to(root.resolve()), 'Path escapes package: ' + str(name))
    require(not any((root / Path(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)), 'Symlink in package evidence: ' + str(name))
    return result


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()



def verify_acceptance(root, bind=None):
    if bind is None:
        def bind(name, wanted):
            path = local_path(root, name)
            require(sha(path) == wanted, 'Acceptance evidence hash differs: ' + name)
            return path
    supplement_path = 'tests/site-closeout-acceptance-results.json'
    supplement = json.loads(local_path(root, supplement_path).read_text())
    revision = supplement['allowedInputRevision']
    require(revision['status'] == 'authorized_exact_measured_bounds_only' and revision['file'] == 'data/known-tyre-contact-limits.json' and revision['preservedBefore'] == 'tests/closeout-evidence/known-limit-adjustment/known-limits-before.json', 'Unexpected acceptance revision scope')
    change_path = 'tests/closeout-evidence/known-limit-adjustment/change.json'
    require(json.loads(local_path(root, change_path).read_text()) == revision, 'Acceptance change record differs')
    before = json.loads(bind(revision['preservedBefore'], revision['beforeSha256']).read_text())
    after = json.loads(bind(revision['file'], revision['afterSha256']).read_text())
    expected_changes = {
        '421_front_to_middle_forward': (0.044424644726126616, 0.04444425121070883),
        '421_front_to_middle_reverse': (0.03942113524487989, 0.03960638307697251),
    }
    require(len(revision['changes']) == 2 and {item['route'] for item in revision['changes']} == set(expected_changes), 'Exactly two approved routes are required')
    for change in revision['changes']:
        old, new = expected_changes[change['route']]
        require(change['field'] == 'maximumRadialOverlapMeters' and change['before'] == old and change['after'] == new, 'Unapproved contact bound revision')
        require(abs(change['deltaMeters'] - (new - old)) < 1e-15, 'Contact-bound delta differs')
        require(before['routes'][change['route']][change['field']] == old, 'Original contact bound differs')
        before['routes'][change['route']][change['field']] = new
    require(before == after, 'Fields beyond the two approved contact bounds changed')
    required_inputs = {change_path, revision['file'], revision['preservedBefore'], 'tests/runtime-runs/site-closeout.json', 'tests/runtime-runs/site-closeout-results/site-closeout-results.json', 'tests/helpers/known-tyre-limits.mjs', 'scripts/reassess-site-known-limits.mjs', 'dist/game.js', 'dist/wheel-suspension.js'}
    require(set(supplement['inputSha256']) == required_inputs, 'Acceptance evidence inputs differ')
    for name, wanted in supplement['inputSha256'].items():
        bind(name, wanted)
    require(supplement['sourceRun'] == 'tests/runtime-runs/site-closeout.json' and supplement['sourceResults'] == 'tests/runtime-runs/site-closeout-results/site-closeout-results.json', 'Acceptance source paths differ')
    report = json.loads(local_path(root, supplement['sourceRun']).read_text())
    original = json.loads(local_path(root, supplement['sourceResults']).read_text())
    require(report['status'] == 'failed' and report['exitCode'] == 1 and not report['changedInputFiles'] and original['passed'] is False and supplement['strictOriginalPassed'] is False, 'Strict original failure was not preserved')
    require(report['inputSha256'][revision['file']] == revision['beforeSha256'], 'Strict run did not use the original bounds')
    bind(supplement['sourceResults'], report['resultSnapshots'][supplement['sourceResults']])
    require(report['nativeSourceSha256'] == supplement['nativeSourceSha256'] and report['rawGLBSha256'] == supplement['rawGLBSha256'], 'Acceptance native/export bindings differ')
    require({row['id'] for row in original['results'] if not row['pass']} == set(expected_changes), 'Original failure set exceeds two approved depths')
    require(supplement['passed'] is True and len(original['results']) == len(supplement['results']) == 20, 'Acceptance must contain the same twenty actual results')
    mutable = {'pass', 'knownContactAssessment', 'unresolvedHits'}
    for old, new in zip(original['results'], supplement['results']):
        require({k: v for k, v in old.items() if k not in mutable} == {k: v for k, v in new.items() if k not in mutable}, 'Acceptance changed recorded geometry, poses, contacts or movement')
        require(new['pass'] is True, 'Reassessed route did not pass')
        if 'hits' in old:
            require(new['complete'] and new['verticalError'] < .25 and not new['wheelSupportFailures'] and not new['unresolvedHits'] and new['knownContactAssessment']['accepted'], 'Acceptance hid a traversal/body/support failure')
        else:
            require(old['pass'] is True, 'Unrelated original failure was changed')
    return supplement, revision



def verify_tyre_source_change(root, entry, bind=None):
    if bind is None:
        def bind(name, wanted):
            path = local_path(root, name)
            require(sha(path) == wanted, 'Tyre source history differs: ' + name)
            return path
    require(entry['path'] == 'tests/closeout-evidence/tyre-footprint/source-change.json', 'Unexpected tyre source-change record')
    change = json.loads(bind(entry['path'], entry['sha256']).read_text())
    require(len(change['changes']) == 2 and {row['file'] for row in change['changes']} == {'dist/game.js', 'dist/wheel-suspension.js'}, 'Tyre source history must bind the two changed runtime files')
    for row in change['changes']:
        name = Path(row['file']).name
        require(row['preserved'] == 'tests/source-history/pre-tyre-footprint/' + name, 'Unexpected preserved pre-tyre source')
        bind(row['preserved'], row['before'])
        bind('tests/source-history/tyre-footprint-uncached/' + name, row['uncached_footprint_sha256'])
        bind(row['file'], row['after'])
    baseline = json.loads(local_path(root, 'tests/BASELINE_EVIDENCE.json').read_text())
    by_file = {row['file']: row for row in change['changes']}
    for run in baseline['runs']:
        for revision in run['sourceRevisions']:
            if revision['input'] == 'dist/game.js':
                require(revision['subsequentSourceSha256'] == by_file['dist/game.js']['before'], 'Baseline-to-pre-tyre game source link differs')
    require(baseline['preservedCodeInputs']['dist/wheel-suspension.js']['sha256'] == by_file['dist/wheel-suspension.js']['before'], 'Baseline-to-pre-tyre wheel source link differs')
    return change



def verify_realism_acceptance(root, entry, bind=None):
    if bind is None:
        def bind(name, wanted):
            path = local_path(root, name)
            require(sha(path) == wanted, 'Realism acceptance hash differs: ' + name)
            return path
    require(entry['path'] == 'tests/realism-acceptance-results.json', 'Unexpected realism acceptance supplement')
    accepted = json.loads(bind(entry['path'], entry['sha256']).read_text())
    require(accepted['sourceRun'] == 'tests/runtime-runs/realism.json' and accepted['sourceResults'] == 'tests/runtime-runs/realism-results/realism-results.json', 'Realism acceptance source differs')
    required_inputs = {accepted['sourceRun'], accepted['sourceResults'], 'data/greenery-infill.json', 'data/native-export-manifest.json', 'data/native-export-campus-inventory.json', 'dist/assets/campus.glb', 'dist/game.js', 'tests/realism.mjs', 'scripts/reassess-realism-tree-grounding.py'}
    require(set(accepted['inputSha256']) == required_inputs, 'Realism acceptance input bindings differ')
    for name, wanted in accepted['inputSha256'].items():
        bind(name, wanted)
    # Import only after hash verification; validate(execute=False) performs no Node run or writes.
    recomputed = __import__('runpy').run_path(str(local_path(root, 'scripts/reassess-realism-tree-grounding.py')))['validate'](root, execute=False)
    require(recomputed == accepted, 'Saved realism classification differs from read-only recomputation')
    require(accepted['passed'] is True and accepted['strictOriginalPassed'] is False and accepted['acceptedCount'] == len(accepted['acceptedFailures']) == 106, 'Realism must retain exactly 106 classified original failures')
    require(accepted['maximumSignedDepthErrorMeters'] <= .0001, 'Realism planting depth error exceeds 0.1 mm')
    report = json.loads(local_path(root, accepted['sourceRun']).read_text())
    original = json.loads(local_path(root, accepted['sourceResults']).read_text())
    require(report['status'] == 'failed' and report['exitCode'] == 1 and not report['changedInputFiles'] and original['passed'] is False, 'Strict realism failure was not preserved')
    require(original['treeExport']['sourceProxyRoots'] == original['treeExport']['actualProxyRoots'] == 2214, 'Native/exported tree-root counts differ')
    require(len(original['failures']) == 106 and len({row['name'] for row in original['failures']}) == 106, 'Original realism failure identities differ')
    require(report['nativeSourceSha256'] == accepted['nativeSourceSha256'] and report['rawGLBSha256'] == accepted['rawGLBSha256'], 'Realism acceptance model bindings differ')
    independent_entry = entry['independentClassification']
    require(independent_entry['path'] == 'tests/closeout-evidence/tree-root-classification/final_a65c2ae1_tree_root_classification.json', 'Unexpected independent tree classification')
    independent = json.loads(bind(independent_entry['path'], independent_entry['sha256']).read_text())
    require(independent['status'] == 'PASS_CLASSIFIED_INTENTIONAL_ROOT_EMBEDDING' and independent['native_sha256'] == accepted['nativeSourceSha256'], 'Independent classification native/status differs')
    require(independent['summary']['classified_roots'] == len(independent['rows']) == 106 and independent['summary']['all_native_foliage_roots'] == 2214 and independent['summary']['positive_floating_gaps'] == 0, 'Independent tree classification scope differs')
    expected = {row['name']: row for row in independent['rows']}
    require(len(expected) == 106 and set(expected) == {row['name'] for row in accepted['acceptedFailures']}, 'Independent classification tree identities differ')
    for row in accepted['acceptedFailures']:
        prior = expected[row['name']]
        require(prior['classification'] == 'INTENTIONAL_SOURCE_BOUND_SLOPE_ROOT_EMBEDDING' and prior['actual_gap_m'] == row['actualSignedGapMeters'] and prior['expected_center_gap_m'] == -row['contractEmbedCenterMeters'] and prior['expected_actual_gap_difference_m'] == row['signedDepthErrorMeters'], 'Independent tree depth evidence differs')
    return accepted


def verify(root=ROOT):
    checked = {}

    def bind(name, wanted):
        path = local_path(root, name)
        if name not in checked:
            checked[name] = sha(path)
        require(checked[name] == wanted, 'Hash mismatch: ' + name)
        return path

    def read(name):
        return json.loads(local_path(root, name).read_text())

    index = read('tests/FINAL_VALIDATION.json')
    release = read('dist/release-manifest.json')
    require(index['status'] == 'passed_with_documented_limits', 'Release validation is incomplete')
    bind('tests/FINAL_VALIDATION.json', release['validationIndexSha256'])
    require(index['browserWebGLVerified'] is False and index['iPhoneVerified'] is False and release['browserWebGLVerified'] is False, 'Unsupported browser/device verification claim')
    require(index['nativeSourceSha256'] == release['nativeSourceSha256'], 'Release native mismatch')
    bind('data/native-export-manifest.json', index['exportManifestSha256'])
    bind('MODEL_PROVENANCE.json', index['modelProvenanceSha256'])
    bind('tests/BASELINE_EVIDENCE.json', index['baselineEvidenceSha256'])
    bind('tests/SITE_FAILURE_RESOLUTION.json', index['siteFailureResolutionSha256'])
    bind(index['modelDelta']['path'], index['modelDelta']['sha256'])
    manifest = read('data/native-export-manifest.json')
    raw = {Path(item['file']).name: item['sha256'] for item in manifest['exports']}
    require(manifest['source_sha256'] == index['nativeSourceSha256'], 'Export native mismatch')
    require(raw == index['rawGLBSha256'] == release['rawGLBSha256'], 'Raw export bindings differ')
    require(release['exportManifestSha256'] == index['exportManifestSha256'], 'Release export manifest differs')
    runtime_names = {p.relative_to(root / 'dist').as_posix() for p in (root / 'dist').rglob('*') if p.is_file() and p.name != 'release-manifest.json'}
    require(runtime_names == set(release['files']), 'Runtime file set differs from release manifest')
    for name, entry in release['files'].items():
        path = bind('dist/' + name, entry['sha256'])
        require(path.stat().st_size == entry['bytes'], 'Runtime byte count differs: ' + name)
    tree = hashlib.sha256(json.dumps(release['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    require(tree == release['runtimeTreeSha256'], 'Runtime tree digest differs')
    provenance = read('MODEL_PROVENANCE.json')
    require(provenance['native_scene']['sha256'] == index['nativeSourceSha256'], 'Provenance native mismatch')
    for name, entry in provenance['runtime_game_code'].items():
        path = bind('dist/' + name, entry['sha256'])
        require(path.stat().st_size == entry['bytes'], 'Provenance code byte count differs: ' + name)
    for name, entry in provenance['assets'].items():
        bind('dist/assets/' + name, entry['sha256'])

    verify_tyre_source_change(root, index['tyreContactSourceChange'], bind)

    canonical_entry = index['canonicalGeometryPreservation']
    canonical_path = bind(canonical_entry['path'], canonical_entry['sha256'])
    canonical = json.loads(canonical_path.read_text())
    require(canonical['status'] == 'PASS' and not canonical['differences'], 'Canonical physical preservation failed')
    require(canonical['native_sha256'] == index['nativeSourceSha256'] and canonical['predecessor_native_sha256'] == OLD_NATIVE, 'Canonical native mismatch')
    for item in canonical['evidence']:
        bind((Path(canonical_entry['path']).parent / Path(item['path']).name).as_posix(), item['sha256'])

    acceptance_entry = index['siteCloseoutAcceptance']
    bind(acceptance_entry['path'], acceptance_entry['sha256'])
    require(acceptance_entry['path'] == 'tests/site-closeout-acceptance-results.json', 'Unexpected acceptance supplement')
    acceptance, revision = verify_acceptance(root, bind)
    require(acceptance['nativeSourceSha256'] == index['nativeSourceSha256'] and acceptance['rawGLBSha256'] == raw, 'Acceptance model is not final')

    realism_entry = index['realismAcceptance']
    realism_acceptance = verify_realism_acceptance(root, realism_entry, bind)
    require(realism_acceptance['nativeSourceSha256'] == index['nativeSourceSha256'] and realism_acceptance['rawGLBSha256'] == raw, 'Realism acceptance model is not final')

    rows = index['requiredReports'] + index.get('diagnosticReports', [])
    current = [row for row in rows if row['role'] == 'executed_on_final_model_and_game']
    require(len(current) == len(CURRENT_TESTS) and {row['test'] for row in current} == CURRENT_TESTS, 'Ten required current suites are not present exactly once')
    base = read('tests/BASELINE_EVIDENCE.json')
    require(len(base['runs']) == len(BASELINE_TESTS) and {row['test'] for row in base['runs']} == BASELINE_TESTS, 'Required baseline suites differ')
    indexed_baselines = [row for row in rows if row['role'] != 'executed_on_final_model_and_game']
    require(len(indexed_baselines) == len(BASELINE_TESTS) and {row['test'] for row in indexed_baselines} == BASELINE_TESTS, 'Baseline evidence omitted or duplicated in final index')
    for row in rows:
        report = json.loads(bind(row['report'], row['sha256']).read_text())
        expected_test = ('scripts/' if row['test'] == 'benchmark-car-grounding' else 'tests/') + row['test'] + '.mjs'
        require(report['test'] == expected_test, 'Report test identity differs: ' + row['test'])
        require(report['resultSnapshots'] == row['resultSnapshots'], 'Indexed snapshots differ: ' + row['test'])
        archive = Path(row.get('archiveRoot', '.'))
        for name, wanted in {**report['resultSnapshots'], report['log']: report['logSha256']}.items():
            bind((archive / name).as_posix(), wanted)
        if row in current:
            if row['test'] == 'site-closeout':
                require(row['acceptanceSupplement'] == acceptance_entry and report['status'] == 'failed', 'Strict site report needs its exact acceptance supplement')
            elif row['test'] == 'realism':
                require(row['acceptanceSupplement'] == realism_entry and report['status'] == 'failed', 'Strict realism report needs its exact classification supplement')
            else:
                require(report['status'] == 'passed' and report['exitCode'] == 0, 'Current suite did not pass: ' + row['test'])
            require(not report['changedInputFiles'], 'Inputs changed during execution: ' + row['test'])
            require(report['nativeSourceSha256'] == row['executionNativeSha256'] == index['nativeSourceSha256'] and report['rawGLBSha256'] == raw, 'Current suite model binding differs: ' + row['test'])
            require(report['inputSha256'] and report['resultSnapshots'], 'Current suite evidence is empty: ' + row['test'])
            if row['test'] == 'benchmark-car-grounding':
                require('scripts/benchmark-car-grounding.mjs' in report['inputSha256'], 'Benchmark source is not hash-bound')
            applied = []
            for name, wanted in report['inputSha256'].items():
                if row['test'] in {'site-closeout', 'tyre-cache-runtime', 'export-contract'} and name == revision['file'] and wanted == revision['beforeSha256']:
                    bind(name, revision['afterSha256'])
                    applied.append(name)
                else:
                    bind(name, wanted)
            require(row.get('acceptedInputRevisions', []) == applied, 'Current suite input exception differs')
        else:
            original = next(item for item in base['runs'] if item['test'] == row['test'])
            require(row['report'] == original['report'] and row['sha256'] == original['reportSha256'] and row['archiveRoot'] == original['archiveRoot'], 'Baseline archive binding differs: ' + row['test'])
            require(report['nativeSourceSha256'] == row['executionNativeSha256'] == OLD_NATIVE, 'Baseline was relabeled as current')
            expected_status = 'failed' if row['test'] == 'site-additions' else 'passed'
            require(report['status'] == original['originalStatus'] == expected_status and not report['changedInputFiles'], 'Original baseline status differs')
            require(row['sourceRevisions'] == original['sourceRevisions'], 'Baseline source revisions differ')
            for source_revision in row['sourceRevisions']:
                require(report['inputSha256'][source_revision['input']] == source_revision['originalSha256'], 'Original source revision binding differs')
                bind(source_revision['preservedSource'], source_revision['originalSha256'])
    for entry in base['preservedCodeInputs'].values():
        bind(entry['path'], entry['sha256'])

    unit_entry = index['tyreContactUnitEvidence']
    unit = json.loads(bind(unit_entry['path'], unit_entry['sha256']).read_text())
    require(unit['passed'] is True and len(unit['runs']) == len(UNIT_TESTS), 'Unit evidence is incomplete')
    require({tuple(run['command']) for run in unit['runs']} == {('node', 'tests/' + name + '.mjs') for name in UNIT_TESTS}, 'Required unit suites differ')
    require(all(run['returncode'] == 0 for run in unit['runs']), 'Unit suite failure')
    required_unit_inputs = {'dist/game.js', 'dist/wheel-suspension.js', 'tests/helpers/known-tyre-limits.mjs', 'data/known-tyre-contact-limits.json', 'tests/source-history/pre-tyre-footprint/game.js', 'tests/source-history/pre-tyre-footprint/wheel-suspension.js'} | {'tests/' + name + '.mjs' for name in UNIT_TESTS}
    require(required_unit_inputs <= set(unit['inputs']), 'Required unit input bindings are missing')
    for name, wanted in unit['inputs'].items():
        bind(name, wanted)

    historical = index['historicalFullWalk']
    require(historical == base['historicalFullWalk'], 'Historical full-walk binding differs')
    for name, wanted in historical['artifacts'].items():
        bind(name, wanted)
    original = read(historical['report'])
    result = read(historical['result'])
    require(original['status'] == 'failed' and original['nativeSourceSha256'] == historical['nativeSourceSha256'], 'Historical run was relabeled')
    require(result['scope']['partial'] is False and result['pathCount'] == historical['paths'] == 142, 'Historical full-walk scope differs')
    walks = [row for row in result['results'] if row.get('type') in ('walk_forward', 'walk_reverse')]
    require(len(walks) == historical['directions'] == 284 and sum(row['pass'] is True for row in walks) == historical['passes'] == 281, 'Historical walk counts differ')
    require(historical['originalFailures'] == 3 and original['recordedRuntimeInputSha256'], 'Historical failures/input hashes missing')
    require(historical['originalLog']['status'] == 'unavailable_original_raw_log' and historical['originalLog']['sha256'] == original['logSha256'], 'Historical missing-log limitation differs')
    for name, wanted in original['resultSnapshots'].items():
        bind((Path(historical['archiveRoot']) / name).as_posix(), wanted)

    resolution = read('tests/SITE_FAILURE_RESOLUTION.json')
    require(resolution['status'] == 'all17_required_behaviors_closed_with_documented_limits' and resolution['finalNativeSha256'] == index['nativeSourceSha256'], 'Site failure closure is incomplete')
    require(resolution['acceptanceSupplement'] == acceptance_entry, 'Site resolution acceptance differs')
    bind(resolution['originalResult']['path'], resolution['originalResult']['sha256'])
    for entry in resolution['evidenceFiles']:
        bind(entry['path'], entry['sha256'])
    require(len(resolution['records']) == 17 and all(row['status'] == 'closed_by_final_required_behavior_with_explicit_limits' for row in resolution['records']), 'Site failure count/status differs')
    return {'currentSuites': len(current), 'baselineSuites': len(base['runs']), 'unitSuites': len(unit['runs']), 'historicalWalkDirections': len(walks), 'checkedFiles': len(checked)}


if __name__ == '__main__':
    result = verify()
    print('PASS: exact runtime, ten current suites (strict site and realism results retained with exact bounded reassessments), archived baseline reports/results/logs, five unit suites, and historical full-walk results are intact. Historical raw walk log is unavailable; preserved wrapper and this limit are explicit. Browser/WebGL remains unverified.')
    print(json.dumps(result, sort_keys=True))
