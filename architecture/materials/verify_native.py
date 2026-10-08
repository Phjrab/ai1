import bpy,sys,os,json,hashlib
P=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,P)
from campus_materials import apply_materials

def digest():
 h=hashlib.sha256()
 for o in sorted(bpy.data.objects,key=lambda o:o.name):
  if o.type!='MESH':continue
  h.update(o.name.encode());h.update(str(tuple(tuple(r) for r in o.matrix_world)).encode())
  for v in o.data.vertices:h.update(str(tuple(v.co)).encode())
  for p in o.data.polygons:h.update(str(tuple(p.vertices)).encode())
 return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath='/workspace/shared/chosun_model/delivery/Chosun_Campus.blend');a=digest()
bpy.ops.wm.open_mainfile(filepath=P+'/PBR_preview_only.blend');b=digest();repeat=apply_materials()
r={'source_mesh_sha256':a,'preview_mesh_sha256':b,'geometry_unchanged':a==b,'idempotence_second_call_changed':repeat,'material_profile_count':sum(bool(m.get('campus_pbr_version')) for m in bpy.data.materials),'all_inputs_have_metres_scale':bpy.context.scene.unit_settings.scale_length==1}
assert a==b;assert not repeat
json.dump(r,open(P+'/native_verification.json','w'),indent=2);print(r)
