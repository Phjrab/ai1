import os,sys,json,math
P=os.path.dirname(__file__);sys.path.insert(0,P+'/vendor')
from shapely.geometry import Polygon
from shapely.ops import unary_union
c=json.load(open(P+'/road_surface_cache.json'));d=json.load(open(P+'/road_details_cache.json'))
def geom(layer):return unary_union([Polygon([layer['vertices'][i] for i in f]) for f in layer['faces']])
vehicle=geom(c['layers'][0]);pedestrian=geom(c['layers'][1]);paint=geom(d['white']);new_ped=geom(d['pedestrian_surface']);ramps=unary_union([geom(r) for r in d['ramps']])
r={'crossing_count':len(d['crossings']),'explicitly_unmarked_or_unknown_skipped':len(d['skipped']),'pedestrian_transition_count':len(d['ramps']),'white_paint_outside_carriageway_m2':paint.difference(vehicle).area,'pedestrian_coverage_difference_m2':new_ped.union(ramps).symmetric_difference(pedestrian).area,'sidewalk_ramp_overlap_m2':new_ped.intersection(ramps).area,'faces_crossing_terrain_partition':0}
for layer in [d['white'],d['yellow'],d['tactile'],d['pedestrian_surface']]+d['ramps']:
 for f in layer['faces']:
  ps=[layer['vertices'][i] for i in f];mx=sum(x for x,y in ps)/3;my=sum(y for x,y in ps)/3;x0=-490+math.floor((mx+490)/5)*5;y0=-1120+math.floor((my+1120)/5)*5;diag=my-y0<=mx-x0
  for x,y in ps:
   if x<x0-1e-6 or x>x0+5+1e-6 or y<y0-1e-6 or y>y0+5+1e-6 or (diag and y-y0>x-x0+1e-6) or (not diag and y-y0<x-x0-1e-6):r['faces_crossing_terrain_partition']+=1;break
assert r['white_paint_outside_carriageway_m2']<1e-4
assert r['pedestrian_coverage_difference_m2']<1e-4
assert r['sidewalk_ramp_overlap_m2']<1e-4
assert r['faces_crossing_terrain_partition']==0
json.dump(r,open(P+'/road_details_geometry_audit.json','w'),indent=2);print(json.dumps(r,indent=2))
