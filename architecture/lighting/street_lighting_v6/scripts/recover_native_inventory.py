"""Read-only evaluated inventory from the restored, exact a65 native."""
import bpy,json,hashlib,resource,time
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT.parent/'inputs/Chosun_Campus_Realism_v2.blend'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
expected='a65c2ae19f02c59f655e0c7eedb2482a5c2f6a9c53bb94f2425769dbd4417fbd'
assert Path(bpy.data.filepath)==SOURCE and sha(SOURCE)==expected
scene=bpy.context.scene;deps=bpy.context.evaluated_depsgraph_get();collection_visible={}
def visit(c,parent):
 visible=parent and not c.hide_render;collection_visible[c.name]=collection_visible.get(c.name,False) or visible
 for ch in c.children:visit(ch,visible)
visit(scene.collection,True)
rows={};start=time.time()
for ob in bpy.data.objects:
 row={'type':ob.type,'collections':sorted(c.name for c in ob.users_collection),'render_visible_in_scene':ob.name in scene.objects and not ob.hide_render and any(collection_visible.get(c.name,False) for c in ob.users_collection),'matrix_world':[list(r) for r in ob.matrix_world],'parent':ob.parent.name if ob.parent else None}
 if ob.type=='MESH':
  eo=ob.evaluated_get(deps);corners=[eo.matrix_world@Vector(c) for c in eo.bound_box]
  row['bounds_min']=[min(c[i] for c in corners) for i in range(3)];row['bounds_max']=[max(c[i] for c in corners) for i in range(3)]
 rows[ob.name]=row
out={'input_sha256':expected,'status':'PASS','object_count':len(rows),'objects':rows,'evaluated_world_bounds':True,'script_sha256':sha(Path(__file__)),'read_only':True,'seconds':time.time()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
(ROOT/'qa/recovered_a65_inventory.json').write_text(json.dumps(out,separators=(',',':'))+'\n')
text_rows=[{'name':t.name,'length':len(t.as_string())} for t in bpy.data.texts]
probe={'blender_version':bpy.app.version_string,'objects':len(rows),'texts':text_rows,'cameras':[o.name for o in bpy.data.objects if o.type=='CAMERA'],'lights':[o.name for o in bpy.data.objects if o.type=='LIGHT'],'worlds':[w.name for w in bpy.data.worlds],'scene_property_names':list(scene.keys())}
(ROOT/'qa/recovered_native_probe.json').write_text(json.dumps(probe,indent=2)+'\n');assert sha(SOURCE)==expected;print('RECOVERED_INVENTORY_PASS',len(rows),out['peak_rss_mib'],flush=True)
