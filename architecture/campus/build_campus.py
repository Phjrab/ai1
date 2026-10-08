"""Recreate Chosun campus original massing/facades over OSM footprint/road data.
Run: blender -b --python build_campus.py
Preserves detailed original mainbuilding separately; embeds cleaned near-main site.
Source geometry map data © OpenStreetMap contributors, ODbL 1.0.
"""
import bpy, math, json, os, sys, random
from mathutils import Vector
P=os.path.dirname(__file__);sys.path.insert(0,P)
OUT=os.environ.get('CAMPUS_OUTPUT_DIR',P);os.makedirs(OUT,exist_ok=True)
from mesh_architecture import Mesh,mat,rect,extrude,alongbox,architecture
sys.path.insert(0,os.path.join(os.path.dirname(P),'site'))
from site_builder import front_z,rear_z
R=random.Random(1046)
DATA=os.path.join(P,'source_data')
manifest=json.load(open(DATA+'/campus_manifest.json'));osm=json.load(open(DATA+'/campus_osm_geometry.json'))
# Restore the explicitly requested dental hospital without dropping prior structures.
for f in osm['features']:
 if f['osm_id']=='493566726':f['include']=True
for b in manifest['buildings']:
 if b['id'] in (166,171,178):b['include']=True
features=[f for f in osm['features'] if f['include']]
landmarks=[b for b in manifest['buildings'] if b['include']]
photos={b['id']:b for b in json.load(open(DATA+'/facades/source_index.json'))}
review_index={r['id']:r for r in json.load(open(DATA+'/architectural_review.json'))['entries'] if r.get('id') is not None}
# Named buildings remain separately inspectable.
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
root=bpy.data.collections.new('CHOSUN_CAMPUS');bpy.context.scene.collection.children.link(root)
def coll(n):
 c=bpy.data.collections.new(n);root.children.link(c);return c
collegecol=coll('CHOSUN_COLLEGE | 조선이공대학교')
terraincol=coll('CAMPUS 01 | Continuous terrain');roadcol=coll('CAMPUS 02 | Mapped roads paths plazas');landcol=coll('CAMPUS 03 | Mapped planting and recreation');treecol=coll('CAMPUS 04 | Original shared vegetation');carcol=coll('CAMPUS 05 | Original contemporary vehicles');detailcol=coll('CAMPUS 06 | Signs lighting furniture')
colors=[('brick',(.45,.19,.135)),('ivory',(.66,.67,.63)),('limestone',(.70,.65,.52)),('light metal',(.73,.78,.77)),('white trim',(.86,.85,.78)),('window frame',(.24,.30,.31)),('service dark',(.21,.24,.24)),('roof membrane',(.26,.33,.31)),('glass blue',(.09,.19,.23)),('glass green',(.14,.26,.27)),('glass dusk',(.22,.31,.33))]
mats=[mat('CAMPUS • '+n,c,.31 if 'glass' in n else .72,.25 if 'glass' in n else .02) for n,c in colors]
grass=mat('CAMPUS • hill grass',(.19,.29,.13));asphalt=mat('CAMPUS • weathered asphalt',(.095,.11,.12));pave=mat('CAMPUS • granite paving',(.53,.53,.48));paint=mat('CAMPUS • faded road white',(.83,.83,.73));trackmat=mat('CAMPUS • track terracotta',(.43,.18,.125));turfmat=mat('CAMPUS • playing field',(.11,.30,.17));watermat=mat('CAMPUS • pond water',(.11,.28,.28),.22)
# Keep the near-main original site as an editable nested collection.
with bpy.data.libraries.load(os.path.join(os.path.dirname(P),'site','site.blend'),link=False) as (src,dst):dst.collections=['CHOSUN_SITE']
site=dst.collections[0];root.children.link(site)
for ob in list(site.all_objects):
 if ob.name in ('Wooded terrace and rear hillside','Lower cross-campus contour road','End connector road -1','End connector road 1'):
  bpy.data.objects.remove(ob,do_unlink=True)
 elif ob.name=='Parking bay markings center lines zebra crossings' and ob.type=='MESH':
  import bmesh
  bm=bmesh.new();bm.from_mesh(ob.data)
  bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.y < -90 or (abs(v.co.x)<4 and -23<v.co.y<-13 and v.co.z<.1)],context='VERTS')
  bm.to_mesh(ob.data);bm.free()
# Existing detailed mainbuilding coordinates and near-main terrace are authoritative.
from terrain_elevation import rawheight,prepare_pads,padded_height,export_ground,metadata as elevation_metadata
from remaining_architecture import FLOORS,HEIGHTS

def cleanpoly(p):
 q=[tuple(v[:2]) for v in p]
 if len(q)>1 and math.dist(q[0],q[-1])<.01:q.pop()
 return q

def inside(x,y,p):
 c=False;j=len(p)-1
 for i in range(len(p)):
  a,b=p[i],p[j]
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:c=not c
  j=i
 return c

