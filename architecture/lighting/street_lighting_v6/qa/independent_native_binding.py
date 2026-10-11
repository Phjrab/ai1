"""Bind the additive native/reopen evidence to actual bytes and fixture GLB.

Reads strict Blender captures and current files. Does not launch Blender or
pretend that reviewing a capture is a second scene evaluation.
"""
from pathlib import Path
import hashlib
import json
import math
import struct

R = Path(__file__).resolve().parents[1]
BASE_SHA = 'a65c2ae19f02c59f655e0c7eedb2482a5c2f6a9c53bb94f2425769dbd4417fbd'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load(p):
    return json.loads(p.read_text())


def evidence(p):
    return {'path': str(p.relative_to(R.parent)), 'sha256': sha(p), 'bytes': p.stat().st_size}


def main():
    manifest = load(R / 'lighting_manifest.json')
    placement = load(R / 'contracts/street_lighting_manifest.json')
    baseline = load(R / 'qa/existing_asset_baseline.json')
    additive = load(R / 'qa/additive_preservation.json')
    reopened = load(R / 'qa/native_reopen.json')
    assert sha(R.parent / 'inputs/Chosun_Campus_Realism_v2.blend') == BASE_SHA
    assert manifest['source_native_sha256'] == BASE_SHA
    assert manifest['placement_sha256'] == sha(R / 'contracts/street_lighting_manifest.json')
    assert manifest['placement_freeze_sha256'] == sha(R / 'qa/placement_freeze.json')
    assert manifest['fixtures'] == placement['fixtures'] and len(manifest['fixtures']) == 536
    assert manifest['native_light_emitter_offset_m'] == [0., 0., -.1]
    native = R / manifest['native_file']
    native_sha = sha(native)
    assert native_sha == manifest['augmented_native_sha256'] == reopened['native_sha256']
    assert native.stat().st_size == manifest['native_bytes']
    assert baseline['source_native']['sha256'] == BASE_SHA
    assert baseline['original_object_count'] == len(baseline['datablocks']['objects']) == 7923
    assert baseline['schema'] == 'blender-native-preservation-v2-raw-deform-guard'
    for guard in [baseline['input_native_deform_storage_guard'], additive['loaded_native_deform_storage_guard'], reopened['loaded_native_deform_storage_guard']]:
        assert guard['status'] == 'PASS' and not guard['reasons']
        assert guard['native_deform_storage_bytes'] == {'MDeformVert': 0, 'MDeformWeight': 0}
        assert guard['objects_with_declared_vertex_groups'] == {} and guard['no_per_vertex_group_getter_used']
    assert Path(reopened['loaded_native_deform_storage_guard']['native_path']).resolve() == native.resolve()
    factory = load(R / 'qa/preservation_factory_checks.json')
    assert factory['status'] == 'PASS' and all(row['status'] == 'PASS' for row in factory['checks'])
    assert factory['helper_sha256'] == sha(R / 'scripts/preservation.py')
    assert factory['capture_native_storage_side_effect_check']['native_type_inventory_equal']
    for record in [additive, reopened]:
        assert record['status'] == 'PASS' and not record['differences'] and not record['disallowed_additions']
        assert record['original_state_sha256'] == record['observed_original_state_sha256'] == baseline['original_state_sha256']
        assert record['source_native_bytes'] == record['source_script_bytes'] == 'PASS'
        assert record['current_object_count'] == 8995
        assert record['new_datablock_counts'] == {'objects': 1072, 'meshes': 2, 'materials': 4, 'lights': 536, 'collections': 1}
    for path, record in baseline['source_files'].items():
        p = Path(path)
        assert sha(p) == record['sha256'], str(p)
    for key, name in [('builder_sha256', 'build_lighting_revision.py'), ('geometry_source_sha256', 'luminaire_geometry.py')]:
        assert manifest[key] == sha(R / 'scripts' / name)
    assert manifest['preservation_report_sha256'] == sha(R / 'qa/additive_preservation.json')
    adapter = load(R / 'qa/native_baseline_serialization_adapter.json')
    assert adapter['status'] == 'PASS' and adapter['canonical_contents_unchanged']
    assert adapter['baseline_fingerprint_before'] == adapter['baseline_fingerprint_after'] == baseline['original_state_sha256']
    assert adapter['baseline_json_sha256'] == sha(R / 'qa/existing_asset_baseline.json')
    assert adapter['adapter_source_sha256'] == sha(R / 'scripts/preservation_json_adapter.py')
    compression = load(R / manifest['native_container_recompression']['report'])
    assert sha(R / manifest['native_container_recompression']['report']) == manifest['native_container_recompression']['sha256']
    assert compression['status'] == 'PASS' and compression['exact_internal_bytes_preserved']
    assert compression['final_native_sha256'] == native_sha
    assert compression['decompressed_stream_sha256'] == reopened['loaded_native_deform_storage_guard']['decompressed_native_sha256']
    exported = manifest['exports']
    assert len(exported) == 1
    glb = R / exported[0]['file']
    assert sha(glb) == exported[0]['sha256'] and glb.stat().st_size == exported[0]['bytes']
    with glb.open('rb') as f:
        header = f.read(20)
        magic, version, total, json_length, kind = struct.unpack('<IIIII', header)
        assert (magic, version, total, kind) == (0x46546c67, 2, glb.stat().st_size, 0x4e4f534a)
        doc = json.loads(f.read(json_length))
    assert len(doc['scenes']) == 1 and len(doc['nodes']) == 536 and len(doc['meshes']) == 2 and len(doc['materials']) == 4
    assert 'KHR_lights_punctual' not in doc.get('extensionsUsed', [])
    assert sorted(doc['scenes'][0]['nodes']) == list(range(536))
    fixture_by_name = {f['fixture_object_names'][0]: f for f in placement['fixtures']}
    position_error = 0.
    for node in doc['nodes']:
        assert node['name'] in fixture_by_name and 'mesh' in node and not node.get('children')
        f = fixture_by_name[node['name']]
        x, y, z = node.get('translation', [0., 0., 0.])
        position_error = max(position_error, max(abs(a-b) for a, b in zip([x, -z, y], f['base_position'])))
        assert node.get('scale', [1., 1., 1.]) == [1., 1., 1.]
    assert position_error < .0001
    candidate = load(R / 'qa/fixture_candidate.json')
    assert exported[0]['sha256'] == candidate['sha256'], 'Final mesh delta changed from tested candidate'
    emitter = load(R / 'qa/emitter_clearance.json')
    assert emitter['geometry_source_sha256'] == manifest['geometry_source_sha256']
    assert emitter['status'] == 'PASS' and not emitter['new_emitter_blocked_by_own_fixture']
    assert emitter['old_center_positive_counterexamples'] == 536
    files = [R / 'lighting_manifest.json', R / 'qa/existing_asset_baseline.json', R / 'qa/additive_preservation.json', R / 'qa/native_reopen.json',
             R / 'qa/fixture_candidate.json', R / 'qa/preservation_factory_checks.json', R / 'qa/emitter_clearance.json',
             R / 'qa/independent_recorded_support.json', R / 'qa/independent_contract_review.json', R / 'qa/independent_emitter_change_review.json',
             R / 'qa/native_baseline_serialization_adapter.json', R / 'qa/independent_serialization_adapter_review.json', R / 'scripts/preservation_json_adapter.py', R / manifest['native_container_recompression']['report'],
             R / 'scripts/preservation.py', R / 'scripts/audit_blend_blocks.py', R / 'scripts/verify_native_reopen.py', Path(__file__)]
    result = {
        'status': 'PASS_NATIVE_ADDITION_BINDING',
        'source_native_sha256': BASE_SHA,
        'native_sha256': native_sha,
        'native_file': str(native.relative_to(R.parent)),
        'native_bytes': native.stat().st_size,
        'placement_sha256': manifest['placement_sha256'],
        'final_fixture_glb_sha256': exported[0]['sha256'],
        'original_objects': 7923,
        'original_meshes': baseline['counts']['meshes'],
        'original_materials': baseline['counts']['materials'],
        'original_state_sha256': baseline['original_state_sha256'],
        'original_differences_after_addition_and_reopen': [],
        'original_and_saved_native_deform_storage': {'MDeformVert': 0, 'MDeformWeight': 0},
        'preservation_helper_storage_counterexample_checks': len(factory['checks']),
        'shader_link_json_pair_type_restorations': adapter['restored_pair_count'],
        'decompressed_native_stream_sha256': compression['decompressed_stream_sha256'],
        'additions': additive['new_datablock_counts'],
        'final_objects': 8995,
        'actual_glb': {'nodes': 536, 'meshes': 2, 'materials': 4, 'maximum_base_coordinate_error_m': position_error, 'same_bytes_as_tested_candidate': True},
        'emitter_offset_from_head_center_m': [0, 0, -.1],
        'evidence': [evidence(p) for p in files],
        'scope': 'Independently inspected preservation implementation and counterexamples, verified actual file hashes and decoded final fixture GLB. Strict before/after/reopen native captures were produced by the coordinated single Blender process.',
        'limitations': ['Rendering review and final game input/report binding are separate checks.', 'Inferred lighting placement and visual radiant power are not surveyed installation or photometric certification.', 'No exact reproduction of the lost pre-recovery v6 coordinate JSON is claimed.'],
    }
    (R / 'qa/independent_native_binding.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'native_sha256', 'original_objects', 'final_objects']}))


if __name__ == '__main__':
    main()
