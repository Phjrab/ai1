import bpy,sys,os,json,hashlib
names=['INFERRED_GAME_WALK_CONNECTORS | terrain connections, not survey','CAMPUS_PAVING_EDGE 0'];root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def read(path):
 bpy.ops.wm.open_mainfile(filepath=path);res={}
 for name in names:
  o=bpy.data.objects[name];polys={}
  for p in o.data.polygons:
   pts=[tuple(round(v,6) for v in (o.matrix_world@o.data.vertices[i].co)) for i in p.vertices];key=str(sorted(pts))+':'+str(p.material_index);polys[key]=pts
  res[name]=polys
 return res
before=read(root+'/lighting/render_prototypes/campus_9627e996.blend');after=read(root+'/campus/campus.blend');res=[]
for name in names:
 removed=[before[name][k] for k in before[name].keys()-after[name].keys()];added=[after[name][k] for k in after[name].keys()-before[name].keys()];pts=[p for poly in removed+added for p in poly]
 res.append({'object':name,'removed_faces':len(removed),'added_faces':len(added),'changed_bbox':{'min':[min(p[k] for p in pts) for k in range(3)],'max':[max(p[k] for p in pts) for k in range(3)]},'removed_vertices':removed,'added_vertices':added})
json.dump({'rounding_m':.000001,'changed_objects':res},open(root+'/lighting/render_prototypes/changed_regions.json','w'),indent=2);print([(r['object'],r['removed_faces'],r['added_faces'],r['changed_bbox']) for r in res])
