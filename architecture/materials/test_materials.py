import bpy,sys,os,json,time,hashlib
P=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,P)
from campus_materials import *
args=sys.argv[sys.argv.index('--')+1:];mode=args[0]
s=bpy.context.scene
s.camera=bpy.data.objects['01_Aerial_Front']
# Identical camera and modern lighting for a controlled material-only comparison.
setup_presentation('test');counts={}
if mode=='after':counts=apply_materials()
s.render.filepath=P+'/'+mode+'.png'
t=time.time();bpy.ops.render.render(write_still=True)
json.dump({'mode':mode,'source':bpy.data.filepath,'sha256':hashlib.sha256(open(bpy.data.filepath,'rb').read()).hexdigest(),'camera':s.camera.name,'seconds':time.time()-t,'samples':s.cycles.samples,'width':s.render.resolution_x,'material_counts':counts,'lighting':'identical original procedural daylight'},open(P+'/'+mode+'.json','w'),indent=2)
if mode=='after':
 bpy.ops.wm.save_as_mainfile(filepath=P+'/PBR_preview_only.blend')
 game_fallback(P+'/game_fallback_materials.json')
 bpy.ops.export_scene.gltf(filepath=P+'/fallback_test.glb',export_format='GLB',use_selection=False,export_cameras=False,export_lights=False)
