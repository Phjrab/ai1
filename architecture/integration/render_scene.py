"""Render named cameras in the integrated original Chosun reconstruction.
Run: blender -b Chosun_Main_Building.blend -t 6 --python render_scene.py -- CAMERA OUTPUT [WIDTH] [SAMPLES]
"""
import bpy, math, sys, os, json
from mathutils import Vector

def aim(obj, point):
    obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()

def setup_lighting():
    scene=bpy.context.scene
    col=bpy.data.collections.get('PRESENTATION')
    if not col:
        col=bpy.data.collections.new('PRESENTATION');scene.collection.children.link(col)
    for ob in list(bpy.data.objects):
        if ob.type=='LIGHT': bpy.data.objects.remove(ob,do_unlink=True)
    world=bpy.data.worlds.new('Clear daylight sky') if not scene.world else scene.world
    scene.world=world;world.use_nodes=True
    world.node_tree.nodes.clear()
    out=world.node_tree.nodes.new('ShaderNodeOutputWorld')
    bg=world.node_tree.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value=(0.68,0.73,0.80,1)
    bg.inputs['Strength'].default_value=0.60
    world.node_tree.links.new(bg.outputs[0],out.inputs[0])
    ld=bpy.data.lights.new('Afternoon sunlight','SUN');ld.energy=3.0;ld.angle=math.radians(5)
    ob=bpy.data.objects.new('Afternoon sunlight',ld);col.objects.link(ob)
    ob.rotation_euler=(math.radians(30),math.radians(-28),math.radians(-35))
    scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.cycles.use_denoising=False;scene.cycles.use_adaptive_sampling=True
    scene.cycles.adaptive_threshold=0.035;scene.cycles.max_bounces=5
    scene.cycles.diffuse_bounces=3;scene.cycles.glossy_bounces=3
    scene.cycles.transmission_bounces=3;scene.cycles.transparent_max_bounces=4
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGB'
    scene.render.film_transparent=False
    scene.view_settings.view_transform='AgX'
    try:scene.view_settings.look='AgX - Medium High Contrast'
    except:pass
    scene.view_settings.exposure=0.35
    return col

CAMERAS={
 '01_Aerial_Front':((265,-355,154),(0,-10,12),31),
 '02_Front_Elevation':((0,-490,92),(0,-8,12),43),
 '03_Main_Entrance':((24,-24,7),(0,0,13),21),
 '04_Rear_Oblique':((-210,275,115),(0,10,14),27),
 '05_Site_Plan':((0,-14,440),(0,-14,0),37),
 '06_Corridor':((10,1.9,1.72),(-11,1.9,1.7),24),
}

def setup_cameras(col):
    for name,(loc,target,lens) in CAMERAS.items():
        cam=bpy.data.objects.get(name)
        if cam is None:
            data=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,data);col.objects.link(cam)
        cam.location=loc;cam.data.lens=lens;cam.data.clip_end=1800;cam.data.clip_start=0.15
        if name=='05_Site_Plan':cam.data.type='ORTHO';cam.data.ortho_scale=515
        aim(cam,target)
    bpy.context.scene.camera=bpy.data.objects['01_Aerial_Front']

def render(camera,path,width=1600,samples=40):
    scene=bpy.context.scene
    scene.camera=bpy.data.objects[camera]
    scene.render.resolution_x=width;scene.render.resolution_y=round(width*0.625)
    scene.render.resolution_percentage=100;scene.cycles.samples=samples
    scene.render.filepath=path
    if camera=='06_Corridor':
        scene.render.engine='BLENDER_EEVEE_NEXT'
        scene.cycles.max_bounces=8;scene.cycles.diffuse_bounces=6
        col=bpy.data.collections.get('PRESENTATION')
        for x in range(-120,25,8):
            ld=bpy.data.lights.new('Corridor photographic lighting','AREA');ld.energy=110;ld.shape='RECTANGLE';ld.size=5.0;ld.size_y=2.7
            ob=bpy.data.objects.new('Corridor ceiling fill',ld);col.objects.link(ob);ob.location=(x,2,3.35)
        scene.view_settings.exposure=0.7
    bpy.ops.render.render(write_still=True)

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    col=setup_lighting();setup_cameras(col)
    if args:render(args[0],args[1],int(args[2]) if len(args)>2 else 1600,int(args[3]) if len(args)>3 else 40)
