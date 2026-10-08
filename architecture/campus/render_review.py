import bpy,sys,json,os,math
from mathutils import Vector
P=os.path.dirname(__file__);OUT=P+'/review_build';bpy.ops.wm.open_mainfile(filepath=OUT+'/campus.blend')
cat=json.load(open(OUT+'/building_render_catalog.json'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=False;s.render.resolution_x=960;s.render.resolution_y=720;s.render.resolution_percentage=100;s.world.color=(.65,.65,.65)
s.view_settings.view_transform='Standard';s.view_settings.look='Medium High Contrast'
bpy.ops.object.light_add(type='SUN',location=(-200,-400,400));sun=bpy.context.object;sun.rotation_euler=(.35,-.5,-.35);sun.data.energy=2.3
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.clip_end=5000;s.camera=cam
os.makedirs(OUT+'/renders',exist_ok=True)
for bid in [128,143,139,152,166,153,158,164,129,137,144,165,171,176,178]:
 row=next(a for a in cat if a['id']==bid);c=bpy.data.collections[row['collection']];visible=set(c.all_objects)
 for ob in bpy.data.objects:
  if ob.type=='MESH':ob.hide_render=ob not in visible
 cam.location=row['camera'];cam.rotation_euler=(Vector(row['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=row['orthographic_scale'];s.render.filepath=OUT+'/renders/'+str(bid)+'.png';bpy.ops.render.render(write_still=True)
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.hide_render=not ob.name.startswith('STAIR_DETAIL')
cam.location=(32,-125,14);cam.rotation_euler=(Vector((0,-56,-7))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=85;s.render.filepath=OUT+'/renders/stairs108.png';bpy.ops.render.render(write_still=True)
