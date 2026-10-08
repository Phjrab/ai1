import bpy,math
from mathutils import Vector
from pathlib import Path
p=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(p/'shuttle_livery.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.30,.36,.45,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
mat=bpy.data.materials.new('Studio warm floor');mat.diffuse_color=(.24,.25,.26,1)
bpy.ops.mesh.primitive_plane_add(size=200);bpy.context.object.data.materials.append(mat)
for loc,energy,size in [((-7,5,12),2300,8),((6,-3,9),1700,7),((1,10,6),1000,6)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=energy;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,1.5))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(-12,15,7));cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=13.8
scene.render.resolution_x=1800;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
for name,loc in [('shuttle_livery_front_left.png',(-12,14,6.8)),('shuttle_livery_rear_left.png',(-12,-14,6.5)),('shuttle_livery_side.png',(-16,1,4.4))]:
 cam.location=loc;cam.rotation_euler=(Vector((0,0,1.65))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(p/name);bpy.ops.render.render(write_still=True)
# Replace only bus in source asset library. Shelter and placements are kept verbatim.
bpy.ops.wm.open_mainfile(filepath=str(p/'transit_assets.blend'))
old=bpy.data.objects.get('CHOSUN_SHUTTLE');loc=old.location.copy()
for o in list(old.children_recursive)+[old]:bpy.data.objects.remove(o,do_unlink=True)
with bpy.data.libraries.load(str(p/'shuttle_livery.blend'),link=False) as (src,dst):dst.objects=src.objects
for o in dst.objects:
 if o and o.name not in bpy.context.scene.objects:bpy.context.collection.objects.link(o)
bpy.data.objects['CHOSUN_SHUTTLE'].location=loc
bpy.ops.wm.save_as_mainfile(filepath=str(p/'transit_assets.blend'))
