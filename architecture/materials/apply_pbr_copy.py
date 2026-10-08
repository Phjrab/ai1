"""Run: blender -b SOURCE.blend -t 2 --python apply_pbr_copy.py -- OUT.blend [OUT.glb]
Creates a native procedural-material copy, then an export-only constant PBR GLB.
Never overwrites the loaded source. Invoke after all geometry and livery integration.
"""
import bpy,sys,os,json,hashlib
P=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,P)
from campus_materials import apply_materials,game_fallback,setup_presentation
args=sys.argv[sys.argv.index('--')+1:];out=os.path.abspath(args[0]);src=os.path.abspath(bpy.data.filepath)
assert out!=src,'Refusing to overwrite source: select an explicit output copy.'
assert out.endswith('.blend')
def geometry_digest():
 h=hashlib.sha256()
 for o in sorted(bpy.data.objects,key=lambda x:x.name):
  if o.type!='MESH':continue
  h.update(o.name.encode());h.update(str(tuple(tuple(row) for row in o.matrix_world)).encode())
  for v in o.data.vertices:h.update(str(tuple(v.co)).encode())
  for p in o.data.polygons:h.update(str(tuple(p.vertices)).encode())
 return h.hexdigest()
before=geometry_digest();counts=apply_materials();setup_presentation('catalogue');after=geometry_digest();assert before==after
bpy.ops.wm.save_as_mainfile(filepath=out,compress=True)
report={'source':src,'output':out,'material_counts':counts,'geometry_sha256_before':before,'geometry_sha256_after':after,'geometry_unchanged':before==after,'native_saved_before_fallback':True}
if len(args)>1:
 glb=os.path.abspath(args[1]);table_path=os.path.splitext(glb)[0]+'_materials.json';table=game_fallback(table_path)
 bpy.ops.export_scene.gltf(filepath=glb,export_format='GLB',export_cameras=False,export_lights=False,export_extras=True,export_apply=True)
 report.update(glb=glb,fallback_table=table_path,glb_sha256=hashlib.sha256(open(glb,'rb').read()).hexdigest())
json.dump(report,open(os.path.splitext(out)[0]+'_pbr_report.json','w'),ensure_ascii=False,indent=2)
