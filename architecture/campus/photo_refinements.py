"""Original procedural geometry from inspected official photographs (2026-10-08).
See architecture/CHANGELOG.md for evidence, interpretations and limitations.
No downloaded image pixels are embedded in the model.
"""
import math,bpy
from mesh_architecture import Mesh,mat,rect,extrude,alongbox
from facade_specials import _edges

def label(text,loc,size,col,material,angle=0):
 cu=bpy.data.curves.new('Original architectural lettering','FONT');cu.body=text;cu.size=size;cu.extrude=.025;cu.align_x='CENTER'
 ob=bpy.data.objects.new('PHOTO_DETAIL sign '+text,cu);col.objects.link(ob);ob.location=loc;ob.rotation_euler=(math.pi/2,0,angle);cu.materials.append(material)
 bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.convert(target='MESH');ob.select_set(False)

def build(bid,parts,base,floors,col,mats):
 if bid not in (127,146,132):return False
 ma=list(mats)+[mat('PHOTO • limestone white',(.79,.80,.75)),mat('PHOTO • oxidized teal glazing',(.13,.38,.40),.25,.25),mat('PHOTO • perforation shadow',(.21,.25,.24)),mat('PHOTO • anodized silver',(.62,.68,.67),.4,.4)]
 wall,gl,trim,roof=Mesh(),Mesh(),Mesh(),Mesh();W,G,D,S=11,12,13,14
 if bid==127:
  for ip,part in enumerate(parts):
   p=part['polygon'];pf=part['floors'];h=pf*3.55
   extrude(wall,p,base+(3.55 if ip==0 else 0),base+h,W);extrude(roof,p,base+h,base+h+.35,W)
   for a,b,le,ux,uy,nx,ny,an in _edges(p):
    if le<3:continue
    cx,cy=(a[0]+b[0])/2,(a[1]+b[1])/2
    alongbox(trim,(cx+nx*.30,cy+ny*.30,base+h+.35),(le+.7,.85,.65),an,W)
    # Narrow, tall closely spaced library windows, not generic paired offices.
    n=max(1,int((le-1)/1.58));pitch=(le-1)/n
    for fl in range(1 if ip==0 else 0,pf):
     z=base+fl*3.55+1.9
     for k in range(n):
      dd=.5+(k+.5)*pitch;x=a[0]+ux*dd;y=a[1]+uy*dd
      alongbox(gl,(x+nx*.12,y+ny*.12,z),(pitch*.69,.12,2.25),an,G)
      alongbox(trim,(x+nx*.35,y+ny*.35,z),(pitch*.20,.65,2.55),an,W)
     alongbox(trim,(cx+nx*.22,cy+ny*.22,z-1.3),(le,.50,.20),an,W)
    if ip==0:
     n=max(2,round(le/7.2))
     for k in range(n):
      dd=(k+.5)*le/n;x=a[0]+ux*dd-nx*.8;y=a[1]+uy*dd-ny*.8
      trim.tube((x,y,base),(x,y,base+3.55),.46,m=W,n=14)
     # Floor slab above open colonnade, distinctly separated from grade.
     alongbox(trim,(cx,cy,base+3.58),(le,.9,.48),an,W)
    if ip==1:
     for k in range(n):
      dd=.5+(k+.5)*pitch
      alongbox(trim,(a[0]+ux*dd+nx*.1,a[1]+uy*dd+ny*.1,base+h-.6),(.26,.28,.75),an,14)
  # The roof pyramid is unambiguously visible in the official 2025 International Hall photo.
  p=parts[1]['polygon'];cx=sum(x for x,y in p)/4;cy=sum(y for x,y in p)/4;z=base+7*3.55+.45
  q=rect(cx,cy,20,18,-.0994);peak=(cx,cy,z+9.4)
  extrude(roof,q,z,z+.7,W)
  for a,b in zip(q,q[1:]+q[:1]):
   roof.poly([(a[0],a[1],z+.7),(b[0],b[1],z+.7),peak],[(0,1,2)],G)
   roof.tube((a[0],a[1],z+.7),peak,.09,m=S,n=6)
   for k in range(1,6):
    t=k/6;aa=(a[0]*(1-t)+cx*t,a[1]*(1-t)+cy*t,z+.7+(8.7)*t);bb=(b[0]*(1-t)+cx*t,b[1]*(1-t)+cy*t,z+.7+8.7*t)
    roof.tube(aa,bb,.048,m=S,n=5)
    start=(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,z+.7);roof.tube(start,peak,.046,m=S,n=5)
  # Green surfaced library roof terrace visible in the 2025 official oblique photo.
  ma.append(mat('PHOTO • library roof recreation green',(.10,.36,.24)))
  alongbox(roof,(49,-244,base+3*3.55+.42),(56,12,.05),-.0994,len(ma)-1)
  for yy in (-249,-239):alongbox(roof,(49,yy,base+3*3.55+.46),(52,.08,.025),-.0994,W)
  # Roof terrace rail rather than an arbitrary HVAC row.
  for a,b,le,ux,uy,nx,ny,an in _edges(parts[0]['polygon']):
   z=base+3*3.55+.8
   alongbox(roof,((a[0]+b[0])/2,(a[1]+b[1])/2,z),(le,.055,.055),an,S)
   for k in range(int(le/2)+1):
    x=a[0]+ux*k*2;y=a[1]+uy*k*2;roof.tube((x,y,z-.65),(x,y,z),.03,m=S,n=4)
 elif bid==146:
  p=parts[0]['polygon'];h=5*3.55
  extrude(wall,p,base,base+h,W);extrude(roof,p,base+h,base+h+.35,W)
  for a,b,le,ux,uy,nx,ny,an in _edges(p):
   if le<4:continue
   cx,cy=(a[0]+b[0])/2,(a[1]+b[1])/2
   alongbox(gl,(cx+nx*.13,cy+ny*.13,base+h*.48),(le-.5,.15,h*.92),an,G)
   for k in range(max(1,int(le/1.6))+1):
    dd=k*le/max(1,int(le/1.6));alongbox(trim,(a[0]+ux*dd+nx*.27,a[1]+uy*dd+ny*.27,base+h*.48),(.08,.15,h*.92),an,S)
   for fl in range(5):alongbox(trim,(cx+nx*.25,cy+ny*.25,base+fl*3.55+.35),(le,.28,.24),an,W)
  # Primary southwest long facade: upper cantilevered perforated screen, inset glazing,
  # two distinct projecting green glass boxes, round columns and shading louvers.
  a=(-84.325,-250.231);b=(-17.758,-252.461);dx=b[0]-a[0];dy=b[1]-a[1];le=math.hypot(dx,dy);ux,uy=dx/le,dy/le;nx,ny=uy,-ux;an=math.atan2(dy,dx)
  def box(u,v,z,w,d,h,mi,mesh=trim):alongbox(mesh,(a[0]+ux*u+nx*v,a[1]+uy*u+ny*v,base+z),(w,d,h),an,mi)
  box(le/2,1.1,3.8,le,2.4,.8,W);box(12,2.0,12.7,25,1.0,9.7,W)
  # Wide left return of the screen follows actual end face.
  box(-1.1,-12,12.7,1.0,28,9.7,W)
  for u in (2,12,23):
   trim.tube((a[0]+ux*u+nx*1.2,a[1]+uy*u+ny*1.2,base+4.2),(a[0]+ux*u+nx*1.2,a[1]+uy*u+ny*1.2,base+8),.37,m=S,n=12)
  # Dark tiny disks visualize perforations as original geometry, no photo texture.
  for iu in range(75):
   for iz in range(24):
    u=.15+iu*.33;z=8.1+iz*.4
    if (iu*7+iz*11)%13<3:continue
    box(u,2.515,z,.072,.018,.075,D)
  for u,w,z,hh in ((36,13,9.8,6.2),(57,11,10,8)):
   box(u,1.6,z,w,1.7,hh,G,gl);box(u,2.0,z+hh/2+.15,w+1.5,2.5,.35,W)
   for k in range(int(w/.8)+1):box(u-w/2+k*.8,2.48,z,.06,.13,hh,S)
   if u==36:
    for k in range(1,6):box(u,2.48,z-hh/2+k*hh/6,w,.10,.055,S)
  # Upper slender beam gently drops from the heavy left screen to the right wing.
  for k in range(24):
   u=25+k*(le-25)/24;z=17.2-1.3*math.sin(k/24*math.pi/2)
   box(u,2.0,z,(le-25)/24+.1,1.0,.65,W)
  for u in range(27,66,7):
   box(u,.8,14.6,.22,.35,2.5,W)
  for z in (13.5,14.1,14.7):box(45,1.5,z,39,.65,.15,S)
  for z in (1.0,1.65,2.3):box(le/2,.45,z,le,.50,.16,S)
  for u in (38,57):
   box(u,3,3.05,7,3.5,.18,G,gl)
  label('CHOSUN', (a[0]+ux*12+nx*2.55,a[1]+uy*12+ny*2.55,base+13.6),2.25,col,mats[5],an)
  label('UNIVERSITY', (a[0]+ux*12+nx*2.55,a[1]+uy*12+ny*2.55,base+11.55),1.65,col,mats[5],an)
  label('SINCE 1946', (a[0]+ux*15+nx*2.55,a[1]+uy*15+ny*2.55,base+10.35),.72,col,mats[5],an)
  label('INTERNATIONAL BUILDING', (a[0]+ux*20+nx*2.5,a[1]+uy*20+ny*2.5,base+3.62),.46,col,mats[8],an)
 elif bid==132:
  # Seven-level gym volume. Top two levels are distinct from tall gridded bays.
  p=parts[0]['polygon'];h=7*3.55;extrude(wall,p,base+3.55,base+h,W);extrude(roof,p,base+h,base+h+.28,W)
  for a,b,le,ux,uy,nx,ny,an in _edges(p):
   if le<4:continue
   cx,cy=(a[0]+b[0])/2,(a[1]+b[1])/2;n=max(1,round(le/7))
   for k in range(n):
    u=(k+.5)*le/n;x=a[0]+ux*u;y=a[1]+uy*u;ww=le/n-.75
    alongbox(gl,(x+nx*.12,y+ny*.12,base+11.5),(ww,.14,16),an,G)
    for j in range(1,7):alongbox(trim,(x+nx*.24,y+ny*.24,base+3.5+j*2.3),(ww,.12,.1),an,S)
    for j in range(1,6):alongbox(trim,(x+ux*(j-3)*ww/6+nx*.25,y+uy*(j-3)*ww/6+ny*.25,base+11.5),(.07,.12,16),an,S)
   for k in range(n+1):
    u=k*le/n;alongbox(trim,(a[0]+ux*u+nx*.4,a[1]+uy*u+ny*.4,base+10),(.7,1.0,20),an,W)
   for z,hh,depth in ((20,.5,.9),(22.1,.6,1.2),(24.4,.4,1.4),(h+.15,.55,2.0)):
    alongbox(trim,(cx+nx*.5,cy+ny*.5,base+z),(le+1,depth,hh),an,W)
   # Thin rounded projecting roof nosing, no massive inset rectangular lid.
   trim.tube((a[0]+nx*.9,a[1]+ny*.9,base+h+.3),(b[0]+nx*.9,b[1]+ny*.9,base+h+.3),.28,m=W,n=10)
   nn=max(1,int(le/1.6))
   for k in range(nn):
    u=(k+.5)*le/nn;x=a[0]+ux*u+nx*.12;y=a[1]+uy*u+ny*.12
    alongbox(gl,(x,y,base+21.0),(1.2,.12,1.25),an,G)
    # Pointed lancet windows in top strip, verified close official gym photo.
    z=base+22.65;w=.72;hh=1.45
    pts=[(x-ux*w/2,y-uy*w/2,z),(x+ux*w/2,y+uy*w/2,z),(x+ux*w/2,y+uy*w/2,z+hh*.58),(x,y,z+hh),(x-ux*w/2,y-uy*w/2,z+hh*.58)]
    gl.poly(pts,[(0,1,2,3,4)],G)
    for pa,pb in zip(pts,pts[1:]+pts[:1]):trim.tube(pa,pb,.038,m=S,n=4)
  # A shallow roof lightwell toward one end, not a second building on the roof.
  xs=[x for x,y in p];ys=[y for x,y in p];cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
  q=rect(cx-12,cy+5,13,10);extrude(roof,q,base+h+.3,base+h+1.2,W)
  for k in range(11):alongbox(roof,(cx-18+k*1.2,cy+5,base+h+1.27),(.07,9.5,.08),0,S)
  alongbox(roof,(cx-12,cy+5,base+h+1.22),(12.5,9.5,.08),0,G)
 for name,mesh in [('corrected volumes',wall),('source-specific glazing',gl),('architectural relief',trim),('verified roof profile',roof)]:
  if mesh.v:
   ob=mesh.object('CAMPUS_BUILDING '+str(bid)+' | PHOTO '+name,ma,col);ob['evidence']='Official campus photos inspected 2026-10-08; dimensions approximate, no photo textures.'
 return True

