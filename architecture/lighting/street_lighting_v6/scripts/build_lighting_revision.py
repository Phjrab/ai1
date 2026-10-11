"""Strictly additive native revision and small fixture-only GLB."""
import bpy,sys,json,hashlib,time,resource,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import preservation as p
from luminaire_geometry import add_luminaires,export_fixture_delta,MATERIAL_NAMES,EMITTER_OFFSET
BASE=ROOT.parent/'inputs/Chosun_Campus_Realism_v2.blend'
BASE_SHA='a65c2ae19f02c59f655e0c7eedb2482a5c2f6a9c53bb94f2425769dbd4417fbd'
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
assert Path(bpy.data.filepath).resolve()==BASE.resolve() and sha(BASE)==BASE_SHA
plan_path=ROOT/'contracts/street_lighting_manifest.json';plan=json.loads(plan_path.read_text())
assert plan['status']=='PASS' and plan['source_native_sha256']==BASE_SHA
freeze_path=ROOT/'qa/placement_freeze.json';freeze=json.loads(freeze_path.read_text());assert freeze['status']=='PASS'
for rec in [freeze['manifest'],*freeze['reports'],*freeze['scripts']]:assert sha(ROOT/rec['path'])==rec['sha256'],rec['path']
image_inputs=[]
for image in bpy.data.images:
 if image.source in {'VIEWER','GENERATED'}:continue
 packed=bool(image.packed_file or len(image.packed_files));resolved=Path(bpy.path.abspath(image.filepath)) if image.filepath else None
 image_inputs.append({'name':image.name,'source':image.source,'packed':packed,'path_exists':bool(resolved and resolved.is_file())})
assert all(x['packed'] or x['path_exists'] for x in image_inputs),image_inputs
(ROOT/'qa/native_image_inputs.json').write_text(json.dumps({'status':'PASS','images':image_inputs},indent=2)+'\n')
source_paths=[Path(__file__),ROOT/'scripts/preservation.py',ROOT/'scripts/luminaire_geometry.py',plan_path,freeze_path]
baseline=p.capture_baseline(source_path=BASE,expected_sha256=BASE_SHA,expected_object_count=7923,source_paths=source_paths)
p.save_manifest(baseline,ROOT/'qa/existing_asset_baseline.json');print('BASELINE_CAPTURED',flush=True)
fixtures,lights=add_luminaires(plan,bpy.context.scene,with_lights=True)
scene=bpy.context.scene;scene['RV6_lighting_placement_sha256']=sha(plan_path);scene['RV6_lighting_accuracy']='Inferred lighting design, not surveyed existing streetlight locations.'
allowed=['RV6_lighting_placement_sha256','RV6_lighting_accuracy']
check=p.compare_baseline(baseline,allowed_scene_customprops=allowed)
check.update({'source_native_sha256':BASE_SHA,'fixture_count':len(fixtures),'new_light_count':len(lights),'placement_sha256':sha(plan_path),'scope':'Only additional luminaire geometry, materials and light objects. No original asset changes.'})
p.save_manifest(check,ROOT/'qa/additive_preservation.json');print('ADDITIVE_PRESERVATION_PASS',flush=True)
output=ROOT/'Chosun_Campus_Street_Lighting_v6.blend';assert not output.exists()
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
new_sha=sha(output);assert sha(BASE)==BASE_SHA;print('NATIVE_SAVED',new_sha,flush=True)
glb=ROOT/'exports/lighting.glb';glb.parent.mkdir(exist_ok=True);assert not glb.exists();export_fixture_delta(fixtures,glb)
data=glb.read_bytes();n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n]);assert len(doc['scenes'])==1 and len(doc['nodes'])==len(fixtures) and len(doc['meshes'])==2
assert sorted(x['name'] for x in doc['nodes'])==sorted(x.name for x in fixtures)
assert 'KHR_lights_punctual' not in doc.get('extensionsUsed',[])
assert sha(output)==new_sha and sha(BASE)==BASE_SHA
manifest=dict(plan);manifest.update({'status':'PASS','augmented_native_sha256':new_sha,'native_file':output.name,'native_bytes':output.stat().st_size,'placement_sha256':sha(plan_path),'placement_freeze_sha256':sha(freeze_path),'exports':[{'file':'exports/lighting.glb','sha256':sha(glb),'bytes':glb.stat().st_size}],'emissive_material_name':MATERIAL_NAMES[-1],'native_spotlights_exported':False,'native_light_emitter_offset_m':list(EMITTER_OFFSET),'lamp_position_role':'luminaire head center; native emitter is offset below opaque lens','existing_base_glbs_reused_unchanged':True,'builder_sha256':sha(__file__),'geometry_source_sha256':sha(ROOT/'scripts/luminaire_geometry.py'),'preservation_report_sha256':sha(ROOT/'qa/additive_preservation.json'),'recovered_revision':True,'previous_unbuilt_536_coordinates_not_claimed_identical':True})
(ROOT/'lighting_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('REVISION_READY',json.dumps({'native_sha256':new_sha,'fixture_count':len(fixtures),'glb_bytes':glb.stat().st_size,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}),flush=True)
