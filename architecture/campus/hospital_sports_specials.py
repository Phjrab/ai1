"""Original photo-informed hospital and sports exterior refinements."""
import math
from mesh_architecture import Mesh,mat,alongbox,rect,extrude

def extras(bid,parts,base,floors,col,mats):
 me=Mesh();ma=list(mats);ma.append(mat('HOSPITAL • blue horizontal accent',(.035,.21,.35)));ma.append(mat('SPORTS • translucent roof lantern',(.18,.39,.40),.25))
 for part in parts:
  p=part['polygon'];h=part['floors']*(3.15 if bid==162 else 3.55)
  if not p:continue
  area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1]));sgn=1 if area>0 else -1
  for a,b in zip(p,p[1:]+p[:1]):
   dx,dy=b[0]-a[0],b[1]-a[1];le=math.hypot(dx,dy)
   if le<3:continue
   nx,ny=sgn*dy/le,-sgn*dx/le;an=math.atan2(dy,dx)
   if bid==162:
    for z in (base+5.5,base+9):alongbox(me,((a[0]+b[0])/2+nx*.25,(a[1]+b[1])/2+ny*.25,z),(le,.15,.72),an,11)
   else:
    n=max(2,int(le/7))
    for k in range(n+1):
     x=a[0]+dx*k/n+nx*.35;y=a[1]+dy*k/n+ny*.35;alongbox(me,(x,y,base+h/2),(.72,.7,h+1.2),an,4)
    alongbox(me,((a[0]+b[0])/2+nx*.3,(a[1]+b[1])/2+ny*.3,base+h+1.5),(le+2,1.5,1.6),an,4)
  x0=min(x for x,y in p);x1=max(x for x,y in p);y0=min(y for x,y in p);y1=max(y for x,y in p);cx=(x0+x1)/2;cy=(y0+y1)/2
  if bid==132:
   extrude(me,rect(cx,cy,(x1-x0)*.65,(y1-y0)*.55),base+h+.6,base+h+3.7,4)
   extrude(me,rect(cx,cy,12,10),base+h+3.7,base+h+5.1,12)
  elif part['floors']==8:
   alongbox(me,(cx,y0-3,base+3.5),(18,7,.28),0,9)
   for dx in (-7,7):me.tube((cx+dx,y0-5,base),(cx+dx,y0-5,base+3.5),.25,m=4,n=10)
 if me.v:
  ob=me.object('CAMPUS_BUILDING '+str(bid)+' | source-photo exterior refinements',ma,col);ob['accuracy']='Reference-informed external proportions; unsurveyed.'
