"""INFERRED game-only pedestrian grade connectors; NOT observed real stair layouts.
Separate from photo-backed detailed_stairs.py. Added only to steep mapped paths.
"""
import math,json,os

def add_inferred_walksteps(nav,height,Mesh,collection,material,outdir=None):
 source='OSM pedestrian centerline plus modeled terrain grade; no photograph or surveyed stair count'
 confidence='INFERRED GAME TERRAIN CONNECTION ONLY; not an assertion that real stairs exist here'
 mesh=Mesh();records=[];surfaces=nav.setdefault('walkableSurfaces',[])
 def xyquad(a,b,width):
  dx,dy=b[0]-a[0],b[1]-a[1];le=math.hypot(dx,dy);nx,ny=-dy/le*width/2,dx/le*width/2
  return [(a[0]-nx,a[1]-ny),(b[0]-nx,b[1]-ny),(b[0]+nx,b[1]+ny),(a[0]+nx,a[1]+ny)]
 def slab(poly,tops,ident,kind):
  # xyquad is CCW. Bottom follows source ground so no suspended void is exposed.
  bottoms=[height(x,y)-.25 for x,y in poly];pts=[(x,y,z) for (x,y),z in zip(poly,bottoms)]+[(x,y,z) for (x,y),z in zip(poly,tops)]
  mesh.poly(pts,[(4,5,6,7),(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
  surfaces.append({'id':ident,'kind':kind,'polygon':[[x,y,z] for (x,y),z in zip(poly,tops)],'triangles':[[0,1,2],[0,2,3]],'source':source,'confidence':confidence})
 def joined_quad(points,i,u,v,width):
  # A shared miter cross-section prevents overlapping rectangles at the 944 elbow.
  def section(k):
   p=points[k];pa=points[max(0,k-1)];pb=points[min(len(points)-1,k+1)]
   dirs=[]
   for aa,bb in ((pa,p),(p,pb)):
    dx,dy=bb[0]-aa[0],bb[1]-aa[1];ll=math.hypot(dx,dy)
    if ll>1e-7:dirs.append((dx/ll,dy/ll))
   if len(dirs)==1:dirs=dirs*2
   na=(-dirs[0][1],dirs[0][0]);nb=(-dirs[1][1],dirs[1][0]);mx,my=na[0]+nb[0],na[1]+nb[1];ml=math.hypot(mx,my)
   if ml<1e-6:mx,my=nb
   else:mx,my=mx/ml,my/ml
   length=min(width*1.5,width*.5/max(.34,mx*nb[0]+my*nb[1]));off=(mx*length,my*length)
   return ((p[0]-off[0],p[1]-off[1]),(p[0]+off[0],p[1]+off[1]))
  a,b=section(i),section(i+1)
  interp=lambda side,t:(a[side][0]+(b[side][0]-a[side][0])*t,a[side][1]+(b[side][1]-a[side][1])*t)
  return [interp(0,u),interp(0,v),interp(1,v),interp(1,u)]
 for road in nav['roads']:
  if road.get('vehicle') or road.get('type') not in ('footway','path','steps','pedestrian'):continue
  p=road['points'];flags=[]
  for i,(a,b) in enumerate(zip(p,p[1:])):
   le=math.dist(a[:2],b[:2]);mx,my=(a[0]+b[0])/2,(a[1]+b[1])/2
   # Do not invent connector geometry over the retained/photo-detailed main site.
   if abs(mx)<=235 and -128<=my<=123:continue
   if le>.02 and abs(b[2]-a[2])/le>.35:flags.append(i)
  if not flags:continue
  # Include one approach segment at either end, then merge adjoining groups.
  ranges=[]
  for i in flags:
   a=max(0,i-1);b=min(len(p)-2,i+1)
   if ranges and a<=ranges[-1][1]+1:ranges[-1][1]=max(ranges[-1][1],b)
   else:ranges.append([a,b])
  width=min(2.,max(1.2,road['width']-.6))
  mitered=str(road.get('osm_id'))=='944569946'
  quad=lambda i,u=0,v=1:joined_quad(p,i,u,v,width) if mitered else xyquad((p[i][0]+(p[i+1][0]-p[i][0])*u,p[i][1]+(p[i+1][1]-p[i][1])*u),(p[i][0]+(p[i+1][0]-p[i][0])*v,p[i][1]+(p[i+1][1]-p[i][1])*v),width)
  for gi,(first,last) in enumerate(ranges):
   if last-first<2:
    first=max(0,first-1);last=min(len(p)-2,last+1)
   # Shared lift avoids step-to-step jumps caused by transverse hillside variation.
   lift=.14
   for i in range(first,last+1):
    a,b=p[i],p[i+1]
    if math.dist(a[:2],b[:2])<.02:continue
    for x,y in quad(i):
     dx,dy=b[0]-a[0],b[1]-a[1];u=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)));center=a[2]*(1-u)+b[2]*u
     lift=max(lift,height(x,y)+.16-center)
   prefix='inferred_walk_connector_'+str(road.get('osm_id','path'))+'_'+str(gi);count=0;path=[]
   for i in range(first,last+1):
    a,b=p[i],p[i+1];le=math.dist(a[:2],b[:2])
    if le<.02:continue
    dz=b[2]-a[2]
    if i in (first,last):
     q=quad(i);l0=0 if i==first else lift;l1=0 if i==last else lift
     # Approach vertices join existing path exactly, with a small surface clearance.
     tops=([height(*q[0])+.155,b[2]+lift,b[2]+lift,height(*q[3])+.155] if i==first else [a[2]+lift,height(*q[1])+.155,height(*q[2])+.155,a[2]+lift])
     slab(q,tops,prefix+'_approach_'+str(i),'inferred_grade_connection');path.extend([[a[0],a[1],a[2]+l0+.065],[b[0],b[1],b[2]+l1+.065]])
     continue
    n=max(1,math.ceil(abs(dz)/.17))
    for j in range(n):
     u=j/n;v=(j+1)/n;aa=(a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u);bb=(a[0]+(b[0]-a[0])*v,a[1]+(b[1]-a[1])*v);q=quad(i,u,v)
     z=max(a[2]+dz*u,a[2]+dz*v)+lift
     slab(q,[z]*4,prefix+'_tread_'+str(count),'inferred_game_steps');path.append([(aa[0]+bb[0])/2,(aa[1]+bb[1])/2,z]);count+=1
   records.append({'id':prefix,'osm_id':road.get('osm_id'),'source_type':road['type'],'modeled_treads':count,'width_m':width,'support_lift_m':round(lift,4),'source':source,'confidence':confidence})
   nav.setdefault('pedestrianPaths',[]).append({'id':prefix,'kind':'inferred_game_steps','width':width,'points':path,'source':source,'confidence':confidence})
 if mesh.v:
  ob=mesh.object('INFERRED_GAME_WALK_CONNECTORS | terrain connections, not surveyed stairs',[material],collection);ob['evidence_status']=confidence
 nav['inferred_walk_connections']=records
 if outdir:
  with open(os.path.join(outdir,'inferred_walk_connections.json'),'w') as f:json.dump(records,f,ensure_ascii=False,indent=2)
 return records
