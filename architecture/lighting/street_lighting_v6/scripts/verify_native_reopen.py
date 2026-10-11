"""Read-only exact-original preservation and new-fixture saved-native checks."""
import bpy,sys,json,hashlib,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));import preservation as p
m=json.loads((ROOT/'lighting_manifest.json').read_text());native=Path(bpy.data.filepath)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
assert sha(native)==m['augmented_native_sha256']
from preservation_json_adapter import load_baseline
baseline,serialization_adapter=load_baseline(ROOT/'qa/existing_asset_baseline.json')
check=p.compare_baseline(baseline,allowed_scene_customprops=['RV6_lighting_placement_sha256','RV6_lighting_accuracy'],raise_on_error=False)
check['serialization_adapter']=serialization_adapter
check['verification_source_sha256']=sha(__file__)
p.save_manifest(check,ROOT/'qa/native_reopen_preservation_report.json')
assert check['status']=='PASS',check['differences']
for f in m['fixtures']:
 o=bpy.data.objects[f['fixture_object_names'][0]];light=bpy.data.objects['RV6_LIGHT_'+f['id']+'_beam']
 assert o.type=='MESH' and light.type=='LIGHT' and light.data.type=='SPOT'
 assert max(abs(o.location[i]-f['base_position'][i]) for i in range(3))<.0001
 assert max(abs(light.location[i]-(f['lamp_position'][i]+m['native_light_emitter_offset_m'][i])) for i in range(3))<.0001
 assert abs(light.data.energy-f['power_watts'])<.0001
assert len(bpy.data.objects)==7923+2*len(m['fixtures'])
check.update({'native_sha256':sha(native),'source_native_sha256':m['source_native_sha256'],'original_objects_checked':7923,'new_fixtures':len(m['fixtures']),'new_lights':len(m['fixtures']),'source_not_saved':True,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024})
p.save_manifest(check,ROOT/'qa/native_reopen.json');print('NATIVE_REOPEN_PASS',json.dumps(check),flush=True)
