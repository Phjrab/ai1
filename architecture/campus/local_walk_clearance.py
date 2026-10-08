"""Local, authored entrance clearance through a procedural paving-edge closure.
No road centerline, road surface, ground height or building elevation is changed.
"""
import math,bpy,json
from mesh_architecture import Mesh

def clip_interval(a,b,poly):
 lo,hi=0.,1.
 for c,d in zip(poly,poly[1:]+poly[:1]):
  ex,ey=d[0]-c[0],d[1]-c[1]
  f=ex*(a[1]-c[1])-ey*(a[0]-c[0]);delta=ex*(b[1]-a[1])-ey*(b[0]-a[0])
  if abs(delta)<1e-12:
   if f<0:return None
  elif delta>0:lo=max(lo,-f/delta)
  else:hi=min(hi,-f/delta)
  if lo>=hi:return None
 return max(0,lo),min(1,hi)

def clear_entry144_paving_edge(nav,collection,outdir):
 path=next(p for p in nav['pedestrianPaths'] if p['id'].startswith('entry_144_'));a,b=path['points'][0],path['points'][-1]
 dx,dy=b[0]-a[0],b[1]-a[1];ll=math.hypot(dx,dy);ux,uy=dx/ll,dy/ll;nx,ny=-uy,ux
 verts=[v for s in nav['walkableSurfaces'] if s['id'].startswith('entry_144_') for v in s['polygon']]
 us=[(v[0]-a[0])*ux+(v[1]-a[1])*uy for v in verts];vs=[(v[0]-a[0])*nx+(v[1]-a[1])*ny for v in verts]
 u0,u1=min(us)-.45,max(us)+.45;v0,v1=min(vs)-.45,max(vs)+.45
 point=lambda u,v:(a[0]+ux*u+nx*v,a[1]+uy*u+ny*v)
 poly=[point(u0,v0),point(u1,v0),point(u1,v1),point(u0,v1)]
 changed=[]
 for ob in list(collection.objects):
  if not ob.name.startswith('CAMPUS_PAVING_EDGE'):continue
  mesh=Mesh();cuts=0
  for face in ob.data.polygons:
   p=[tuple(ob.data.vertices[i].co) for i in face.vertices]
   if len(p)!=4:mesh.poly(p,[tuple(range(len(p)))],face.material_index);continue
   interval=clip_interval(p[0],p[1],poly)
   if not interval:mesh.poly(p,[(0,1,2,3)],face.material_index);continue
   cuts+=1;lo,hi=interval
   for start,end in [(0,lo),(hi,1)]:
    if end-start<1e-7:continue
    lerp=lambda aa,bb,t:tuple(aa[j]+(bb[j]-aa[j])*t for j in range(3))
    mesh.poly([lerp(p[0],p[1],start),lerp(p[0],p[1],end),lerp(p[3],p[2],end),lerp(p[3],p[2],start)],[(0,1,2,3)],face.material_index)
  if cuts:
   name=ob.name;materials=list(ob.data.materials);props={k:ob[k] for k in ob.keys()};bpy.data.objects.remove(ob,do_unlink=True);replacement=mesh.object(name,materials,collection)
   for k,v in props.items():replacement[k]=v
   replacement['local_entrance_clearance']='Entry144 stair and ramp footprint, 0.45m margin; paving surface and vehicle route unchanged.'
   changed.append({'object':name,'edge_faces_split_or_removed':cuts})
 report={'id':'entry144_paving_edge_clearance','cut_polygon_xy':poly,'changed_objects':changed,'scope':'Boundary skirt only; no road/top surface/terrain/grid/nav-centerline changes'}
 nav['local_entrance_clearances']=[report]
 if outdir:
  with open(outdir+'/local_walk_clearance.json','w') as f:json.dump(report,f,ensure_ascii=False,indent=2)
 return report
