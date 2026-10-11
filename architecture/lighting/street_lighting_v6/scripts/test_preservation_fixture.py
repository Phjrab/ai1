"""Factory-only mutation tests and raw-storage side-effect checks.

Commands from this scripts directory:
  blender -b --factory-startup -t 2 --python-exit-code 19 --python test_preservation_fixture.py
  blender -b /tmp/preservation_fixture_v3/revised.blend -t 2 --python-exit-code 19 --python test_preservation_fixture.py -- --reopen

All fixture saves are compressed to exercise the actual Blender zstandard fallback.
Only /tmp fixtures are created. Deform-weight inputs are intentionally unsupported.
"""
import sys,json
from pathlib import Path
import bpy
S=Path(__file__).resolve().parent
sys.path.insert(0,str(S))
import preservation as p
root=Path('/tmp/preservation_fixture_v3');root.mkdir(exist_ok=True)

def run_fixture():
 mesh=bpy.data.objects['Cube'].data
 obj=bpy.data.objects['Cube']
 obj['original_property']='keep';bpy.context.scene['original_property']='keep'
 mat=bpy.data.materials.new('FixtureMat');mat.use_nodes=True;mesh.materials.append(mat)
 attr=mesh.attributes.new('fixture_weight','FLOAT','POINT');attr.data[0].value=.35
 mod=obj.modifiers.new('FixtureBevel','BEVEL');mod.width=.1
 group=bpy.data.node_groups.new('FixtureShaderGroup','ShaderNodeTree');group.interface.new_socket(name='Factor',in_out='INPUT',socket_type='NodeSocketFloat')
 group.nodes.new('NodeGroupInput')
 group_node=mat.node_tree.nodes.new('ShaderNodeGroup');group_node.node_tree=group
 script=root/'source.py';script.write_text('value = 1\n')
 bpy.ops.wm.save_as_mainfile(filepath=str(root/'base.blend'),compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(root/'base.blend'))
 obj=bpy.data.objects['Cube'];mesh=obj.data;mat=bpy.data.materials['FixtureMat'];mod=obj.modifiers['FixtureBevel'];group=bpy.data.node_groups['FixtureShaderGroup']
 base=p.capture_baseline(expected_object_count=3,source_paths=[script,__file__])
 p.save_manifest(base,root/'baseline.json')
 bpy.ops.wm.save_as_mainfile(filepath=str(root/'after_capture.blend'),compress=True)
 from audit_blend_blocks import inventory
 raw_before=inventory(root/'base.blend');raw_after=inventory(root/'after_capture.blend')
 raw_diffs={k:[raw_before['native_types'].get(k),raw_after['native_types'].get(k)] for k in set(raw_before['native_types'])|set(raw_after['native_types']) if raw_before['native_types'].get(k)!=raw_after['native_types'].get(k)}
 assert not raw_diffs,raw_diffs
 p.save_manifest({'status':'PASS','native_type_inventory_equal':True,'before':raw_before,'after_capture':raw_after},root/'capture_side_effect_check.json')
 assert p.compare_baseline(base)['status']=='PASS'
 print('FIXTURE_BASELINE_PASS',flush=True)
 checks=[{'case':'capture_native_storage_counts_unchanged','status':'PASS'}]
 assert (root/'base.blend').read_bytes()[:4]==b'\x28\xb5\x2f\xfd'
 assert raw_before['reader_backend']=='installed_system_python_zstandard_subprocess'
 checks.append({'case':'compressed_native_system_reader_fallback','status':'PASS'})
 def reject(label,change,restore):
  change()
  report=p.compare_baseline(base,raise_on_error=False)
  assert report['status']=='FAIL',(label,report)
  checks.append({'case':label,'status':'PASS','difference':report['differences'][:2],'new':report['disallowed_additions']})
  restore()
  assert p.compare_baseline(base)['status']=='PASS',label
 reject('declared_vertex_group',lambda:obj.vertex_groups.new(name='Unsupported'),lambda:obj.vertex_groups.remove(obj.vertex_groups['Unsupported']))
 co=obj.data.vertices[0].co.copy();reject('vertex',lambda:setattr(obj.data.vertices[0].co,'x',co.x+.125),lambda:setattr(obj.data.vertices[0],'co',co))
 uv=mesh.uv_layers[0].data[0].uv.copy();reject('uv',lambda:setattr(mesh.uv_layers[0].data[0].uv,'x',uv.x+.125),lambda:setattr(mesh.uv_layers[0].data[0],'uv',uv))
 v=mesh.attributes['fixture_weight'].data[0].value;reject('attribute',lambda:setattr(mesh.attributes['fixture_weight'].data[0],'value',.5),lambda:setattr(mesh.attributes['fixture_weight'].data[0],'value',v))
 v=mod.width;reject('modifier',lambda:setattr(mod,'width',.2),lambda:setattr(mod,'width',v))
 sock=mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'];v=sock.default_value;reject('shader',lambda:setattr(sock,'default_value',.125),lambda:setattr(sock,'default_value',v))
 sock=group.interface.items_tree[0];v=sock.default_value;reject('node_group',lambda:setattr(sock,'default_value',.2),lambda:setattr(sock,'default_value',v))
 light=bpy.data.lights[0];v=light.energy;reject('light',lambda:setattr(light,'energy',v+1),lambda:setattr(light,'energy',v))
 world=bpy.context.scene.world;sock=world.node_tree.nodes.get('Background').inputs['Strength'];v=sock.default_value;reject('world',lambda:setattr(sock,'default_value',.5),lambda:setattr(sock,'default_value',v))
 cam=bpy.data.cameras[0];v=cam.lens;reject('camera',lambda:setattr(cam,'lens',v+1),lambda:setattr(cam,'lens',v))
 v=obj.location.copy();reject('transform',lambda:setattr(obj.location,'x',.125),lambda:setattr(obj,'location',v))
 reject('parent',lambda:setattr(obj,'parent',bpy.data.objects['Camera']),lambda:setattr(obj,'parent',None))
 reject('visibility',lambda:setattr(obj,'hide_render',True),lambda:setattr(obj,'hide_render',False))
 reject('view_layer_hide',lambda:obj.hide_set(True),lambda:obj.hide_set(False))
 reject('scene_customprop_change',lambda:bpy.context.scene.__setitem__('original_property','changed'),lambda:bpy.context.scene.__setitem__('original_property','keep'))
 reject('script_change',lambda:script.write_text('value = 2\n'),lambda:script.write_text('value = 1\n'))
 obj.select_set(False);mesh.vertices[0].select=not mesh.vertices[0].select
 assert p.compare_baseline(base)['status']=='PASS'
 checks.append({'case':'selection_ignored','status':'PASS'})
 newmat=bpy.data.materials.new('AddedMaterial')
 newmesh=bpy.data.meshes.new('AddedPole');newmesh.from_pydata([(0,0,0),(1,0,0),(0,1,0)],[],[(0,1,2)]);newmesh.materials.append(newmat)
 newobj=bpy.data.objects.new('AddedPole',newmesh);bpy.context.scene.collection.objects.link(newobj)
 newlight=bpy.data.lights.new('AddedLight','POINT');newlightobj=bpy.data.objects.new('AddedLight',newlight);bpy.context.scene.collection.objects.link(newlightobj)
 bpy.context.scene['RV6_audit']='fixture_addition'
 assert p.compare_baseline(base,allowed_scene_customprops={'RV6_audit'})['status']=='PASS'
 assert p.compare_baseline(base,raise_on_error=False)['status']=='FAIL'
 checks.append({'case':'explicit_additions_and_scene_prop','status':'PASS'})
 empty=bpy.data.objects.new('DisallowedEmpty',None);bpy.context.scene.collection.objects.link(empty)
 assert p.compare_baseline(base,allowed_scene_customprops={'RV6_audit'},raise_on_error=False)['status']=='FAIL'
 bpy.data.objects.remove(empty,do_unlink=True)
 checks.append({'case':'unexpected_object_type','status':'PASS'})
 bpy.ops.wm.save_as_mainfile(filepath=str(root/'revised.blend'),compress=True)
 raw_final=inventory(root/'revised.blend')
 assert not raw_final['native_types'].get('MDeformVert') and not raw_final['native_types'].get('MDeformWeight')
 checks.append({'case':'saved_native_raw_deform_absence','status':'PASS'})
 unsupported=obj.vertex_groups.new(name='UnsupportedDeform');unsupported.add([0],.25,'REPLACE')
 bpy.ops.wm.save_as_mainfile(filepath=str(root/'unsupported_deform.blend'),compress=True)
 try:
  p.capture_baseline()
 except p.PreservationError:
  checks.append({'case':'deform_input_explicitly_rejected','status':'PASS'})
 else:
  raise AssertionError('Unsupported deform input was not rejected')
 p.save_manifest({'status':'PASS','checks':checks},root/'checks.json')
 print('FIXTURE_MUTATION_CHECKS_PASS',len(checks),flush=True)

if '--reopen' in sys.argv:
 base=p.load_manifest(root/'baseline.json')
 report=p.compare_baseline(base,allowed_scene_customprops={'RV6_audit'})
 p.save_manifest(report,root/'reopen_report.json')
 print('FIXTURE_FRESH_REOPEN_PASS',report['original_state_sha256'],flush=True)
else:
 run_fixture()
