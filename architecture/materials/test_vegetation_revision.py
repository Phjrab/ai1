import bpy,sys,os,json,time
P=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,P)
from campus_materials import *
s=bpy.context.scene;s.camera=bpy.data.objects['01_Aerial_Front'];setup_presentation('test')
verts=sum(len(o.data.vertices) for o in bpy.data.objects if o.type=='MESH')
# Capture all non-foliage face shading flags, verify them after revision.
flags={o.name:[(i,p.use_smooth) for i,p in enumerate(o.data.polygons) if not(o.data.materials and p.material_index<len(o.data.materials) and o.data.materials[p.material_index] and classify(o.data.materials[p.material_index].name)=='foliage')] for o in bpy.data.objects if o.type=='MESH'}
counts=apply_materials()
assert verts==sum(len(o.data.vertices) for o in bpy.data.objects if o.type=='MESH')
for name,items in flags.items():
 for i,f in items:assert bpy.data.objects[name].data.polygons[i].use_smooth==f,(name,i)
s.render.filepath=P+'/after_vegetation_v11.png';t=time.time();bpy.ops.render.render(write_still=True)
json.dump({'version':VERSION,'seconds':time.time()-t,'vertices_unchanged':True,'non_foliage_normals_unchanged':True,'counts':counts},open(P+'/vegetation_revision_verification.json','w'),indent=2)
bpy.ops.wm.save_as_mainfile(filepath=P+'/PBR_preview_only.blend')
game_fallback(P+'/game_fallback_materials.json')
bpy.ops.export_scene.gltf(filepath=P+'/fallback_test.glb',export_format='GLB',export_cameras=False,export_lights=False)
