"""Building-by-building procedural reconstruction from individually inspected official photos.
Only visible cues are reconstructed. Hidden facades, metric sizes and entrance orientations
are approximate. No reference photograph is embedded in the distributable mesh.
"""
import math
from mesh_architecture import Mesh,mat,rect,extrude,alongbox
from facade_specials import _edges
from photo_refinements import label
# max directory level is not a measurement of height: auditoriums have larger storeys.
FLOORS={171:1,176:1,178:2,130:5,153:5,158:2,128:2,129:1,131:8,137:3,139:5,140:4,143:3,144:3,148:4,151:3,152:6,154:5,155:4,156:4,157:4,159:3,160:5,165:4,166:5,167:1,177:5}
HEIGHTS={171:4.2,176:3.4,178:8.0,158:10.8,128:15.5,129:7.5,143:11.2,167:4.5,164:12.4}
# Individual schedules, not randomly selected generic campus families.
SPECS={
 130:dict(color=(.44,.24,.16),glass=(.15,.27,.27),pitch=3.4,win=(.65,1.65),belts=.09,feature="natural_curtain"),
 153:dict(color=(.48,.25,.18),glass=(.24,.41,.42),pitch=3.8,win=(.64,1.75),belts=.10,feature="cylinder_stair"),
 131:dict(color=(.76,.77,.73),glass=(.22,.39,.37),pitch=3.3,win=(.70,1.65),belts=.30,feature='law_tower'),
 137:dict(color=(.49,.12,.105),glass=(.12,.27,.25),pitch=3.05,win=(.53,2.25),belts=.12,feature='classical_portico'),
 139:dict(color=(.71,.72,.69),glass=(.13,.27,.27),pitch=3.5,win=(.73,1.80),belts=.08,feature='research'),
 140:dict(color=(.45,.22,.17),glass=(.16,.33,.33),pitch=3.2,win=(.64,1.70),belts=.12,feature='cylinder_stair'),
 144:dict(color=(.59,.43,.32),glass=(.20,.36,.34),pitch=3.4,win=(.58,2.0),belts=.1,feature='vertical_panels'),
 148:dict(color=(.65,.69,.62),glass=(.17,.35,.33),pitch=2.8,win=(.84,1.9),belts=.45,feature='ribbon'),
 151:dict(color=(.68,.71,.65),glass=(.18,.30,.28),pitch=3.5,win=(.57,1.85),belts=.32,feature='sloped_roof'),
 152:dict(color=(.75,.77,.73),glass=(.12,.29,.28),pitch=3.5,win=(.75,1.65),belts=.10,feature='dental_education'),
 154:dict(color=(.78,.78,.72),glass=(.16,.32,.34),pitch=3.8,win=(.54,1.85),belts=.16,feature='medical_curtain'),
 155:dict(color=(.48,.22,.15),glass=(.17,.35,.35),pitch=3.4,win=(.60,1.75),belts=.13,feature='cylinder_stair'),
 156:dict(color=(.72,.72,.63),glass=(.26,.36,.34),pitch=4.3,win=(.72,1.8),belts=.26,feature='pharmacy_frame'),
 157:dict(color=(.38,.23,.17),glass=(.15,.24,.23),pitch=3.3,win=(.53,1.7),belts=.09,feature='brick_lintels'),
 159:dict(color=(.10,.36,.33),glass=(.21,.30,.28),pitch=2.65,win=(.82,1.65),belts=.48,feature='dining_colonnade'),
 160:dict(color=(.46,.20,.15),glass=(.17,.32,.30),pitch=3.6,win=(.55,1.8),belts=.08,feature='brick_entry'),
 165:dict(color=(.56,.60,.59),glass=(.15,.27,.29),pitch=5.2,win=(.66,1.9),belts=.30,feature='box_balconies'),
 166:dict(color=(.71,.73,.70),glass=(.13,.40,.38),pitch=4.5,win=(.84,2.30),belts=.65,feature='dental_hospital'),
 177:dict(color=(.77,.78,.71),glass=(.18,.31,.30),pitch=4.0,win=(.70,1.65),belts=.13,feature='gold_stair'),
}

