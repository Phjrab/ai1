import bpy,math,sys
from mathutils import Vector
P='/workspace/shared/chosun_model/campus'
bpy.ops.wm.open_mainfile(filepath=P+'/campus.blend')
with bpy.data.libraries.load('/workspace/shared/chosun_model/building/chosun_main_building.blend',link=False) as (a,b):b.collections=[c for c in a.collections if c.startswith('CHOSUN')]
for c in b.collections:
 if c and not c.name in bpy.context.scene.collection.children:bpy.context.scene.collection.children.link(c)
bpy.ops.object.light_add(type='SUN',location=(0,-200,900));bpy.context.object.rotation_euler=(.35,-.5,-.3);bpy.context.object.data.energy=3
bpy.ops.object.camera_add(location=(1250,-1500,1250));c=bpy.context.object;c.rotation_euler=(Vector((50,-390,0))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=1500;c.data.clip_end=8000;bpy.context.scene.camera=c
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=10;s.cycles.use_denoising=False;s.render.resolution_x=1600;s.render.resolution_y=1100;s.render.resolution_percentage=100;s.world.color=(.6,.6,.6);s.render.filepath=P+'/campus_qa.png';bpy.ops.render.render(write_still=True)