def bounds(p):return min(v[0] for v in p),min(v[1] for v in p),max(v[0] for v in p),max(v[1] for v in p)
# Different verified facade families, with contextual buildings assigned approximate forms.
styles={146:'modern',133:'stone','cit_1':'modern','cit_main':'brick','cit_3':'brick','cit_2':'modern','cit_4':'brick',162:'hospital',132:'modern',130:'brick',138:'modern',134:'modern',150:'brick',142:'dorm',147:'dorm',136:'stone',135:'arts',141:'stone',145:'brick',127:'stone'}
exclude={'190176334','190176326','471778461'}
byosm={}
for b in landmarks:
 if b.get('osm_id') and b['id'] not in (126,149):byosm.setdefault(b['osm_id'],b)
 for oid in b.get('additional_osm_ids',[]):byosm.setdefault(oid,b)
built=[]
for f in features:
 if f['category']!='building' or f['osm_id'] in exclude:continue
 p=cleanpoly(f['points'])
 if len(p)<3:continue
 if any(x<-490 or x>660 or y<-1120 or y>240 for x,y in p):continue
 b=byosm.get(f['osm_id']);bid=b['id'] if b else None
 # Remove accessory footprints already covered by preserved main wings.
 bx=bounds(p)
 if bx[0]>-195 and bx[2]<195 and bx[1]>-5 and bx[3]<32:continue
 cx=(bx[0]+bx[2])/2;cy=(bx[1]+bx[3])/2
 fs=len(photos[bid]['floors']) if bid in photos else int(float(f.get('levels') or 4))
 fs=FLOORS.get(bid,{146:5,133:8}.get(bid,fs))
 fs=max(1,min(18,fs));style=styles.get(bid,'engineering' if '공학' in f['name'] else ('brick' if len(built)%3==0 else 'stone'))
 built.append(dict(id=bid,name=b['name'] if b else f['name'] or '교내 부속동 '+f['osm_id'],osm_id=f['osm_id'],poly=p,holes=f.get('holes',[]),bbox=bx,cx=cx,cy=cy,floors=fs,style=style,base=rawheight(cx,cy),source=f['source']))
# Official centers without a mapped footprint get explicitly approximate, modest massing.
nonbuilding={126,149,167,168,163,158}
for b in landmarks:
 if b['id'] in nonbuilding or any(d['id']==b['id'] for d in built):continue
 if b.get('osm_id') and any(d['osm_id']==b['osm_id'] for d in built):continue
 cx,cy=b['x'],b['y'];w,d={164:(64,43),171:(38,16),176:(60,44),178:(42,16)}.get(b['id'],(58,22))
 p=rect(cx,cy,w,d);bx=bounds(p)
 built.append(dict(id=b['id'],name=b['name'],osm_id=None,poly=p,bbox=bx,cx=cx,cy=cy,floors=5 if b['id'] not in (165,164) else 4,style='dorm' if b['id']==165 else 'engineering',base=rawheight(cx,cy),source=b['source']))
# Split the mapped dental complex into two complementary, non-overlapping footprints.
# Boundary y=-605 is an evidence-informed interpretation of the narrow connector.
def split_dental(poly,above):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ia=a[1]>=-605 if above else a[1]<=-605;ib=b[1]>=-605 if above else b[1]<=-605
  if ia:out.append(a)
  if ia!=ib:
   t=(-605-a[1])/(b[1]-a[1]);out.append((a[0]+t*(b[0]-a[0]),-605))
 return out
for dental in list(built):
 if dental['id']!=152:continue
 original=dental['poly']
 for bid,above in [(152,True),(139,False)]:
  target=dental if bid==152 else dict(dental)
  target['id']=bid;target['name']='치과대학(교육동)' if bid==152 else '치과대학(연구동)'
  target['poly']=split_dental(original,above);target['bbox']=bounds(target['poly']);a,c,d,e=target['bbox'];target['cx']=(a+d)/2;target['cy']=(c+e)/2;target['base']=rawheight(target['cx'],target['cy']);target['floors']=FLOORS[bid];target['split_status']='Complementary split of shared OSM503476184; internal boundary approximate'
  if bid==139:built.append(target)
# Floors for official-pin-only contextual buildings also use individually reviewed evidence.
for b in built:
 b['floors']=FLOORS.get(b['id'],b['floors'])
 if b['id']==176:b['collision_polys']=[rect(b['cx']-18+j*18,b['cy']-9+row*18,7.2,5.6) for row in range(2) for j in range(3)]
 b['height_m']=HEIGHTS.get(b['id'],b['floors']*(3.15 if b['style'] in ('dorm','hospital') else 3.55))
# Flatten building terraces, with blended landscaped margins; exact near-main apron retained.
json.dump(built,open(OUT+'/terrain_building_pads.json','w'),ensure_ascii=False,indent=2)
terrain_pads=prepare_pads(built)
from terrain_roadbeds import Roadbeds
pad_height=lambda x,y:padded_height(x,y,terrain_pads)
roadbeds=Roadbeds(pad_height,terrain_pads)
roadbeds.write_report(OUT+'/roadbed_corrections.json')
footbeds=Roadbeds(roadbeds,terrain_pads,max_grade=.32,graph_kind='walking',fixed=lambda x,y:roadbeds.near_corridor(x,y,-1.))
footbeds.write_report(OUT+'/footbed_corrections.json')
def height(x,y):return footbeds(x,y)
# All roads use the same piecewise-linear height surface as the rendered terrain.
analytic_height=height
height_cache={}
def gridheight(x,y):
 key=(x,y)
 if key not in height_cache:height_cache[key]=analytic_height(x,y)
 return height_cache[key]
