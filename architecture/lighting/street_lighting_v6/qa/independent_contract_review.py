"""Reconstructed revision: independent contract arithmetic, no original-coordinate identity claim."""
import hashlib,json,math
from collections import Counter
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(p.read_text())
freeze=load(R/'qa/placement_freeze.json');mp=R/freeze['manifest']['path']
assert freeze['status']=='PASS'
evidence=[R/'qa/placement_freeze.json']
for row in [freeze['manifest']]+freeze['reports']+freeze['scripts']:
 p=R/row['path'];assert sha(p)==row['sha256'];evidence.append(p)
m=load(mp);pr=load(R/'qa/placement_report.json');audit=load(R/'qa/final_placement_audit.json');fs=m['fixtures']
assert m['status']=='PASS' and len(fs)==len({f['id'] for f in fs})==536
assert Counter(f['kind'] for f in fs)==audit['counts_by_kind']==pr['counts_by_kind']
assert not any('1319139167' in str(f['route_source']) for f in fs)
radius=math.hypot(1.38,.15)
pair=min((math.dist(a['base_position'][:2],b['base_position'][:2]),a['id'],b['id']) for i,a in enumerate(fs) for b in fs[i+1:])
assert pair[0]>2*radius
legacy=pr['legacy_lamp_local_bounds'];assert len(legacy)==152
legacy_dist=[];deltas=[];mixed=[];head_min={};negative=Counter();vertical=[];patches=0
garage=audit['garage_audit'];lo=garage['min'];hi=garage['max'];garage_inside=[]
for f in fs:
 p=f['base_position'];lamp=f['lamp_position'];h=f['collision']['pole_height_m']
 assert h==(6.2 if f['kind'] in ['road','parking','transit'] else 4.2)
 assert abs(math.dist(p[:2],lamp[:2])-1)<2e-6 and abs(lamp[2]-p[2]-h)<2e-6
 head_min[f['kind']]=min(head_min.get(f['kind'],math.inf),lamp[2]-.075-f['target_position'][2])
 assert len(f['footing_ground_hits'])==8
 signed=[]
 for hit in f['footing_ground_hits']:
  assert abs(math.dist(p[:2],hit['position'][:2])-.19)<1e-6
  dz=hit['position'][2]-f['base_ground_hit']['position'][2]
  assert abs(dz-hit['signed_height_delta_m'])<1e-8 and abs(dz)<=.11
  signed.append(dz)
 deltas.extend(signed)
 if len({x['object'] for x in f['footing_ground_hits']})>1:mixed.append({'fixture':f['id'],'objects':sorted({x['object'] for x in f['footing_ground_hits']}),'signed_delta_m':[min(signed),max(signed)]})
 if lo[0]-.39<p[0]<hi[0]+.39 and lo[1]-.39<p[1]<hi[1]+.39:garage_inside.append(f['id'])
 for i,o in enumerate(legacy):
  a,b=o['min'],o['max']
  if b[2]<p[2]-.2 or a[2]>p[2]+h+.08:continue
  distance=math.hypot(max(a[0]-p[0],0,p[0]-b[0]),max(a[1]-p[1],0,p[1]-b[1]))
  legacy_dist.append((distance-radius,f['id'],i,o['object']))
 assert len(f['ground_patch_triangles'])==len(f['ground_patch_provenance']['triangles'])
 for ti,t in enumerate(f['ground_patch_triangles']):
  a,b,c=t;u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
  cr=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
  area=math.sqrt(sum(x*x for x in cr))/2;assert area>0
  if cr[2]<0:negative[f['ground_hit']['object']]+=1
  if cr[2]==0:vertical.append({'fixture':f['id'],'patch_index':ti,'area_3d_m2':area,'role':'Positive-area rounded sliver; visual-only pool, not a support floor.'})
  patches+=1
