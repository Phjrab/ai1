"""Original parametric architectural interpretation of Chosun University Main Building.
Metric, front = -Y, ground floor threshold Z=.15; reference photos, not survey/BIM.
Run blender -b --python build_building.py. No third-party meshes/textures used.
"""
import bpy, bmesh, math, os, json, random
from mathutils import Vector
OUT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for d in list(bpy.data.collections):
 if d.name!='Collection': bpy.data.collections.remove(d)
root=bpy.data.collections.get('Collection');root.name='CHOSUN | Building — original reconstruction'
root['provenance']='Original geometry from public reference photographs; dimensions approximate except documented 375m overall length and 19 front gables.'
def col(n):
 c=bpy.data.collections.new(n);root.children.link(c);return c
ext=col('01 EXTERIOR | photo-based proportions')
roofcol=col('02 ROOFS | pitched forms and simplified services')
inter=col('03 INTERIOR | CONCEPTUAL unsurveyed layouts')
exemplar=col('04 CORRIDOR EXEMPLAR | public photo-based finishes')
detail=col('05 ENTRANCES | photographed architectural details')

def mat(n,c,rough=.5,metal=0,trans=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;p.inputs['Transmission Weight'].default_value=trans
 return m
white=mat('Warm white painted masonry',(0.81,.815,.78),.73)
trim=mat('White projecting cornices and frames',(.91,.92,.88),.39)
stone=mat('Granite plinth | fine grey',(.32,.345,.34),.68)
glass=mat('Smoky blue green glazing',(.17,.27,.30),.18,.28,.32)
roof=mat('Pale grey standing seam roof',(.39,.46,.49),.43,.35)
flat=mat('Green waterproofing',(.16,.29,.22),.75)
metal=mat('Brushed aluminum',(.51,.55,.55),.29,.7)
dark=mat('Deep window recess',(.058,.067,.064),.8)
brick=mat('Rear lower storey | dark red-brown brick',(.19,.085,.056),.82)
serviceblue=mat('Rear service doors | pale blue paint',(.32,.59,.65),.57)
nt=brick.node_tree;geo=nt.nodes.new('ShaderNodeNewGeometry');sep=nt.nodes.new('ShaderNodeSeparateXYZ');comb=nt.nodes.new('ShaderNodeCombineXYZ');nt.links.new(geo.outputs['Position'],sep.inputs[0]);nt.links.new(sep.outputs['X'],comb.inputs['X']);nt.links.new(sep.outputs['Z'],comb.inputs['Y'])
bt=nt.nodes.new('ShaderNodeTexBrick');nt.links.new(comb.outputs[0],bt.inputs['Vector']);bt.inputs['Scale'].default_value=1;bt.inputs['Brick Width'].default_value=.26;bt.inputs['Row Height'].default_value=.095;bt.inputs['Mortar Size'].default_value=.007;bt.inputs['Mortar Smooth'].default_value=.003;bt.inputs['Color1'].default_value=(.26,.073,.036,1);bt.inputs['Color2'].default_value=(.045,.035,.029,1);bt.inputs['Mortar'].default_value=(.28,.25,.21,1);nt.links.new(bt.outputs['Color'],nt.nodes.get('Principled BSDF').inputs['Base Color']);bu=nt.nodes.new('ShaderNodeBump');bu.inputs['Strength'].default_value=.23;bu.inputs['Distance'].default_value=.017;nt.links.new(bt.outputs['Fac'],bu.inputs['Height']);nt.links.new(bu.outputs[0],nt.nodes.get('Principled BSDF').inputs['Normal'])
wood=mat('Corridor varnished warm wood',(.29,.105,.046),.4)
low=mat('Corridor grey lower paint',(.33,.40,.41),.7)
floor=mat('Terrazzo light aggregate',(.43,.445,.41),.53)
cream=mat('Interior cream plaster',(.78,.77,.70),.83)
light=mat('Warm frosted fluorescent diffusers',(.86,.90,.85),.4)
p=light.node_tree.nodes.get('Principled BSDF');p.inputs['Emission Color'].default_value=(.8,.87,.76,1);p.inputs['Emission Strength'].default_value=.3
# Fine procedural surface roughness; native nodes, no external textures.
for m,scale,strength in [(white,42,.06),(stone,12,.18),(floor,18,.14)]:
 nt=m.node_tree;no=nt.nodes.new('ShaderNodeTexNoise');no.inputs['Scale'].default_value=scale;no.inputs['Detail'].default_value=2.1;bu=nt.nodes.new('ShaderNodeBump');bu.inputs['Strength'].default_value=strength;bu.inputs['Distance'].default_value=.035;nt.links.new(no.outputs['Fac'],bu.inputs['Height']);nt.links.new(bu.outputs['Normal'],nt.nodes.get('Principled BSDF').inputs['Normal'])
class Batch:
 def __init__(self,n,c):self.n=n;self.c=c;self.v=[];self.f=[];self.mi=[];self.mats=[]
 def geom(self,verts,faces,m):
  k=len(self.v);self.v.extend(verts);self.f.extend([tuple(k+i for i in f) for f in faces]);
  if m not in self.mats:self.mats.append(m)
  self.mi.extend([self.mats.index(m)]*len(faces))
 def box(self,x,y,z,sx,sy,sz,m):
  if min(sx,sy,sz)<=0:return
  self.geom([(x+i*sx/2,y+j*sy/2,z+k*sz/2) for i,j,k in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]],[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],m)
 def beam(self,a,b,w,d,m):
  a,b=Vector(a),Vector(b);v=b-a;u=v.normalized();r=u.cross(Vector((0,1,0))).normalized()*w/2;s=Vector((0,1,0))*d/2
  vs=[tuple(p+rr*r+ss*s) for p in (a,b) for rr,ss in [(-1,-1),(1,-1),(1,1),(-1,1)]];self.geom(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],m)
 def finish(self):
  me=bpy.data.meshes.new(self.n);me.from_pydata(self.v,[],self.f);me.materials.clear()
  for m in self.mats:me.materials.append(m)
  for p,i in zip(me.polygons,self.mi):p.material_index=i
  me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update();o=bpy.data.objects.new(self.n,me);self.c.objects.link(o);return o

