"""Terrain-triangle-conforming mapped plazas/parking/pitches; no large floating n-gons."""
import math
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from terrain_cutouts import half,area

def add_ground_polygon(mesh,poly,height,offset=.04,step=5):
    if len(poly)<3:return
    loop=[Vector((x,y,0)) for x,y in poly]
    for raw in tessellate_polygon([loop]):
        tri=[(loop[v].x,loop[v].y) if isinstance(v,int) else (v.x,v.y) for v in raw]
        if abs(area(tri))<1e-8:continue
        if area(tri)<0:tri.reverse()
        xmin=math.floor((min(x for x,y in tri)+490)/step)*step-490
        xmax=math.ceil((max(x for x,y in tri)+490)/step)*step-490
        ymin=math.floor((min(y for x,y in tri)+1120)/step)*step-1120
        ymax=math.ceil((max(y for x,y in tri)+1120)/step)*step-1120
        for y in range(int(ymin),int(ymax),step):
            for x in range(int(xmin),int(xmax),step):
                for cell in [[(x,y),(x+step,y),(x+step,y+step)],[(x,y),(x+step,y+step),(x,y+step)]]:
                    q=cell
                    for a,b in zip(tri,tri[1:]+tri[:1]):
                        if not q:break
                        q=half(q,a,b,True)
                    if len(q)<3 or abs(area(q))<1e-8:continue
                    pts=[(a,b,height(a,b)+offset) for a,b in q]
                    mesh.poly(pts,[(0,i,i+1) for i in range(1,len(q)-1)])

def add_ground_skirt(mesh,poly,height,offset=.04):
    for a,b in zip(poly,poly[1:]+poly[:1]):
        n=max(1,math.ceil(math.dist(a,b)/1.5))
        for k in range(n):
            aa=(a[0]+(b[0]-a[0])*k/n,a[1]+(b[1]-a[1])*k/n);bb=(a[0]+(b[0]-a[0])*(k+1)/n,a[1]+(b[1]-a[1])*(k+1)/n)
            za=height(*aa);zb=height(*bb)
            mesh.poly([(aa[0],aa[1],za+offset),(bb[0],bb[1],zb+offset),(bb[0],bb[1],zb-.22),(aa[0],aa[1],za-.22)],[(0,1,2,3)])
