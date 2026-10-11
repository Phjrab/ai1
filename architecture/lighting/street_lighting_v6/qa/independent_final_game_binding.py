"""Bind final lighting-only game evidence to the saved native, without Node."""
from pathlib import Path
import json
import re
from independent_game_addition_review import R, G, ROOT, sha, evidence, f32, cross


def main():
    m = json.loads((R / 'lighting_manifest.json').read_text())
    native_qa = json.loads((R / 'qa/independent_native_binding.json').read_text())
    assert native_qa['status'] == 'PASS_NATIVE_ADDITION_BINDING'
    final_index = json.loads((G / 'tests/FINAL_VALIDATION.json').read_text())
    assert final_index['status'] == 'bounded_lighting_passed_with_preserved_a65_limits'
    rev = final_index['lightingRevision']
    assert rev['augmentedNativeSha256'] == m['augmented_native_sha256'] == native_qa['native_sha256']
    assert rev['fixtures'] == 536 and sha(G / rev['nativeBinding']) == rev['nativeBindingSha256']
    binding = json.loads((G / rev['nativeBinding']).read_text())
    reports = []
    for relative, expected in final_index['boundedReports'].items():
        path = G / relative
        assert sha(path) == expected
        report = json.loads(path.read_text())
        for source, source_sha in report['sourceSha256'].items():
            assert sha(G / source) == source_sha, source
        reports.append(path)
    unit = json.loads((G / 'tests/street-lighting-unit-results.json').read_text())
    place = json.loads((G / 'tests/street-lighting-placement-results.json').read_text())
    assert unit['status'] == 'PASS_LIGHTWEIGHT_LIGHTING_UNIT' and unit['checks'] == 67
    assert place['status'] == 'PASS_ADDITION_ONLY_LIGHTING_CHECKS' and not place['issues']
    assert place['sourceSha256']['dist/street-lighting.json'] == m['placement_sha256']
    assert place['sourceSha256']['dist/assets/lighting.glb'] == m['exports'][0]['sha256']
    options = (G / 'dist/street-lighting-native.js').read_text()
    assert m['augmented_native_sha256'] in options
    match = re.search(r'emitterOffset\s*:\s*Object.freeze\((\[[^\]]+\])\)', options)
    if match is None:
        match = re.search(r'"emitterOffset"\s*:\s*(\[[^\]]+\])', options)
    assert match and json.loads(match.group(1)) == m['native_light_emitter_offset_m']
    source_triangles = 0
    exclusions = []
    for fixture in m['fixtures']:
        for index, triangle in enumerate(fixture['ground_patch_triangles']):
            source_triangles += 1
            ab = [triangle[1][i] - triangle[0][i] for i in range(3)]
            ac = [triangle[2][i] - triangle[0][i] for i in range(3)]
            assert any(cross(ab, ac))
            out = [[f32(p[0]), f32(p[2] + .002), f32(-p[1])] for p in triangle]
            ab = [out[1][i] - out[0][i] for i in range(3)]
            ac = [out[2][i] - out[0][i] for i in range(3)]
            if not any(cross(ab, ac)):
                exclusions.append({'fixtureId': fixture['id'], 'sourceTriangleIndex': index, 'float32Triangle': [v for p in out for v in p]})
    assert source_triangles == 120333 and len(exclusions) == 60
    assert place['poolNormalization'] == {'sourceTriangles': 120333, 'renderedTriangles': 120273, 'excludedExactFloat32Degenerates': exclusions}
    untouched = {}
    for name in ['world-config.js', 'parking-config.js', 'parking-system.js', 'transit-config.js', 'walking-floor.js', 'wheel-suspension.js', 'vehicle-surfaces.js']:
        assert sha(G / 'dist' / name) == sha(ROOT / 'game_base/dist' / name)
        untouched[name] = sha(G / 'dist' / name)
    release = json.loads((G / 'dist/release-manifest.json').read_text())
    assert release['validationIndexSha256'] == sha(G / 'tests/FINAL_VALIDATION.json')
    assert release['lightingRevision'] == rev
    files = [R / 'lighting_manifest.json', R / 'qa/independent_native_binding.json',
             G / 'tests/FINAL_VALIDATION.json', G / 'dist/release-manifest.json', G / rev['nativeBinding'],
             G / 'dist/street-lighting-native.js', *reports, Path(__file__), R / 'qa/independent_game_addition_review.py']
    out = {
        'status': 'PASS_FINAL_ADDITION_ONLY_GAME_BINDING', 'native_sha256': m['augmented_native_sha256'],
        'placement_sha256': m['placement_sha256'], 'final_fixture_glb_sha256': m['exports'][0]['sha256'],
        'unit_checks': 67, 'fixture_count': 536, 'tested_counts': place['counts'], 'interferences': [],
        'native_emitter_offset_m': m['native_light_emitter_offset_m'],
        'independent_pool_float32': {'source_triangles': 120333, 'positive_render_triangles': 120273, 'exact_collapsed_draw_triangles': 60, 'all_exclusion_ids_coordinates_match': True},
        'unchanged_existing_physics_and_world': untouched,
        'evidence': [evidence(p) for p in files],
        'limits': ['Lighting-only route-record interference checks; original full-scene game tests were not rerun.',
                   'Browser/WebGL/GPU/mobile and game pixel readability are unverified.',
                   'All approved a65 tyre, bus animation, turnaround and unverified-step limits remain in the final game validation index.',
                   'Native render review and game archive packaging are separate checks.'],
    }
    (R / 'qa/independent_final_game_binding.json').write_text(json.dumps(out, indent=2) + '\n')
    print(out['status'])


if __name__ == '__main__':
    main()
