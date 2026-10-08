"""Conservative road-corridor earthwork for a navigable approximate campus.
Does not change mapped XY, and does not claim real surveyed road grades.
"""
import os,json,math
from terrain_elevation import preservation_weight,_inpoly
class Roadbeds:
 def __init__(self,base,pads,path=None,max_grade=.14,graph_kind="vehicle",fixed=None):
  self.base=base;self.pads=pads;self.buckets={};self.cell=25.;self.fixed=fixed;self.graph_kind=graph_kind
  if path is None:path=os.path.join(os.path.dirname(__file__),'road_graph.json')
  graph=json.load(open(path))[graph_kind];pts=[tuple(p[:2]) for p in graph['nodes']];edges=[]
  for e in graph['edges']:
   p,q=pts[e['a']],pts[e['b']];le=math.dist(p,q);n=max(1,math.ceil(le/4));ids=[e['a']]
   for j in range(1,n):ids.append(len(pts));pts.append((p[0]+(q[0]-p[0])*j/n,p[1]+(q[1]-p[1])*j/n))
   ids.append(e['b'])
   for a,b in zip(ids,ids[1:]):edges.append((a,b,le/n,float(e['width']),e['osm_id']))
  z0=[base(*p) for p in pts];z=list(z0);locked=[preservation_weight(*p)==0 or (fixed is not None and fixed(*p)) for p in pts]
  close={};extra=[]
  for a,(x,y) in enumerate(pts):
   key=(math.floor(x/12),math.floor(y/12))
   for dx in [-1,0,1]:
    for dy in [-1,0,1]:
     for b in close.get((key[0]+dx,key[1]+dy),[]):
      le=math.dist(pts[a],pts[b])
      if le<12 and le>.02:extra.append((a,b,le,0,'proximity'))
   close.setdefault(key,[]).append(a)
  constraints=edges+extra
  # Alternating pair projections solve bounded slope while moving as little as possible.
  for iteration in range(2500):
   err=0.
   for a,b,le,w,oid in (constraints if iteration%2==0 else reversed(constraints)):
    # The authored main route is preserved, including its ~28% steep approach.
    cap=(.29 if graph_kind=="vehicle" and (locked[a] or locked[b]) else max_grade)*le;diff=z[b]-z[a];over=abs(diff)-cap
    if over<=.00001:continue
    if locked[a] and locked[b]:continue
    err=max(err,over);s=1 if diff>0 else -1
    if locked[a]:z[b]-=s*over
    elif locked[b]:z[a]+=s*over
    else:z[a]+=s*over*.5;z[b]-=s*over*.5
   if err<.0001:break
  changes={};self.segments=[]
  for a,b,le,width,oid in edges:
   pa,pb=pts[a],pts[b];delta=max(abs(z[a]-z0[a]),abs(z[b]-z0[b]));changes.setdefault(oid,[]).append(delta)
   # Include unchanged neighbors too so corridor targets remain continuous.
   # Full-width road support with additional 5m for final terrain grid interpolation.
   inner=width/2+5.;outer=inner+max(20.,min(60.,delta/.25));seg=(pa,pb,z[a],z[b],inner,outer,oid);idx=len(self.segments);self.segments.append(seg)
   for i in range(math.floor((min(pa[0],pb[0])-outer)/self.cell),math.floor((max(pa[0],pb[0])+outer)/self.cell)+1):
    for j in range(math.floor((min(pa[1],pb[1])-outer)/self.cell),math.floor((max(pa[1],pb[1])+outer)/self.cell)+1):self.buckets.setdefault((i,j),[]).append(idx)
  self.report={'graph_kind':graph_kind,'method':'Road-graph pairwise slope projection; road corridor graded; exposed foundations require skirts; original detailed core locked; smooth corridor earthwork','purpose':'approximate game/model traversability, NOT surveyed road grades','outside_core_target_grade':max_grade,'locked_core_interface_grade':.29,'nodes':len(pts),'segments':len(edges),'iterations':iteration+1,'max_node_shift_m':max(abs(a-b) for a,b in zip(z,z0)),'modified_roads':[{'osm_id':k,'max_abs_height_adjustment_m':round(max(v),4)} for k,v in changes.items() if max(v)>.005],'remaining_unlocked_constraint_excess_m':max([max(0,abs(z[b]-z[a])-(.29 if graph_kind=="vehicle" and (locked[a] or locked[b]) else max_grade)*le) for a,b,le,w,o in edges if not (locked[a] and locked[b])] or [0])}
 def __call__(self,x,y):
  original=self.base(x,y)
  if preservation_weight(x,y)==0 or (self.fixed is not None and self.fixed(x,y)):return original
  cand=self.buckets.get((math.floor(x/self.cell),math.floor(y/self.cell)),[])
  if not cand:return original
  # Road grading has priority even beside building edges. Builders must
  # close any exposed foundation to the final sampled ground.
  nearest=None
  for idx in cand:
   a,b,za,zb,inner,outer,oid=self.segments[idx];dx=b[0]-a[0];dy=b[1]-a[1];u=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy or 1)))
   dist=math.hypot(x-a[0]-u*dx,y-a[1]-u*dy)
   if dist>=outer:continue
   if nearest is None or dist<nearest[0]:nearest=(dist,za*(1-u)+zb*u,inner,outer)
  if nearest is None:return original
  dist,target,inner,outer=nearest;t=max(0,min(1,(dist-inner)/(outer-inner)));w=1-t*t*(3-2*t)
  # Preserve core boundary continuously; saturation within 12m outside protected site.
  dx=max(abs(x)-235,0);dy=max(-128-y,y-123,0);u=min(1,math.hypot(dx,dy)/12);w*=u*u*(3-2*u)
  return original*(1-w)+target*w
 def write_report(self,path):
  with open(path,'w') as f:json.dump(self.report,f,ensure_ascii=False,indent=2)

 def near_corridor(self,x,y,padding=8.):
  for idx in self.buckets.get((math.floor(x/self.cell),math.floor(y/self.cell)),[]):
   a,b,za,zb,inner,outer,oid=self.segments[idx];dx=b[0]-a[0];dy=b[1]-a[1];u=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy or 1)))
   if math.hypot(x-a[0]-u*dx,y-a[1]-u*dy)<inner+padding:return True
  return False
