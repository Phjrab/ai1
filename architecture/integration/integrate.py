import bpy,sys,os,json,math
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(ROOT,'integration'))
from render_scene import setup_lighting,setup_cameras
building=os.path.join(ROOT,'building','chosun_main_building.blend')
site=os.path.join(ROOT,'site','site.blend')
out=os.path.join(ROOT,'delivery')
os.makedirs(out,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=building)
with bpy.data.libraries.load(site,link=False) as (src,dst):
    assert 'CHOSUN_SITE' in src.collections,src.collections
    dst.collections=['CHOSUN_SITE']
for col in dst.collections:
    if col: bpy.context.scene.collection.children.link(col)
col=setup_lighting();setup_cameras(col)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['project']='Chosun University Main Building | original photographic reconstruction'
scene['basis']='Public university photographs and cultural-heritage references; no survey or verified floorplans.'
scene['separate_project']='Architectural model. The Three.js campus exploration game is a separate project.'
scene['interior_status']='Representative photo-backed corridor; room positions and inaccessible interior areas are conceptual.'
scene['site_status']='Terrain, parking, vegetation and vehicles approximate public views; not a current survey.'
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.cycles.samples=40
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.clip_end=2000
            area.spaces.active.region_3d.view_distance=460
            area.spaces.active.region_3d.view_location=(0,-10,10)
            area.spaces.active.shading.type='MATERIAL'
bpy.ops.file.pack_all()
target=os.path.join(out,'Chosun_Main_Building.blend')
bpy.ops.wm.save_as_mainfile(filepath=target,compress=True)
meshes=[o for o in scene.objects if o.type=='MESH']
bad=[o.name for o in meshes if any(not math.isfinite(c) for v in o.data.vertices for c in v.co)]
stats={'mesh_objects':len(meshes),'unique_meshes':len({o.data.name for o in meshes}),'instanced_polygons':sum(len(o.data.polygons) for o in meshes),'nonfinite_objects':bad,'cameras':[o.name for o in scene.objects if o.type=='CAMERA'],'units':'meters','building_length_reference_m':375,'original_reconstruction':True}
json.dump(stats,open(os.path.join(out,'verification.json'),'w'),indent=2)
print('INTEGRATION_READY',target,json.dumps(stats))