def accents(bid,parts,base,floors,col,mats):
 """Secondary photo-backed features, using mapped outlines without moving buildings."""
 if bid not in (133,141,142,145,150,135,147):return
 me=Mesh();ma=list(mats)+[mat('PHOTO • warm olive balcony recess',(.31,.32,.22)),mat('PHOTO • pale stone cladding',(.76,.75,.69)),mat('PHOTO • green canopy glazing',(.19,.44,.41),.3,.2)]
 for ip,part in enumerate(parts):
  p=part['polygon'];h=part['floors']*(3.15 if bid in (142,147) else 3.55)
  edges=list(_edges(p));long=sorted(edges,key=lambda e:e[2],reverse=True)
  if bid in (133,145):
   for a,b,le,ux,uy,nx,ny,an in edges:
    if le<15:continue
    nn=max(1,round(le/6));cx,cy=(a[0]+b[0])/2,(a[1]+b[1])/2
    for k in range(nn+1):
     dd=k*le/nn;alongbox(me,(a[0]+ux*dd+nx*.3,a[1]+uy*dd+ny*.3,base+h/2),(.52,.72,h),an,12 if bid==133 else 0)
    for fl in range(part['floors']):alongbox(me,(cx+nx*.22,cy+ny*.22,base+fl*3.55+.3),(le,.65,.5 if bid==145 else .28),an,12)
   if bid==133:
    a,b,le,ux,uy,nx,ny,an=min(edges,key=lambda e:(e[0][1]+e[1][1])/2);cx,cy=(a[0]+b[0])/2,(a[1]+b[1])/2
    alongbox(me,(cx+nx*1.5,cy+ny*1.5,base+4),(14,3.5,.42),an,12)
  elif bid==142:
   if ip>0:
    for a,b,le,ux,uy,nx,ny,an in edges:
     cx,cy=(a[0]+b[0])/2,(a[1]+b[1])/2
     alongbox(me,(cx+nx*.7,cy+ny*.7,base+h+.55),(le+2.1,2.2,.45),an,4)
     if le>30:
      for frac in (.17,.82):
       xx=a[0]+ux*le*frac+nx*.27;yy=a[1]+uy*le*frac+ny*.27
       alongbox(me,(xx,yy,base+h*.52),(2.4,.30,h*.9),an,11)
       for fl in range(2,11):
        alongbox(me,(xx+nx*.30,yy+ny*.30,base+fl*3.15),(2.55,.85,.14),an,4)
        alongbox(me,(xx+nx*.5,yy+ny*.5,base+fl*3.15+.85),(2.5,.08,.08),an,5)
   else:
    for a,b,le,ux,uy,nx,ny,an in long[:2]:
     alongbox(me,((a[0]+b[0])/2+nx*.25,(a[1]+b[1])/2+ny*.25,base+3.3),(le*.7,.15,3.2),an,13)
  elif bid==147:
   # Both dormitory footprints show tall glazed end stair cores and broad roof caps.
   short=[ed for ed in edges if ed[2]>6 and ed[2]<max(ee[2] for ee in edges)*.6]
   for a,b,le,ux,uy,nx,ny,an in short[:2]:
    cx,cy=(a[0]+b[0])/2,(a[1]+b[1])/2;ww=min(6.5,le*.60)
    alongbox(me,(cx+nx*.35,cy+ny*.35,base+h*.51),(ww,.24,h*.97),an,13)
    for f in range(19):alongbox(me,(cx+nx*.50,cy+ny*.50,base+.4+f*(h-.6)/18),(ww,.08,.07),an,4)
    for u in (-ww/2,0,ww/2):alongbox(me,(cx+ux*u+nx*.51,cy+uy*u+ny*.51,base+h*.51),(.07,.08,h*.97),an,4)
    alongbox(me,(cx,cy,base+h+.7),(le+2.4,7.5,.35),an,4)
  elif bid==141 and part['floors']==4:
   a,b,le,ux,uy,nx,ny,an=min(edges,key=lambda e:(e[0][1]+e[1][1])/2);dd=le*.16;x=a[0]+ux*dd;y=a[1]+uy*dd
   alongbox(me,(x+nx*.35,y+ny*.35,base+h/2),(3.4,.3,h*.96),an,13)
   for fl in range(9):alongbox(me,(x+nx*.54,y+ny*.54,base+fl*h/9),(3.4,.08,.065),an,4)
   for k in (-1,0,1):alongbox(me,(x+ux*k+nx*.54,y+uy*k+ny*.54,base+h/2),(.065,.08,h*.96),an,4)
  elif bid==150:
   a,b,le,ux,uy,nx,ny,an=min(edges,key=lambda e:(e[0][0]+e[1][0])/2)
   cx,cy=(a[0]+b[0])/2,(a[1]+b[1])/2
   for fl in range(1,6):
    z=base+fl*3.55;alongbox(me,(cx+nx*1.4,cy+ny*1.4,z),(min(10,le+1),3.4,.3),an,4)
    alongbox(me,(cx+nx*3,cy+ny*3,z+1),(min(10,le+1),.07,.07),an,5)
    for k in range(8):
     u=(k-3.5)*1.1;xx=cx+ux*u+nx*3;yy=cy+uy*u+ny*3;me.tube((xx,yy,z),(xx,yy,z+1),.035,m=5,n=4)
  elif bid==135 and ip==0:
   a,b,le,ux,uy,nx,ny,an=min(edges,key=lambda e:(e[0][1]+e[1][1])/2);cx,cy=(a[0]+b[0])/2,(a[1]+b[1])/2
   # Fan-shaped green glass entry canopy, directly visible in official exterior.
   apex=(cx-nx,cy-ny,base+4.3)
   for k in range(12):
    aa=math.pi*k/12;bb=math.pi*(k+1)/12
    p1=(cx+ux*8*math.cos(aa)+nx*5*math.sin(aa),cy+uy*8*math.cos(aa)+ny*5*math.sin(aa),base+3.3)
    p2=(cx+ux*8*math.cos(bb)+nx*5*math.sin(bb),cy+uy*8*math.cos(bb)+ny*5*math.sin(bb),base+3.3)
    me.poly([apex,p1,p2],[(0,1,2)],13);me.tube(apex,p1,.045,m=4,n=4);me.tube(p1,p2,.06,m=4,n=4)
 if me.v:
  ob=me.object('CAMPUS_BUILDING '+str(bid)+' | PHOTO verified secondary accents',ma,col);ob['evidence']='Inspected official exterior photo; feature dimensions and hidden faces approximate.'