def window(b,x,y,z,w=1.04,h=2.2,back=False):
 # z at bottom; actual wall voids are assembled separately.
 s=1 if back else -1
 b.box(x,y+s*.04,z+h/2,w,.085,h,glass)
 for xx in [x-w/2-.04,x+w/2+.04]:b.box(xx,y+s*.09,z+h/2,.085,.12,h+.13,trim)
 for zz in [z-.04,z+h+.04]:b.box(x,y+s*.09,zz,w+.17,.12,.085,trim)
 b.box(x,y+s*.11,z+h/2,.045,.12,h,metal)
 for q in [1/3,2/3]:b.box(x,y+s*.115,z+h*q,w,.11,.043,metal)
 b.box(x,y+s*.23,z-.065,w+.14,.20,.075,trim)
 b.box(x,y-s*.17,z+h+.1,w+.2,.08,.12,dark)

def arch(b,x,y,z,w,h):
 # Pointed Gothic opening silhouette and slim frame, grounded in front photos.
 pts=[(x-w/2,z),(x+w/2,z),(x+w/2,z+h*.58),(x+w*.35,z+h*.8),(x,z+h),(x-w*.35,z+h*.8),(x-w/2,z+h*.58)]
 b.geom([(a,y-.045,c) for a,c in pts],[tuple(range(7))],glass)
 for i in range(len(pts)):
  a,c=pts[i];aa,cc=pts[(i+1)%len(pts)];b.beam((a,y-.11,c),(aa,y-.11,cc),.085,.14,trim)
 b.box(x,y-.15,z+h*.40,.042,.1,h*.8,metal);b.box(x,y-.15,z+h*.48,w,.1,.045,metal);b.box(x,y-.13,z-.065,w+.14,.18,.075,trim)

