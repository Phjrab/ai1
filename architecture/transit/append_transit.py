"""Import transit assets into a campus Blender scene, without rebuilding the campus.
Usage in build_campus.py after terrain is final:
    from append_transit import append_transit
    append_transit(height_fn=height, include_display_bus=True)
Requires transit_placements.json prepared from game road graph. No unverified fallback placement.
"""
import bpy,json,os,math
from mathutils import Vector
P=os.path.dirname(__file__)

def import_asset(file,name,position,yaw=0,target_collection=None):
 before=set(bpy.data.objects)
 bpy.ops.import_scene.gltf(filepath=os.path.join(P,file))
 added=set(bpy.data.objects)-before
 roots=[o for o in added if o.parent not in added]
 root=bpy.data.objects.new(name,None)
 (target_collection or bpy.context.scene.collection).objects.link(root)
 for o in added:
  if target_collection:
   for c in list(o.users_collection):c.objects.unlink(o)
   target_collection.objects.link(o)
 for o in roots:o.parent=root
 root.location=position;root.rotation_euler.z=yaw
 root['placement_accuracy']='Representative placement snapped to reconstructed campus road; not measured curb location'
 return root

def append_transit(height_fn=None,include_display_bus=True,placement_path=None):
 data=json.load(open(placement_path or P+'/transit_placements.json'))
 c=bpy.data.collections.new('CAMPUS_TRANSIT | Photo-informed representative stops');bpy.context.scene.collection.children.link(c)
 made=[]
 for item in data.get('assets',[]):
  if item.get('role')=='display_bus' and not include_display_bus:continue
  p=list(item['position'])
  # Ground-relative fixtures and road-relative tires must use different surfaces.
  mode=item.get('height_mode','placementZ')
  if height_fn and mode=='groundHeight':p[2]=height_fn(p[0],p[1])+item.get('height_offset',.025)
  elif height_fn and mode=='roadHeight':p[2]=height_fn(p[0],p[1])+item.get('height_offset',.105)
  # placementZ preserves graph-sampled road/safe-sidewalk elevation exactly.
  foundation=None
  if height_fn and item.get('role')=='shelter':
   w,d=(9.8,3.35) if item['file']=='shelter_reference.glb' else (4.95,2.8)
   yaw=item.get('yaw',0);co,si=math.cos(yaw),math.sin(yaw)
   corners=[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]
   ground=[height_fn(p[0]+x*co-y*si,p[1]+x*si+y*co)-.20 for x,y in corners]
   p[2]=max(ground)+.01
   foundation=(corners,ground)
  ob=import_asset(item['file'],item['name'],p,item.get('yaw',0),c)
  if foundation:
   corners,ground=foundation
   verts=[(x,y,g-p[2]-.01) for (x,y),g in zip(corners,ground)]+[(x,y,.035) for x,y in corners]
   mesh=bpy.data.meshes.new('Terrain-conforming shelter foundation');mesh.from_pydata(verts,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);mesh.update()
   foot=bpy.data.objects.new(item['name']+'__terrain_foundation',mesh);c.objects.link(foot);foot.parent=ob;foot['accuracy']='Inferred terrain leveling base, not a photographed dimension'
   mat=bpy.data.materials.get('Concrete plinth')
   if mat:mesh.materials.append(mat)
  if item.get('role')=='display_bus':
   for child in ob.children_recursive:child.name='TRANSIT_DISPLAY_BUS__'+child.name
  ob['role']=item.get('role','static_transit');ob['source']=item.get('source','');ob['inferred']=True;ob['source_url']=item.get('source_url','')
  made.append(ob)
 return made

if __name__=='__main__':
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 append_transit()
 bpy.ops.wm.save_as_mainfile(filepath=P+'/transit_placed.blend')
 bpy.ops.export_scene.gltf(filepath=P+'/transit_placed.glb',export_format='GLB',export_extras=True)
