"""Native PBR detail shots; original source never saved, materials never modified."""
import bpy,sys,os,json,hashlib
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,ROOT+'/materials')
from campus_materials import setup_presentation
args=sys.argv[sys.argv.index('--')+1:];name,path,sha=args[:3];width=int(args[3]) if len(args)>3 else 1600;samples=int(args[4]) if len(args)>4 else 48
assert hashlib.sha256(open(bpy.data.filepath,'rb').read()).hexdigest()==sha
cfg=json.load(open(ROOT+'/lighting/final_extra_cameras.json'))[name]
setup_presentation('catalogue',width);s=bpy.context.scene;s.cycles.samples=samples;s.cycles.use_denoising=False
cam=bpy.data.objects.new(name,bpy.data.cameras.new(name));s.collection.objects.link(cam);cam.location=cfg['location'];cam.rotation_euler=(Vector(cfg['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=cfg['ortho_scale'];cam.data.clip_start=.05;cam.data.clip_end=6000;s.camera=cam
s.render.filepath=path;os.makedirs(os.path.dirname(path),exist_ok=True);bpy.ops.render.render(write_still=True)
meta=dict(camera=name,camera_definition=cfg,source=bpy.data.filepath,source_sha256=sha,source_modified=False,geometry_modified=False,materials_modified=False,width=width,height=s.render.resolution_y,samples=samples,denoising=False,file=os.path.basename(path),file_sha256=hashlib.sha256(open(path,'rb').read()).hexdigest(),visual_review='pending')
json.dump(meta,open(os.path.splitext(path)[0]+'.json','w'),ensure_ascii=False,indent=2)
assert hashlib.sha256(open(bpy.data.filepath,'rb').read()).hexdigest()==sha
