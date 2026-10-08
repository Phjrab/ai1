import bpy,json,os,math
from mathutils import Vector
P=os.path.dirname(__file__);OUT=P+'/review_build';bpy.ops.wm.open_mainfile(filepath=OUT+'/campus.blend')
with bpy.data.libraries.load(os.path.dirname(P)+'/building/chosun_main_building.blend',link=False) as (a,b):b.collections=[c for c in a.collections if c.startswith('CHOSUN')]
for c in b.collections:
 if c and c.name not in bpy.context.scene.collection.children:bpy.context.scene.collection.children.link(c)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=False;s.render.resolution_x=1200;s.render.resolution_y=850;s.render.resolution_percentage=100;s.world.color=(.8,.8,.8)
bpy.ops.object.light_add(type='SUN',location=(-200,-400,400));sun=bpy.context.object;sun.rotation_euler=(.35,-.5,-.35);sun.data.energy=3
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.clip_end=5000;s.camera=cam
for name,loc,target,scale in [('priority_context',(245,-380,130),(112,-174,-5),230),('dental_context',(-105,-835,140),(-322,-620,-20),200),('stairs_context',(26,-178,30),(0,-53,-8),120)]:
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;s.render.filepath=OUT+'/renders/'+name+'.png';bpy.ops.render.render(write_still=True)
