"""Conceptual same-camera lighting studies, native Blender illumination.
Usage: blender -b FINAL.blend -t 6 --python render_times.py -- night output.png 2000 96
Presets: morning, noon, sunset, night. No geometry or source blend is saved/changed.
These are illustrative lighting treatments, not date-specific solar simulations or
verified operational lighting. Existing glazing receives selectively lit materials;
streetlights are placed beneath the existing model's lamp-head meshes.
"""
import bpy, math, os, sys, hashlib, json
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:]
preset,path=args[:2]; width=int(args[2]) if len(args)>2 else 2000; samples=int(args[3]) if len(args)>3 else 96
scene=bpy.context.scene
col=bpy.data.collections.new('CONCEPTUAL TIME OF DAY LIGHTING');scene.collection.children.link(col)
for ob in list(bpy.data.objects):
 if ob.type=='LIGHT':bpy.data.objects.remove(ob,do_unlink=True)
P={
 'morning': dict(sky=(.52,.66,.90),strength=.36,sun=3.0,color=(1,.79,.58),rotation=(55,-25,-65),exposure=.2),
 'noon': dict(sky=(.63,.75,1),strength=.48,sun=3.5,color=(1,.96,.86),rotation=(18,-12,-20),exposure=.12),
 'sunset':dict(sky=(.28,.40,.73),strength=.23,sun=2.3,color=(1,.39,.12),rotation=(77,10,65),exposure=.15),
 'night':dict(sky=(.18,.28,.53),strength=.18,sun=.48,color=(.46,.62,1),rotation=(32,-30,-45),exposure=.6)
}[preset]
world=scene.world or bpy.data.worlds.new('Time-of-day sky');scene.world=world;world.use_nodes=True
world.node_tree.nodes.clear();bg=world.node_tree.nodes.new('ShaderNodeBackground');out=world.node_tree.nodes.new('ShaderNodeOutputWorld')
bg.inputs['Color'].default_value=(*P['sky'],1);bg.inputs['Strength'].default_value=P['strength'];world.node_tree.links.new(bg.outputs[0],out.inputs[0])
def light(name,typ,pos,power,color,size=1):
 d=bpy.data.lights.new(name,typ);d.energy=power;d.color=color;o=bpy.data.objects.new(name,d);col.objects.link(o);o.location=pos
 if typ=='SUN':d.angle=math.radians(size)
 elif typ=='POINT':d.shadow_soft_size=size
 elif typ=='AREA':d.shape='DISK';d.size=size
 return o
sun=light('Conceptual '+preset+' sun' if preset!='night' else 'Soft moonlight','SUN',(0,0,0),P['sun'],P['color'],3 if preset!='night' else 10)
sun.rotation_euler=tuple(math.radians(v) for v in P['rotation'])
count=0
if preset in ('sunset','night'):
 # Native mesh material assignments only; do not alter model geometry.
 for ob in list(bpy.data.objects):
  if ob.type!='MESH':continue
  slots={i:s.material for i,s in enumerate(ob.material_slots) if s.material and (s.material.name.startswith('CAMPUS • glass') or s.material.name=='Smoky blue green glazing' or (s.material.name=='PHOTO • oxidized teal glazing' and 'source-specific glazing' in ob.name))}
  if not slots:continue
  variants={}
  for i,mat in slots.items():
   n=mat.copy();n.name=mat.name+' | conceptual illuminated rooms';n.use_nodes=True
   if hasattr(n,'cycles'):n.cycles.emission_sampling='NONE'
   bs=next((x for x in n.node_tree.nodes if x.type=='BSDF_PRINCIPLED'),None)
   if bs:
    bs.inputs['Emission Color'].default_value=(1,.59,.24,1);bs.inputs['Emission Strength'].default_value=1.5 if preset=='night' else .65
    bs.inputs['Roughness'].default_value=.42
   ob.data.materials.append(n);variants[i]=len(ob.data.materials)-1
  for poly in ob.data.polygons:
   if poly.material_index in variants:
    v=ob.matrix_world@poly.center
    key=f'{ob.name}:{round(v.x/3)}:{round(v.y/3)}:{round(v.z/3)}'
    k=int(hashlib.md5(key.encode()).hexdigest()[:8],16)%100
    if k<(42 if preset=='night' else 27):poly.material_index=variants[poly.material_index];count+=1
 # Lamps integrated in original mesh, with real local area-light pools.
 lamp=bpy.data.objects.get('CAMPUS street lighting')
 if lamp:
  # Each luminaire box top is unique. Material 1 is original white lamp head.
  for p in lamp.data.polygons:
   if p.material_index==1 and p.normal.z>.9:
    v=lamp.matrix_world@p.center
    light('Warm campus streetlight','AREA',(v.x,v.y,v.z-.2),450 if preset=='night' else 140,(1,.65,.31),1.4)
 for x in range(-180,181,30):
  if abs(x)>=10:light('Main approach lamp','AREA',(x,-22.7,5.02),330 if preset=='night' else 95,(1,.7,.4),1)
 # Existing entrance architecture remains legible under understated facade uplight.
 if preset=='night':
  for x in [-150,-100,-50,0,50,100,150]:
   o=light('Conceptual main facade wash','AREA',(x,-20,3),900,(1,.72,.43),8)
   o.rotation_euler=(Vector((x,0,15))-o.location).to_track_quat('-Z','Y').to_euler()
scene.camera=bpy.data.objects['07_Whole_Campus']
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=samples;scene.cycles.use_denoising=False
scene.cycles.sample_clamp_indirect=2.0
scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.025;scene.cycles.max_bounces=5;scene.cycles.diffuse_bounces=3;scene.cycles.glossy_bounces=3;scene.cycles.transmission_bounces=3;scene.cycles.transparent_max_bounces=4
scene.render.resolution_x=width;scene.render.resolution_y=round(width*.625);scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except:pass
scene.view_settings.exposure=P['exposure'];scene.render.filepath=path
# A physically rendered faint fog-glow pass softens bright points, never adds geometry.
scene.use_nodes=True;tree=scene.node_tree;tree.nodes.clear();rl=tree.nodes.new('CompositorNodeRLayers');comp=tree.nodes.new('CompositorNodeComposite')
if preset=='night':
 glare=tree.nodes.new('CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.quality='HIGH';glare.threshold=1.8;glare.size=6;glare.mix=-.94
 tree.links.new(rl.outputs['Image'],glare.inputs['Image']);tree.links.new(glare.outputs['Image'],comp.inputs['Image'])
else:tree.links.new(rl.outputs['Image'],comp.inputs['Image'])
os.makedirs(os.path.dirname(os.path.abspath(path)),exist_ok=True)
bpy.ops.render.render(write_still=True)
with open(path.replace('.png','.json'),'w') as f:json.dump(dict(preset=preset,source=bpy.data.filepath,source_sha256=hashlib.sha256(open(bpy.data.filepath,'rb').read()).hexdigest(),engine=scene.render.engine,camera=scene.camera.name,camera_location=list(scene.camera.location),camera_rotation=list(scene.camera.rotation_euler),lens=scene.camera.data.lens,width=width,height=scene.render.resolution_y,samples=samples,illuminated_faces=count,lights=len([o for o in col.objects if o.type=='LIGHT']),disclaimer='Conceptual time-of-day lighting. Not a solar study or verified building lighting.'),f,indent=2)
