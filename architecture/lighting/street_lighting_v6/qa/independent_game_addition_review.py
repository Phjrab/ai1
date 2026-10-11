"""Read-only independent review of current lighting-only game evidence.

No Blender, Node, full world triangle index, or runtime re-execution.
"""
import hashlib
import json
from pathlib import Path
import struct
import time

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'street_lighting_v6'
G = ROOT / 'game_lighting_v6'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def evidence(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path), 'bytes': path.stat().st_size}


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def main():
    started = time.monotonic()
    manifest_path = R / 'contracts/street_lighting_manifest.json'
    report_path = G / 'tests/street-lighting-placement-results.json'
    unit_path = G / 'tests/street-lighting-unit-results.json'
    manifest = json.loads(manifest_path.read_text())
    report = json.loads(report_path.read_text())
    unit = json.loads(unit_path.read_text())
    assert report['status'] == 'PASS_ADDITION_ONLY_LIGHTING_CHECKS' and not report['issues']
    assert unit['status'] == 'PASS_LIGHTWEIGHT_LIGHTING_UNIT' and unit['checks'] == 63
    verified_sources = {}
    for result in [report, unit]:
        for relative, expected in result['sourceSha256'].items():
            actual = sha(G / relative)
            assert actual == expected, relative
            verified_sources[relative] = actual
    assert verified_sources['dist/street-lighting.json'] == sha(manifest_path)
    candidate = json.loads((R / 'qa/fixture_candidate.json').read_text())
    assert candidate['placement_sha256'] == sha(manifest_path)
    assert candidate['sha256'] == sha(R / candidate['file']) == verified_sources['dist/assets/lighting.glb']
    originals = ['world-config.js', 'parking-config.js', 'parking-system.js', 'transit-config.js',
                 'walking-floor.js', 'wheel-suspension.js', 'vehicle-surfaces.js']
    original_hashes = {}
    for name in originals:
        expected, actual = sha(ROOT / 'game_base/dist' / name), sha(G / 'dist' / name)
        assert expected == actual, name
        original_hashes[name] = actual
    excluded = []
    source_count = 0
    positive_source = 0
    for fixture in manifest['fixtures']:
        for index, triangle in enumerate(fixture['ground_patch_triangles']):
            source_count += 1
            ab = [triangle[1][j] - triangle[0][j] for j in range(3)]
            ac = [triangle[2][j] - triangle[0][j] for j in range(3)]
            assert any(cross(ab, ac)), (fixture['id'], index, 'zero source triangle')
            positive_source += 1
            # Reproduce only the documented coordinate serialization; arithmetic
            # after Float32 round-trip uses doubles, matching JS number arithmetic.
            out = [[f32(p[0]), f32(p[2] + .002), f32(-p[1])] for p in triangle]
            a = [out[1][j] - out[0][j] for j in range(3)]
            b = [out[2][j] - out[0][j] for j in range(3)]
            if not any(cross(a, b)):
                excluded.append({'fixtureId': fixture['id'], 'sourceTriangleIndex': index,
                                 'float32Triangle': [x for point in out for x in point]})
    pool = report['poolNormalization']
    assert source_count == pool['sourceTriangles'] == 120333
    assert excluded == pool['excludedExactFloat32Degenerates']
    assert len(excluded) == 60 and pool['renderedTriangles'] == source_count - len(excluded) == 120273
    source = ''.join((G / 'dist/street-lighting.js').read_text().split())
    assert 'side:THREE.DoubleSide' in source and 'depthWrite:false' in source
    assert 'userData.walkable_support=false' in source and 'userData.collision=false' in source
    result = {
        'status': 'PASS_ADDITION_ONLY_EVIDENCE_REVIEW',
        'scope': 'New fixture contract and actual candidate GLB evidence only; no whole campus runtime or browser execution.',
        'source_native_sha256': manifest['source_native_sha256'],
        'placement_sha256': sha(manifest_path),
        'candidate_glb_sha256': candidate['sha256'],
        'fixture_count': len(manifest['fixtures']),
        'recorded_route_counts': report['counts'],
        'recorded_interferences': report['issues'],
        'source_sha256_verified': verified_sources,
        'unchanged_existing_physics_and_world_sha256': original_hashes,
        'independent_pool_serialization': {
            'source_positive_area_triangles': positive_source,
            'exact_zero_after_float32_visual_transform': len(excluded),
            'rendered_positive_triangles': pool['renderedTriangles'],
            'all_exact_exclusion_records_match': True,
            'visual_only_lift_m': .002,
            'excluded_records': excluded,
            'scope': 'The source contract retains all positive-area slivers. Only exactly collapsed draw triangles are omitted; no physical support or ground geometry is altered.'
        },
        'evidence': [evidence(p) for p in [manifest_path, report_path, unit_path, R / 'qa/fixture_candidate.json', R / 'qa/independent_contract_review.json', Path(__file__)]],
        'limitations': ['Candidate fixture GLB is not yet bound to the newly saved/reopened native.',
                        'Route evidence tests only the added finite-height pole/base blockers against existing route records.',
                        'No full Octree/driveStep, actual WebGL, mobile performance, or pixel readability test is claimed.'],
        'elapsed_seconds': time.monotonic() - started,
    }
    target = R / 'qa/independent_game_addition_review.json'
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'fixture_count', 'recorded_route_counts', 'elapsed_seconds']}))


if __name__ == '__main__':
    main()