def height(x,y):
 x0=-490+math.floor((x+490)/5)*5;y0=-1120+math.floor((y+1120)/5)*5
 u=(x-x0)/5;v=(y-y0)/5;a=gridheight(x0,y0);c=gridheight(x0+5,y0+5)
 if v<=u:return a*(1-u)+gridheight(x0+5,y0)*(u-v)+c*v
 return a*(1-v)+c*u+gridheight(x0,y0+5)*(v-u)
# Core grounds and surrounding woodland skirt. Full boundary is retained as map evidence.
xs=[-490+i*5 for i in range(231)];ys=[-1120+j*5 for j in range(273)]
nav={'coordinate_system':'Blender Z-up meters; export glTF Y-up','bounds':{'min':[-490,-1120,-80],'max':[660,240,110]},'roads':[],'landmarks':[],'collisionBoxes':[],'notes':'Ground slopes and unmapped building dimensions approximate; original main building unchanged. Road/footprint data © OpenStreetMap contributors ODbL 1.0.'}
from detailed_stairs import build_central,entry_access,workshop_stair
build_central(site,detailcol,nav)
entry_locations={};render_catalog=[]
# Connected ribbons sampled tightly across slopes. Shared mitered edges avoid cracks.
def ribbon(name,pts,width,material,zoff=.075,record=False,skipmain=False):
 if len(pts)<2:return
 dense=[]
 for p,q in zip(pts,pts[1:]):
  le=math.dist(p[:2],q[:2]);n=max(1,math.ceil(le/2.2))
  dense.extend([(p[0]+(q[0]-p[0])*j/n,p[1]+(q[1]-p[1])*j/n) for j in range(n)])
 dense.append(pts[-1][:2]);mesh=Mesh();path=[]
 for i,(x,y) in enumerate(dense):path.append([x,y,height(x,y)+zoff])
 for i,(a,b) in enumerate(zip(dense,dense[1:])):
  mx,my=(a[0]+b[0])/2,(a[1]+b[1])/2
  if any(x<-490+width or x>660-width or y<-1120+width or y>240-width for x,y in (a,b)):continue
  if skipmain and abs(mx)<232 and -128<my<123:continue
  va=[]
  for j,p in [(i,a),(i+1,b)]:
   prev=dense[max(0,j-1)];nxt=dense[min(len(dense)-1,j+1)];dx,dy=nxt[0]-prev[0],nxt[1]-prev[1];le=max(.0001,math.hypot(dx,dy));nx,ny=-dy/le,dx/le
   for sign in (-1,1):
    px=p[0]+nx*sign*width/2;py=p[1]+ny*sign*width/2;va.append((px,py,height(px,py)+zoff))
  mesh.poly(va,[(0,2,3),(0,3,1)])
 if mesh.v:mesh.object(name,[material],roadcol)
 if record:nav['roads'].append({'name':name,'width':width,'points':[p for p in path if -480<p[0]<650 and -1110<p[1]<230]})
from road_continuity import build_continuous_roads
roadfeatures=build_continuous_roads(features,built,height,Mesh,roadcol,asphalt,pave,nav,P)
# Every mapped area is clipped to the exact final terrain triangles.
from grounded_areas import add_ground_polygon,add_ground_skirt
parking=[];plantareas=[]
for f in features:
 if f['category']!='area' or f['osm_id']=='468689587':continue
 p=cleanpoly(f['points']);t=f['tags'];typ=t.get('leisure');ispark=t.get('amenity')=='parking'
 if len(p)<3:continue
 if t.get('natural') in ('wood','scrub') or t.get('landuse')=='forest':plantareas.append(p)
 if ispark and t.get('parking') in ('multi-storey','underground'):continue
 material=asphalt if ispark else (trackmat if typ=='track' else (turfmat if typ=='pitch' else (watermat if t.get('natural')=='water' else None)))
 if material:
  me=Mesh()
  if typ=='track':
   cx=sum(q[0] for q in p)/len(p);cy=sum(q[1] for q in p)/len(p)
   for a,b in zip(p,p[1:]+p[:1]):
    pp=[a,b,(cx+(b[0]-cx)*.89,cy+(b[1]-cy)*.89),(cx+(a[0]-cx)*.89,cy+(a[1]-cy)*.89)]
    add_ground_polygon(me,pp,height,.08)
  else:add_ground_polygon(me,p,height,.04)
  add_ground_skirt(me,p,height,.08 if typ=='track' else .04)
  me.object('CAMPUS_PLAZA '+f['osm_id']+' '+(f['name'] or typ or 'parking'),[material],landcol)
  if ispark:parking.append(p)

