"""Use precisely the campus builder's height definition before any terrain generation."""
import bpy,os,json,sys
P=os.path.dirname(__file__);CP=os.path.join(os.path.dirname(P),'campus');sys.path.insert(0,P)
source=open(CP+'/build_campus.py').read().split('# Core grounds and surrounding woodland skirt.')[0]
ns={'__file__':CP+'/build_campus.py'};exec(compile(source,CP+'/build_campus.py','exec'),ns)
height=ns['height']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
from append_transit import append_transit
objs=append_transit(height_fn=height)
data=json.load(open(P+'/transit_placements.json'))
for item,ob in zip(data['assets'],objs):item['position']=list(ob.location);item['z_recomputed_from_final_campus_height']=True
for stop in data['stops']:
 stop['position'][2]=height(*stop['position'][:2])+.105
 for key in ['waitingPosition','shelterPosition']:
  if stop.get(key):stop[key][2]=height(*stop[key][:2])-.18
# Route heights are road centerline geometry, not sampled from sideways furniture points.
if isinstance(data.get('route'),dict):
 for point in data['route'].get('points',[]):point[2]=height(*point[:2])+.095
elif isinstance(data.get('route'),list):
 for point in data['route']:point[2]=height(*point[:2])+.095
data['xy_ground_resample_required']=False
json.dump(data,open(P+'/transit_placements.json','w'),ensure_ascii=False,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=P+'/transit_placed.blend')
bpy.ops.export_scene.gltf(filepath=P+'/transit_placed.glb',export_format='GLB',export_extras=True)
print('TRANSIT_PLACED_READY',len(objs))
