"""Idempotent local cache update: retain all unaffected original triangles."""
import os,sys,json,hashlib
P=os.path.dirname(__file__);sys.path.insert(0,P+'/vendor')
from shapely.geometry import Polygon
from shapely import constrained_delaunay_triangles
from shapely.ops import unary_union
from road_surface_masks import detailed_stair_exclusion
mask=detailed_stair_exclusion()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def clip(layer):
 verts=layer['vertices'][:];index={tuple(v):i for i,v in enumerate(verts)};faces=[];removed=0
 def vi(p):
  key=(round(p[0],7),round(p[1],7))
  if key not in index:index[key]=len(verts);verts.append(list(key))
  return index[key]
 for f in layer['faces']:
  tri=Polygon([verts[i] for i in f]);cut=tri.intersection(mask)
  if cut.area<1e-12:faces.append(f);continue
  removed+=cut.area
  diff=tri.difference(mask)
  if diff.is_empty:continue
  for part in ([diff] if diff.geom_type=='Polygon' else diff.geoms):
   if part.geom_type!='Polygon' or part.area<1e-10:continue
   for t in constrained_delaunay_triangles(part).geoms:
    if t.area>1e-8:faces.append([vi(v) for v in list(t.exterior.coords)[:3]])
 layer['vertices']=verts;layer['faces']=faces
 if 'area_m2' in layer:layer['area_m2']-=removed
 layer['render_exclusion']='Detailed central 108 stairs/landings; nav graph preserved'
 overlap=sum(Polygon([verts[i] for i in f]).intersection(mask).area for f in faces)
 assert overlap<1e-7,(overlap,removed)
 return {'removed_m2':removed,'remaining_overlap_m2':overlap}
cache_path=P+'/road_surface_cache.json';d=json.load(open(cache_path));g0=open(P+'/road_graph.json','rb').read();vh=digest(d['layers'][0]);rh=digest(d['roads']);r={'base_pedestrian':clip(d['layers'][1])};assert digest(d['layers'][0])==vh and digest(d['roads'])==rh
json.dump(d,open(cache_path,'w'),separators=(',',':'))
p=P+'/road_details_cache.json';q=json.load(open(p));r['detail_pedestrian']=clip(q['pedestrian_surface']);r['ramps']=[clip(a) for a in q['ramps']];r['tactile']=clip(q['tactile']);json.dump(q,open(p,'w'),ensure_ascii=False,separators=(',',':'))
assert open(P+'/road_graph.json','rb').read()==g0
r['road_graph_sha256']=hashlib.sha256(g0).hexdigest();r['vehicle_layer_unchanged']=True;r['road_paths_and_widths_unchanged']=True
json.dump(r,open(P+'/central_stair_surface_mask_qa.json','w'),indent=2)
print(json.dumps({k:v for k,v in r.items() if k!='ramps'},indent=2))
