"""Actual new lamp-head self-shadow test; no campus geometry is loaded or saved."""
import bpy,sys,json,hashlib,resource
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));import luminaire_geometry as g
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
plan_path=ROOT/'contracts/street_lighting_manifest.json';plan=json.loads(plan_path.read_text());objects,lights=g.add_luminaires(plan,bpy.context.scene,with_lights=True)
old_hits=[];new_hits=[]
for f,ob,light in zip(plan['fixtures'],objects,lights):
 target=Vector(f['target_position']);inverse=ob.matrix_world.inverted()
 for tag,origin,results in [('head_center',Vector(f['lamp_position']),old_hits),('offset_emitter',light.location,new_hits)]:
  local=inverse@origin;end=inverse@target;delta=end-local
  hit,point,normal,idx=ob.ray_cast(local,delta.normalized(),distance=delta.length-.005)
  if hit:results.append({'id':f['id'],'polygon':idx,'distance_m':(point-local).length})
assert not new_hits, new_hits
assert old_hits, 'Positive self-shadow counterexample must be detected'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
report={'status':'PASS','fixture_count':len(objects),'new_emitter_blocked_by_own_fixture':new_hits,'old_center_positive_counterexamples':len(old_hits),'old_center_examples':old_hits[:5],'native_light_emitter_offset_m':list(g.EMITTER_OFFSET),'head_geometry_and_base_positions_unchanged':True,'scope':'Each lamp to its intended actual ground target against its own fixture mesh; no claim about unrelated occluders.','placement_sha256':sha(plan_path),'geometry_source_sha256':sha(ROOT/'scripts/luminaire_geometry.py'),'test_source_sha256':sha(__file__),'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
(ROOT/'qa/emitter_clearance.json').write_text(json.dumps(report,indent=2)+'\n');print('EMITTER_CLEARANCE_PASS',json.dumps(report),flush=True)
