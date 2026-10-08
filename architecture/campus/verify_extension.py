import bpy,json,os,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=os.path.dirname(__file__);bpy.ops.wm.open_mainfile(filepath=P+'/campus.blend')
nav=json.load(open(P+'/navigation.json'));cov=json.load(open(P+'/campus_coverage.json'))
terrain=next(o for o in bpy.context.scene.objects if o.name.startswith('CAMPUS_TERRAIN'));verts=[terrain.matrix_world@v.co for v in terrain.data.vertices];bvh=BVHTree.FromPolygons(verts,[list(p.vertices) for p in terrain.data.polygons])
collisions=[]
for dest in nav['landmarks']:
 p=dest['position']
 for box in nav['collisionBoxes']:
  if all(box['min'][i]<p[i]<box['max'][i] for i in range(3)):collisions.append((dest['id'],box['label']))
roadn=0;missing=0;low=1000;high=-1000
for ob in bpy.context.scene.objects:
 if not ob.name.startswith(('CAMPUS_ROAD','CAMPUS_PATH')) or ob.type!='MESH':continue
 for vi,v in enumerate(ob.data.vertices):
  if vi%max(1,len(ob.data.vertices)//80):continue
  p=ob.matrix_world@v.co;hit=bvh.ray_cast(Vector((p.x,p.y,500)),Vector((0,0,-1)),1000)
  if hit[0] is None:missing+=1;continue
  d=p.z-hit[0].z;low=min(low,d);high=max(high,d);roadn+=1
ids=['cit_main','cit_1','cit_2','cit_3','cit_4',162];coverage=[d for d in cov['named_coverage'] if d['id'] in ids];names=[o.name for o in bpy.context.scene.objects];bad=[o.name for o in bpy.context.scene.objects if o.type=='MESH' and any(not math.isfinite(x) for v in o.data.vertices for x in v.co)]
report={'building_count':cov['buildings'],'new_buildings':coverage,'required_ids_present':len(coverage)==6,'unique_new_osm_ids':len({a['osm_id'] for a in coverage})==6,'destination_count':len(nav['landmarks']),'destinations_inside_building_collision':collisions,'sampled_road_vertices':roadn,'road_terrain_missing':missing,'road_clearance_m':[low,high],'nonfinite_objects':bad,'mainbuilding_excluded':not any('Gable' in n for n in names),'bounds':nav['bounds']}
json.dump(report,open(P+'/extension_verification.json','w'),ensure_ascii=False,indent=2);print(json.dumps(report,ensure_ascii=False),flush=True)
