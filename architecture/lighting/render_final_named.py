import bpy,sys,os,json,hashlib,time
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,ROOT+'/materials')
from campus_materials import setup_presentation
args=sys.argv[sys.argv.index('--')+1:];name,path,sha=args[:3];width=int(args[3]) if len(args)>3 else 1600;samples=int(args[4]) if len(args)>4 else 32
assert hashlib.sha256(open(bpy.data.filepath,'rb').read()).hexdigest()==sha
setup_presentation('catalogue',width);s=bpy.context.scene;s.cycles.samples=samples;s.cycles.use_denoising=False;s.camera=bpy.data.objects[name];s.render.filepath=path;os.makedirs(os.path.dirname(path),exist_ok=True);start=time.time();bpy.ops.render.render(write_still=True)
json.dump(dict(camera=name,source=bpy.data.filepath,source_sha256=sha,source_modified=False,geometry_modified=False,materials_modified=False,width=width,height=s.render.resolution_y,samples=samples,seconds=time.time()-start,file=os.path.basename(path),file_sha256=hashlib.sha256(open(path,'rb').read()).hexdigest()),open(os.path.splitext(path)[0]+'.json','w'),ensure_ascii=False,indent=2)
assert hashlib.sha256(open(bpy.data.filepath,'rb').read()).hexdigest()==sha