# 19-gable bar. Widths calibrated to 375m overall including round end annexes.
# Large outer peaks are higher than historical six-storey center, as photographed.
types=['M','L','M']+['S']*5+['M','C','M']+['S']*5+['M','L','M']
widths={'S':14.6,'M':17,'L':28,'C':28}
floors={'S':3,'M':4,'L':6,'C':5}; rises={'S':6.2,'M':7.0,'L':10.6,'C':10.0}
DEPTH=17.;FH=3.6;TOTAL=sum(widths[t] for t in types);left=-TOTAL/2;bayinfo=[]
for idx,t in enumerate(types):
 w=widths[t];cx=left+w/2;nf=floors[t];eave=nf*FH+.15;peak=eave+rises[t];n=6 if t=='S' else 7 if t=='M' else 11
 b=Batch(f'{idx+1:02d} | {t} gable | walls and fenestration',ext)
 fb=Batch(f'{idx+1:02d} | conceptual floor plates and rooms',inter)
 pitch=w/n;winw=1.00 if t=='S' else 1.04;winh=2.23
 for side,y in [('front',0),('rear',DEPTH)]:
  for f in range(nf):
   base=f*FH+.15;bot=base+.72;top=bot+winh
   if f==0 and side=='rear':
    # Source-backed rear service elevation: dark red/brown brick, pale blue doors,
    # dark-framed windows, and a white projecting slab at the first-floor line.
    holes=[]
    for k in range(n):
     xx=left+(k+.5)*pitch;isservice=k in [1,n-2]
     zlo=.15 if isservice else bot;zhi=2.95 if isservice else top
     holes.append((xx-winw/2,xx+winw/2,zlo,zhi))
     if isservice:
      b.box(xx,DEPTH+.245,(zlo+zhi)/2,winw,.065,zhi-zlo,serviceblue)
      for dx in [-winw/2-.04,winw/2+.04]:b.box(xx+dx,DEPTH+.275,(zlo+zhi)/2,.065,.08,zhi-zlo+.1,dark)
      b.box(xx,DEPTH+.275,zhi+.025,winw+.14,.08,.075,dark)
      b.box(xx+winw*.33,DEPTH+.315,1.21,.09,.08,.035,metal)
     else:
      b.box(xx,DEPTH+.24,(zlo+zhi)/2,winw,.06,zhi-zlo,glass)
      for dx in [-winw/2-.025,0,winw/2+.025]:b.box(xx+dx,DEPTH+.275,(zlo+zhi)/2,.045,.07,zhi-zlo+.08,dark)
      for zz in [zlo-.025,(zlo+zhi)/2,zhi+.025]:b.box(xx,DEPTH+.275,zz,winw+.1,.07,.05,dark)
      b.box(xx,DEPTH+.275,zlo-.08,winw+.15,.20,.075,stone)
    holes.sort();prev=left
    for lo,hi,zlo,zhi in holes:
     b.box((prev+lo)/2,y,base+FH/2,lo-prev,.45,FH,brick)
     b.box((lo+hi)/2,y,(base+zlo)/2,hi-lo,.45,zlo-base,brick)
     b.box((lo+hi)/2,y,(zhi+base+FH)/2,hi-lo,.45,base+FH-zhi,brick)
     prev=hi
    b.box((prev+left+w)/2,y,base+FH/2,left+w-prev,.45,FH,brick)
    b.box(cx,DEPTH+.14,3.65,w,.8,.28,white)
    continue
   if f==0 and t in ['L','C'] and side=='front':
    holes=[(cx-2.45,cx+2.45,.15,3.05)]
    for k in range(n):
     xx=left+(k+.5)*pitch
     if abs(xx-cx)>3.5:
      holes.append((xx-winw/2,xx+winw/2,bot,top));window(b,xx,y,bot,winw,winh)
    holes.sort();prev=left
    for lo,hi,zlo,zhi in holes:
     b.box((prev+lo)/2,y,base+FH/2,lo-prev,.45,FH,white)
     b.box((lo+hi)/2,y,(base+zlo)/2,hi-lo,.45,zlo-base,white)
     b.box((lo+hi)/2,y,(zhi+base+FH)/2,hi-lo,.45,base+FH-zhi,white)
     prev=hi
    b.box((prev+left+w)/2,y,base+FH/2,left+w-prev,.45,FH,white)
    continue
   b.box(cx,y,base+.36,w,.45,.72,white);b.box(cx,y,(top+base+FH)/2,w,.45,base+FH-top,white)
   for k in range(n):
    xx=left+(k+.5)*pitch
    # Entrance doors replace low windows under the 3 major gables.
    isdoor=(f==0 and t in ['L','C'] and abs(xx-cx)<2.2 and side=='front')
    if isdoor:
     b.box(xx,y,1.5,winw,.10,2.7,glass);b.box(xx-winw/2,y-.1,1.5,.09,.14,2.7,metal);b.box(xx+winw/2,y-.1,1.5,.09,.14,2.7,metal)
    else:window(b,xx,y,bot,winw,winh,side=='rear')
    if k==0:b.box(left+(pitch-winw)/4,y,(bot+top)/2,(pitch-winw)/2,.45,winh,white)
    if k<n-1:b.box(xx+pitch/2,y,(bot+top)/2,pitch-winw,.45,winh,white)
    else:b.box(left+w-(pitch-winw)/4,y,(bot+top)/2,(pitch-winw)/2,.45,winh,white)
  # Gable face true thin wall, NOT filled building volume. Upper glazing surface inset.
  b.geom([(left,y-.22,eave),(left+w,y-.22,eave),(cx,y-.22,peak),(left,y+.22,eave),(left+w,y+.22,eave),(cx,y+.22,peak)],[(0,1,2),(5,4,3),(0,3,4,1),(1,4,5,2),(2,5,3,0)],white)
  # Pointed windows array follows triangular gable silhouette.
  if t in ['L','C']:
   for k in range(8):window(b,cx+(k-3.5)*1.8,y-.30 if side=='front' else y+.30,eave+.75,.90,1.88,side=='rear')
   for k in range(4):arch(b,cx+(k-1.5)*1.30,y-.25 if side=='front' else y+.32,eave+3.9+(.8 if k in [1,2] else 0),.81,1.65)
  else:
   for k in range(4):
    xx=cx+(k-1.5)*1.5
    arch(b,xx,y-.25 if side=='front' else y+.32,eave+.85,.85,2.2-abs(k-1.5)*.27)
  # Double white eaves following roof edge.
  yy=y-.38 if side=='front' else y+.38
  for dz,bw in [(0,.35),(-.42,.15)]:
   b.beam((left-.30,yy,eave+dz),(cx,yy,peak+dz),bw,.45,trim);b.beam((cx,yy,peak+dz),(left+w+.30,yy,eave+dz),bw,.45,trim)
  b.box(cx,yy,eave-.2,w+.45,.52,.24,trim)
  # Slender continuous pilasters articulate gable edges.
  for xx in [left+.10,left+w-.10]:
   if side=='rear':b.box(xx,y+.10,(eave+3.8)/2,.30,.34,eave-3.8,trim)
   else:b.box(xx,y-.10,eave/2,.30,.34,eave,trim)
  if t in ['L','C'] and side=='front':
   for ss in [-1,1]:b.box(cx+ss*(w/4+1.225),y-.05,.30,w/2-2.45,.57,.60,stone)
  else:b.box(cx,y-.05,.30,w,.57,.60,stone)
 # Close the exposed vertical cheeks between unequal gables; these are real thin walls.
 for ss,other in [(-1,idx-1),(1,idx+1)]:
  if 0<=other<len(types):
   lowh=floors[types[other]]*FH+.15
   if eave>lowh:
    xx=cx+ss*w/2
    b.box(xx,DEPTH/2,(lowh+eave)/2,.4,DEPTH,eave-lowh,white)
    for lev in range(floors[types[other]],nf):
     for yy in [3,6.6,10.2,13.8]:
      zz=lev*FH+1.98
      b.box(xx+ss*.24,yy,zz,.06,1.08,2.15,glass)
      for dy in [-.59,.59]:b.box(xx+ss*.28,yy+dy,zz,.10,.08,2.3,trim)
      for dz in [-1.12,1.12]:b.box(xx+ss*.28,yy,zz+dz,.10,1.25,.08,trim)
      b.box(xx+ss*.31,yy,zz,.1,.045,2.15,metal)
 # Solid end walls have modest return fenestration only at terminal bays.
 if idx in [0,18]:
  x=left if idx==0 else left+w
  b.box(x,DEPTH/2,eave/2,.45,DEPTH,eave,white)
 # Actual floor slabs and inferred corridor/room partitions, always independently toggleable.
 for f in range(nf):
  z=f*FH+.15;fb.box(cx,DEPTH/2,z-.10,w,.0+DEPTH,.20,floor)
  if f<nf-1:fb.box(cx,DEPTH/2,z+FH-.19,w,DEPTH,.09,cream)
  # External gallery corridor + undimensioned classroom zone.
  fb.box(cx,4.0,z+1.72,w,.16,3.35,cream)
  for k in range(1,3):fb.box(left+w*k/3,10.5,z+1.72,.14,12.7,3.35,cream)
 b.finish();o=fb.finish();o['accuracy']='Conceptual internal organization. NOT a surveyed floor plan.'
 rb=Batch(f'{idx+1:02d} | pitched roof and seams',roofcol)
 for xa,xb,za,zb in [(left-.30,cx,eave+.15,peak+.15),(cx,left+w+.30,peak+.15,eave+.15)]:
  rb.geom([(xa,-.28,za),(xb,-.28,zb),(xb,DEPTH+.28,zb),(xa,DEPTH+.28,za)],[(0,1,2,3)],roof)
  for j in range(24):
   yy=-.22+j*(DEPTH+.44)/23;rb.beam((xa,yy,za+.045),(xb,yy,zb+.045),.035,.045,metal)
 rb.beam((cx,-.4,peak+.25),(cx,DEPTH+.4,peak+.25),.15,.16,trim) if False else None
 rb.box(cx,DEPTH/2,peak+.24,.16,DEPTH+.7,.14,trim);rb.finish()
 bayinfo.append({'index':idx+1,'type':t,'x':cx,'width':w,'full_rectangular_tiers':nf,'eave':eave,'peak':peak});left+=w

