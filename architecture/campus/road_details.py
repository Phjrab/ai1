"""Blender crossing paint, mapped sidewalk transitions and grounded edge closures."""
import math
from collections import Counter
from mathutils import Vector

def surface_object(name,layer,height,offset,Mesh,material,col):
 mesh=Mesh();mesh.v=[Vector((x,y,height(x,y)+(offset(x,y) if callable(offset) else offset))) for x,y in layer['vertices']]
 mesh.f=[f for f in layer['faces'] if (mesh.v[f[1]]-mesh.v[f[0]]).cross(mesh.v[f[2]]-mesh.v[f[0]]).length>2e-9];mesh.mi=[0]*len(mesh.f)
 ob=mesh.object(name,[material],col);return ob

def boundary_skirt(name,layer,height,offset,Mesh,material,col):
 edges=Counter(tuple(sorted((a,b))) for f in layer['faces'] for a,b in zip(f,f[1:]+f[:1]));mesh=Mesh()
 for (a,b),count in edges.items():
  if count!=1:continue
  pa=layer['vertices'][a];pb=layer['vertices'][b]
  if math.dist(pa,pb)<1e-4:continue
  z=lambda p:height(*p)+(offset(*p) if callable(offset) else offset)
  mesh.poly([(pa[0],pa[1],z(pa)),(pb[0],pb[1],z(pb)),(pb[0],pb[1],height(*pb)-.215),(pa[0],pa[1],height(*pa)-.215)],[(0,1,2,3)])
 if not mesh.f:return None
 ob=mesh.object(name,[material],col);ob['purpose']='Close exposed paving edges down into terrain; no collision curb or surveyed retaining wall';ob['bottom_offset_from_height_m']=-.215;return ob

def ramp_offset(r,x,y):
 dx=x-r['center'][0];dy=y-r['center'][1];d=(dx*r['across'][0]+dy*r['across'][1])*r['sign']-r['half_road']
 return .095+.06*max(0,min(1,d/r['run']))

def add_details(data,height,Mesh,col,pave,nav):
 from mesh_architecture import mat
 paint=mat('CAMPUS • crossing warm white',(.86,.86,.78),.8)
 tactile=mat('CAMPUS • source-mapped tactile ochre',(.65,.46,.12),.82)
 ob=surface_object('CAMPUS_CROSSINGS | 39 source mapped zebra crossings',data['white'],height,.103,Mesh,paint,col)
 ob['source']='© OpenStreetMap contributors; crossing nodes individually recorded in navigation.json';ob['width_status']='3.5m indicative; local roadway tangent-derived orientation';ob['not_surveyed']=True
 for i,r in enumerate(data['ramps']):
  offset=lambda x,y,r=r:ramp_offset(r,x,y)
  ob=surface_object('CAMPUS_CURB_TRANSITION '+r['crossing']+' '+str(r['sign']),r,height,offset,Mesh,pave,col)
  ob['status']='Schematic dropped-kerb transition on mapped pedestrian surface; physical kerb not verified';ob['osm_crossing_node']=r['crossing'];ob['rise_m']=.06
  boundary_skirt('CAMPUS_CURB_TRANSITION edge '+str(i),r,height,offset,Mesh,pave,col)
 def tactile_offset(x,y):
  result=.155
  for r in data['ramps']:
   dx=x-r['center'][0];dy=y-r['center'][1];u=r['across'];along=abs(-u[1]*dx+u[0]*dy);across=(dx*u[0]+dy*u[1])*r['sign']-r['half_road']
   if along<1.76 and -.01<across<1.81:result=min(result,ramp_offset(r,x,y))
  return result+.008
 if data.get('yellow',{}).get('faces'):
  yellow=mat('CAMPUS • verified library yellow road paint',(.84,.60,.10),.8)
  ob=surface_object('CAMPUS_LIBRARY | streetview checked yellow road lines',data['yellow'],height,.104,Mesh,yellow,col)
  ob['source']='Naver March 2026 library frontage';ob['extent_status']='Between source-mapped library crossings; approximate paint width'
 if data['tactile']['faces']:
  ob=surface_object('CAMPUS_TACTILE | OSM yes-tagged crossings only',data['tactile'],height,tactile_offset,Mesh,tactile,col)
  ob['status']='Presence OSM-tagged; pad extent reconstructed, no accessibility certification'
 nav['crossings']=[]
 for crossing in data['crossings']:
  c=dict(crossing);x,y=c['position'];c['position']=[x,y,round(height(x,y)+.103,5)];nav['crossings'].append(c)
 nav['crossing_limits']=data['limits']
