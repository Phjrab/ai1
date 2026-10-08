import bpy,json,os
from mathutils.bvhtree import BVHTree
from mathutils import Vector
P=os.path.dirname(__file__)
bpy.ops.wm.open_mainfile(filepath=P+'/campus.blend')
terrain=bpy.data.objects.get('CAMPUS_TERRAIN | continuous hillside ground');tree=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
result={'surface':'old CAMPUS_ROAD and CAMPUS_PATH','triangle_samples':0,'below_terrain':0,'min_clearance':1000,'examples':[]}
for ob in bpy.data.objects:
 if not (ob.name.startswith('CAMPUS_ROAD') or ob.name.startswith('CAMPUS_PATH')) or ob.type!='MESH':continue
 ob.data.calc_loop_triangles()
 for tri in ob.data.loop_triangles:
  ps=[ob.matrix_world@ob.data.vertices[i].co for i in tri.vertices]
  for weights in [(1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)]:
   p=sum((ps[i]*weights[i] for i in range(3)),Vector())
   hit=tree.ray_cast(Vector((p.x,p.y,500)),Vector((0,0,-1)))
   if hit[0] is None:continue
   gap=p.z-hit[0].z;result['triangle_samples']+=1;result['min_clearance']=min(result['min_clearance'],gap)
   if gap<-.005:
    result['below_terrain']+=1
    if len(result['examples'])<20:result['examples'].append({'object':ob.name,'point':list(p),'clearance':gap})
json.dump(result,open(P+'/road_before_surface_qa.json','w'),indent=2);print(result)