# Rounded five-level end pavilions, 375m total outermost dimension.
annexradius=9.5;annexc=187.5-annexradius
for sign in [-1,1]:
 ax=sign*annexc;ay=8.5;ab=Batch(('WEST' if sign<0 else 'EAST')+' | rounded annex',ext);N=32;h=18.2
 for f in range(5):
  z=f*3.6+.15
  # radial curtain wall modules with white columns / horizontal slab bands
  for j in range(N):
   a=2*math.pi*j/N;aa=2*math.pi*(j+1)/N;r=annexradius
   vs=[(ax+r*math.cos(q),ay+r*math.sin(q),zz) for zz in [z+.52,z+3.2] for q in [a,aa]]
   ab.geom(vs,[(0,1,3,2)],glass)
   for zz,hh in [(z+.25,.5),(z+3.45,.3)]:
    ab.geom([(ax+rr*math.cos(q),ay+rr*math.sin(q),zzz) for zzz in [zz-hh/2,zz+hh/2] for rr,q in [(r-.3,a),(r+.1,a),(r+.1,aa),(r-.3,aa)]],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],white)
   px=ax+(r+.1)*math.cos(a);py=ay+(r+.1)*math.sin(a);ab.box(px,py,z+1.8,.22,.22,3.6,trim)
   am=(a+aa)/2;px=ax+r*math.cos(am);py=ay+r*math.sin(am);ab.box(px,py,z+1.85,.065,.065,2.7,metal)
  # rings and floor discs
  verts=[(ax,ay,z)]+[(ax+(r-.25)*math.cos(2*math.pi*j/N),ay+(r-.25)*math.sin(2*math.pi*j/N),z) for j in range(N)]
  ab.geom(verts,[(0,j+1,(j+1)%N+1) for j in range(N)],floor)
 for j in range(N):
  a=2*math.pi*j/N;aa=2*math.pi*(j+1)/N
  ab.geom([(ax+annexradius*math.cos(q),ay+annexradius*math.sin(q),zz) for zz in [18.05,18.55] for q in [a,aa]],[(0,1,3,2)],trim)
 ab.geom([(ax,ay,18.15)]+[(ax+9.3*math.cos(2*math.pi*j/N),ay+9.3*math.sin(2*math.pi*j/N),18.15) for j in range(N)],[(0,j+1,(j+1)%N+1) for j in range(N)],flat)
 # open connector between the historic bar and annex
 ab.box(sign*(TOTAL/2+2.3),8.5,8.9,4.6,12,17.8,white)
 for f in range(5):
  for k in [-1,0,1]:window(ab,sign*(TOTAL/2+2.3)+k*1.3,2.4,f*3.6+.85,.86,2.1)
 ab.finish()

