import bpy,math,os
from mathutils import Vector
P=os.path.dirname(__file__);bpy.ops.wm.open_mainfile(filepath=P+'/road_details_qa.blend')
col=bpy.data.collections['ROAD DETAILS STANDALONE TEST']
for ob in bpy.data.objects:
 if ob.type=='MESH' and ob.name.startswith('CAMPUS_CONTINUOUS') and ob.name not in col.objects:ob.hide_render=True
pts=[v.co for o in col.objects if o.name.startswith('CAMPUS_CROSSINGS') for v in o.data.vertices if abs(v.co.x+10.621)<5 and abs(v.co.y+269.02)<8]
z=sum(p.z for p in pts)/len(pts)
target=Vector((-10.621,-269.02,z));bpy.ops.object.camera_add(location=target+Vector((25,-32,29)));camera=bpy.context.object;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=54;bpy.context.scene.camera=camera
bpy.ops.object.light_add(type='SUN',location=(0,0,200));bpy.context.object.rotation_euler=(.5,-.5,-.3);bpy.context.object.data.energy=2
sc=bpy.context.scene;sc.render.engine='BLENDER_EEVEE_NEXT';sc.render.resolution_x=1000;sc.render.resolution_y=760;sc.render.resolution_percentage=100;sc.world.color=(.7,.7,.7);sc.render.filepath=P+'/road_details_crossing_qa.png';bpy.ops.render.render(write_still=True)
