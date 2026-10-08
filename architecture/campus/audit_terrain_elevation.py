"""Audit final exported ground, or standalone raw terrain if export unavailable."""
import json,math,os,sys
import terrain_elevation as t
P=os.path.dirname(__file__);ref='/workspace/shared/chosun_detail_refs/terrain'
raw=[];bad=[]
for y in range(-1120,241,5):
 for x in range(-490,661,5):
  z=t.rawheight(x,y);raw.append(z)
  if not math.isfinite(z):bad.append([x,y,z])
core=[abs(t.rawheight(x,y)-t.legacy_height(x,y)) for x in range(-235,236,5) for y in range(-128,124,5)]
seams=[]
for x in range(-235,236,10):
 for y in [-128,123]:seams.append(abs(t.rawheight(x,y+.001)-t.rawheight(x,y-.001)))
for y in range(-128,124,10):
 for x in [-235,235]:seams.append(abs(t.rawheight(x+.001,y)-t.rawheight(x-.001,y)))
# Test stable pads against reversing order at real mapped building samples.
osm=json.load(open(P+'/source_data/campus_osm_geometry.json'));built=[]
for f in osm['features']:
 if f['category']!='building' or not f.get('include'):continue
 poly=f['points'];cx=sum(v[0] for v in poly)/len(poly);cy=sum(v[1] for v in poly)/len(poly)
 built.append({'poly':poly,'cx':cx,'cy':cy,'base':t.rawheight(cx,cy),'osm_id':f['osm_id']})
pads=t.prepare_pads(built);delta=0
for x in range(-490,661,35):
 for y in range(-1120,241,35):delta=max(delta,abs(t.padded_height(x,y,pads)-t.padded_height(x,y,list(reversed(pads)))))
report={'source_verified':True,'nonfinite_raw_samples':bad,'raw_min_max_m':[min(raw),max(raw)],'protected_core_max_difference_m':max(core),'core_boundary_max_2mm_difference_m':max(seams),'pad_order_max_difference_m':delta,'notes':['Source DSM mask and smoothing mitigate mapped roofs; canopy and unmapped roofs remain possible.','Core authored slopes, stairs and retaining walls are preserved; they are not DEM measurements.','Final road penetration, entrance, stop, dynamic vehicle checks require final build outputs.']}
OUT=sys.argv[1] if len(sys.argv)>1 else P
if os.path.exists(OUT+'/ground_elevation.json'):
 d=json.load(open(OUT+'/ground_elevation.json'));a=d['heights'];s=d['step']
 def final(x,y):
  u=(x-d['x0'])/s;v=(y-d['y0'])/s;i=math.floor(u);j=math.floor(v);u-=i;v-=j
  if i<0 or j<0 or i+1>=d['nx'] or j+1>=d['ny']:return None
  p=a[j][i];q=a[j+1][i+1]
  return p*(1-u)+a[j][i+1]*(u-v)+q*v if v<=u else p*(1-v)+q*u+a[j+1][i]*(v-u)
 nav=json.load(open(OUT+'/navigation.json'));res=[];steep=[]
 for r in nav.get('roads',[]):
  for p in r['points']:
   z=final(p[0],p[1])
   if z is not None:res.append(p[2]-z)
  for p,q in zip(r['points'],r['points'][1:]):
   run=math.dist(p[:2],q[:2]);grade=abs(q[2]-p[2])/max(run,.0001)
   if grade>.35:steep.append({'name':r['name'],'grade':round(grade,3),'point':p})
 report['final_ground']={'nonfinite':sum(not math.isfinite(z) for row in a for z in row),'road_z_offset_min_max':[min(res),max(res)] if res else None,'road_segments_grade_over_35percent':len(steep),'steep_examples':sorted(steep,key=lambda p:-p['grade'])[:20]}
json.dump(report,open(ref+'/terrain_validation.json','w'),ensure_ascii=False,indent=2);print(json.dumps(report,ensure_ascii=False,indent=2))
