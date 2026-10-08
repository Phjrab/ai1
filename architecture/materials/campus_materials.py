"""Original procedural campus PBR. Blender 4.3+. No geometry changes.
apply_materials() is idempotent. Save native .blend BEFORE game_fallback().
World-position noise uses scene units = metres, independent of object scale.
"""
import bpy, math, json, re
VERSION='campus-pbr-1.1'
# roughness, metalness, micro frequency / m, bump distance m, tonal variation
PROFILES={
 'white_masonry':(.72,0,130,.0008,.025),
 'concrete':(.82,0,95,.0012,.045),
 'stone':(.70,0,160,.0009,.045),
 'brick':(.86,0,115,.0014,.065),
 'asphalt':(.91,0,180,.0017,.10),
 'paving':(.81,0,120,.0012,.045),
 'grass':(.96,0,28,.005,.14),
 'foliage':(.86,0,12,.002,.12),
 'bark':(.93,0,35,.002,.10),
 'metal':(.31,.92,200,.00007,.018),
 'painted_metal':(.46,0,160,.0001,.018),
 'glass':(.16,0,0,0,0),
 'roof':(.79,0,110,.0007,.045),
}
def classify(name):
 n=name.lower()
 if n.startswith('review') and 'observed facade' in n:
  ident=re.search(r'review\s+(\d+)',n)
  key=int(ident.group(1)) if ident else None
  return 'brick' if key in {130,137,140,144,153,155,157,160} else ('white_masonry' if key==159 else 'stone')
 if n.startswith('review') and any(x in n for x in ['sky blue cladding','warm yellow entrance','ochre stair cladding']):return 'painted_metal' if 'sky blue' in n else 'white_masonry'
 if n.startswith('stairs') and any(x in n for x in ['metal','steel','handrail']):return 'metal'
 # Bus livery, signage, art and emissive lamps retain their authored treatment.
 if any(x in n for x in ['coach','campus blue','bus sign','lamp','indicator','diffuser','timetable','campus art','vehicle paint','rose ','rubber','tire','seating']): return None
 if any(x in n for x in ['glass','glazing','glazed','translucent','roof lantern']):return 'glass'
 if any(x in n for x in ['asphalt']):return 'asphalt'
 if 'brick' in n:return 'brick'
 if any(x in n for x in ['grass','playing field','recreation green']):return 'grass'
 if 'canopy ' in n or 'leaf ' in n:return 'foliage'
 if 'bark' in n:return 'bark'
 if any(x in n for x in ['aluminium','aluminum','anodized','alloy','light metal']):return 'metal'
 if any(x in n for x in ['painted steel','metal roof','standing seam','window frame']):return 'painted_metal'
 if any(x in n for x in ['granite paving','granite curb','stair granite','terrazzo']):return 'paving'
 if any(x in n for x in ['granite','limestone','stone cladding','stone podium','chalk stone','ochre stone','honed gray granite','granite nosing']):return 'stone'
 if any(x in n for x in ['concrete','plinth']):return 'concrete'
 if any(x in n for x in ['masonry','cornices','plaster','white trim','ivory']):return 'white_masonry'
 if any(x in n for x in ['membrane','waterproofing']):return 'roof'
 return None

