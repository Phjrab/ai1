import bpy,math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/workspace/shared/chosun_model/building/chosun_main_building.blend')
s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=False;s.render.resolution_x=1200;s.render.resolution_y=700;s.render.resolution_percentage=100
w=bpy.data.worlds.new('Preview sky');w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.55,.69,.8,1);w.node_tree.nodes['Background'].inputs[1].default_value=.6;s.world=w
bpy.ops.object.light_add(type='SUN',location=(0,-60,100));bpy.context.object.rotation_euler=(math.radians(25),math.radians(-15),math.radians(-25));bpy.context.object.data.energy=3
bpy.ops.object.camera_add(location=(30,65,15));c=bpy.context.object;c.rotation_euler=(Vector((0,17,6))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=60;s.camera=c
s.render.filepath='/workspace/shared/chosun_model/building/rear_detail.png';bpy.ops.render.render(write_still=True)
