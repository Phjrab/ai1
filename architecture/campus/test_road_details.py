import bpy,os,sys,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=os.path.dirname(__file__);sys.path.insert(0,P)
from mesh_architecture import Mesh
from road_continuity import build_continuous_roads
bpy.ops.wm.open_mainfile(filepath=P+'/campus.blend')
terrain=bpy.data.objects['CAMPUS_TERRAIN | continuous hillside ground'];tree=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def height(x,y):
 hit=tree.ray_cast(Vector((min(659.999,max(-489.999,x)),min(239.999,max(-1119.999,y)),500)),Vector((0,0,-1)))
 return hit[0].z+.20
col=bpy.data.collections.new('ROAD DETAILS STANDALONE TEST');bpy.context.scene.collection.children.link(col)
nav={'roads':[]};build_continuous_roads([],[],height,Mesh,col,bpy.data.materials['CAMPUS • weathered asphalt'],bpy.data.materials['CAMPUS • granite paving'],nav,P)
r={'surface_samples':0,'below_terrain':0,'min_clearance':1000,'max_clearance':-1000,'invalid_faces':0,'crossings':len(nav['crossings']),'objects':len(col.objects),'scope':'Standalone new road detail module on existing campus terrain. Grounding skirts intentionally penetrate 0.015m.'}
for ob in col.objects:
 ob.data.calc_loop_triangles()
 for tri in ob.data.loop_triangles:
  if tri.area<1e-9:r['invalid_faces']+=1
  if 'EDGE' in ob.name or ' edge ' in ob.name:continue
  ps=[ob.data.vertices[i].co for i in tri.vertices]
  for w in [(1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)]:
   p=sum((ps[i]*w[i] for i in range(3)),Vector());gap=p.z-(height(p.x,p.y)-.2)
   r['surface_samples']+=1;r['min_clearance']=min(r['min_clearance'],gap);r['max_clearance']=max(r['max_clearance'],gap)
   if gap<-.005:r['below_terrain']+=1
json.dump(r,open(P+'/road_details_qa.json','w'),indent=2);print(json.dumps(r,indent=2));assert not r['below_terrain'];assert r['min_clearance']>.29;assert r['crossings']==39;assert r['invalid_faces']==0
# Save ONLY QA scene; do not replace modeler's final files or nav.
bpy.ops.wm.save_as_mainfile(filepath=P+'/road_details_qa.blend')
