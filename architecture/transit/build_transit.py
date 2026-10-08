"""Original geometry based on inspected official campus photographs. Blender 3.4+.
Axes: +Y forward, Z up, meters. Tire contact Z=0. Photo-informed 2025 livery reconstruction; right side inferred and fleet-wide identity unverified.
"""
import bpy, math, json, os
from mathutils import Vector
P=os.path.dirname(__file__)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
 if c.name!='Collection' and c.users==0:bpy.data.collections.remove(c)
def material(n,c,metal=0,rough=.5):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True
 b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*c,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
 return m
white=material('Coach pearl ivory',(.88,.90,.86),.15,.32);blue=material('Campus blue',(.025,.12,.32),.2,.3);glass=material('Dark cool glass',(.035,.075,.09),.5,.16);black=material('Rubber charcoal',(.019,.021,.024),0,.75);silver=material('Brushed aluminium',(.43,.49,.5),.8,.3);lamp=material('Headlamp ivory',(.95,.94,.74),.2,.2);red=material('Red tail lamps',(.7,.015,.015),.2,.25);amber=material('Amber indicators',(.97,.43,.04),.1,.25);roof=material('Green translucent canopy simplified opaque',(.12,.52,.44),.15,.3);salmon=material('Salmon shelter columns',(.7,.29,.2));seat=material('Green moulded seating',(.075,.32,.09),.2,.29);yellow=material('Yellow circular BUS sign',(.96,.57,.045),.1,.3);pave=material('Concrete plinth',(.48,.49,.46));paper=material('Timetable paper',(.92,.91,.85))
font_candidates=[os.environ.get('CHOSUN_CJK_FONT',''),'/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc','/System/Library/Fonts/AppleSDGothicNeo.ttc','C:/Windows/Fonts/malgunbd.ttf']
font=next((bpy.data.fonts.load(f) for f in font_candidates if f and os.path.isfile(f)),None)
if font is None:print('WARNING: No CJK font found. Set CHOSUN_CJK_FONT for Korean lettering. Default Blender font fallback may omit Korean glyphs.')
active=None

def parent(n):
 o=bpy.data.objects.new(n,None);bpy.context.collection.objects.link(o);return o

def finish(o,n,ma,par=None):
 o.name=n
 if ma:o.data.materials.append(ma)
 o.parent=par if par else active
 return o

def box(n,loc,dim,ma,par=None,bevel=0):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);finish(o,n,ma,par)
 if bevel:
  m=o.modifiers.new('Soft manufactured edges','BEVEL');m.width=bevel;m.segments=2
  bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=m.name)
 return o

def cyl(n,loc,r,depth,ma,rot=(0,0,0),par=None,verts=24):
 bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc,rotation=rot);return finish(bpy.context.object,n,ma,par)

def beam(n,a,b,r,ma,par=None):
 o=cyl(n,(Vector(a)+Vector(b))/2,r,(Vector(b)-Vector(a)).length,ma,par=par,verts=10);o.rotation_euler=(Vector(b)-Vector(a)).to_track_quat('Z','Y').to_euler();return o

def text(n,s,loc,size,ma,rot=(math.pi/2,0,0),par=None):
 cu=bpy.data.curves.new(n,'FONT');cu.body=s;
 if font:cu.font=font
 cu.size=size*1.7;cu.align_x='CENTER';cu.align_y='CENTER';cu.extrude=.002;cu.resolution_u=1;o=bpy.data.objects.new(n,cu);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=rot;finish(o,n,ma,par);bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.convert(target='MESH');o.select_set(False);return o

def export(root,file):
 # Batch static parts by material and immediate parent; preserve each wheel pivot.
 groups={}
 for o in list(root.children_recursive):
  if o.type=='MESH':groups.setdefault((o.parent.name,o.active_material.name if o.active_material else ''),[]).append(o)
 for (pn,mn),obs in groups.items():
  if len(obs)<2:continue
  bpy.ops.object.select_all(action='DESELECT')
  for o in obs:o.select_set(True)
  bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();obs[0].name=pn+'__'+mn
 bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
 for o in root.children_recursive:o.select_set(True)
 bpy.ops.export_scene.gltf(filepath=P+'/'+file,export_format='GLB',use_selection=True,export_yup=True,export_extras=True)

