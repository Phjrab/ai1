"""Reference-informed original landmark trim, no photo textures.
Official photos and caveats: /workspace/shared/chosun_campus_refs/facades/facade_guide.json.
Call after base architecture. Uses directory seq IDs or 2026 handbook IDs.
"""
import math
from mesh_architecture import Mesh, extrude, rect, alongbox, mat

def _area(p):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1]))/2

def _edges(poly):
    for a,b in zip(poly,poly[1:]+poly[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        if length<1:continue
        ux,uy=dx/length,dy/length
        sign=1 if _area(poly)>=0 else -1
        yield a,b,length,ux,uy,sign*uy,-sign*ux,math.atan2(dy,dx)

def _arch(me,c,ux,uy,nx,ny,r,t,depth,z,mi):
    # A rectangular-section half-ring projecting out of the facade.
    n=16;pts=[]
    for dd in (-depth/2,depth/2):
        for rr in (r,r+t):
            for k in range(n+1):
                an=k*math.pi/n
                pts.append((c[0]+ux*rr*math.cos(an)+nx*dd,c[1]+uy*rr*math.cos(an)+ny*dd,z+rr*math.sin(an)))
    m=n+1;faces=[]
    for k in range(n):
        faces += [(k,k+1,m+k+1,m+k),(2*m+k,3*m+k,3*m+k+1,2*m+k+1),(k,2*m+k,2*m+k+1,k+1),(m+k,m+k+1,3*m+k+1,3*m+k)]
    faces += [(0,m,3*m,2*m),(n,2*m+n,3*m+n,m+n)]
    me.poly(pts,faces,mi)

def extra_details(bid,parts,base,floors,collection,mats):
    bid=str(bid);kind=None
    if bid in ('136','4','04','education'):kind='education'
    elif bid in ('135','15','art'):kind='art'
    elif bid in ('134','57','engineering1'):kind='engineering1'
    if kind is None:return None
    me=Mesh();localmats=list(mats)
    prepared=[p if isinstance(p,dict) else {'polygon':p} for p in parts]
    if not prepared:return None
    if kind=='art':
        colors=[('red',(.73,.035,.065)),('gold',(.96,.66,.018)),('blue',(.025,.28,.62)),('charcoal',(.045,.05,.075))]
        cm=[]
        for label,color in colors:
            cm.append(len(localmats));localmats.append(mat('CAMPUS ART • '+label,color))
        prepared=[max(prepared,key=lambda p:abs(_area(p['polygon'])))]
    for ip,p in enumerate(prepared):
        poly=list(p['polygon']);poly=poly[:-1] if len(poly)>2 and poly[0]==poly[-1] else poly;h=p.get('floors',floors)*3.55
        if kind=='education':
            for a,b,length,ux,uy,nx,ny,ang in _edges(poly):
                n=max(1,round(length/6.0));pitch=length/n;thick=min(.78,pitch*.15);radius=(pitch-thick)/2
                spring=base+h-3.5-radius;bottom=base+.3
                for j in range(n+1):
                    x=a[0]+ux*j*pitch+nx*.45;y=a[1]+uy*j*pitch+ny*.45
                    alongbox(me,(x,y,(spring+bottom)/2),(thick,1.25,spring-bottom),ang,4)
                for j in range(n):
                    c=(a[0]+ux*(j+.5)*pitch+nx*.45,a[1]+uy*(j+.5)*pitch+ny*.45)
                    _arch(me,c,ux,uy,nx,ny,radius,thick,1.25,spring,4)
                # Broad thin cantilevered roof edge, source-defining profile.
                alongbox(me,((a[0]+b[0])/2+nx*1.25,(a[1]+b[1])/2+ny*1.25,base+h+.12),(length+2.5,3,.24),ang,4)
        elif kind=='engineering1':
            for a,b,length,ux,uy,nx,ny,ang in _edges(poly):
                if length<8:continue
                n=max(2,round(length/2.2))
                for j in range(n+1):
                    dd=(j+.25)*length/(n+.5)
                    alongbox(me,(a[0]+ux*dd+nx*.27,a[1]+uy*dd+ny*.27,base+h/2),(.28,.58,h+.3),ang,4)
        elif kind=='art':
            for edge,(a,b,length,ux,uy,nx,ny,ang) in enumerate(_edges(poly)):
                for fl in range(int(p.get('floors',floors))):
                    if (fl+edge)%3==0:
                        alongbox(me,((a[0]+b[0])/2+nx*.16,(a[1]+b[1])/2+ny*.16,base+fl*3.55+.48),(length+.1,.23,.85),ang,cm[(fl+edge)%3])
            # Eight projecting cylindrical columns with bold irregular stacked bands.
            cx=sum(x for x,y in poly)/len(poly);cy=sum(y for x,y in poly)/len(poly)
            rx=max(abs(x-cx) for x,y in poly);ry=max(abs(y-cy) for x,y in poly)
            for j in range(8):
                an=2*math.pi*j/8;x=cx+(rx+.48)*math.cos(an);y=cy+(ry+.48)*math.sin(an)
                for k in range(6):
                    z0=base+k*(h+1.5)/6;z1=base+(k+1)*(h+1.5)/6
                    mi=4 if (j+k)%3==0 else cm[(j+k)%4]
                    me.tube((x,y,z0),(x,y,z1),.62,m=mi,n=12)
    if me.v:
        ob=me.object('Landmark source-informed trim | '+kind,localmats,collection)
        ob['evidence']='Official campusMap exterior photograph; interpretive geometry, not measured survey.'
        return ob
    return None
