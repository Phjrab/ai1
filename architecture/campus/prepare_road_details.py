"""Source-grounded crossing inventory and exact-terrain paint tessellation.
No new centerlines; OSM node positions + intersecting mapped carriageway tangent.
Curb/landing dimensions are explicitly reconstructed, not accessibility survey data.
"""
import os,sys,json,math,xml.etree.ElementTree as ET
P=os.path.dirname(__file__);sys.path.insert(0,P+'/vendor')
from shapely.geometry import Point,LineString,Polygon,box
from shapely.ops import unary_union,substring
from shapely import constrained_delaunay_triangles
from prepare_road_continuity import polygon_parts
from road_surface_masks import detailed_stair_exclusion

def tessellate(surface):
 verts=[];faces=[];index={}
 def vi(p):
  k=(round(p[0],7),round(p[1],7))
  if k not in index:index[k]=len(verts);verts.append(k)
  return index[k]
 if surface.is_empty:return {'vertices':verts,'faces':faces}
 minx,miny,maxx,maxy=surface.bounds
 for y in range(-1120+int((miny+1120)//5)*5,int(maxy)+5,5):
  for x in range(-490+int((minx+490)//5)*5,int(maxx)+5,5):
   for tri in [[(x,y),(x+5,y),(x+5,y+5)],[(x,y),(x+5,y+5),(x,y+5)]]:
    for part in polygon_parts(surface.intersection(Polygon(tri))):
     if part.area<1e-9:continue
     for t in constrained_delaunay_triangles(part).geoms:
      f=[vi(c) for c in list(t.exterior.coords)[:3]]
      if len(set(f))==3 and t.area>1e-7:faces.append(f)
 return {'vertices':verts,'faces':faces}

def rectangle(c,u,v,lo,hi,half):
 return Polygon([(c[0]+u[0]*a+v[0]*b,c[1]+u[1]*a+v[1]*b) for a,b in [(lo,-half),(hi,-half),(hi,half),(lo,half)]])

def main():
 src=json.load(open(P+'/source_data/campus_osm_geometry.json')); tr=src['transform']
 def xy(n):
  e=(float(n.attrib['lon'])-tr['origin_lon'])*111320*math.cos(math.radians(tr['origin_lat']));no=(float(n.attrib['lat'])-tr['origin_lat'])*110950
  return (e*tr['x_axis_east_north'][0]+no*tr['x_axis_east_north'][1],e*tr['y_axis_east_north'][0]+no*tr['y_axis_east_north'][1]+tr['offset_y'])
 root=ET.parse('/workspace/shared/chosun_campus_refs/osm_map.xml').getroot();nodes={n.attrib['id']:n for n in root.findall('node')};ways={w.attrib['id']:[x.attrib['ref'] for x in w.findall('nd')] for w in root.findall('way')}
 cache=json.load(open(P+'/road_surface_cache.json'));roadmap={r['osm_id']:r for r in cache['roads']};roads=[r for r in cache['roads'] if r['vehicle']];lines={r['osm_id']:LineString(r['points']) for r in roads}
 vehicle=unary_union([Polygon([cache['layers'][0]['vertices'][i] for i in f]) for f in cache['layers'][0]['faces']]);pedestrian=unary_union([Polygon([cache['layers'][1]['vertices'][i] for i in f]) for f in cache['layers'][1]['faces']])
 pedestrian=pedestrian.difference(detailed_stair_exclusion())
 candidates={}
 for wid,refs in ways.items():
  if wid not in roadmap:continue
  for nid in refs:
   n=nodes.get(nid)
   if n is None:continue
   tags={t.attrib['k']:t.attrib['v'] for t in n.findall('tag')}
   if tags.get('highway')=='crossing':candidates[nid]=(n,tags)
 crossings=[];skipped=[];white=[];tactile=[];ramps=[];ramp_polys=[]
 for nid,(node,tags) in candidates.items():
  c=xy(node);pt=Point(c)
  rr=sorted(roads,key=lambda r:(nid not in ways.get(r['osm_id'],[]),lines[r['osm_id']].distance(pt)))
  if not rr:continue
  road=rr[0];line=lines[road['osm_id']];dist=line.distance(pt)
  if dist>2 or not vehicle.buffer(.1).covers(pt):skipped.append({'node':nid,'reason':'Outside included vehicle surface','distance':dist});continue
  mark=tags.get('crossing:markings');marked=mark not in (None,'no') or tags.get('crossing')=='marked'
  if not marked:skipped.append({'node':nid,'reason':'Crossing exists but painted marking not established'});continue
  s=line.project(pt);a=line.interpolate(max(0,s-2));b=line.interpolate(min(line.length,s+2));l=a.distance(b);v=((b.x-a.x)/l,(b.y-a.y)/l);u=(-v[1],v[0])
  w=road['width'];span=w;breadth=3.5
  # White bars run parallel to vehicle tangent; repetition spans crossing direction.
  n=max(3,round(span/.95));pitch=span/n
  for k in range(n):
   mid=-span/2+(k+.5)*pitch;poly=rectangle(c,u,v,mid-.24,mid+.24,breadth/2).intersection(vehicle)
   if not poly.is_empty:white.append(poly)
  ends=[]
  for sign in (-1,1):
   end=[c[0]+u[0]*sign*w/2,c[1]+u[1]*sign*w/2]
   # No invented complete sidewalks: transition only where mapped pedestrian paving exists.
   ramp=rectangle(c,u,v,sign*w/2,sign*(w/2+1.8),breadth/2).intersection(pedestrian)
   if not ramp.is_empty and ramp.area>.3:
    ramp_polys.append(ramp)
    ramps.append({'crossing':nid,'sign':sign,'center':list(c),'across':list(u),'half_road':w/2,'run':1.8,**tessellate(ramp)})
   if tags.get('tactile_paving')=='yes':
    pad=rectangle(c,u,v,sign*(w/2+.3),sign*(w/2+.9),breadth/2).intersection(pedestrian)
    if not pad.is_empty:tactile.append(pad)
   ends.append(end)
  crossings.append({'osm_node_id':nid,'source':'https://www.openstreetmap.org/node/'+nid,'osm_last_edit':node.attrib.get('timestamp'),'position':[round(x,3) for x in c],'lat':float(node.attrib['lat']),'lon':float(node.attrib['lon']),'road_osm_id':road['osm_id'],'road_tangent':v,'crossing_direction':u,'crossing_length_m':w,'crossing_width_m':breadth,'width_status':'Approximate 3.5m; not measured on site','span_status':'Follows mapped or estimated carriageway width','direction_status':'Perpendicular to local mapped road centerline','tactile_paving_source':tags.get('tactile_paving','unknown'),'kerb_status':'Unverified; schematic flush transitions only on mapped pedestrian surface','endpoint_xy':ends,'tags':tags})
 # March 2026 library-road streetview directly shows yellow edges/centre line.
 # Limit visual infill to the mapped section between the two library crossings.
 yellow=[];marking_section=None
 lib=[c for c in crossings if c['road_osm_id']=='190176308']
 if len(lib)==2:
  line=lines['190176308'];lo,hi=sorted(line.project(Point(c['position'])) for c in lib)
  section=substring(line,lo+2.8,hi-2.8);half=roadmap['190176308']['width']/2-.28
  for curve in [section,section.offset_curve(half),section.offset_curve(-half)]:yellow.append(curve.buffer(.065,cap_style='flat').intersection(vehicle))
  marking_section={'osm_way':'190176308','between_crossing_nodes':[c['osm_node_id'] for c in lib],'source':'Naver streetview 2026-03 library frontage','status':'Yellow center/edge marking presence visually checked; width/extent approximate'}
 payload={'schema':1,'attribution':'© OpenStreetMap contributors, ODbL 1.0','crossings':crossings,'skipped':skipped,'white':tessellate(unary_union(white)),'yellow':tessellate(unary_union(yellow)),'marking_section':marking_section,'tactile':tessellate(unary_union(tactile)),'ramps':ramps,'pedestrian_surface':tessellate(pedestrian.difference(unary_union(ramp_polys))),'limits':'Coordinates are source-mapped; orientation derived from roadway. Widths, stripe spacing and curb transitions are reconstruction estimates. Not an accessibility or legal routing survey. Kakao satellite latest layer has no exposed capture date. Naver streetview March 2026 visually corroborates library-road crossing, yellow edge lines, raised paver sidewalks and tactile guidance; this is not exhaustive per-node verification.'}
 json.dump(payload,open(P+'/road_details_cache.json','w'),ensure_ascii=False,separators=(',',':'))
 json.dump({k:v for k,v in payload.items() if k not in ('white','yellow','tactile','ramps','pedestrian_surface')},open('/workspace/shared/chosun_detail_refs/satellite_roads/crossings_inventory.json','w'),ensure_ascii=False,indent=2)
 print('Crossings',len(crossings),'skipped',len(skipped),'mapped pedestrian ramps',len(ramps),'paint faces',len(payload['white']['faces']))
if __name__=='__main__':main()
