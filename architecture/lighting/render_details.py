"""Reproducible detail revision cameras. Run on the before or final model.
blender -b MODEL.blend -t 4 --python render_details.py -- CAMERA OUTPUT.png 1600 64
Optional CAMERA definitions can be added to detail_cameras.json without source edits.
These are original scene renders. The source model is never saved by this script.
"""
import bpy,os,sys,json,hashlib
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(ROOT,'integration'))
from render_scene import setup_lighting
args=sys.argv[sys.argv.index('--')+1:]
name,path=args[:2];width=int(args[2]) if len(args)>2 else 1600;samples=int(args[3]) if len(args)>3 else 64
cfg=json.load(open(os.path.join(ROOT,'lighting','detail_cameras.json')))[name]
col=setup_lighting();scene=bpy.context.scene
cam=bpy.data.objects.new('DETAIL | '+name,bpy.data.cameras.new('DETAIL | '+name));col.objects.link(cam)
cam.location=cfg['location'];cam.rotation_euler=(Vector(cfg['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=cfg.get('lens',48)
cam.data.clip_start=.15;cam.data.clip_end=7000
if 'ortho_scale' in cfg:cam.data.type='ORTHO';cam.data.ortho_scale=cfg['ortho_scale']
scene.camera=cam;scene.render.resolution_x=width;scene.render.resolution_y=round(width*.625);scene.render.resolution_percentage=100
scene.cycles.samples=samples;scene.cycles.sample_clamp_indirect=3;scene.cycles.adaptive_threshold=.025
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.filepath=path
scene.use_nodes=False
os.makedirs(os.path.dirname(os.path.abspath(path)),exist_ok=True)
bpy.ops.render.render(write_still=True)
meta=dict(camera=name,definition=cfg,source=bpy.data.filepath,source_sha256=hashlib.sha256(open(bpy.data.filepath,'rb').read()).hexdigest(),width=width,height=scene.render.resolution_y,samples=samples,engine=scene.render.engine,source_modified=False)
json.dump(meta,open(path.replace('.png','.json'),'w'),ensure_ascii=False,indent=2)