assert not garage_inside and min(legacy_dist)[0]>0
assert patches==audit['raw_finite_patch_triangles_checked']==120333
coverage=[]
for stop in m['coverage']['transit_stops']:
 p=stop['waiting_position'];observed=[]
 for fid in stop['covered_by_actual_ground_patch']:
  f=next(x for x in fs if x['id']==fid);zs=[]
  for a,b,c in f['ground_patch_triangles']:
   bx,by=b[0]-a[0],b[1]-a[1];cx,cy=c[0]-a[0],c[1]-a[1];den=bx*cy-by*cx
   if not den:continue
   u=((p[0]-a[0])*cy-(p[1]-a[1])*cx)/den;v=(bx*(p[1]-a[1])-by*(p[0]-a[0]))/den
   if min(u,v,1-u-v)>=-1e-8:zs.append(a[2]+u*(b[2]-a[2])+v*(c[2]-a[2]))
  if zs:observed.append({'fixture':fid,'height_delta_m':min(abs(z-p[2]) for z in zs)})
 assert observed and min(x['height_delta_m'] for x in observed)<.16
 coverage.append({'stop_id':stop['stop_id'],'actual_finite_patch_hits':observed})
assert len(coverage)==10
support_path=R/'qa/independent_recorded_support.json';support=load(support_path)
assert support['status']=='PASS_RECORDED_FINITE_SUPPORT' and support['placement_manifest']['sha256']==sha(mp)
geometry_path=R/'scripts/luminaire_geometry.py';geometry_test=load(R/'qa/fixture_geometry.json')
assert geometry_test['geometry_source_sha256']==sha(geometry_path)
spec_path=R/'qa/recovery_algorithm_specification.json';spec=load(spec_path)
assert not spec['prior_exact_coordinates_available'] and not spec['coordinate_identity_claim']
evidence += [support_path,R/'qa/independent_recorded_support.py',geometry_path,R/'qa/fixture_geometry.json',spec_path,R.parent/'native_recovery.json',R.parent/'glb_recovery.json']
report={'status':'PASS_NEW_FROZEN_CONTRACT_REVIEW','source_native_sha256':m['source_native_sha256'],'placement_sha256':sha(mp),'fixture_count':len(fs),
 'scope':'Independent new-contract arithmetic and independently decoded5360 raw source support points. Original a65 assets are reused. This is not a repeat of all previous model/game/image checks.',
 'counts_by_kind':dict(Counter(f['kind'] for f in fs)),
 'metrics':{'minimum_base_pair_m':pair[0],'closest_pair':list(pair[1:]),'whole_fixture_enclosing_xy_radius_m':radius,'minimum_new_fixture_envelope_gap_m':pair[0]-2*radius,'minimum_legacy_fixture_envelope_gap_m':min(legacy_dist)[0],'closest_legacy_pair':list(min(legacy_dist)[1:]),'legacy_bound_parts':len(legacy),'ring_rays':len(deltas),'signed_footing_range_m':[min(deltas),max(deltas)],'base_bottom_below_sampled_support_min_m':.2+min(deltas),'head_bottom_above_target_min_by_kind_m':head_min,'garage_fixture_count':0,'finite_pool_triangles':patches,'negative_winding_visual_triangles':sum(negative.values()),'positive_area_vertical_slivers':vertical},
 'mixed_footing_sources':mixed,'waiting_point_coverage':coverage,
 'recovery_limits':['The unavailable pre-reset manifest46c355c8 is historical only. Equal fixture counts do not establish equal placement or source bytes.','This newly inspected manifest has120333 positive-area pool triangles; no triangle-set inclusion/identity comparison with the unavailable prior120312 set is claimed.'],
 'pending_final_evidence':['Native save/reopen with all7923 original objects, geometry, materials, visibility, hierarchy, existing lights/world/cameras preserved.','Final fixture-only GLB and addition-only game consumer/capsule/OBB result bound to the new native.','Three final images bound to installed Blender4.3.2,256samples,denoising=false; prior official OIDN settings do not carry over.'],
 'limits':['Footing support is tested at the recorded centre and eight ring points, not every continuum point.','Existing lamp bounds are finite source geometry portions, not a surveyed lamp count.','Visual pools require double-sided presentation for inherited downward faces and must stay excluded from walk/drive/collision support.','Lighting layout,3000K color target and irradiance are inferred visualization choices, not measured installation or safety certification.','No new native/Node/render process was started by this reviewer.'],
 'evidence':[{'path':str(p),'sha256':sha(p)} for p in evidence],'script_sha256':sha(Path(__file__))}
(R/'qa/independent_contract_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':report['status'],'fixture_count':len(fs),'minimum_base_pair_m':pair[0],'minimum_legacy_envelope_gap_m':min(legacy_dist)[0],'pool_triangles':patches,'negative_winding':sum(negative.values()),'vertical_slivers':len(vertical)}))
