"""Original reusable facade geometry. Source photos are not embedded."""
import bpy, math, sys, os
from mathutils import Vector
sys.path.insert(0,os.path.join(os.path.dirname(os.path.dirname(__file__)),'site'))
from site_builder import Mesh,mat

def extrude(mesh,poly,z0,z1,mi=0):
    n=len(poly);pts=[(x,y,z) for z in (z0,z1) for x,y in poly]
    mesh.poly(pts,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mi)

def rect(cx,cy,w,d,a=0):
    ca,sa=math.cos(a),math.sin(a)
    return [(cx+x*ca-y*sa,cy+x*sa+y*ca) for x,y in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]

def alongbox(mesh,c,size,angle,mi):
    x,y,z=c;w,d,h=size;extrude(mesh,rect(x,y,w,d,angle),z-h/2,z+h/2,mi)

def architecture(name,parts,base,floors,style,collection,mats):
    # Mesh groups preserve inspectable facade and roof geometry while limiting draw calls.
    shell,detail,glass,roof=Mesh(),Mesh(),Mesh(),Mesh()
    floorh=3.55 if style not in ('dorm','hospital') else 3.15
    for ip,part in enumerate(parts):
        poly=part['polygon'];pf=part.get('floors',floors);h=pf*floorh
        cx=sum(p[0] for p in poly)/len(poly);cy=sum(p[1] for p in poly)/len(poly)
        wallmi={'brick':0,'dorm':1,'stone':2,'modern':3,'arts':2,'hospital':3,'engineering':1}.get(style,1)
        extrude(shell,poly,base+(floorh if part.get('open_ground') else 0),base+h,wallmi)
        extrude(roof,poly,base+h,base+h+.24,7)
        # Parapets and concrete floor belts are independent actual geometry.
        for a,b in zip(poly,poly[1:]+poly[:1]):
            dx,dy=b[0]-a[0],b[1]-a[1];le=math.hypot(dx,dy)
            if le<2:continue
            ux,uy=dx/le,dy/le;nx,ny=uy,-ux
            # account for orientation of footprint polygon
            area=sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(poly,poly[1:]+poly[:1]))
            if area<0:nx,ny=-nx,-ny
            an=math.atan2(dy,dx)
            def strip(z,hh,depth=.18,mi=4):
                alongbox(detail,((a[0]+b[0])/2+nx*.07,(a[1]+b[1])/2+ny*.07,z),(le,depth,hh),an,mi)
            strip(base+.26,.48,.28,6);strip(base+h+.53,.7,.3,wallmi)
            if style in ('modern','hospital'):spacing=3.2
            elif style=='dorm':spacing=3.5
            elif style=='arts':spacing=4.2
            else:spacing=3.6
            n=max(1,int((le-2)/spacing));margin=(le-n*spacing)/2
            for fl in range(pf):
                if fl==0 and part.get('open_ground'):continue
                zz=base+fl*floorh
                if style in ('stone','engineering','hospital','brick'):strip(zz+floorh-.16,.21,.22)
                if style=='modern':strip(zz+floorh-.35,.6,.20,5)
                if part.get('ribbon_glass'):
                    alongbox(glass,((a[0]+b[0])/2+nx*.24,(a[1]+b[1])/2+ny*.24,zz+floorh*.53),(le-.25,.07,2.2),an,9)
                for j in range(n):
                    dist=margin+(j+.5)*spacing
                    wx=a[0]+ux*dist+nx*.075;wy=a[1]+uy*dist+ny*.075
                    ww=spacing*(.70 if style in ('modern','hospital') else .55)
                    wh=1.8 if style!='arts' else 2.1
                    wz=zz+floorh*.53
                    alongbox(detail,(wx,wy,wz),(ww+.22,.22,wh+.22),an,5)
                    alongbox(glass,(wx+nx*.13,wy+ny*.13,wz),(ww,.055,wh),an,8+(j+fl+ip)%3)
                    alongbox(detail,(wx+nx*.19,wy+ny*.19,wz),(.065,.07,wh),an,4)
                    alongbox(detail,(wx+nx*.20,wy+ny*.20,wz-wh*.15),(ww,.07,.06),an,4)
                    alongbox(detail,(wx+nx*.15,wy+ny*.15,wz-wh/2-.13),(ww+.32,.38,.13),an,4)
            if part.get('open_ground'):
                for j in range(max(2,int(le/6))+1):
                    dd=le*j/max(2,int(le/6));px=a[0]+ux*dd-nx*.8;py=a[1]+uy*dd-ny*.8
                    detail.tube((px,py,base),(px,py,base+floorh),.42,m=4,n=12)
            # Grid mullions for modern curtain wall corners.
            if style=='modern':
                for j in range(n+1):
                    dd=margin+j*spacing
                    alongbox(detail,(a[0]+ux*dd+nx*.19,a[1]+uy*dd+ny*.19,base+h/2),(.10,.10,h),an,4)
        # Rooftop service core and air-handling plant, explicitly approximate.
        if ip==0:
            core=rect(cx,cy,8,6);extrude(roof,core,base+h+.24,base+h+3.0,wallmi)
            for t in range(3):alongbox(roof,(cx+11+t*2.7,cy,base+h+.8),(1.7,3,.9),0,6)
        # Public entrance canopy on most southerly local edge, no fabricated interiors.
        aa,bb=min(zip(poly,poly[1:]+poly[:1]),key=lambda ab:(ab[0][1]+ab[1][1])/2)
        ex=(aa[0]+bb[0])/2;ey=(aa[1]+bb[1])/2;an=math.atan2(bb[1]-aa[1],bb[0]-aa[0])
        alongbox(detail,(ex,ey-1.6,base+3.4),(min(10,math.dist(aa,bb)*.45),4,.25),an,4)
        alongbox(glass,(ex,ey-.14,base+1.4),(4,.12,2.8),an,9)
        for s in (-1,1):alongbox(detail,(ex+s*2.5,ey-2.8,base+1.6),(.2,.2,3.2),0,5)
    for label,me in [('Massing',shell),('Frames sills and cornices',detail),('Fenestration',glass),('Roof and approximate service',roof)]:
        if me.v:me.object(name+' | '+label,mats,collection)