bus=parent('CHOSUN_SHUTTLE');active=bus
bus['source']='2025-10-15 Minju Chosun magazine p77 front/left photo; 2026-05-11 Chodae Newspaper p6 rear livery corroboration. Photo-informed stylized geometry, dimensions inferred; right side mirrored inference, exact model and fleet-wide identity unverified.'
bus['livery_reference_date']='2025-10-15'
busblue=material('Verified shuttle cobalt blue',(.045,.12,.43),.15,.32)
pale_blue=material('Livery pale cyan stars',(.11,.28,.59),.05,.45)
wordblue=material('Shuttle navy lettering',(.018,.035,.12),0,.48)
bus['forward_axis']='Blender +Y / glTF -Z';bus['length_m']=10.7;bus['width_m']=2.5;bus['height_m']=3.32
box('Chassis',(0,0,.69),(2.10,10.15,.37),black)
box('Coach body lower',(0,0,1.15),(2.37,10.45,.8),white,bevel=.12)
box('Coach cabin core',(0,-.08,2.21),(2.35,10.4,1.47),white,bevel=.13)
box('Swept white roof',(0,-.06,3.09),(2.42,10.36,.31),white,bevel=.13)
box('Roof air conditioning',(0,-.65,3.3),(1.50,2.70,.22),white,bevel=.07)
for side in [-1,1]:
 x=side*1.188
 box('Continuous black glazing band',(side*1.181,-.1,2.34),(.018,10.13,1.15),black)
 # individual glazed panes; geometric mullions remain visible
 for i in range(7):
  y=-4.55+i*1.29
  box('Side window %s %s'%(side,i),(x,y,2.34),(.035,1.19,1.03),glass,bevel=.025)
  box('Window lower extrusion',(x,y,1.81),(.055,1.24,.045),silver)
 # Blue swept livery follows the observed LEFT side; opposite side mirrored as an explicitly marked inference.
 for y in [-3.3,-1.25,.8]:
  box('Luggage hatch',(side*1.194,y,1.23),(.016,1.93,.61),white)
  box('Luggage seam',(side*1.205,y-1.0,1.23),(.018,.018,.64),silver)
  box('Luggage handle',(side*1.21,y,1.49),(.023,.22,.025),black)
 # black wheel arch surrounds and independent tire pivots
 for axle,y in [('front',3.24),('rear',-3.16)]:
  cyl('Wheel arch '+axle+str(side),(side*1.208,y,.60),.57,.035,black,(0,math.pi/2,0))
  steering=parent('steer_'+axle+('_L' if side<0 else '_R'));steering.parent=bus;steering.location=(side*1.205,y,.51)
  wheel=parent('wheel_'+axle+('_L' if side<0 else '_R'));wheel.parent=steering
  cyl('Tire '+axle+str(side),(0,0,0),.51,.25,black,(0,math.pi/2,0),wheel,32)
  cyl('Rim '+axle+str(side),(side*.138,0,0),.305,.028,silver,(0,math.pi/2,0),wheel,24)
  cyl('Hub '+axle+str(side),(side*.16,0,0),.115,.055,silver,(0,math.pi/2,0),wheel,20)
  for a in range(8):
   t=a*math.tau/8;cyl('Rim recess',(side*.16,.222*math.cos(t),.222*math.sin(t)),.036,.009,black,(0,math.pi/2,0),wheel,8)
 # geometry text on both bus sides, normals pointing outward
 # Side livery and readable geometric lettering are added after service hatches below.
 # marker lamps
 for y in [-4.8,0,4.8]:box('Side amber marker',(side*1.22,y,.92),(.025,.13,.075),amber)
# Coach front +Y
box('Panoramic windscreen',(0,5.235,2.34),(2.18,.035,1.3),glass,bevel=.06)
box('Windshield centre mullion',(0,5.259,2.34),(.035,.023,1.28),black)
# Reference has continuous dark windscreen rather than a fabricated destination display.
text('Front campus wordmark','조선대학교',(-.13,5.30,1.44),.19,wordblue,(math.pi/2,0,math.pi))
text('Front small English','CHOSUN UNIVERSITY',(-.13,5.301,1.30),.076,wordblue,(math.pi/2,0,math.pi))
box('Front blue emblem tile',(.55,5.302,1.40),(.16,.014,.25),busblue)
for zz in [1.34,1.40,1.46]:
 for xx in [.515,.555,.595]:box('Emblem light cells',(xx,5.314,zz),(.021,.008,.034),white)
