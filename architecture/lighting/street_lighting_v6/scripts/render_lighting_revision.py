"""Three actual Cycles illustrations, using only unsaved camera/light overrides."""
import bpy,sys,json,math,time,hashlib,resource
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
view=sys.argv[sys.argv.index('--view')+1];assert view in ('evening','night','detail')
manifest=json.loads((ROOT/'lighting_manifest.json').read_text());native=Path(bpy.data.filepath);native_sha=sha(native);assert native_sha==manifest['augmented_native_sha256']
s=bpy.context.scene;s.world=s.world.copy();sun=bpy.data.objects['RV2 | diffused afternoon sun'];original_sun={'energy':sun.data.energy,'color':list(sun.data.color),'matrix':[list(r) for r in sun.matrix_world]}
if view=='evening':
 sky=next(n for n in s.world.node_tree.nodes if n.type=='TEX_SKY');bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');sky.sun_elevation=math.radians(3);sky.sun_rotation=math.radians(258);sky.dust_density=3.5
 sun.rotation_euler=Vector((-.21,-.97,.052)).to_track_quat('Z','Y').to_euler();sun.data.energy=.70;sun.data.color=(1,.68,.43);sun.data.angle=math.radians(3);bg.inputs['Strength'].default_value=.18;exposure=1.3
 overrides={'period':'evening','sun_energy':.70,'world_strength':.18,'sky_elevation_degrees':3,'new_window_emission':False}
else:
 nt=s.world.node_tree;nt.nodes.clear();bg=nt.nodes.new('ShaderNodeBackground');bg.inputs['Color'].default_value=(.025,.045,.085,1);bg.inputs['Strength'].default_value=.45;out=nt.nodes.new('ShaderNodeOutputWorld');nt.links.new(bg.outputs[0],out.inputs['Surface'])
 sun.data.energy=.09;sun.data.color=(.45,.60,1);sun.data.angle=math.radians(10);sun.rotation_euler=Vector((-.25,-.4,.88)).to_track_quat('Z','Y').to_euler();exposure=2.4
 overrides={'period':'night','sun_energy':.09,'world_color':[.025,.045,.085],'world_strength':.45,'new_window_emission':False}
if view=='detail':
 near=min(manifest['fixtures'],key=lambda f:(f['target_position'][0]+72.1)**2+(f['target_position'][1]+535.9)**2)
 target=Vector(near['target_position'])+Vector((0,0,2));base=Vector(near['base_position']);direction=Vector(near['target_position'])-base;direction.z=0;direction.normalize();side=Vector((-direction.y,direction.x,0))
 cd=bpy.data.cameras.new('RV6_LIGHT_Detail_Camera');camera=bpy.data.objects.new(cd.name,cd);s.collection.objects.link(camera);camera.location=target-direction*21+side*14+Vector((0,0,12));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=35;cd.clip_end=3000;s.camera=camera
else:s.camera=bpy.data.objects['RV2_Full_Site']
s.render.engine='CYCLES';s.cycles.device='CPU';s.render.threads_mode='FIXED';s.render.threads=8
s.render.resolution_x=1400 if view!='detail' else 1100;s.render.resolution_y=875 if view!='detail' else 825;s.render.resolution_percentage=100
s.cycles.samples=1024 if view=='detail' else 256;s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=.0075 if view=='detail' else .015;s.cycles.use_denoising=False;s.use_nodes=False
s.cycles.max_bounces=6;s.cycles.diffuse_bounces=3;s.cycles.glossy_bounces=3;s.cycles.seed=0;s.cycles.use_animated_seed=False
if hasattr(s.cycles,'use_light_tree'):s.cycles.use_light_tree=True
assert bool(getattr(s.cycles,'use_light_tree',False)), 'Light Tree is required for the536-source render.'
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=exposure
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.use_persistent_data=False
output=ROOT/'renders'/('Street_Lighting_'+view+'.png');output.parent.mkdir(exist_ok=True);assert not output.exists();s.render.filepath=str(output)
start=time.time();bpy.ops.render.render(write_still=True)
report={'status':'RENDERED_PENDING_PIXEL_REVIEW','native_sha256':native_sha,'lighting_manifest_sha256':sha(ROOT/'lighting_manifest.json'),'view':view,'file':str(output.relative_to(ROOT)),'sha256':sha(output),'bytes':output.stat().st_size,'seconds':time.time()-start,'renderer':{'blender_version':bpy.app.version_string,'binary':bpy.app.binary_path,'binary_sha256':sha(bpy.app.binary_path),'engine':'CYCLES','device':'CPU','denoising':False,'reason':('Installed build lacks OIDN; actual CPU Cycles render without denoising.' if view=='detail' else 'Installed build lacks OIDN; approved 256 sample actual render instead of historical96/OIDN.')},'samples':s.cycles.samples,'adaptive_threshold':s.cycles.adaptive_threshold,'threads':8,'width':s.render.resolution_x,'height':s.render.resolution_y,'camera':{'name':s.camera.name,'location':list(s.camera.location),'rotation_euler':list(s.camera.rotation_euler),'type':s.camera.data.type,'lens':s.camera.data.lens,'ortho_scale':s.camera.data.ortho_scale},'original_sun':original_sun,'lighting_overrides':overrides,'source_native_unchanged':sha(native)==native_sha,'source_saved':False,'new_window_emission':False,'accuracy':'Inferred lighting design, not surveyed installation or measured photometric performance.','render_script_sha256':sha(__file__),'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
if view=='detail':report['light_tree_enabled']=bool(s.cycles.use_light_tree)
report['color_management']={'view_transform':s.view_settings.view_transform,'look':s.view_settings.look,'exposure':s.view_settings.exposure,'gamma':s.view_settings.gamma}
report['native_fixture_powers_unchanged']=all(abs(bpy.data.objects['RV6_LIGHT_'+f['id']+'_beam'].data.energy-f['power_watts'])<.0001 for f in manifest['fixtures'])
assert report['source_native_unchanged'] and report['native_fixture_powers_unchanged'];(ROOT/'qa'/('render_'+view+'.json')).write_text(json.dumps(report,indent=2)+'\n');print('LIGHTING_RENDER_READY',json.dumps(report),flush=True)
