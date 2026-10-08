import bpy,os,json
from mathutils import Vector
P=os.path.dirname(__file__);out={}
for f in ['shuttle_bus.glb','shelter_reference.glb','shelter_education.glb','bus_stop_sign.glb','bus_stop_generic.glb']:
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 bpy.ops.import_scene.gltf(filepath=P+'/'+f);bpy.context.view_layer.update()
 pts=[o.matrix_world@Vector(c) for o in bpy.context.scene.objects if o.type=='MESH' for c in [v.co for v in o.data.vertices]]
 lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
 out[f]={'bounds_blender_min':lo,'bounds_blender_max':hi,'mesh_count':sum(o.type=='MESH' for o in bpy.context.scene.objects)}
 if f=='shuttle_bus.glb':
  assert abs(lo[2])<.002,lo
  for s in ['front_L','front_R','rear_L','rear_R']:
   wheel=bpy.data.objects.get('wheel_'+s);assert wheel and wheel.parent.name=='steer_'+s
   assert (wheel.location-Vector((0,0,0))).length<.001
  out[f]['wheel_pivots_verified']=True
 assert min(hi[i]-lo[i] for i in range(3))>0
json.dump(out,open(P+'/import_validation.json','w'),indent=2);print(json.dumps(out,indent=2))
