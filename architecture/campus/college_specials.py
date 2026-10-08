"""Original source-informed CIT landmark accents from official exterior photographs."""
import math
from mesh_architecture import Mesh,mat,alongbox

def extras(bid,poly,base,floors,col,mats):
 if not str(bid).startswith('cit_'):return
 me=Mesh();ma=list(mats);ma.extend([mat('CIT • pink stone podium',(.58,.37,.36)),mat('CIT • salmon metal roof',(.60,.34,.32)),mat('CIT • green glazed barrel',(.12,.39,.36),.25,.2),mat('CIT • buff brick',(.64,.39,.25))])
 p=poly[:-1] if poly[0]==poly[-1] else poly;x0=min(x for x,y in p);x1=max(x for x,y in p);y0=min(y for x,y in p);y1=max(y for x,y in p);cx=(x0+x1)/2;cy=(y0+y1)/2;h=floors*3.55
 area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1]));sgn=1 if area>0 else -1
 if bid in ('cit_1','cit_2'):
  for a,b in zip(p,p[1:]+p[:1]):
   dx,dy=b[0]-a[0],b[1]-a[1];le=math.hypot(dx,dy)
   if le<3:continue
   nx,ny=sgn*dy/le,-sgn*dx/le;an=math.atan2(dy,dx)
   if bid=='cit_1':
    for fl in range(2):alongbox(me,((a[0]+b[0])/2+nx*.24,(a[1]+b[1])/2+ny*.24,base+fl*3.55+.58),(le,.19,1.12),an,11)
   for fl in range(floors):alongbox(me,((a[0]+b[0])/2+nx*.3,(a[1]+b[1])/2+ny*.3,base+(fl+1)*3.55-.24),(le+.15,.22,.32),an,4)
 if bid=='cit_main':
  for ob in col.objects:
   if ob.type=='MESH' and len(ob.data.materials)>0:ob.data.materials[0]=ma[14]
  # Long green barrel vault spanning the roof, with structural ribs.
  r=(y1-y0)*.44;z=base+h+.5;length=x1-x0-2
  for i in range(32):
   a=i*math.pi/32;b=(i+1)*math.pi/32
   points=[(x,cy+r*math.cos(t),z+r*.50*math.sin(t)) for x in (cx-length/2,cx+length/2) for t in (a,b)]
   me.poly(points,[(0,2,3,1)],13)
  for j in range(10):
   xx=cx-length/2+length*j/9
   for i in range(24):
    a=i*math.pi/24;b=(i+1)*math.pi/24;me.tube((xx,cy+r*math.cos(a),z+r*.5*math.sin(a)),(xx,cy+r*math.cos(b),z+r*.5*math.sin(b)),.08,m=4,n=5)
  alongbox(me,(cx,y0-.22,base+h*.48),((x1-x0)*.36,.18,h*.89),0,8)
 if bid in ('cit_3','cit_4'):
  # A mapped-footprint-derived folded roof. Pitch and exact eaves are approximate.
  ridge=cx;half=max(.1,(x1-x0)/2);peak=4.5 if bid=='cit_3' else 5.2
  def clip(poly,greater):
   out=[]
   for a,b in zip(poly,poly[1:]+poly[:1]):
    ia=a[0]>=ridge if greater else a[0]<=ridge;ib=b[0]>=ridge if greater else b[0]<=ridge
    if ia:out.append(a)
    if ia!=ib:
     t=(ridge-a[0])/(b[0]-a[0]);out.append((ridge,a[1]+t*(b[1]-a[1])))
   return out
  for side in (False,True):
   q=clip(p,side);verts=[(x,y,base+h+.5+peak*(1-abs(x-ridge)/half)) for x,y in q];me.poly(verts,[tuple(range(len(q)))],12 if bid=='cit_3' else 7)
  alongbox(me,(cx,y0-2.2,base+3.7),(13,5,.35),0,13)
  for dx in (-5,5):me.tube((cx+dx,y0-3.5,base),(cx+dx,y0-3.5,base+3.7),.30,m=4,n=12)
 if me.v:
  ob=me.object('CAMPUS_BUILDING '+str(bid)+' | official-photo accents',ma,col);ob['source']='https://www.cst.ac.kr/page/?mn=952&site=basic';ob['confidence']='Source-informed facade colors and roof typology; dimensions approximate.'
