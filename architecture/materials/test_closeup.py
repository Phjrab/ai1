import bpy,sys,os,time,json
P=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,P)
from campus_materials import *
mode=sys.argv[-1];s=bpy.context.scene;s.camera=bpy.data.objects['03_Main_Entrance']
setup_presentation('catalogue',1400);s.cycles.samples=64;s.cycles.adaptive_threshold=.025
if mode=='after':apply_materials()
s.render.filepath=P+'/entrance_'+mode+'.png';t=time.time();bpy.ops.render.render(write_still=True)
json.dump({'mode':mode,'camera':s.camera.name,'samples':64,'seconds':time.time()-t,'width':1400},open(P+'/entrance_'+mode+'.json','w'),indent=2)