for x in [-.91,.91]:
 box('Tall swept front lamp housing',(x,5.244,1.02),(.32,.067,.62),silver,bevel=.07)
 for zz in [.84,1.04,1.23]:box('Stacked clear headlamp',(x,5.286,zz),(.225,.018,.12),lamp,bevel=.025)
 box('Vertical amber front indicator',(x+math.copysign(.145,x),5.285,1.06),(.048,.02,.46),amber)
 beam('Windshield wiper',(x*.8,5.272,1.83),(x*.56,5.275,2.16),.012,black)
 beam('Mirror horizontal arm',(x,4.93,2.94),(math.copysign(1.54,x),4.93,2.94),.035,black)
 beam('Mirror down arm',(math.copysign(1.54,x),4.93,2.94),(math.copysign(1.54,x),4.93,2.53),.032,black)
 box('Black rear view mirror',(math.copysign(1.54,x),4.90,2.49),(.18,.24,.4),black,bevel=.05)
 box('Mirror reflective face',(math.copysign(1.54,x),4.765,2.49),(.13,.012,.30),silver)
box('Front blue bumper',(0,5.27,.68),(2.32,.12,.32),busblue,bevel=.045)
box('Blank white number plate',(0,5.347,.72),(.47,.01,.16),white)
box('Front silver trim',(0,5.277,1.15),(1.03,.02,.046),silver)
# Passenger folding door is right-hand side when facing forward (Blender +X).
for y in [3.99,4.48]:
 box('Passenger door frame',(1.222,y,1.64),(.05,.46,2.08),black)
 box('Passenger door glazing',(1.252,y,2.05),(.012,.37,1.12),glass)
 box('Passenger door lower',(1.255,y,1.12),(.012,.38,.63),white)
for z in [.42,.55,.68]:box('Entry stair',(1.26,4.22,z),(.17,.91,.04),silver)
box('Rear window',(0,-5.29,2.43),(1.99,.04,.94),glass,bevel=.04)
for x in [-.94,.94]:
 box('Rear tail lamp',(x,-5.305,1.26),(.20,.04,.36),red,bevel=.025)
 box('Rear indicator',(x,-5.33,1.5),(.19,.016,.08),amber)
box('Rear cobalt panel',(0,-5.312,1.12),(2.32,.019,1.17),busblue)
text('Rear university','CHOSUN UNIVERSITY',(0,-5.339,1.29),.20,white)
box('Rear blank white number plate',(0,-5.34,.97),(.47,.011,.16),white)
# Original geometric reconstruction of visible 2025 livery; no photo texture is embedded.
def side_poly(name,side,coords,ma,xoff=1.224):
 me=bpy.data.meshes.new(name);vs=[(side*xoff,y,z) for y,z in coords];me.from_pydata(vs,[],[tuple(range(len(vs)))]);me.update()
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);finish(ob,name,ma);return ob
for side in [-1,1]:
 rot=(math.pi/2,0,side*math.pi/2)
 # Direction along +Y is front. Rising blue sweep terminates beneath rear-side glazing.
 curve=[(5.13,1.03),(4.0,.89),(3.4,.84),(2.6,.91),(1.7,.98),(.8,.84),(0,.92),(-.65,1.08),(-1.2,1.20),(-1.7,1.58),(-2.03,1.80),(-5.12,1.80)]
 side_poly('Cobalt rising wave '+str(side),side,[(-5.12,.64),(5.13,.64)]+curve,busblue)
 # continuous rear panel to roof; thin white slash across rising blue region
 side_poly('Rear blue corner '+str(side),side,[(-5.15,.76),(-4.93,.76),(-4.93,3.14),(-5.15,3.14)],busblue)
 side_poly('Rear blue roof edge '+str(side),side,[(-5.11,2.96),(-1.9,2.96),(-1.9,3.14),(-5.11,3.14)],busblue)
 side_poly('White swept pinstripe '+str(side),side,[(.1,.73),(-.55,.95),(-1.05,1.25),(-1.50,1.80),(-1.63,1.80),(-1.14,1.22),(-.59,.91)],white,1.229)
 # Outward-facing original text, transcribed from the visible left-side photo.
 text('Regional future slogan '+str(side),'지역과 함께 100년, 학생과 함께 미래로! 조선대학교',(side*1.236,-3.62,1.58),.155,white,rot)
 text('Side English line 1 '+str(side),'100 years with the region,',(side*1.235,.50,1.32),.14,wordblue,rot)
 text('Side English line 2 '+str(side),'To the future with our students',(side*1.235,.50,1.18),.14,wordblue,rot)
 # Main-building roofline emblem. Simplified from observed peaks and window grid.
 # Text local horizontal maps to longitudinal body. Decorative motif occupies center white field.
 for row in range(5):
  for col in range(13):
   yy=.50+(col-6)*.084;zz=1.48+row*.047
   box('Motif navy window',(side*1.231,yy,zz),(.012,.022,.021),wordblue)
 pts=[(-.10,1.74),(.06,1.90),(.24,1.78),(.51,2.04),(.81,1.80),(.97,1.93),(1.15,1.75)]
 for (y1,z1),(y2,z2) in zip(pts,pts[1:]):beam('Motif blue roof',(side*1.234,y1,z1),(side*1.234,y2,z2),.016,busblue)
 # Subtle blue four-point stars on lower back panel.
 for yy,zz in [(-1.5,1.04),(-2.25,1.19),(-2.9,1.0),(-3.75,1.24)]:
  side_poly('Livery four point star',side,[(yy,zz+.12),(yy+.028,zz+.024),(yy+.12,zz),(yy+.027,zz-.024),(yy,zz-.12),(yy-.028,zz-.024),(yy-.12,zz),(yy-.027,zz+.024)],pale_blue,1.230)
 # Rear quarter cooling slots, photographed below slogan.
 for zz in [1.01+i*.06 for i in range(8)]:box('Rear side ventilation',(side*1.238,-4.65,zz),(.013,.52,.025),black)