def apply_materials():
 counts={}
 for m in bpy.data.materials:
  p=classify(m.name)
  if not p:continue
  if m.get('campus_pbr_version')==VERSION:continue
  m.use_nodes=True
  old=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  color=list(old.inputs['Base Color'].default_value if old else m.diffuse_color)
  if m.get('campus_original_color'): color=list(m['campus_original_color'])
  m['campus_original_color']=color
  # Modest reflectance, not fully-white architectural paint or candy-like grass.
  if p=='white_masonry' and not m.name.startswith('REVIEW'):color=[min(v,.79) for v in color[:3]]+[1]
  if p=='glass' and not m.name.startswith('REVIEW'):color=[color[0]*.55,color[1]*.65,color[2]*.72,1]
  if p=='grass':color=[color[0]*.65,color[1]*.70,color[2]*.62,1]
  if p=='foliage':color=[color[0]*.73,color[1]*.78,color[2]*.68,1]
  r,metal,freq,dist,var=PROFILES[p]
  m['campus_pbr_version']=VERSION;m['campus_profile']=p
  m['campus_fallback_color']=color;m['campus_fallback_roughness']=r;m['campus_fallback_metalness']=metal
  m.diffuse_color=color;m.roughness=r;m.metallic=metal
  nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');out.location=(850,0)
  bs=nt.nodes.new('ShaderNodeBsdfPrincipled');bs.location=(570,0)
  bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=r;bs.inputs['Metallic'].default_value=metal
  nt.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
  if p=='glass':
   # Thin, backed facade panels: opaque tinted dielectric + polished coat.
   # Honest approximation avoids rendering nonexistent interiors through solids.
   bs.inputs['IOR'].default_value=1.5;bs.inputs['Coat Weight'].default_value=.8;bs.inputs['Coat Roughness'].default_value=.10
  else:
   pos=nt.nodes.new('ShaderNodeNewGeometry');pos.location=(-900,0)
   noise=nt.nodes.new('ShaderNodeTexNoise');noise.location=(-650,0);noise.inputs['Scale'].default_value=freq;noise.inputs['Detail'].default_value=2;noise.inputs['Roughness'].default_value=.65
   nt.links.new(pos.outputs['Position'],noise.inputs['Vector'])
   ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.location=(-360,130)
   for e,mul in zip(ramp.color_ramp.elements,[1-var,1+var]):e.color=tuple(min(.95,v*mul) for v in color[:3])+(1,)
   nt.links.new(noise.outputs['Fac'],ramp.inputs[0]);nt.links.new(ramp.outputs['Color'],bs.inputs['Base Color'])
   rough=nt.nodes.new('ShaderNodeMapRange');rough.location=(-80,-100)
   rough.inputs['To Min'].default_value=max(.05,r-.065);rough.inputs['To Max'].default_value=min(1,r+.065)
   nt.links.new(noise.outputs['Fac'],rough.inputs[0]);nt.links.new(rough.outputs['Result'],bs.inputs['Roughness'])
   bump=nt.nodes.new('ShaderNodeBump');bump.location=(290,-180);bump.inputs['Strength'].default_value=.25;bump.inputs['Distance'].default_value=dist
   nt.links.new(noise.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
   # Grass gets a metre-scale variation in addition to fine blades approximation.
   if p in ('grass','foliage'):
    noise.inputs['Scale'].default_value=.45 if p=='grass' else 1.4
    fine=nt.nodes.new('ShaderNodeTexNoise');fine.location=(-380,-400);fine.inputs['Scale'].default_value=freq;fine.inputs['Detail'].default_value=2
    nt.links.new(pos.outputs['Position'],fine.inputs['Vector']);nt.links.new(fine.outputs['Fac'],bump.inputs['Height'])
  if p=='foliage':
   # Broad per-crown spatial variation works even when all trees share one mesh.
   # Object Random adds small independent variation for separate tree instances.
   noise.inputs['Scale'].default_value=.18
   oi=nt.nodes.new('ShaderNodeObjectInfo');oi.location=(-900,350)
   mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.16
   add=nt.nodes.new('ShaderNodeMath');add.operation='ADD'
   nt.links.new(oi.outputs['Random'],mul.inputs[0]);nt.links.new(noise.outputs['Fac'],add.inputs[0]);nt.links.new(mul.outputs[0],add.inputs[1])
   nt.links.new(add.outputs[0],ramp.inputs[0]);nt.links.new(add.outputs[0],rough.inputs[0])
   bs.inputs['Sheen Weight'].default_value=.14;bs.inputs['Sheen Roughness'].default_value=.75
   bs.inputs['Subsurface Weight'].default_value=.025;bs.inputs['Subsurface Radius'].default_value=(.06,.035,.02)
  counts[p]=counts.get(p,0)+1
 # Only foliage-slot faces are smoothed; building hard edges and bark are untouched.
 smooth_foliage_normals()
 return counts

def smooth_foliage_normals():
 changed=0
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  slots={i for i,m in enumerate(o.data.materials) if m and classify(m.name)=='foliage'}
  if not slots:continue
  for p in o.data.polygons:
   if p.material_index in slots and not p.use_smooth:p.use_smooth=True;changed+=1
  o.data.update()
 return changed

def game_fallback(json_path=None):
 """Mutates materials in current in-memory scene; use only export copy/process."""
 table={}
 for m in bpy.data.materials:
  if not m.get('campus_pbr_version'):continue
  c=list(m['campus_fallback_color']);r=m['campus_fallback_roughness'];metal=m['campus_fallback_metalness']
  nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');bs=nt.nodes.new('ShaderNodeBsdfPrincipled')
  bs.inputs['Base Color'].default_value=c;bs.inputs['Roughness'].default_value=r;bs.inputs['Metallic'].default_value=metal
  nt.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
  table[m.name]={'profile':m['campus_profile'],'baseColorLinear':c,'roughness':r,'metalness':metal,'alphaMode':'OPAQUE','transmission':0}
 if json_path:json.dump({'version':VERSION,'colorSpace':'linear-sRGB','materials':table},open(json_path,'w'),ensure_ascii=False,indent=2)
 return table

def setup_presentation(preset='catalogue',width=None):
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU'
 conf={'test':(1400,24,.06),'catalogue':(1600,48,.035),'hero':(2400,128,.018)}[preset]
 s.render.resolution_x=width or conf[0];s.render.resolution_y=round(s.render.resolution_x*.625);s.render.resolution_percentage=100
 s.cycles.samples=conf[1];s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=conf[2]
 s.cycles.use_denoising=False;s.cycles.max_bounces=5;s.cycles.diffuse_bounces=3;s.cycles.glossy_bounces=3;s.cycles.transmission_bounces=2
 s.cycles.sample_clamp_indirect=3;s.render.use_persistent_data=False
 s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=-.35
 s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.use_nodes=False
 # One analytic sunlight + gradient sky. No downloaded HDRI or licensed texture.
 for o in list(bpy.data.objects):
  if o.type=='LIGHT':bpy.data.objects.remove(o,do_unlink=True)
 d=bpy.data.lights.new('PBR natural afternoon sun','SUN');d.energy=2.6;d.angle=math.radians(.8);d.color=(1,.94,.84)
 o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.rotation_euler=tuple(math.radians(v) for v in (32,-27,-38))
 w=bpy.data.worlds.new('Original procedural daylight') if not s.world else s.world;s.world=w;w.use_nodes=True
 nt=w.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputWorld');bg=nt.nodes.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=.5
 tc=nt.nodes.new('ShaderNodeTexCoord');sep=nt.nodes.new('ShaderNodeSeparateXYZ');ramp=nt.nodes.new('ShaderNodeValToRGB')
 ramp.color_ramp.elements[0].color=(.65,.70,.76,1);ramp.color_ramp.elements[1].color=(.22,.40,.68,1)
 nt.links.new(tc.outputs['Normal'],sep.inputs[0]);nt.links.new(sep.outputs['Z'],ramp.inputs[0]);nt.links.new(ramp.outputs[0],bg.inputs[0]);nt.links.new(bg.outputs[0],out.inputs[0])
 return conf
