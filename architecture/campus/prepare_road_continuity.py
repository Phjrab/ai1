"""Reproducible XY-only road union and terrain-aligned triangulation. Requires Shapely.
Run with system Python; Blender runtime only consumes resulting JSON.
No new centre-lines are inferred. OSM dead ends remain legitimate dead ends.
"""
import os,sys,json,math
P=os.path.dirname(__file__);sys.path.insert(0,P+'/vendor')
from shapely.geometry import LineString,Polygon,Point,box
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles, STRtree
from road_surface_masks import detailed_stair_exclusion
WALK={'footway','path','steps','pedestrian','cycleway','bridleway'}
def width(f):
 t=f['tags'];s=str(t.get('width','0'));w=float(s) if s.replace('.','').isdigit() else 0
 return w or (3 if t.get('highway') in WALK else (5 if t.get('highway')=='service' else 8))
def polygon_parts(g):
 if g.geom_type=='Polygon':return [g]
 return [p for q in getattr(g,'geoms',[]) for p in polygon_parts(q)]
def main():
 fs=[f for f in json.load(open(P+'/source_data/campus_osm_geometry.json'))['features'] if f['include']]
 roads=[f for f in fs if f['category']=='road' and len(f['points'])>1]
 buildings=[]
 for f in fs:
  if f['category']=='building' and len(f['points'])>2:
   p=Polygon(f['points'],f.get('holes',[])).buffer(0)
   if not p.is_empty:buildings.append(p)
 obstacles=unary_union(buildings).buffer(.12);boundary=box(-490,-1120,660,240)
 raw=[];layers=[]
 for pedestrian in [False,True]:
  r=[LineString(f['points']).buffer(width(f)/2,cap_style='round',join_style='round',quad_segs=4) for f in roads if (f['tags'].get('highway') in WALK)==pedestrian]
  raw.append(unary_union(r).intersection(boundary))
 # Vehicle paving wins at shared intersections, avoiding coplanar duplicate faces.
 layers=[raw[0].difference(obstacles),raw[1].difference(obstacles).difference(raw[0]).difference(detailed_stair_exclusion())]
 # Render-only tread/landing ownership; graph and centerline paths remain unchanged.
 payload={'schema':1,'source':'OSM mapped centerlines; no fabricated missing connections','layers':[],'roads':[]}
 for f in roads:
  clipped=LineString(f['points']).intersection(boundary).difference(obstacles)
  paths=[list(g.coords) for g in getattr(clipped,'geoms',[clipped]) if g.geom_type=='LineString' and g.length>.01]
  payload['roads'].append({'paths':paths,'osm_id':f['osm_id'],'name':f['name'],'width':width(f),'type':f['tags'].get('highway'),'points':f['points'],'source':f['source'],'vehicle':f['tags'].get('highway') not in WALK,'tags':f['tags']})
 for li,surface in enumerate(layers):
  verts=[];faces=[];index={}
  def vi(p):
   k=(round(p[0],7),round(p[1],7))
   if k not in index:index[k]=len(verts);verts.append(k)
   return index[k]
  minx,miny,maxx,maxy=surface.bounds
  for y in range(-1120+int((miny+1120)//5)*5,int(maxy)+5,5):
   for x in range(-490+int((minx+490)//5)*5,int(maxx)+5,5):
    cell=box(x,y,x+5,y+5)
    if not surface.intersects(cell):continue
    for triangle in [[(x,y),(x+5,y),(x+5,y+5)],[(x,y),(x+5,y+5),(x,y+5)]]:
     cut=surface.intersection(Polygon(triangle))
     for part in polygon_parts(cut):
      if part.area<1e-10:continue
      for tri in constrained_delaunay_triangles(part).geoms:
       f=[vi(c) for c in list(tri.exterior.coords)[:3]]
       if len(set(f))==3 and tri.area>1e-5:faces.append(f)
  payload['layers'].append({'name':'CAMPUS_CONTINUOUS '+('vehicle asphalt' if li==0 else 'pedestrian paving'),'vertices':verts,'faces':faces,'area_m2':surface.area})
  print('Layer',li,len(verts),len(faces),flush=True)
 json.dump(payload,open(P+'/road_surface_cache.json','w'),separators=(',',':'))
 # Noded XY graph splits actual intersections, not nearest-neighbor artificial links.
 def graph(vehicle):
  selected=[f for f in roads if not vehicle or f['tags'].get('highway') not in WALK]
  lines=[LineString(f['points']) for f in selected];tree=STRtree(lines)
  noded=unary_union(lines).intersection(boundary).difference(obstacles);nodes=[];index={};edges=[]
  def node(p):
   key=(round(p[0],3),round(p[1],3))
   if key not in index:index[key]=len(nodes);nodes.append(list(key))
   return index[key]
  for line in getattr(noded,'geoms',[noded]):
   if line.geom_type!='LineString':continue
   coords=list(line.coords)
   for a,b in zip(coords,coords[1:]):
    if math.dist(a,b)>.001:
     mid=Point((a[0]+b[0])/2,(a[1]+b[1])/2);idx=int(tree.nearest(mid));src=selected[idx]
     edges.append({'a':node(a),'b':node(b),'length':round(math.dist(a,b),4),'width':width(src),'osm_id':src['osm_id'],'highway':src['tags'].get('highway'),'oneway':src['tags'].get('oneway','no'),'access':src['tags'].get('access'),'source':src['source']})
  adj={i:[] for i in range(len(nodes))}
  for e in edges:adj[e['a']].append(e['b']);adj[e['b']].append(e['a'])
  remaining=set(adj);components=[]
  while remaining:
   start=next(iter(remaining));todo=[start];remaining.remove(start);comp=[]
   while todo:
    n=todo.pop();comp.append(n)
    for q in adj[n]:
     if q in remaining:remaining.remove(q);todo.append(q)
   components.append(comp)
  return {'nodes':nodes,'edges':edges,'components':sorted(components,key=len,reverse=True),'note':'Undirected geometry graph. Not a verified legal driving routing network. No proximity bridges added.'}
 graphs={'coordinate_system':'Blender Z-up XY meters','walking':graph(False),'vehicle':graph(True)}
 json.dump(graphs,open(P+'/road_graph.json','w'),separators=(',',':'))
 # Reproduce old skip rectangle missing mapped lengths.
 skip=box(-232,-128,232,123)
 missing=sum(LineString(f['points']).intersection(skip).length for f in roads)
 report={'mapped_ways':len(roads),'old_skipped_mapped_centerline_m':round(missing,3),'new_skipped_centerline_due_to_main_rectangle_m':0,'new_centerlines_added':0,'building_footprint_exclusion':True,'excluded_centerline_inside_building_m':round(sum(LineString(f['points']).intersection(obstacles).length for f in roads),3),'union_overlap_free':layers[0].intersection(layers[1]).area<1e-7,'terrain_partition':'Every face contained in one exact 5m terrain triangle','surface_meshes':[{'vertices':len(l['vertices']),'faces':len(l['faces']),'area_m2':l['area_m2']} for l in payload['layers']],'graph_components':{k:[len(c) for c in graphs[k]['components']] for k in ('walking','vehicle')},'limits':'OSM disconnected ways/dead ends intentionally retained; terrain and mapped widths approximate. Road presence does not establish legal motor/bus access.'}
 json.dump(report,open(P+'/road_continuity_report.json','w'),indent=2)
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
