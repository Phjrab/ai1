"""Dense post-export checks against actual native terrain and all collision boxes."""
import bpy,json,os,sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=os.path.dirname(__file__)
bpy.ops.wm.open_mainfile(filepath=P+'/campus.blend')
n=json.load(open(P+'/navigation.json'));ob=bpy.data.objects.get('CAMPUS_TERRAIN | continuous hillside ground');assert ob
bvh=BVHTree.FromObject(ob,bpy.context.evaluated_depsgraph_get())
badterrain=[];badcollision=[];count=0
for s in n['walkableSurfaces']:
 p=s['polygon'];minimum=0;worst=None;coll=None
 for tri in s['triangles']:
  a,b,c=[Vector(p[i]) for i in tri]
  for i in range(1,10):
   for j in range(1,10-i):
    pt=a*(i/10)+b*(j/10)+c*(1-(i+j)/10);count+=1
    hit,normal,index,dist=bvh.ray_cast(Vector((pt.x,pt.y,1000)),Vector((0,0,-1)),2000)
    if hit:
     gap=pt.z-hit.z
     if gap<minimum:minimum=gap;worst=list(pt)
    for box in n['collisionBoxes']:
     lo,hi=box['min'],box['max']
     if lo[0]<pt.x<hi[0] and lo[1]<pt.y<hi[1] and lo[2]<pt.z+1<hi[2]:coll={'label':box['label'],'point':list(pt)};break
 if minimum<-.015:badterrain.append({'id':s['id'],'minimum_gap_m':minimum,'point':worst})
 if coll:badcollision.append({'id':s['id'],**coll})
report={'sample_count':count,'walkable_surface_count':len(n['walkableSurfaces']),'terrain_interior_violations':badterrain,'building_collision_interior_violations':badcollision,'status':'pass' if not badterrain and not badcollision else 'fail','method':'Every triangle: positive barycentric i/10,j/10,1-(i+j)/10; actual Blender terrain BVH down-ray, threshold -.015m; strict collision-box XY interior and z+1m'}
json.dump(report,open(P+'/dense_walk_surface_verification.json','w'),ensure_ascii=False,indent=2)
print(json.dumps(report,ensure_ascii=False,indent=2))
