"""Expand the original main-building project with the map-based campus asset."""
import bpy,sys,os,json,math
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(ROOT,'integration'))
from render_scene import setup_lighting,setup_cameras,aim
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT,'building','chosun_main_building.blend'))
with bpy.data.libraries.load(os.path.join(ROOT,'campus','campus.blend'),link=False) as (src,dst):
    assert 'CHOSUN_CAMPUS' in src.collections,src.collections
    dst.collections=['CHOSUN_CAMPUS']
for col in dst.collections:
    if col:bpy.context.scene.collection.children.link(col)
col=setup_lighting();setup_cameras(col)
scene=bpy.context.scene
views={
 '07_Whole_Campus':((1250,-1800,1350),(85,-440,-15),38),
 '08_Campus_Centre':((720,-1020,490),(90,-300,-10),42),
 '09_Campus_Plan':((85,-440,1800),(85,-440,0),45),
}
for name,(loc,target,lens) in views.items():
    ca=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,ca);col.objects.link(ob)
    ob.location=loc;ca.lens=lens;ca.clip_start=.2;ca.clip_end=7000;aim(ob,target)
    if name=='09_Campus_Plan':ca.type='ORTHO';ca.ortho_scale=2350
scene.camera=bpy.data.objects['07_Whole_Campus']
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['project']='Chosun University campus | expanded original main-building project'
scene['accuracy']='Photo- and map-based visual reconstruction, not a measured survey or verified BIM. Heights, terrain and unobserved interiors approximate.'
scene['map_attribution']='Map data © OpenStreetMap contributors, ODbL 1.0. https://www.openstreetmap.org/copyright'
scene['official_reference']='University campus map and facade photos. https://www3.chosun.ac.kr/campusMap/chosun/view.do'
scene['game_project']='The separately maintained Three.js game consumes a copy of this architectural model.'
scene.render.resolution_x=1800;scene.render.resolution_y=1125;scene.render.resolution_percentage=100;scene.cycles.samples=48
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            s=area.spaces.active;s.clip_end=7000;s.shading.type='SOLID';s.shading.color_type='MATERIAL'
            s.shading.light='STUDIO';s.shading.show_shadows=True;s.shading.show_cavity=True
            s.region_3d.view_location=(85,-440,0);s.region_3d.view_distance=1800
            s.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion()
            s.region_3d.view_perspective='CAMERA';s.region_3d.view_camera_zoom=0
out=os.path.join(ROOT,'delivery');os.makedirs(out,exist_ok=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,'Chosun_Campus.blend'),compress=True)
meshes=[o for o in scene.objects if o.type=='MESH']
bad=[o.name for o in meshes if any(not math.isfinite(c) for v in o.data.vertices for c in v.co)]
stats={'mesh_objects':len(meshes),'unique_meshes':len({o.data.name for o in meshes}),'instanced_polygons':sum(len(o.data.polygons) for o in meshes),'nonfinite_objects':bad,'cameras':[o.name for o in scene.objects if o.type=='CAMERA'],'units':'meters','map_attribution':scene['map_attribution']}
json.dump(stats,open(os.path.join(out,'campus_verification.json'),'w'),ensure_ascii=False,indent=2)
print('CAMPUS_INTEGRATED',json.dumps(stats,ensure_ascii=False))
