import bpy, math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/workspace/shared/chosun_model/site/site.blend')
s=bpy.context.scene
bpy.ops.object.light_add(type='SUN',location=(0,-50,120));bpy.context.object.rotation_euler=(math.radians(25),math.radians(-25),math.radians(-20));bpy.context.object.data.energy=3
bpy.ops.object.camera_add(location=(230,-335,215));c=bpy.context.object;c.rotation_euler=(Vector((0,-10,0))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=495;s.camera=c
s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=False;s.render.resolution_x=1200;s.render.resolution_y=800;s.render.resolution_percentage=100;s.render.filepath='/workspace/shared/chosun_model/site/site_qa.png';s.world.color=(.5,.5,.5);bpy.ops.render.render(write_still=True)