def _frame(edge,base):
 a,b,le,ux,uy,nx,ny,an=edge
 def pos(u,v,z):return a[0]+ux*u+nx*v,a[1]+uy*u+ny*v,base+z
 return pos

def _front(p):
 es=list(_edges(p));long=max(e[2] for e in es)
 return min([e for e in es if e[2]>max(6,long*.28)] or es,key=lambda e:(e[0][1]+e[1][1])/2)

def build(b,parts,col,mats):
 bid=b['id'];base=b['base'];fs=b['floors'];p=b['poly']
 if bid is None:
  # Unidentified auxiliary footprints must not inherit invented office facades.
  me=Mesh();h=b.get('height_m',fs*3.55);extrude(me,p,base,base+h,1)
  ob=me.object('CAMPUS_BUILDING '+str(b['osm_id'])+' | UNVERIFIED plain contextual mass only',mats,col)
  ob['confidence']='Mapped footprint; previous estimated height retained. Exterior, storeys and use unverified; no fabricated windows, entrance or rooftop plant.'
  return True
 if bid not in SPECS and bid not in (128,129,143,158,164,167,171,176,178):return False
 ma=list(mats)+[mat('REVIEW • chalk stone',(.79,.80,.75)),mat('REVIEW • muted teal glass',(.13,.35,.34),.27,.2),mat('REVIEW • metal',(.51,.56,.55),.35,.5),mat('REVIEW • recessed shadow',(.09,.13,.14)),mat('REVIEW • warm yellow entrance',(.87,.65,.035))]
 W,G,S,D,Y=11,12,13,14,15
 shell,win,trim,roof=Mesh(),Mesh(),Mesh(),Mesh();h=HEIGHTS.get(bid,fs*3.55)
 e=_front(p)
 if bid==128:
  aa=(147.,-215.);bb=(206.,-220.);dx,dy=bb[0]-aa[0],bb[1]-aa[1];ll=math.hypot(dx,dy);e=(aa,bb,ll,dx/ll,dy/ll,dy/ll,-dx/ll,math.atan2(dy,dx))
 a,bb,le,ux,uy,nx,ny,an=e;b['front_edge']=e;pos=_frame(e,base)
 def box(u,v,z,w,d,hh,mi=W,mesh=trim):alongbox(mesh,pos(u,v,z),(w,d,hh),an,mi)
 if bid==128:
  # Two usable floor levels in an auditorium-height stepped volume, not four office bands.
  extrude(shell,p,base,base+h*.78,W);extrude(roof,p,base+h*.78,base+h*.78+.24,W)
  # Separate rear auditorium roof volume, retaining the source-mapped outside boundary.
  rear=[]
  for pa,pb in zip(p,p[1:]+p[:1]):
   ia=pa[1]>-185;ib=pb[1]>-185
   if ia:rear.append(pa)
   if ia!=ib:
    t=(-185-pa[1])/(pb[1]-pa[1]);rear.append((pa[0]+t*(pb[0]-pa[0]),-185))
  extrude(shell,rear,base+h*.78,base+h,W);extrude(roof,rear,base+h,base+h+.24,W)
  for ed in _edges(p):
   aa,bb,ll,uu,vv,nn,mm,ang=ed;po=_frame(ed,base)
   for z in [1.3,4.9,8.5,12.1,15.2]:
    if z<=12.1 or min(aa[1],bb[1])>=-185:alongbox(trim,po(ll/2,.075,z),(ll,.1,.07),ang,1)
   n=max(1,int(ll/1.8))
   for k in range(n):
    u=(k+.5)*ll/n
    # Long slender side windows and the lower horizontal slit in inspected image.
    alongbox(win,po(u,.10,9.2),(.58,.08,3.1),ang,G)
    alongbox(win,po(u,.11,3.35),(1.32,.08,.52),ang,G)
  # Main large glass frontage with visible orthogonal mullion grid.
  box(le*.56,.20,h*.52,le*.51,.15,h*.84,G,win)
  for k in range(15):box(le*.305+k*le*.51/14,.34,h*.52,.09,.11,h*.84,S)
  for k in range(9):box(le*.56,.34,1.6+k*h*.84/8,le*.51,.11,.085,S)
  # A high central rectangular return, lower adjoining block and yellow portal.
  box(le*.17,-5,h*.57,le*.25,10,h*1.14,W,shell)
  box(le*.91,-5,h*.43,le*.17,10,h*.86,W,shell)
  box(le*.55,2,4.25,le*.27,3.8,.95,Y)
  for u in (le*.415,le*.685):box(u,2,2.35,.55,3.8,3.8,Y)
  box(le*.55,.35,1.85,le*.24,.16,3.5,G,win)
  label('HAEOREUM',pos(le*.16,.2,h*1.12-2),.67,col,mats[5],an)
 elif bid==143:
  # Rear dining block, open front pergola, rounded right brick wall and separate low entry.
  # Retain mapped outline at low plinth; upper volume is deliberately recessed.
  extrude(shell,p,base,base+.22,0)
  bx=b['bbox'];cx,cy=b['cx'],b['cy'];depth=bx[3]-bx[1]
  # Build the rear strip and a left brick stair/core, leaving open sky in front frame.
  rear=rect(cx,cy+depth*.23,(bx[2]-bx[0])*.98,depth*.52)
  extrude(shell,rear,base,base+h*.72,0);extrude(roof,rear,base+h*.72,base+h*.72+.20,W)
  box(le*.12,-3,h*.52,le*.22,8,h*1.04,0,shell)
  box(le*.23,.13,h*.48,2.15,.15,h*.94,G,win)
  for zz in range(1,11):box(le*.23,.24,zz,2.2,.08,.08,S)
  for u in (le*.33,le*.78):box(u,.15,h*.49,.55,.65,h*.98,W)
  box(le*.555,.15,h*.98,le*.46,.70,.72,W)
  # Thin steel pergola grid genuinely spans open air, rather than textured ceiling.
  for k in range(9):box(le*.34+k*le*.44/8,-4.1,h*.96,.055,8.4,.07,S)
  for k in range(6):box(le*.56,-k*1.65,h*.96,le*.45,.065,.065,S)
  # The visibly curved right red-brick parapet and wall are segmented original geometry.
  cc=pos(le*.79,-5,0);r=min(7,le*.17)
  for k in range(24):
   t0=-math.pi/2+k*math.pi/24;t1=-math.pi/2+(k+1)*math.pi/24
   pa=(cc[0]+r*math.cos(t0),cc[1]+r*math.sin(t0));pb=(cc[0]+r*math.cos(t1),cc[1]+r*math.sin(t1));ang=math.atan2(pb[1]-pa[1],pb[0]-pa[0]);mid=((pa[0]+pb[0])/2,(pa[1]+pb[1])/2)
   for zz,hh in ((2.0,4.0),(h-.7,1.4)):
    alongbox(shell,(*mid,base+zz),(math.dist(pa,pb)+.04,.38,hh),ang,0)
   alongbox(trim,(*mid,base+h+.06),(math.dist(pa,pb)+.08,.56,.13),ang,W)
  box(le*.47,1.0,2.15,le*.20,4.2,4.3,W,shell)
  box(le*.47,3.15,2.1,le*.14,.10,1.8,G,win)
  box(le*.10,.2,1.6,le*.17,.12,3.0,G,win)
  label('SOLMARU',pos(le*.11,.24,5.1),.53,col,mats[4],an)
 elif bid==129:
  # A small gable-fronted museum; official directory lists one floor, attic-like front windows.
  extrude(shell,p,base,base+4.2,W)
  x0,y0,x1,y1=b['bbox'];cx=b['cx'];ridge=base+7.5
  roof.poly([(x0-.4,y0-.4,base+4.2),(cx,y0-.4,ridge),(cx,y1+.4,ridge),(x0-.4,y1+.4,base+4.2)],[(0,1,2,3)],6)
  roof.poly([(cx,y0-.4,ridge),(x1+.4,y0-.4,base+4.2),(x1+.4,y1+.4,base+4.2),(cx,y1+.4,ridge)],[(0,1,2,3)],6)
  for yy in (y0,y1):shell.poly([(x0,yy,base+4.2),(x1,yy,base+4.2),(cx,yy,ridge)],[(0,1,2)],W)
  for ed in _edges(p):
   po=_frame(ed,base);ll=ed[2];ang=ed[-1]
   for k in range(max(1,int(ll/3))):alongbox(win,po((k+.5)*ll/max(1,int(ll/3)),.13,2.1),(1.5,.13,2.2),ang,G)
  box(le/2,1.2,2.0,le*.42,2.5,4.0,W)
  box(le/2,2.48,1.8,le*.29,.13,3.6,D,win)
  for u in (le*.3,le*.7):box(u,.17,5.1,le*.17,.13,1.45,G,win)
 elif bid==178:
  # Two brick storeys under deep pale cantilevers, with a small pale rooftop service block.
  extrude(shell,p,base,base+7.1,0);extrude(roof,p,base+7.1,base+7.23,W)
  for ed in _edges(p):
   po=_frame(ed,base);ll=ed[2];ang=ed[-1]
   for z in (3.55,7.15):alongbox(trim,po(ll/2,.6,z),(ll+1.2,1.3,.30),ang,W)
   n=max(1,int(ll/3.4))
   for k in range(n):
    for f in range(2):
     u=(k+.5)*ll/n;ww=1.5;zz=1.9+f*3.55
     alongbox(trim,po(u,.15,zz),(ww+.25,.22,1.9),ang,W);alongbox(win,po(u,.30,zz),(ww,.09,1.65),ang,G)
   if ll>10:
    for k in range(n+1):alongbox(trim,po(k*ll/n,1.1,1.65),(.25,.25,3.3),ang,W)
  extrude(roof,rect(b['cx'],b['cy'],13,9),base+7.1,base+10.3,W)
  box(le/2,.35,1.5,3.0,.16,3,G,win)
 elif bid==171:
  # Single-storey hospital funeral facility, independently placed at its official map pin.
  extrude(shell,p,base,base+4.0,2);extrude(roof,p,base+4,base+4.25,W)
  for ed in _edges(p):
   po=_frame(ed,base);ll=ed[2];ang=ed[-1]
   alongbox(trim,po(ll/2,.15,1.0),(ll,.24,.9),ang,W)
   for k in range(max(2,int(ll/3.2))):alongbox(win,po((k+.5)*ll/max(2,int(ll/3.2)),.20,2.3),(1.35,.10,2.6),ang,G)
  box(le/2,1.5,3.65,le*.92,3.2,.40,W)
  box(le/2,.32,1.6,le*.48,.16,3.2,G,win)
  for k in range(7):
   u=le*.28+k*le*.44/6;z=2.75
   win.poly([pos(u-.7,.43,z),pos(u,.43,z+.72),pos(u+.7,.43,z),pos(u,.43,z-.72)],[(0,1,2,3)],Y)
 elif bid==176:
  # Low experimental huts/pads and solar test arrays, not an invented tower.
  b['collision_polys']=[]
  for row in range(2):
   for j in range(3):
    x=b['cx']-18+j*18;y=b['cy']-9+row*18;q=rect(x,y,7.2,5.6);b['collision_polys'].append(q)
    extrude(shell,q,base,base+2.8,W)
    roof.poly([(x-3.9,y-3.1,base+2.8),(x+3.9,y-3.1,base+2.8),(x+3.9,y,base+3.6),(x-3.9,y,base+3.6)],[(0,1,2,3)],G)
    roof.poly([(x-3.9,y,base+3.6),(x+3.9,y,base+3.6),(x+3.9,y+3.1,base+2.8),(x-3.9,y+3.1,base+2.8)],[(0,1,2,3)],G)
    alongbox(win,(x,y-2.85,base+1.4),(2.2,.1,2.4),0,G)
  for j in range(9):
   x=b['cx']-24+j*6;y=b['cy']-20
   roof.poly([(x-2.3,y-1.8,base+.45),(x+2.3,y-1.8,base+.45),(x+2.3,y+1.8,base+1.75),(x-2.3,y+1.8,base+1.75)],[(0,1,2,3)],8)
   for k in range(5):trim.tube((x-2.3+k*1.15,y-1.8,base+.46),(x-2.3+k*1.15,y+1.8,base+1.76),.025,m=S,n=4)
 elif bid==167:
  # Existing OSM stage footprint is not a four-storey office building.
  extrude(shell,p,base,base+1.0,W);extrude(roof,p,base+4.3,base+4.6,W)
  for ed in _edges(p):
   aa,bb,ll,uu,vv,nn,mm,ang=ed
   if ll>6:
    for k in (0,1):trim.tube((aa[0]+(bb[0]-aa[0])*k,aa[1]+(bb[1]-aa[1])*k,base+1),(aa[0]+(bb[0]-aa[0])*k,aa[1]+(bb[1]-aa[1])*k,base+4.3),.18,m=W,n=8)
  # Audience terracing remains outside building footprint and documented separately.
 elif bid==158:
  # High-ceiling teaching workshop, large industrial doors and attached exterior steel stairs.
  extrude(shell,p,base,base+h,W);extrude(roof,p,base+h,base+h+.30,W)
  for ed in _edges(p):
   po=_frame(ed,base);ll=ed[2];ang=ed[-1]
   alongbox(trim,po(ll/2,.14,3.3),(ll,.20,.28),ang,1)
   alongbox(trim,po(ll/2,.14,7.1),(ll,.20,.28),ang,1)
   if ll>8:
    alongbox(win,po(ll/2,.17,8.2),(ll*.68,.12,1.8),ang,G)
    for k in range(max(3,int(ll/1.2))):alongbox(trim,po(ll*.16+k*ll*.68/max(3,int(ll/1.2)),.27,8.2),(.065,.10,1.8),ang,S)
  box(le*.33,.23,2.4,min(9,le*.37),.15,4.8,D,win)
  box(le*.75,.23,1.6,3.1,.15,3.2,G,win)
 elif bid==164:
  # Parking building: open concrete decks rather than occupied office window copies.
  for floor in range(5):extrude(shell,p,base+floor*3.1,base+floor*3.1+.30,W)
  for ed in _edges(p):
   aa,bb,ll,uu,vv,nn,mm,ang=ed;po=_frame(ed,base)
   for j in range(max(2,int(ll/6))+1):alongbox(trim,po(j*ll/max(2,int(ll/6)),0,h/2),(.45,.65,h),ang,W)
   for floor in range(4):alongbox(trim,po(ll/2,.1,floor*3.1+1.2),(ll,.18,.85),ang,Y)
  blue=len(ma);ma.append(mat('REVIEW • parking sky blue cladding',(.045,.40,.59)))
  trim.mi=[blue if x==Y else x for x in trim.mi]
 else:
  sp=SPECS[bid];mi=len(ma);ma.append(mat('REVIEW '+str(bid)+' • observed facade',sp['color']));gi=len(ma);ma.append(mat('REVIEW '+str(bid)+' • observed glazing',sp['glass'],.28,.2))
  for part in parts:
   pp=part['polygon'];pf=part.get('floors',fs);ph=pf*3.55
   extrude(shell,pp,base,base+ph,mi);extrude(roof,pp,base+ph,base+ph+.28,W)
   for ed in _edges(pp):
    aa,bb,ll,uu,vv,nn,mm,ang=ed;po=_frame(ed,base)
    if ll<2:continue
    n=max(1,round((ll-1)/sp['pitch']));pitch=(ll-1)/n
    for fl in range(pf):
     z=fl*3.55+1.9
     for k in range(n):
      u=.5+(k+.5)*pitch;ww=pitch*sp['win'][0];wh=sp['win'][1]
      alongbox(trim,po(u,.13,z),(ww+.16,.21,wh+.16),ang,W)
      alongbox(win,po(u,.255,z),(ww,.075,wh),ang,gi)
      alongbox(trim,po(u,.31,z),(.055,.08,wh),ang,S)
      alongbox(trim,po(u,.32,z-wh*.15),(ww,.08,.05),ang,S)
      if bid in (137,157):alongbox(trim,po(u,.32,z+wh/2+.15),(ww+.26,.32,.17),ang,W)
     alongbox(trim,po(ll/2,.16,(fl+1)*3.55-.12),(ll,.30,sp['belts']),ang,W)
    if bid in (144,156,166,177):
     for k in range(n+1):alongbox(trim,po(.5+k*pitch,.18,ph/2),(.28,.40,ph),ang,W)
    if bid in (139,166):
     alongbox(win,po(ll/2,.15,ph-1.0),(ll-.4,.10,1.15),ang,D)
    if bid==148:
     for fl in range(pf):alongbox(trim,po(ll/2,.28,fl*3.55+2.8),(ll,.60,.18),ang,W)
  feature=sp['feature'];w=min(le*.28,10.)
  if feature in ('cylinder_stair','medical_curtain','natural_curtain','dental_education','gold_stair','law_tower'):
   cw=min(10.,le*.45) if bid==153 else min(7.,le*.19);u=le*(.25 if feature=='dental_education' else .5)
   box(u,.20,h*.51,cw,.24,h*.96,gi,win)
   for k in range(fs*2+1):box(u,.39,.5+k*(h-.8)/(fs*2),cw,.08,.07,S)
   for du in (-cw/2,0,cw/2):box(u+du,.38,h*.51,.085,.10,h*.96,S)
   if feature=='cylinder_stair':
    r=cw/2
    for k in range(16):
     t0=math.pi*k/16;t1=math.pi*(k+1)/16
     pa=pos(u+r*math.cos(t0),r*(1.0 if bid==153 else .45)*math.sin(t0),.5);pb=pos(u+r*math.cos(t1),r*(1.0 if bid==153 else .45)*math.sin(t1),.5)
     win.poly([pa,pb,(pb[0],pb[1],base+h+.6),(pa[0],pa[1],base+h+.6)],[(0,1,2,3)],gi)
     trim.tube(pa,(pa[0],pa[1],base+h+.6),.04,m=S,n=5)
     for floor in range(fs*2+1):
      zz=base+.5+floor*h/(fs*2);trim.tube((pa[0],pa[1],zz),(pb[0],pb[1],zz),.045,m=S,n=5)
    box(u,-.6,h+.25,cw+1,2,1.5,mi,shell)
   if feature=='medical_curtain':
    for k in range(10):box(le/2-w/2+k*w/9,2,h+.55,.12,4.5,.14,S)
   if feature=='gold_stair':
    gold=len(ma);ma.append(mat('REVIEW • ochre stair cladding',(.55,.40,.20)))
    box(le*.1,-1,h/2,le*.18,3,h,gold,shell)
    for f in range(fs):box(le*.1,1.1,f*3.55+1.4,le*.16,1.3,.25,W)
   if feature=='law_tower':box(le*.17,-2,h*.53,le*.23,4,h*1.06,W,shell)
  if feature=='classical_portico':
   w=min(14,le*.42);box(le/2,1.8,3.0,w,4,6.0,W,shell);box(le/2,3.83,2.3,3.4,.12,4.6,D,win)
   for du in (-w*.39,w*.39):
    trim.tube(pos(le/2+du,4.05,.1),pos(le/2+du,4.05,5.4),.40,m=W,n=12)
    box(le/2+du,4.05,5.45,1.,.95,.35,W)
   box(le/2,3.9,5.9,w+1,.6,.45,W)
   q=[pos(le/2-w*.40,1,6.25),pos(le/2+w*.40,1,6.25),pos(le/2,1,8.45)]
   trim.poly(q,[(0,1,2)],W)
  elif feature=='research':
   for u in (le*.42,le*.57,le*.72):box(u,.31,h*.55,1.8,.16,5.5,gi,win)
   roof.tube((b['cx'],b['cy'],base+h+.3),(b['cx'],b['cy'],base+h+2),2.6,m=S,n=20)
  elif feature=='dental_hospital':
   for ed in _edges(p):
    aa,bb,ll,uu,vv,nn,mm,ang=ed;po=_frame(ed,base)
    if ll<7:continue
    for k in range(max(2,int(ll/5))+1):alongbox(trim,po(k*ll/max(2,int(ll/5)),.8,h-1.0),(.45,1.6,2.0),ang,W)
    alongbox(roof,po(ll/2,1,h+.05),(ll+2,2.3,.30),ang,W)
    # Teal round portholes on the end return, as photographed.
    if ll>10:
     for f in range(fs):
      c=po(ll*.10,.62,f*3.55+1.8)
      alongbox(trim,po(ll*.10,.43,h/2),(3.2,.34,h),ang,W)
      win.poly([c]+[(c[0]+uu*.85*math.cos(k*math.tau/24),c[1]+vv*.85*math.cos(k*math.tau/24),c[2]+.85*math.sin(k*math.tau/24)) for k in range(24)],[(0,k+1,(k+1)%24+1) for k in range(24)],G)
  elif feature=='pharmacy_frame':
   ochre=len(ma);ma.append(mat('REVIEW • pharmacy ochre stone',(.57,.47,.27)))
   box(le*.08,-1,h/2,1.1,2,h+1,ochre);box(le/2,-1,h+.2,le,2,.55,ochre)
  elif feature=='dining_colonnade':
   box(le/2,2.0,4.4,le+2,4.6,.75,W)
   for k in range(max(3,int(le/5))+1):trim.tube(pos(k*le/max(3,int(le/5)),3.2,0),pos(k*le/max(3,int(le/5)),3.2,4.1),.26,m=mi,n=12)
  elif feature=='box_balconies':
   for f in range(fs):
    for k in range(max(2,int(le/5))):
     u=(k+.5)*le/max(2,int(le/5));box(u,1.,f*3.55+.4,4.2,2,.22,W);box(u,1.8,f*3.55+1.1,4.2,.22,1.2,W)
  elif feature=='sloped_roof':
   x0,y0,x1,y1=b['bbox'];roof.poly([(x0-.8,y0-.8,base+h+.3),(x1+.8,y0-.8,base+h+.3),(x1+.8,b['cy'],base+h+2.2),(x0-.8,b['cy'],base+h+2.2)],[(0,1,2,3)],6)
   roof.poly([(x0-.8,b['cy'],base+h+2.2),(x1+.8,b['cy'],base+h+2.2),(x1+.8,y1+.8,base+h+.3),(x0-.8,y1+.8,base+h+.3)],[(0,1,2,3)],6)
  # Actual entrance door and restrained canopy; special large portal already above.
  if feature!='classical_portico':
   box(le/2,.38,1.7,4.0,.16,3.2,gi,win);box(le/2,1.8,3.6,min(8,le*.35),3.6,.32,W)
 for title,me in [('individually reviewed mass',shell),('individual fenestration',win),('photo-specific relief and entry',trim),('observed roof typology',roof)]:
  if me.v:
   ob=me.object('CAMPUS_BUILDING '+str(bid)+' | REVIEWED '+title,ma,col)
   ob['source']='https://www3.chosun.ac.kr/campusMap/chosun/'+str(bid)+'/detailView.do'
   ob['confidence']='Exterior photo individually inspected; dimensions, hidden elevations and facade placement approximate.'
 return True
