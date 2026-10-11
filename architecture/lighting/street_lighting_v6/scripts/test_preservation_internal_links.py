"""Compressed native fixture for the narrow shader-internal-link JSON adapter.

blender -b --factory-startup -t 2 --python-exit-code 19 --python test_preservation_internal_links.py
blender -b /tmp/preservation_internal_links/revised.blend -t 2 --python-exit-code 19 --python test_preservation_internal_links.py -- --reopen
"""
from pathlib import Path
import copy
import json
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
import preservation as p
import preservation_json_adapter as adapter
ROOT = Path('/tmp/preservation_internal_links')
ROOT.mkdir(exist_ok=True)
PIN = '244aaa2a2374657baaf77e999c566adb0888e120ab7460e44a96d1a81f476466'
assert p.file_sha256(p.__file__) == PIN


def verify_reopen():
    baseline, normalization = adapter.load_baseline(ROOT/'baseline.json')
    report = p.compare_baseline(baseline, raise_on_error=False)
    report['serialization_adapter'] = normalization
    p.save_manifest(report, ROOT/'fresh_reopen_report.json')
    assert report['status'] == 'PASS', report['differences']
    assert normalization['restored_pair_count'] >= 3
    print('INTERNAL_LINKS_FRESH_REOPEN_PASS', normalization['restored_pair_count'], flush=True)


def create_fixture():
    material = bpy.data.materials.new('InternalLinksFixture')
    material.use_nodes = True
    bpy.data.objects['Cube'].data.materials.clear()
    bpy.data.objects['Cube'].data.materials.append(material)
    nodes = material.node_tree.nodes
    for node_type in ('ShaderNodeMath', 'ShaderNodeBump', 'ShaderNodeValToRGB'):
        node = nodes.new(node_type)
    value=nodes.new('ShaderNodeValue')
    links=material.node_tree.links
    links.new(value.outputs[0],nodes['Math'].inputs[0])
    links.new(nodes['Math'].outputs[0],nodes['Color Ramp'].inputs['Fac'])
    links.new(nodes['Color Ramp'].outputs['Color'],nodes['Bump'].inputs['Height'])
    links.new(nodes['Bump'].outputs['Normal'],nodes['Principled BSDF'].inputs['Normal'])
    links.new(nodes['Color Ramp'].outputs['Color'],nodes['Principled BSDF'].inputs['Base Color'])
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'base.blend'), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'base.blend'))
    for name in ('Math','Bump','Color Ramp'):
        assert len(bpy.data.materials['InternalLinksFixture'].node_tree.nodes[name].internal_links)>0, name
    baseline = p.capture_baseline(source_paths=[__file__, adapter.__file__])
    p.save_manifest(baseline, ROOT/'baseline.json')
    original_bytes_sha = p.file_sha256(ROOT/'baseline.json')
    loaded = p.load_manifest(ROOT/'baseline.json')
    reproduced = p.compare_baseline(loaded, raise_on_error=False)
    p.save_manifest(reproduced, ROOT/'serialization_failure_report.json')
    assert reproduced['status'] == 'FAIL'
    assert reproduced['differences'] and all('/internal_links/' in d and d.endswith('type changed') for d in reproduced['differences'])
    assert reproduced['original_state_sha256'] == reproduced['observed_original_state_sha256']
    restored, normalized = adapter.load_baseline(ROOT/'baseline.json')
    report = p.compare_baseline(restored, raise_on_error=False)
    assert report['status'] == 'PASS', report['differences']
    assert normalized['restored_pair_count'] >= 3
    # A real shader operation change must still fail after the type adapter.
    math = bpy.data.materials['InternalLinksFixture'].node_tree.nodes.get('Math')
    operation = math.operation
    math.operation = 'MULTIPLY'
    actual_mutation = p.compare_baseline(restored, raise_on_error=False)
    assert actual_mutation['status'] == 'FAIL'
    assert any('properties_sha256' in d for d in actual_mutation['differences'])
    math.operation = operation
    assert p.compare_baseline(restored)['status'] == 'PASS'
    # Changed socket identity in the JSON must never be normalized away.
    tampered = copy.deepcopy(loaded)
    node = next(v for v in tampered['datablocks']['materials'].values() if v.get('node_tree') and 'Math' in v['node_tree']['nodes'])['node_tree']['nodes']['Math']
    node['internal_links'][0][0]['index'] += 1
    try:
        adapter.restore_internal_link_pairs(tampered)
    except p.PreservationError:
        pass
    else:
        raise AssertionError('Tampered socket identity was accepted')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'revised.blend'), compress=True)
    assert p.file_sha256(ROOT/'baseline.json') == original_bytes_sha
    assert p.file_sha256(p.__file__) == PIN
    result = {'status':'PASS', 'cases':['JSON tuple/list failure reproduced with equal canonical fingerprints',
              'Math/Bump/ColorRamp pairs restored without content changes', 'actual shader mutation still rejected',
              'tampered JSON socket identity rejected', 'baseline JSON/helper bytes unchanged'],
              'serialization_adapter':normalized, 'source_sha256':p.file_sha256(__file__),
              'actual_shader_mutation_report':actual_mutation}
    p.save_manifest(result, ROOT/'fixture_checks.json')
    print('INTERNAL_LINKS_ADAPTER_FIXTURE_PASS', normalized['restored_pair_count'], flush=True)


if '--reopen' in sys.argv:
    verify_reopen()
else:
    create_fixture()
