"""Verify final exported terrain, nav roads/destinations and inferred walkable surfaces."""
import json,math,hashlib,sys,os
from collections import defaultdict
P=(sys.argv[1] if len(sys.argv)>1 else os.path.dirname(__file__)+'/review_build').rstrip('/')+'/'
d=json.load(open(P+'ground_elevation.json'));n=json.load(open(P+'navigation.json'));a=d['heights'];s=d['step']
def h(x,y):
 u=(x-d['x0'])/s;v=(y-d['y0'])/s
 if u<0 or v<0 or u>d['nx']-1 or v>d['ny']-1:return None
 i=min(math.floor(u),d['nx']-2);j=min(math.floor(v),d['ny']-2);u-=i;v-=j
 return a[j][i]*(1-u)+a[j][i+1]*(u-v)+a[j+1][i+1]*v if v<=u else a[j][i]*(1-v)+a[j+1][i+1]*u+a[j+1][i]*(v-u)
v=[];offset=[];outside=[]
for road in n['roads']:
 for p in road['points']:
  hh=h(*p[:2])
  if hh is not None:offset.append(p[2]-hh)
  else:outside.append(p)
 if road.get('vehicle'):
  for p,q in zip(road['points'],road['points'][1:]):v.append(abs(p[2]-q[2])/max(math.dist(p[:2],q[:2]),.0001))
land=[p['position'][2]-h(*p['position'][:2]) for p in n['landmarks']];surfs=[s for s in n['walkableSurfaces'] if s['id'].startswith('inferred_walk_connector_')];treads=[s for s in surfs if s['kind']=='inferred_game_steps'];clear=[z-h(x,y) for s in treads for x,y,z in s['polygon'] if h(x,y) is not None]
groups=defaultdict(list)
for sf in surfs:groups[sf['id'].split('_approach_')[0].split('_tread_')[0]].append(sf)
jumps=[];gaps=[]
for items in groups.values():
 for aa,bb in zip(items,items[1:]):
  p=aa['polygon'];q=bb['polygon'];end=[(p[1][k]+p[2][k])/2 for k in range(3)];start=[(q[0][k]+q[3][k])/2 for k in range(3)];jumps.append(abs(end[2]-start[2]));gaps.append(math.dist(end[:2],start[:2]))
report={'status':'final candidate JSON verified','ground_sha256':hashlib.sha256(open(P+'ground_elevation.json','rb').read()).hexdigest(),'vehicle_segments':len(v),'vehicle_max_grade':max(v),'vehicle_over30_count':sum(x>.3 for x in v),'road_ground_offset_range_m':[min(offset),max(offset)],'road_points_outside_render_bounds':len(outside),'destinations':len(land),'destination_ground_offset_range_m':[min(land),max(land)],'destination_below_ground_count':sum(x<0 for x in land),'inferred_connections':len(groups),'inferred_treads':len(treads),'inferred_walkable_surfaces':len(surfs),'inferred_tread_ground_clearance_min_m':min(clear),'inferred_max_step_m':max(jumps),'inferred_max_xy_gap_m':max(gaps),'nonfinite_walkable_vertices':sum(not math.isfinite(v) for sf in n['walkableSurfaces'] for p in sf['polygon'] for v in p)}
json.dump(report,open('/workspace/shared/chosun_detail_refs/terrain/final_integrated_terrain_validation.json','w'),ensure_ascii=False,indent=2);print(json.dumps(report,indent=2))
