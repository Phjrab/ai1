"""Remove terrain faces from building footprints, leaving terrain/nav heights intact.
Pure-Python convex clipping; Blender mathutils is used once to tessellate outlines.
"""
import math

def area(p):return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1]))*.5

def half(poly,a,b,inside=True):
 out=[]
 def side(v):return (b[0]-a[0])*(v[1]-a[1])-(b[1]-a[1])*(v[0]-a[0])
 for p,q in zip(poly,poly[1:]+poly[:1]):
  sp,sq=side(p),side(q);ip=sp>=-1e-9 if inside else sp<=1e-9;iq=sq>=-1e-9 if inside else sq<=1e-9
  if ip:out.append(p)
  if ip!=iq:
   t=sp/(sp-sq);out.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
 return out

def subtract(poly,tri):
 if abs(area(tri))<1e-8:return [poly]
 # Partition polygon into outside pieces, dropping the final intersection.
 if area(tri)<0:tri=list(reversed(tri))
 remaining=poly;out=[]
 for a,b in zip(tri,tri[1:]+tri[:1]):
  if len(remaining)<3:break
  q=half(remaining,a,b,False)
  if len(q)>=3 and abs(area(q))>1e-8:out.append(q)
  remaining=half(remaining,a,b,True)
 return out

class TerrainCutouts:
 def __init__(self,buildings):
  from mathutils import Vector
  from mathutils.geometry import tessellate_polygon
  self.bucket={};self.tris=[];self.cell=20.;self.faces=0
  for b in buildings:
   outline=[Vector((p[0],p[1],0)) for p in b['poly']]
   outline_tris=[[(outline[v].x,outline[v].y) if isinstance(v,int) else (v.x,v.y) for v in tri] for tri in tessellate_polygon([outline])]
   # Preserve open courtyard terrain: subtract each hole from the mask itself.
   hole_tris=[]
   for hole in b.get('holes',[]):
    if len(hole)<3:continue
    loop=[Vector((p[0],p[1],0)) for p in hole]
    hole_tris.extend([[(loop[v].x,loop[v].y) if isinstance(v,int) else (v.x,v.y) for v in tri] for tri in tessellate_polygon([loop])])
   mask_polys=outline_tris
   for hole in hole_tris:
    next_polys=[]
    for poly in mask_polys:next_polys.extend(subtract(poly,hole))
    mask_polys=next_polys
   mask_tris=[]
   for poly in mask_polys:
    mask_tris.extend([[poly[0],poly[i],poly[i+1]] for i in range(1,len(poly)-1)])
   for tri in mask_tris:
    if abs(area(tri))<1e-7:continue
    index=len(self.tris);self.tris.append(tri)
    for i in range(math.floor(min(p[0] for p in tri)/self.cell),math.floor(max(p[0] for p in tri)/self.cell)+1):
     for j in range(math.floor(min(p[1] for p in tri)/self.cell),math.floor(max(p[1] for p in tri)/self.cell)+1):self.bucket.setdefault((i,j),[]).append(index)
 def add_cell(self,mesh,x,y,height,step=5):
  indices=set()
  for i in range(math.floor(x/self.cell),math.floor((x+step)/self.cell)+1):
   for j in range(math.floor(y/self.cell),math.floor((y+step)/self.cell)+1):indices.update(self.bucket.get((i,j),[]))
  polys=[[(x,y),(x+step,y),(x+step,y+step)],[(x,y),(x+step,y+step),(x,y+step)]]
  for idx in sorted(indices):
   tri=self.tris[idx];new=[]
   for p in polys:new.extend(subtract(p,tri))
   polys=new
   if not polys:break
  for p in polys:
   if len(p)<3:continue
   vertices=[(a,b,height(a,b)-(.95 if abs(a)<6.5 and -96<=b<=-24 else .20)) for a,b in p]
   mesh.poly(vertices,[(0,i,i+1) for i in range(1,len(p)-1)]);self.faces+=len(p)-2