def clipaxis(poly,axis,value,above=True):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ia=a[axis]>=value if above else a[axis]<=value;ib=b[axis]>=value if above else b[axis]<=value
  if ia:out.append(a)
  if ia!=ib:
   t=(value-a[axis])/(b[axis]-a[axis]);out.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
 return out

# Landmark buildings use actual OSM outline; source-backed exterior families.
coverage=[]
for b in built:
 bid=b['id'];p=b['poly'];base=b['base'];fs=b['floors'];name='CAMPUS_BUILDING '+str(bid or b['osm_id'])+' '+b['name'];c=coll(name)
 if str(bid).startswith('cit_'):
  root.children.unlink(c);collegecol.children.link(c)
 c['source']=b['source'];c['footprint_status']='OSM traced' if b['osm_id'] else 'approximate footprint around official pin';c['height_status']='official directory floor count; per-floor height approximate' if bid in photos or str(bid).startswith('cit_') else 'approximate massing height'
 parts=[{'polygon':p,'floors':fs}]
 if bid==162:parts=[{'polygon':clipaxis(p,1,-825,False),'floors':7},{'polygon':clipaxis(clipaxis(p,1,-825,True),1,-775,False),'floors':8},{'polygon':clipaxis(p,1,-775,True),'floors':7}]
 elif bid==127:parts=[{'polygon':[q for q in p if q not in [(30.275,-190.821),(71.199,-194.901)]],'floors':3,'open_ground':True},{'polygon':[(27.726,-216.181),(30.275,-190.821),(71.199,-194.901),(68.827,-218.495)],'floors':7}]
 elif bid==138:parts=[{'polygon':clipaxis(p,0,269,False),'floors':4},{'polygon':clipaxis(p,0,269,True),'floors':10,'ribbon_glass':True}]
 elif bid==141:parts=[{'polygon':clipaxis(p,0,-295,False),'floors':2},{'polygon':clipaxis(p,0,-295,True),'floors':4}]
 elif bid==142:
  parts=[{'polygon':p,'floors':2},{'polygon':rect(466,-124,17,43,-.17),'floors':11},{'polygon':rect(535,-132,17,42,-.17),'floors':11}]
 from photo_refinements import build as photo_architecture
 from remaining_architecture import build as remaining_architecture,_front
 if not remaining_architecture(b,parts,c,mats) and not photo_architecture(bid,parts,base,fs,c,mats):
  architecture(name,parts,base,fs,b['style'],c,mats)
 from photo_refinements import accents
 accents(bid,parts,base,fs,c,mats)
 if str(bid).startswith('cit_'):
  from college_specials import extras
  extras(bid,p,base,fs,c,mats)
 try:
  from facade_specials import extra_details
  extra_details(bid,parts,base,fs,c,mats)
 except ImportError:pass
 if bid==162:
  from hospital_sports_specials import extras as campus_extras
  campus_extras(bid,parts,base,fs,c,mats)
 # Outside-wall, photo-supported stairs have real treads/landings and nav tops.
 entrance_edge=b.get('front_edge') or _front(p);source_page='https://www3.chosun.ac.kr/campusMap/chosun/'+str(bid)+'/detailView.do'
 if bid in (133,141,144,153,177):
  arrival,door=entry_access(b,entrance_edge,c,nav,height,source_page,steps={133:8,141:9,144:4,153:6,177:5}[bid],width={133:16,141:16,144:5,153:8,177:6}[bid],add_ramp=bid==144)
  entry_locations[str(bid)]={'arrival':arrival,'door':door}
 if bid==158:workshop_stair(b,entrance_edge,c,nav)
 # Cut mapped courtyard holes through mass and roof, keeping outline data intact.
 for hole in b.get('holes',[]):
  cutter=Mesh();extrude(cutter,cleanpoly(hole),base-2,base+fs*3.55+8);co=cutter.object('Temporary mapped courtyard cutter',[mats[1]],c)
  for ob in list(c.objects):
   if ob==co or ob.type!='MESH' or not ('Massing' in ob.name or 'Roof and' in ob.name or 'individually reviewed mass' in ob.name or 'observed roof typology' in ob.name):continue
   mod=ob.modifiers.new('Mapped inner courtyard opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=co
   bpy.context.view_layer.objects.active=ob
   bpy.ops.object.modifier_apply(modifier=mod.name)
  bpy.data.objects.remove(co,do_unlink=True)
 # Continuous retaining/foundation skins close the base-to-final-ground transition.
 foundation=Mesh()
 for foundation_poly in b.get('collision_polys',[p]):
  for pa,pb in zip(foundation_poly,foundation_poly[1:]+foundation_poly[:1]):
   count=max(1,math.ceil(math.dist(pa,pb)/2))
   for k in range(count):
    aa=(pa[0]+(pb[0]-pa[0])*k/count,pa[1]+(pb[1]-pa[1])*k/count);bb=(pa[0]+(pb[0]-pa[0])*(k+1)/count,pa[1]+(pb[1]-pa[1])*(k+1)/count)
    za=height(*aa)-.25;zb=height(*bb)-.25
    if abs(za-base)<.12 and abs(zb-base)<.12:continue
    foundation.poly([(aa[0],aa[1],base+.03),(bb[0],bb[1],base+.03),(bb[0],bb[1],zb),(aa[0],aa[1],za)],[(0,1,2,3)],1)
 if foundation.v:
  fo=foundation.object('FOUNDATION '+str(bid or b['osm_id'])+' | final-ground retaining closure',mats,c);fo['confidence']='Terrain-integration construction, not a surveyed retaining wall.'
 # Collision vertical bounds follow the actual detailed roofline, not assumed storey spacing.
 b['height_m']=max(v.co.z for ob in c.all_objects if ob.type=='MESH' and not ob.name.startswith('FOUNDATION') for v in ob.data.vertices)-base
 # Fine footprint collision grid instead of one solid block across courtyards.
 a,d,e,f=b['bbox'];step=2
 for y in range(math.floor(d),math.ceil(f),step):
  run=None
  for x in range(math.floor(a),math.ceil(e)+step,step):
   hit=x<e and any(all(inside(xx,yy,cp) for xx,yy in ((x+.05,y+.05),(x+step-.05,y+.05),(x+step-.05,y+step-.05),(x+.05,y+step-.05))) for cp in b.get('collision_polys',[p])) and not any(inside(x+step/2,y+step/2,hh) for hh in b.get('holes',[]))
   if hit and run is None:run=x
   if not hit and run is not None:
    nav['collisionBoxes'].append({'min':[run,y,base],'max':[x,min(f,y+step),base+b['height_m']+1],'label':b['name']});run=None
 # Distinguish storeys, directory labels and interpreted mass height.
 review_status='photo individually inspected; hidden sides/dimensions approximate' if bid in FLOORS or bid in (127,132,133,134,135,136,138,141,142,145,146,147,150,164) else ('CIT group photo reviewed; individual attribution incomplete' if str(bid).startswith('cit_') else 'unidentified accessory: exterior/height unverified; preserved contextual estimate')
 coverage.append({'id':bid,'name':b['name'],'osm_id':b['osm_id'],'floors':fs,'footprint':c['footprint_status'],'height':c['height_status'],'model_height_m':b['height_m'],'source':b['source'],'facade_source':source_page if bid is not None and not str(bid).startswith('cit_') else photos.get(bid,{}).get('page_url'),'original_meshes':True,'review_status':review_status,'split_status':b.get('split_status')})
 c['review_status']=review_status
 coverage[-1]['official_directory_floor_labels']=review_index.get(bid,{}).get('official_directory_floor_labels',[])
 coverage[-1]['reference_image']=review_index.get(bid,{}).get('image_url')
 # Cameras are derived from actually emitted geometry, including projecting canopies.
 verts=[ob.matrix_world @ Vector(v) for ob in c.all_objects if ob.type=='MESH' for v in ob.bound_box]
 lo=[min(v[i] for v in verts) for i in range(3)];hi=[max(v[i] for v in verts) for i in range(3)]
 target=[(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,(lo[2]+hi[2])/2]
 span=max(hi[0]-lo[0],hi[1]-lo[1],hi[2]-lo[2]);ee=entrance_edge;outward=(ee[5],ee[6]);along=(ee[3],ee[4])
 camera=[target[0]+span*(outward[0]*1.15+along[0]*.65),target[1]+span*(outward[1]*1.15+along[1]*.65),target[2]+span*.43]
 entrance=entry_locations.get(str(bid),{}).get('door',[(ee[0][0]+ee[1][0])/2+ee[5]*.4,(ee[0][1]+ee[1][1])/2+ee[6]*.4,base+.1])
 render_catalog.append({'index':len(render_catalog)+1,'id':bid,'osm_id':b['osm_id'],'name':b['name'],'collection':c.name,'bbox':{'min':lo,'max':hi},'target':target,'camera':camera,'orthographic_scale':span*1.42,'entrance':entrance,'entrance_orientation_status':'photo-informed facade assumption; no surveyed entrance coordinate','footprint_status':b.get('split_status') or c['footprint_status'],'modeled_floor_count':fs,'reference_image':review_index.get(bid,{}).get('image_url'),'source':source_page if bid else b['source'],'review_status':review_status})

# Terrain-only estimated connections remain separately inspectable from photographed stairs.
from terrain_walksteps import add_inferred_walksteps
inferred_col=coll('CAMPUS 07 | INFERRED game terrain connections — not photo-verified stairs')
inferred_col['evidence_status']='INFERRED GAME TERRAIN CONNECTION ONLY; not an assertion that real stairs exist here'
add_inferred_walksteps(nav,height,Mesh,inferred_col,pave,OUT)
from local_walk_clearance import clear_entry144_paving_edge
clear_entry144_paving_edge(nav,roadcol,OUT)
# Retaining skins around inset pedestrian approaches prevent open terrain-cut edges.
walk_edges={}
for surface in nav.get('walkableSurfaces',[]):
 if surface['id'].startswith(('workshop','inferred_walk_connector')):continue
 pp=surface['polygon']
 for aa,bb in zip(pp,pp[1:]+pp[:1]):
  key=tuple(sorted(((round(aa[0],4),round(aa[1],4)),(round(bb[0],4),round(bb[1],4)))))
  walk_edges.setdefault(key,[]).append((aa,bb))
walk_walls=Mesh()
for entries in walk_edges.values():
 if len(entries)!=1:continue
 aa,bb=entries[0];za=height(aa[0],aa[1])-.20;zb=height(bb[0],bb[1])-.20
 if max(abs(aa[2]-za),abs(bb[2]-zb))<.12:continue
 walk_walls.poly([aa,bb,(bb[0],bb[1],zb),(aa[0],aa[1],za)],[(0,1,2,3)])
if walk_walls.v:
 ob=walk_walls.object('STAIR_DETAIL | exterior terrain retaining closures',[pave],detailcol);ob['confidence']='Construction closure to approximate final ground, not a surveyed retaining wall.'
from terrain_cutouts import TerrainCutouts
cutout_buildings=[]
for b in built:
 for cp in b.get('collision_polys',[b['poly']]):cutout_buildings.append({**b,'poly':cp})
# The same explicit walk polygons cut terrain so hillside triangles cannot bury treads.
for surface in nav.get('walkableSurfaces',[]):
 if surface['id'].startswith('entry_133_') or any(height(v[0],v[1])-.20>v[2]-.025 for v in surface['polygon']):cutout_buildings.append({'poly':[(v[0],v[1]) for v in surface['polygon']]})
terrain_cutouts=TerrainCutouts(cutout_buildings)
g=Mesh()
for y in ys[:-1]:
 for x in xs[:-1]:
  terrain_cutouts.add_cell(g,x,y,height)
terrain_object=g.object('CAMPUS_TERRAIN | continuous hillside ground',[grass],terraincol)
# Weld duplicate clipped-triangle vertices so normals shade as continuous earth.
import bmesh
bm=bmesh.new();bm.from_mesh(terrain_object.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bm.normal_update();bm.to_mesh(terrain_object.data);bm.free()
for face in terrain_object.data.polygons:face.use_smooth=True
# Retain old detailed assets, culling clashes with new mapped structures.
def obstructed(x,y,margin=3):
 for b in built:
  a,c,d,e=b['bbox']
  if a-margin<x<d+margin and c-margin<y<e+margin:return True
 return False
for ob in list(site.all_objects):
 if ('Tree ' in ob.name or 'Parked vehicle' in ob.name or 'Rear parked' in ob.name) and obstructed(ob.location.x,ob.location.y):bpy.data.objects.remove(ob,do_unlink=True)
# Original low-complexity broadleaf/conifer meshes are shared over the whole campus.
leaf=[mat('CAMPUS • canopy '+str(i),c) for i,c in enumerate([(.075,.18,.085),(.12,.235,.105),(.20,.30,.105),(.29,.33,.12)])];bark=mat('CAMPUS • bark',(.22,.17,.12))
treemesh=[]
for k in range(4):
 me=Mesh();me.tube((0,0,0),(0,0,6.8),.27,.12,0,n=7)
 for j in range(6):
  a=j*2.399;me.ellipsoid((math.cos(a)*1.6,math.sin(a)*1.6,6+j*.30),(2.5,2.2,3),1+(j+k)%4,seed=100*k+j,rings=4,segs=7)
 ob=me.object('CAMPUS tree prototype',[bark]+leaf,treecol);treemesh.append(ob.data);treecol.objects.unlink(ob);bpy.data.objects.remove(ob)
def segdist(x,y,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(.001,dx*dx+dy*dy)));return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)
def roadnear(x,y):
 return any(segdist(x,y,a,b)<w/2+3 for p,w,t in roadfeatures for a,b in zip(p,p[1:]) if min(a[0],b[0])-10<x<max(a[0],b[0])+10 and min(a[1],b[1])-10<y<max(a[1],b[1])+10)
# Imported near-main trees also obey the final connected road clearance.
for ob in list(site.all_objects):
 if any(k in ob.name for k in ('Tree ','Parked vehicle','Rear parked')) and roadnear(ob.location.x,ob.location.y):bpy.data.objects.remove(ob,do_unlink=True)
 elif 'Tree ' in ob.name:ob.location.z=height(ob.location.x,ob.location.y)-.20
nt=0
for p in plantareas:
 a,c,d,e=bounds(p);area=(d-a)*(e-c);count=min(180,int(area/95))
 for k in range(count):
  x=R.uniform(a,d);y=R.uniform(c,e)
  if not(-480<x<650 and -1110<y<230) or not inside(x,y,p) or (abs(x)<235 and -140<y<123) or obstructed(x,y,7) or roadnear(x,y):continue
  ob=bpy.data.objects.new('CAMPUS_TREE %04d'%nt,treemesh[nt%4]);treecol.objects.link(ob);ob.location=(x,y,height(x,y)-.20);s=R.uniform(.75,1.35);ob.scale=(s,s,s);ob.rotation_euler.z=R.random()*6.28;nt+=1
# Parking markings and linked vehicles reuse our original car meshes, no third-party vehicle models.
car_sources=[o.data for o in site.all_objects if 'Parked vehicle' in o.name][:6]
marks=Mesh();nc=0
for p in parking:
 a,c,d,e=bounds(p)
 for y in range(math.ceil(c+4),math.floor(e-4),13):
  for x in range(math.ceil(a+3),math.floor(d-3),3):
   if not inside(x,y,p) or not inside(x+2.5,y+5,p) or obstructed(x,y,2) or (abs(x)<235 and -140<y<123):continue
   z=height(x,y)+.055;add_ground_polygon(marks,rect(x,y,.08,4.8),height,.055)
   gx=(height(x+2.1,y)-height(x+.5,y))/1.6;gy=(height(x+1.3,y+1.4)-height(x+1.3,y-1.4))/2.8
   if car_sources and R.random()<.39 and nc<280 and math.hypot(gx,gy)<.20:
    ob=bpy.data.objects.new('CAMPUS_CAR %03d'%nc,car_sources[nc%len(car_sources)]);carcol.objects.link(ob);ob.location=(x+1.3,y,height(x+1.3,y)+.02);ob.rotation_mode='QUATERNION';ob.rotation_quaternion=Vector((0,0,1)).rotation_difference(Vector((-gx,-gy,1)).normalized());nc+=1
# Actual tire vertices, not an assumed vehicle pivot, determine final contact.
bpy.context.view_layer.update()
for ob in list(carcol.objects):
 if not ob.name.startswith('CAMPUS_CAR'):continue
 inds={i for face in ob.data.polygons if face.material_index==3 for i in face.vertices}
 groups={}
 for i in inds:
  local=ob.data.vertices[i].co
  if abs(local.x)<.6 or abs(local.y)<.6 or local.z>.95:continue
  world=ob.matrix_world@local;gap=world.z-height(world.x,world.y)-.04
  key=(local.x>0,local.y>0);groups[key]=min(groups.get(key,float('inf')),gap)
 if not groups:continue
 if len(groups)==4 and max(groups.values())-min(groups.values())>.12:
  bpy.data.objects.remove(ob,do_unlink=True);nc-=1;continue
 ob.location.z+=.005-min(groups.values())
 ob['placement']='Actual tire-vertex contact on final parking surface; highly uneven parking spots omitted.'
marks.object('CAMPUS_PARKING painted bay lines',[paint],roadcol)

# Original field markings on the verified sports polygons, with source-shaped track lanes.
for f in features:
 if f['category']!='area':continue
 p=cleanpoly(f['points']);t=f['tags'];typ=t.get('leisure')
 if typ not in ('pitch','track') or len(p)<3:continue
 if typ=='track':
  cx=sum(a[0] for a in p)/len(p);cy=sum(a[1] for a in p)/len(p)
  for k in range(1,7):
   fac=1-k*.015;pp=[(cx+(x-cx)*fac,cy+(y-cy)*fac) for x,y in p];ribbon('CAMPUS_PATH track lane',pp+[pp[0]],.10,paint,zoff=.12)
 else:
  ribbon('CAMPUS_PATH sports boundary',p+[p[0]],.13,paint,zoff=.11)
  if len(p)==4:
   a,b,c,d=p;mid1=((a[0]+b[0])/2,(a[1]+b[1])/2);mid2=((c[0]+d[0])/2,(c[1]+d[1])/2)
   ribbon('CAMPUS_PATH field center line',[mid1,mid2],.13,paint,zoff=.11)
   cx=sum(a[0] for a in p)/4;cy=sum(a[1] for a in p)/4;rad=8 if t.get('sport')=='soccer' else 3
   pp=[(cx+rad*math.cos(k*math.tau/48),cy+rad*math.sin(k*math.tau/48)) for k in range(49)]
   ribbon('CAMPUS_PATH field center circle',pp,.13,paint,zoff=.12)
# Rose garden beds at the mapped garden, no unverified current planting claims.
rose=next((f for f in features if f['name']=='장미원'),None)
if rose:
 pp=cleanpoly(rose['points']);a,c,d,e=bounds(pp);beds=Mesh();rose_mats=[mat('CAMPUS • rose '+str(i),co) for i,co in enumerate([(.37,.055,.08),(.57,.16,.24),(.65,.56,.23),(.12,.24,.08)])]
 for y in range(math.ceil(c+5),math.floor(e-5),7):
  for x in range(math.ceil(a+5),math.floor(d-5),7):
   if not inside(x,y,pp) or obstructed(x,y,3):continue
   beds.box((x,y,height(x,y)+.025),(4.6,2.4,.45),3)
   for j in range(4):beds.ellipsoid((x-1.8+j*1.2,y,height(x,y)+.65),(.65,.75,.55),j%3,seed=j,rings=3,segs=6)
 beds.object('CAMPUS rose garden original planting',[*rose_mats],landcol)

# Wayfinding: verified official landmarks, safe pedestrian arrival coordinates outside walls.
for b in landmarks:
 if b['id']==149:continue
 builtb=next((d for d in built if d['id']==b['id'] or d['osm_id']==b.get('osm_id') and b.get('osm_id')),None)
 if b['id']==126:x,y,z=0,-6,0
 elif str(b['id']) in entry_locations:x,y,z=entry_locations[str(b['id'])]['arrival']
 elif builtb:
  a,c,d,e=builtb['bbox'];x,y=(a+d)/2,c-6;z=height(x,y)
 else:x,y=b['x'],b['y'];z=height(x,y)
 nav['landmarks'].append({'id':str(b['id']),'label':b['name'],'position':[round(x,3),round(y,3),round(z+.12,3)],'yaw':math.pi,'source':b['source'],'pin':[b['x'],b['y']]})
# Keep all arrival points clear of adjacent buildings, including shared-footprint aliases.
def blocked_arrival(x,y):
 return any(bb['min'][0]-1<x<bb['max'][0]+1 and bb['min'][1]-1<y<bb['max'][1]+1 for bb in nav['collisionBoxes'])
for dest in nav['landmarks']:
 x,y,z=dest['position']
 if not blocked_arrival(x,y):continue
 candidates=[]
 for road in nav['roads']:
  for aa,bb in zip(road['points'],road['points'][1:]):
   if math.hypot(aa[0]-x,aa[1]-y)>120:continue
   dx,dy=bb[0]-aa[0],bb[1]-aa[1];le=max(.001,math.hypot(dx,dy));nx,ny=-dy/le,dx/le
   for side in (-1,1):
    px=aa[0]+side*nx*(road['width']/2+1.5);py=aa[1]+side*ny*(road['width']/2+1.5)
    if not blocked_arrival(px,py):candidates.append((math.hypot(px-x,py-y),px,py))
 if candidates:
  _,px,py=min(candidates);dest['position']=[round(px,3),round(py,3),round(height(px,py)+.12,3)];dest['arrival_note']='Nearest clear roadside arrival; avoids neighboring footprint.'
# Lighting poles and benches remain restrained illustrative furniture.
fur=Mesh()
for i in range(0,len(nav['roads']),9):
 pp=nav['roads'][i]['points']
 if not pp:continue
 x,y,z=pp[len(pp)//2];x+=6
 if obstructed(x,y) or (abs(x)<235 and -140<y<123):continue
 fur.tube((x,y,height(x,y)-.22),(x,y,height(x,y)+5.8),.085,m=0,n=6);fur.box((x,y,height(x,y)+5.85),(1.2,.35,.16),1)
fur.object('CAMPUS street lighting',[mats[5],mats[4]],detailcol)
# Representative source-informed transit facilities, authored in a separate module.
sys.path.insert(0,os.path.join(os.path.dirname(P),'transit'))
from append_transit import append_transit
from resample_transit import resample as resample_transit
transit_data=resample_transit(os.path.join(os.path.dirname(P),'transit','transit_placements.json'),OUT+'/transit_placements.json',height,nav,features)
if os.environ.get('CAMPUS_SKIP_TRANSIT')!='1':
 append_transit(height_fn=height,include_display_bus=True,placement_path=OUT+'/transit_placements.json')
 for tc in list(scene_col for scene_col in bpy.context.scene.collection.children if scene_col.name.startswith('CAMPUS_TRANSIT')):
  root.children.link(tc);bpy.context.scene.collection.children.unlink(tc)
root['geometry_authorship']='All architectural, vegetation and vehicle meshes original procedural work; no photo textures or external models.'
root['map_attribution']='© OpenStreetMap contributors, ODbL 1.0 | https://www.openstreetmap.org/copyright'
root['limits']='Mapped footprints and roads; approximate terrain, heights, inaccessible facade sides, trees and current vehicle placements. Exterior reconstruction, not survey or verified interior plan.'
root['mainbuilding']='Unchanged detailed building is a separate asset. This collection replaces the earlier CHOSUN_SITE.'
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
stats={'buildings':len(built),'named_coverage':coverage,'trees_added':nt,'vehicles_added':nc,'objects':len(root.all_objects),'polygons':sum(len(o.data.polygons) for o in root.all_objects if o.type=='MESH'),'map_attribution':root['map_attribution']}
export_ground(height,OUT+'/ground_elevation.json');nav['elevation']=elevation_metadata()
json.dump(render_catalog,open(OUT+'/building_render_catalog.json','w'),ensure_ascii=False,indent=2)
json.dump(nav,open(OUT+'/navigation.json','w'),ensure_ascii=False,indent=2);json.dump(stats,open(OUT+'/campus_coverage.json','w'),ensure_ascii=False,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/campus.blend',compress=True)
bpy.ops.export_scene.gltf(filepath=OUT+'/campus.glb',export_format='GLB',export_yup=True,export_cameras=False,export_lights=False,export_extras=True)
print('CAMPUS_READY',len(built),nt,nc,flush=True)