export(bus,'shuttle_bus.glb')
# Photographed 2021 shelter: salmon columns, blue beams, curved green roof, double-sided green seats.
shelter=parent('CHOSUN_SHELTER_REFERENCE');active=shelter
shelter['source']='Official Chosun 2021 shelter_campaign photograph, Seollip Monument stop. Dimensions inferred; repeat at other stops is representative only.'
box('Paving apron',(0,0,.035),(9.8,3.35,.07),pave)
for x in [-4.4,0,4.4]:
 for y in [-1.23,1.23]:box('Salmon square column',(x,y,1.30),(.26,.26,2.60),salmon)
for y in [-1.28,1.28]:box('Blue longitudinal fascia',(0,y,2.64),(9.70,.15,.24),blue)
# Continuous arched canopy shell as quads, cross ribs traced explicitly.
vs=[];fs=[];N=24
for x in [-4.85,4.85]:
 for i in range(N+1):
  y=-1.55+3.1*i/N;z=2.72+.48*math.sqrt(max(0,1-(y/1.55)**2));vs.append((x,y,z))
for i in range(N):fs.append((i,i+1,N+2+i,N+1+i))
me=bpy.data.meshes.new('Arched canopy mesh');me.from_pydata(vs,[],fs);me.update();ob=bpy.data.objects.new('Continuous green barrel canopy',me);bpy.context.collection.objects.link(ob);finish(ob,ob.name,roof)
for x in [-4.85,-3.3,-1.7,0,1.7,3.3,4.85]:
 for i in range(N):
  a=vs[i];b=vs[i+1];beam('Curved canopy rib',(x,a[1],a[2]+.015),(x,b[1],b[2]+.015),.027,silver)
for y in [-.75,0,.75]:beam('Roof longitudinal tie',(-4.85,y,3.12),(4.85,y,3.12),.026,silver)
# Repeated contoured seat plates and V legs, like photographed seats.
for xc in [-2.2,2.2]:
 for x in [xc-.84,xc-.28,xc+.28,xc+.84]:
  for y in [-.36,.36]:
   box('Individual green seat',(x,y,.52),(.51,.59,.085),seat,bevel=.05)
   box('Raised rear seat lip',(x,y+math.copysign(.25,y),.57),(.48,.07,.045),seat,bevel=.02)
 for x in [xc-.73,xc+.73]:
  beam('V bench leg',(x,-.56,.07),(x,0,.48),.045,black);beam('V bench leg',(x,.56,.07),(x,0,.48),.045,black)
 beam('Seat support rail',(xc-1.1,0,.44),(xc+1.1,0,.44),.05,silver)
