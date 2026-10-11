"""Shared geometry for inferred campus luminaires; Blender XYZ in metres."""
import bpy,math
from mathutils import Vector
EMITTER_OFFSET=(0.0,0.0,-0.10)
MATERIAL_NAMES=('RV6_StreetLight_Charcoal_Metal','RV6_StreetLight_Base_Concrete','RV6_StreetLight_Bronze_Collar','RV6_StreetLight_Emissive_Warm3000K')
def material(name,color,metallic,roughness,emission=0):
 assert name not in bpy.data.materials
 m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=roughness
 if emission:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
 return m
def create_materials():
 return [material(MATERIAL_NAMES[0],(.045,.055,.065),.72,.30),material(MATERIAL_NAMES[1],(.24,.26,.27),0,.70),material(MATERIAL_NAMES[2],(.31,.23,.10),.75,.28),material(MATERIAL_NAMES[3],(1,.63,.32),0,.25,5)]
def fixture_mesh(height,materials):
 vertices=[];faces=[];mats=[]
 def cyl(x,y,z,r0,r1,h,mat,n=12):
  k=len(vertices)
  for zz,rr in ((z,r0),(z+h,r1)):vertices.extend((x+rr*math.cos(2*math.pi*i/n),y+rr*math.sin(2*math.pi*i/n),zz) for i in range(n))
  faces.extend([tuple(k+i for i in reversed(range(n))),tuple(k+n+i for i in range(n))]);mats.extend([mat,mat])
  for i in range(n):faces.append((k+i,k+(i+1)%n,k+n+(i+1)%n,k+n+i));mats.append(mat)
 def box(cx,cy,cz,sx,sy,sz,mat):
  k=len(vertices);vertices.extend((cx+x*sx/2,cy+y*sy/2,cz+z*sz/2) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)])
  for ff in [(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]:faces.append(tuple(k+i for i in ff));mats.append(mat)
 cyl(0,0,-.20,.19,.19,.38,1);cyl(0,0,.18,.085,.055,height-.18,0);cyl(0,0,.25,.099,.099,.085,2)
 box(.46,0,height+.03,1.03,.07,.085,0);box(1,0,height,.76,.30,.13,0);box(1,0,height-.069,.65,.24,.012,3)
 mesh=bpy.data.meshes.new('RV6_LIGHT_shared_fixture_'+str(height));mesh.from_pydata(vertices,[],faces);mesh.update()
 for m in materials:mesh.materials.append(m)
 for p,m in zip(mesh.polygons,mats):p.material_index=m
 return mesh
def add_luminaires(plan,scene,with_lights=True):
 assert not any(o.name.startswith('RV6_LIGHT_') for o in bpy.data.objects)
 materials=create_materials();meshes={h:fixture_mesh(h,materials) for h in (4.2,6.2)}
 c=bpy.data.collections.new('RV6_STREET_LIGHTING | inferred design additions');scene.collection.children.link(c);fixtures=[];lights=[]
 for item in plan['fixtures']:
  name='RV6_LIGHT_'+item['id'];h=float(item['collision']['pole_height_m']);base=Vector(item['base_position']);target=Vector(item['target_position']);v=target-base;assert v.xy.length>.01
  yaw=math.atan2(v.y,v.x);o=bpy.data.objects.new(name+'_fixture',meshes[h]);c.objects.link(o);o.location=base;o.rotation_euler.z=yaw
  o['lighting_design_estimated']=True;o['placement_id']=item['id'];o['game_export']=True;o['collision_role']='thin pole and base; explicit contract';o['source_native_sha256']=plan['source_native_sha256']
  assert item['fixture_object_names']==[o.name];fixtures.append(o)
  lamp=Vector(item['lamp_position']);assert (lamp-(base+Vector((math.cos(yaw),math.sin(yaw),h)))).length<.0001
  if with_lights:
   ld=bpy.data.lights.new(name+'_beam','SPOT');ld.energy=item['power_watts'];ld.color=item['color'];ld.spot_size=math.radians(125);ld.spot_blend=.65;ld.shadow_soft_size=.42;ld.use_shadow=True
   light=bpy.data.objects.new(ld.name,ld);c.objects.link(light);light.location=lamp+Vector(EMITTER_OFFSET);light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler();light['game_export']=False;light['design_cct_kelvin']=3000;lights.append(light)
 bpy.context.view_layer.update();return fixtures,lights

def export_fixture_delta(fixtures,path):
 previous=bpy.context.window.scene;temporary=bpy.data.scenes.new('RV6_export_fixture_only')
 for o in fixtures:temporary.collection.objects.link(o)
 try:
  bpy.context.window.scene=temporary
  bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=False,use_active_scene=True,export_extras=True,export_yup=True,export_animations=False,export_cameras=False,export_lights=False)
 finally:bpy.context.window.scene=previous;bpy.data.scenes.remove(temporary)