# Three photographed flat canopies, two columns, granite plinths, entry glazing.
for info in bayinfo:
 if info['type'] not in ['C','L']:continue
 x=info['x'];cb=Batch(('MAIN' if info['type']=='C' else 'WING')+' | canopy entrance',detail)
 cb.box(x,-2.0,3.65,7.2,4.9,.37,white);cb.box(x,-4.45,3.85,7.45,.25,.35,trim)
 for dx in [-2.9,2.9]:
  cb.box(x+dx,-3.95,1.8,.4,.4,3.6,white);cb.box(x+dx,-3.95,.5,.53,.53,1.0,stone)
 for j in range(4):cb.box(x,-2.4-j*.48,-.01-j*.075,7.3+j*.12,4.8+j*.95,.16,stone)
 # Open central paired doors; fixed side lights leave real walk-through opening.
 for dx in [-1.8,1.8]:cb.box(x+dx,-.3,1.55,1.25,.15,3.,glass)
 cb.box(x,-.3,2.88,2.4,.15,.36,glass)
 for dx in [-2.45,-1.2,1.2,2.45]:cb.box(x+dx,-.41,1.55,.075,.12,3.1,metal)
 cb.box(x,-.41,2.7,5.,.12,.065,metal)
 for dx in [-1.26,1.26]:cb.box(x+dx,-.52,1.25,.035,.08,.45,metal)
 # understated flag staffs visible in source, no invented branding.
 for dx in [-1.2,0,1.2]:cb.box(x+dx,-2.1,5.35,.045,.045,3.1,metal)
 cb.finish()