export(shelter,'shelter_reference.glb')
# Sign is separately instanced per stop so inferred stops can remain sign-only.
sign=parent('CHOSUN_BUS_STOP_SIGN');active=sign
cyl('Silver sign pole',(0,0,1.64),.045,3.28,silver)
cyl('Thick grey circular sign rim',(0,-.06,2.98),.52,.115,silver,(math.pi/2,0,0),verts=48)
cyl('Circular yellow BUS face',(0,-.124,2.98),.485,.018,yellow,(math.pi/2,0,0),verts=48)
text('BUS label','BUS',(0,-.14,3.14),.40,white)
box('BUS underline',(0,-.143,2.93),(.62,.014,.013),white)
text('Stop name example','설립기념탑',(0,-.144,2.78),.12,black)
text('Stop destination example','사회과학관',(0,-.144,2.62),.095,black)
box('Timetable frame',(0,-.061,1.93),(.46,.10,.73),silver)
box('Timetable white face',(0,-.12,1.93),(.423,.015,.688),paper)
box('Timetable blue heading',(0,-.132,2.22),(.425,.014,.10),blue)
text('Timetable header','교내 순환버스',(0,-.145,2.22),.053,white)
for i in range(10):
 z=2.11-i*.048
 for x in [-.13,0,.13]:box('Indicative timetable line',(x,-.135,z),(.080,.01,.01),blue)
# schedule is intentionally schematic; no invented service times.
# Generic version avoids repeating the photographed stop name at other locations.
generic=parent('CHOSUN_BUS_STOP_GENERIC')
for original in list(sign.children_recursive):
 if original.name in ['Stop name example','Stop destination example']:continue
 copy=original.copy();copy.data=original.data.copy();bpy.context.collection.objects.link(copy);copy.parent=generic
active=generic
text('Generic circulation label','교내 순환버스',(0,-.144,2.78),.11,black)
export(generic,'bus_stop_generic.glb')
generic.hide_render=True
for o in generic.children_recursive:o.hide_render=True
export(sign,'bus_stop_sign.glb')
# Second photographed typology: 2021 College of Education flat roof / orange rear portal.
edu=parent('CHOSUN_EDUCATION_SHELTER');active=edu
edu['source']='Official College of Education exterior photo 2021-03-08; dimensions inferred from image.'
orange=material('Education shelter orange portal',(.95,.19,.015),.05,.4)
wood=material('Wooden bench slats',(.34,.20,.095),0,.65)
box('Education paving',(0,0,.04),(4.95,2.8,.08),pave)
for x in [-1.4,0]:box('Tall orange portal upright',(x,.88,1.9),(.23,.26,3.8),orange)
box('Tall orange portal lintel',(-.7,.88,3.8),(1.63,.26,.23),orange)
box('Education flat blue canopy',(0,0,2.78),(4.95,2.72,.19),blue)
box('Education canopy light soffit',(0,0,2.67),(4.78,2.53,.035),silver)
for x in [-2.12,2.12]:
 for y in [-1.1,1.1]:cyl('Slim grey canopy support',(x,y,1.35),.045,2.70,silver,verts=12)
for x in [-1.0,1.0]:
 for y in [-.32,-.12,.08,.28]:box('Wood bench seat slat',(x,y,.48),(1.78,.14,.055),wood,bevel=.008)
 for z in [.76,.96]:box('Wood bench back slat',(x,.42,z),(1.78,.06,.15),wood,bevel=.01)
 for dx in [-.65,.65]:
  beam('Bench steel leg',(x+dx,-.25,.06),(x+dx,-.25,.48),.035,silver)
  beam('Bench back frame',(x+dx,.38,.06),(x+dx,.38,1.07),.035,silver)
export(edu,'shelter_education.glb')
edu.location=(0,12,0)

# Asset review scene, assets separated for visual QA without changing local exports.
shelter.location=(-7,0,0);sign.location=(-7,-1.8,0);bus.location=(5,0,0)
bpy.ops.wm.save_as_mainfile(filepath=P+'/transit_assets.blend')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False;scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.58,.64,.72,1);scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.8
bpy.ops.object.light_add(type='AREA',location=(0,-8,15));bpy.context.object.data.energy=4200;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=12
bpy.ops.object.camera_add(location=(21,23,18));cam=bpy.context.object;cam.rotation_euler=(Vector((-1,0,1))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=30;scene.camera=cam
scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.filepath=P+'/transit_assets_preview.png';bpy.ops.render.render(write_still=True)

cam.location=(5,-21,13);cam.rotation_euler=(Vector((-5,0,1))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=21;scene.render.filepath=P+'/shelter_front_preview.png';bpy.ops.render.render(write_still=True)

cam.location=(9,1,8);cam.rotation_euler=(Vector((0,12,1.5))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=8;scene.render.filepath=P+'/education_shelter_preview.png';bpy.ops.render.render(write_still=True)
