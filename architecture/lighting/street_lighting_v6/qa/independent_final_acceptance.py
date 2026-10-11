"""Close only this recovered lighting revision's native/game/three-view scope."""
import hashlib
import json
from pathlib import Path
from PIL import Image

R = Path(__file__).resolve().parents[1]


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(p):
    return json.loads(p.read_text())


def evidence(p):
    return {'path': str(p.relative_to(R.parent)), 'sha256': sha(p), 'bytes': p.stat().st_size}


def main():
    m = read(R / 'lighting_manifest.json')
    native = read(R / 'qa/independent_native_binding.json')
    game = read(R / 'qa/independent_final_game_binding.json')
    assert native['status'] == 'PASS_NATIVE_ADDITION_BINDING'
    assert game['status'] == 'PASS_FINAL_ADDITION_ONLY_GAME_BINDING'
    ns = m['augmented_native_sha256']
    assert native['native_sha256'] == game['native_sha256'] == ns
    assert sha(R / m['native_file']) == ns
    observations = read(R / 'qa/independent_pixel_observations.json')['observations']
    passed = {row['sha256']: row for row in observations if row['status'] == 'PASS' and row['direct_pixel_review']}
    script_candidates = [R / 'scripts/render_lighting_revision.py', *sorted((R / 'qa').rglob('render_lighting_revision.py'))]
    tools = {sha(p): p for p in script_candidates}
    files = [R / 'lighting_manifest.json', R / 'qa/independent_native_binding.json', R / 'qa/independent_final_game_binding.json',
             R / 'qa/independent_pixel_observations.json', Path(__file__)]
    records = []
    for view in ['evening', 'night', 'detail']:
        p = R / 'qa' / f'render_{view}.json'
        r = read(p)
        assert r['view'] == view and r['native_sha256'] == ns
        assert r['lighting_manifest_sha256'] == sha(R / 'lighting_manifest.json')
        image = R / r['file']
        assert sha(image) == r['sha256'] and image.stat().st_size == r['bytes']
        assert r['sha256'] in passed
        expected_size = (1100, 825) if view == 'detail' else (1400, 875)
        with Image.open(image) as im:
            assert im.format == 'PNG' and im.size == expected_size and im.mode in ('RGB', 'RGBA')
        renderer = r['renderer']
        assert renderer['blender_version'] == '4.3.2' and renderer['engine'] == 'CYCLES' and renderer['device'] == 'CPU'
        expected_samples = 1024 if view == 'detail' else 256
        assert renderer['denoising'] is False and r['samples'] == expected_samples
        assert sha(Path(renderer['binary'])) == renderer['binary_sha256']
        assert r['source_native_unchanged'] and not r['source_saved'] and not r['new_window_emission']
        assert r['native_fixture_powers_unchanged']
        assert r['render_script_sha256'] in tools, 'Exact renderer source snapshot is required'
        files.extend([p, image, tools[r['render_script_sha256']]])
        records.append({'view': view, 'image_sha256': r['sha256'], 'dimensions': list(expected_size),
                        'samples': r['samples'], 'denoising': False, 'threads': r['threads'], 'color_management': r['color_management'], 'renderer_binary_sha256': renderer['binary_sha256'],
                        'render_script_sha256': r['render_script_sha256'], 'camera': r['camera'],
                        'lighting_overrides': r['lighting_overrides'], 'pixel_conclusion': passed[r['sha256']]['notes']})
    assert len({x['image_sha256'] for x in records}) == 3
    assert records[0]['camera'] == records[1]['camera']
    handoff = R.parent / 'GAME_LIGHTING_FINAL_HANDOFF.json'
    if handoff.exists():
        h = read(handoff)
        assert h['augmentedNativeSha256'] == ns and h['status'] == 'LOCAL_LIGHTING_GAME_COMPLETE'
        for key in ['zip', 'releaseManifest', 'validationIndex']:
            assert sha(Path(h[key]['path'])) == h[key]['sha256']
        files.append(handoff)
    unique = {str(p): p for p in files}
    report = {
        'status': 'PASS', 'revision': 'recovered_street_lighting_v6', 'native_sha256': ns,
        'source_native_sha256': m['source_native_sha256'], 'placement_sha256': m['placement_sha256'],
        'checks': {'restored_source_and_native_preservation': 'PASS', '536_fixture_placement_support': 'PASS',
                   'saved_native_reopen': 'PASS', 'final_fixture_glb_and_bounded_game_binding': 'PASS', 'three_native_render_views': 'PASS'},
        'original_objects_preserved': 7923, 'added_fixture_objects': 536, 'added_native_spotlights': 536,
        'final_objects': 8995, 'images': records, 'unresolved_in_this_scope': [],
        'evidence': [evidence(p) for p in unique.values()],
        'scope': 'Recovered a65 inputs, additive street-lighting native/game relationship, and three actual new native render views. No expansion into old campus deficiencies or repetition of the 47-image/71-catalogue audit.',
        'limits': ['Placement, radiant powers and color are inferred design; no surveyed installation or certified photometry is claimed.',
                   'Reconstructed placement has a new hash; old pre-recovery coordinate JSON identity is not claimed.',
                   'These use installed Blender 4.3.2 and no denoising: 256 samples for overviews and 1024 for the detail. They do not match the earlier official OIDN render configuration.',
                   'Game validation is lighting-addition-only; original campus full traversal was not rerun and browser/WebGL/mobile night pixels remain unverified.',
                   'Existing a65 source limitations and accepted vehicle/shuttle animation residuals remain unchanged.',
                   'Remote GitHub publishing remains stopped and the Site is not deployed. Local QA does not authorize either action.'],
    }
    (R / 'qa/independent_final_acceptance.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'PASS', 'native_sha256': ns, 'views': [x['view'] for x in records]}))


if __name__ == '__main__':
    main()