# Photo-supported corridor finishes, section at rear of central bay to avoid obscuring exterior.
# A separate exemplar, clearly labeled: spatial location and dimensions are illustrative.
cb=Batch('CORRIDOR EXEMPLAR | grey dado, terrazzo, wood frames',exemplar)
xc=0; start=-12;end=12;y=4.0
# facade-side corridor itself spans y=.4..3.9 in inferred ground floor
cb.box(0,3.89,.82,24,.035,1.35,low)
for j in range(8):
 x=start+1.5+j*3
 # wood transom and glazed partition/door assemblages on classroom side
 cb.box(x,3.78,1.55,1.38,.075,2.85,wood);cb.box(x,3.71,1.64,1.19,.03,2.30,glass)
 for dx in [-.64,.64]:cb.box(x+dx,3.66,1.57,.075,.09,2.85,wood)
 for zz in [.45,1.25,2.7]:cb.box(x,3.65,zz,1.34,.10,.095,wood)
 cb.box(x+.47,3.59,1.16,.035,.07,.16,metal)
 # suspended rectangular diffuse fixtures along corridor
 cb.box(x,2.1,3.34,1.2,.3,.075,light)
# photo-inspired coffer strips and skirting
for j in range(33):cb.box(-12+j*.75,2.1,3.40,.055,3.25,.11,cream)
cb.box(0,3.71,.18,24,.09,.12,wood);cb.finish()
exemplar['accuracy']='Finishes supported by public corridor photograph. Location, dimensions, partition positions are illustrative; no verified floor plan.'

# Simplified gutters, roof access and satellite/service equipment on annex roofs.
sb=Batch('Roof drainage and simplified service details',roofcol)
for info in bayinfo:
 x=info['x']+info['width']/2-.25;h=info['eave'];sb.box(x,.0,h/2,.09,.12,h,metal)
for sign in [-1,1]:
 ax=sign*annexc
 for j in range(3):sb.box(ax-2+j*1.5,11,18.62,1.,1.25,.85,stone);sb.box(ax-2+j*1.5,11,19.08,1.04,1.3,.08,metal)
sb.finish()
# Model metadata and saved view.
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['model_title']='Chosun University Main Building | 조선대학교 본관'
scene['accuracy_notice']='Photo-based architectural interpretation. Not a measured survey or verified BIM. Internal layouts conceptual; one corridor finish exemplar derived from public photo.'
scene['documented_features']='375m total length; 19 front gables; central historical core lower than outer tall gables; rounded end pavilions.'
scene['sources']='https://www3.chosun.ac.kr/fund/2217/subview.do | https://dh.aks.ac.kr/~gwangju/wiki/index.php/제작기록:3d-광주조선대학교본관'
scene.world.color=(.25,.25,.25)
# Useful viewport framing.
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':
  area.spaces.active.clip_end=2000;area.spaces.active.region_3d.view_distance=300;area.spaces.active.region_3d.view_location=(0,0,9)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'chosun_main_building.blend'))
stats={'objects':len(bpy.data.objects),'vertices':sum(len(o.data.vertices) for o in bpy.data.objects if o.type=='MESH'),'polygons':sum(len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'),'bar_width':TOTAL,'overall_width':375,'depth':DEPTH,'front_y':0,'ground_z':0,'bays':bayinfo}
with open(os.path.join(OUT,'building_contract.json'),'w') as f:json.dump(stats,f,indent=2)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'chosun_main_building.glb'),export_format='GLB',export_materials='EXPORT',export_extras=True)
print('BUILDING_COMPLETE',json.dumps(stats))
