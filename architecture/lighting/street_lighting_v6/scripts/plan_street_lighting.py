"""Recovered v6 placement algorithm. Explicit input paths; never opens Blender.
This is reconstructed source, not a claim of byte-identical script/manifest recovery.
"""
import argparse,gc,json,math,resource,time
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from lighting_core import *
SHA='a65c2ae19f02c59f655e0c7eedb2482a5c2f6a9c53bb94f2425769dbd4417fbd'
class Clearance:
 def __init__(self,nav,world,inv,routes):
  self.cell=25.;self.grid=defaultdict(list);self.ogrid=defaultdict(list);self.obs=[];self.obbs=[];self.polys=[];self.water=nav.get('waterHazards',[]);self.parking=[];self.inventory_counts=Counter();self.garage=[]
  for name,o in inv['objects'].items():
   if o.get('type')!='MESH' or not o.get('render_visible_in_scene') or 'bounds_min' not in o:continue
   lo=np.array(o['bounds_min']);hi=np.array(o['bounds_max']);dim=hi-lo;n=name.lower();cols=' '.join(o['collections']).lower()
   if any('CAMPUS_BUILDING 164' in c for c in o['collections']):self.garage.append((lo,hi))
   if ('campus_plaza' in n and 'parking' in n) or 'rv2_v5_parking_terrace' in n:self.parking.append((name,lo,hi))
   kind='tree' if ('vegetation' in cols or 'canopies' in cols or 'canopy |' in n) else 'vehicle' if ('vehicles' in cols or 'parked vehicle' in n) else 'native_obstacle'
   if kind in ['tree','vehicle'] or (max(dim[:2])<60 and dim[2]>.6 and not any(t in n for t in ['terrain','paving','asphalt','plaza','path_grounded','retaining','foundation','treads','steps','stair','floor','drive_surface'])):self.obs.append((lo,hi,name,kind));self.inventory_counts[kind]+=1
  for o in world['collisionBoxes']:
   lo=blender_xyz([o['min'][0],o['min'][1],o['max'][2]]);hi=blender_xyz([o['max'][0],o['max'][1],o['min'][2]]);self.obs.append((lo,hi,o.get('label','game_box'),'game_box'))
  for key in ['staticColliders','closedDoors']:
   for o in world.get(key,[]):self.obbs.append((blender_xyz(o['center']),np.array([o['halfSize'][0],o['halfSize'][2],o['halfSize'][1]]),-o.get('yaw',0),o.get('name',key),1.3 if key=='closedDoors' else .35))
  for o in world.get('collisionPolygons',[]):
   if o.get('type','solid') not in ['solid','barrier']:continue
   p=np.array(o['polygon'],float);p[:,1]*=-1;self.polys.append((p,o.get('minY',o.get('min_z',-100)),o.get('maxY',o.get('max_z',200)),o.get('id','polygon')))
  segments=[]
  for r in routes:
   for a,b in zip(r['points'][:-1],r['points'][1:]):
    if np.linalg.norm(b[:2]-a[:2])<1e-5:continue
    i=len(segments);segments.append((a,b,r['width']/2,r['vehicle']));pad=r['width']/2+2;low=np.floor((np.minimum(a[:2],b[:2])-pad)/25).astype(int);high=np.floor((np.maximum(a[:2],b[:2])+pad)/25).astype(int)
    for x in range(low[0],high[0]+1):
     for y in range(low[1],high[1]+1):self.grid[x,y].append(i)
  self.sa=np.array([s[0] for s in segments]);self.sb=np.array([s[1] for s in segments]);self.sd=self.sb-self.sa;self.sl=np.sum(self.sd[:,:2]**2,axis=1);self.sw=np.array([s[2] for s in segments]);self.sv=np.array([s[3] for s in segments]);self.reindex()
 def reindex(self):
  self.ol=np.array([o[0] for o in self.obs]);self.oh=np.array([o[1] for o in self.obs]);self.ok=[o[3] for o in self.obs];self.ogrid=defaultdict(list)
  for i,(a,b,_,_) in enumerate(self.obs):
   low=np.floor((a[:2]-2)/25).astype(int);high=np.floor((b[:2]+2)/25).astype(int)
   for x in range(low[0],high[0]+1):
    for y in range(low[1],high[1]+1):self.ogrid[x,y].append(i)
 def add_legacy(self,rows):
  for r in rows:self.obs.append((np.array(r['min']),np.array(r['max']),r['object'],'legacy_lamp'))
  self.reindex()
 def corridor(self,p,h):
  ix=np.array(self.grid.get(tuple(np.floor(p[:2]/25).astype(int)),[]),int)
  if not len(ix):return True,99.,99.
  t=np.clip(np.sum((p[:2]-self.sa[ix,:2])*self.sd[ix,:2],axis=1)/self.sl[ix],0,1);q=self.sa[ix]+t[:,None]*self.sd[ix];edge=np.linalg.norm(p[:2]-q[:,:2],axis=1)-self.sw[ix];layers=(q[:,2]+np.where(self.sv[ix],4.7,2.5)>p[2])&(q[:,2]-.4<p[2]+h+.2);required=.19+np.where(self.sv[ix],.65,.45)
  return not np.any(layers&(edge<required-1e-6)),float(np.min(edge[layers&self.sv[ix]]-.19)) if np.any(layers&self.sv[ix]) else 99.,float(np.min(edge[layers&~self.sv[ix]]-.19)) if np.any(layers&~self.sv[ix]) else 99.
 @staticmethod
 def envelopes(p,h,arm):return [(p[:2],p[2],p[2]+h+.2,.39),((p[:2]+arm[:2])*.5,arm[2]-.25,arm[2]+.25,.35),(arm[:2],arm[2]-.25,arm[2]+.25,.5)]
 def obstacle(self,p,h,arm):
  nearest=99.
  for xy,zlo,zhi,rad in self.envelopes(p,h,arm):
   ix=np.array(self.ogrid.get(tuple(np.floor(xy/25).astype(int)),[]),int)
   if len(ix):
    layer=(self.oh[ix,2]>zlo+.08)&(self.ol[ix,2]<zhi);ds=np.linalg.norm(np.maximum(np.maximum(self.ol[ix,:2]-xy,xy-self.oh[ix,:2]),0),axis=1)
    if np.any(layer):nearest=min(nearest,float(ds[layer].min()-rad))
    if np.any(layer&(ds<rad)):return False,'obstacle:'+self.ok[ix[np.where(layer&(ds<rad))[0][0]]],nearest
   for c,half,yaw,name,extra in self.obbs:
    if c[2]+half[2]<zlo or c[2]-half[2]>zhi:continue
    d=xy-c[:2];co=math.cos(yaw);si=math.sin(yaw);local=np.array([co*d[0]+si*d[1],-si*d[0]+co*d[1]])
    if np.linalg.norm(np.maximum(np.abs(local)-half[:2],0))<rad+extra:return False,'obstacle:obb_or_door',nearest
   for poly,low,high,name in self.polys:
    if high<zlo or low>zhi or np.any(xy<poly.min(axis=0)-rad) or np.any(xy>poly.max(axis=0)+rad):continue
    if point_polygon(xy,poly) or polygon_distance(xy,poly)<rad:return False,'obstacle:polygon',nearest
  for o in self.water:
   if point_polygon(p[:2],np.array(o['polygon'])):return False,'water',nearest
  return True,None,nearest

def sample_route(r,spacing):
 p=r['points'];dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p[:,:2],axis=0),axis=1))];length=dist[-1]
 if length<6:return []
 n=max(1,int(math.ceil(length/spacing)));out=[]
 for s in (np.arange(n)+.5)*length/n:
  i=min(len(p)-2,max(0,int(np.searchsorted(dist,s)-1)));delta=p[i+1]-p[i];t=(s-dist[i])/max(1e-9,dist[i+1]-dist[i]);q=p[i]+t*delta;tan=delta[:2]/max(1e-9,np.linalg.norm(delta[:2]));out.append((q,tan,float(s),float(length/n)))
 return out

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--game-root',type=Path,required=True);parser.add_argument('--inventory',type=Path,required=True);parser.add_argument('--raw-dir',type=Path,required=True);parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args();root=args.output_root;start=time.time();reasons=Counter();evidence=[]
 for sub in ['contracts','qa']: (root/sub).mkdir(parents=True,exist_ok=True)
 paths=[args.game_root/'data/campus-navigation.json',args.game_root/'dist/world-config.js',args.game_root/'dist/transit-config.js',args.inventory]
 for p in paths:evidence.append({'path':str(p),'sha256':sha(p)})
 nav=read_json(paths[0]);world=read_js(paths[1]);transit=read_js(paths[2]);inv=read_json(paths[3]);assert inv['input_sha256']==SHA
 routes=[]
 for r in nav['roads']:
  vehicle=r.get('vehicle',r.get('type') not in ['footway','steps','path','pedestrian']);kind='road' if vehicle else 'stairs' if r.get('type')=='steps' else 'walk';routes.append(dict(id=r.get('name',r.get('id')),points=np.array(r['points']),width=float(r.get('width',3)),kind=kind,source='navigation.roads',vehicle=bool(vehicle)))
 for r in nav['pedestrianPaths']:
  kind='stairs' if any(x in r.get('kind','') for x in ['stair','step']) else 'walk';routes.append(dict(id=r['id'],points=np.array(r['points']),width=float(r.get('width',2)),kind=kind,source='navigation.pedestrianPaths',vehicle=False))
 for r in world['roads'][:2]:routes.append(dict(id=r['name'],points=np.array([blender_xyz(p) for p in r['points']]),width=float(r['width']),kind='road',source='WORLD.roads',vehicle=True))
 clear=Clearance(nav,world,inv,routes);del inv,world;gc.collect();jobs=[]
 for r in routes:
  if '1319139167' in str(r['id']):continue
  for q,tan,s,spacing in sample_route(r,29 if r['vehicle'] else 19):
   priority=1 if r['kind']=='stairs' else 3 if r['vehicle'] and r['width']>=7 else 4 if r['vehicle'] else 5;jobs.append(dict(kind=r['kind'],q=q,tan=tan,width=r['width'],source=r['source'],route=r['id'],chainage=s,spacing=spacing,priority=priority))
 for stop in transit['stops']+[s for s in transit.get('cityStops',[]) if s.get('waitingPosition')]:
  q=blender_xyz(stop['waitingPosition']);t=np.array(stop.get('travelTangent',[1,0]),float);t[1]*=-1;t/=max(np.linalg.norm(t),1e-9)
  for along in [0.,-3.,3.]:jobs.append(dict(kind='transit',q=q+np.r_[t*along,0],tan=t,width=3.,source='TRANSIT.stops',route=stop['id'],chainage=along,spacing=8.,priority=0))
 for name,lo,hi in clear.parking:
  for axis in [0,1]:
   length=hi[axis]-lo[axis]
   for s in np.linspace(0,length,max(2,int(math.ceil(length/29))+1))[1:-1]:
    for side in [0,1]:
     q=(lo+hi)/2;q[axis]=lo[axis]+s;q[1-axis]=[lo[1-axis]+4,hi[1-axis]-4][side];q[2]=hi[2];t=np.zeros(2);t[axis]=1;jobs.append(dict(kind='parking',q=q,tan=t,width=5.,source='native.parking_bounds_seeds',route=name,chainage=float(s),spacing=29.,priority=2))
 jobs.sort(key=lambda j:(j['priority'],j['route'],j['chainage']));staged=[]
 for job in jobs:
  q=job['q'];t=job['tan'];normal=np.array([-t[1],t[0]]);h=6.2 if job['kind'] in ['road','parking','transit'] else 4.2;opts=[]
  for shift in [0.,-3.,3.,-6.,6.]:
   target=q+np.r_[t*shift,0]
   for extra in [0.,.7,1.5]:
    for side in [1,-1]:
     offset=job['width']/2+.19+(.75 if job['kind'] in ['road','parking'] else .55)+extra;p=target+np.r_[side*normal*offset,0];arm=p+np.r_[-side*normal,h];ok,_,_=clear.corridor(p,h)
     if not ok:reasons['stage_corridor']+=1;continue
     ok,why,_=clear.obstacle(p,h,arm)
     if not ok:reasons['stage_'+why]+=1;continue
     opts.append((p.tolist(),target.tolist()))
   if len(opts)>=6:break
  if opts:staged.append((job,opts[:12]))
  else:reasons['job_no_safe_design_seed']+=1
 targeted=[];targeted_seeds=[]
 for stop in transit['stops']:
  if stop['id'] not in ['monument','engineering2','student_union']:continue
  q=blender_xyz(stop['waitingPosition']);opts=[];reject=Counter()
  for radius in [3.,4.,5.,6.,7.,8.]:
   for angle in np.arange(24)*math.pi/12:
    d=np.array([math.cos(angle),math.sin(angle)]);p=q+np.r_[d*radius,0];arm=p+np.r_[-d,6.2];ok,_,_=clear.corridor(p,6.2)
    if not ok:reject['finite_corridor_margin']+=1;continue
    ok,why,_=clear.obstacle(p,6.2,arm)
    if not ok:reject[why]+=1;continue
    opts.append((p.tolist(),q.tolist()))
  job=dict(kind='transit',q=q,tan=np.array([1.,0.]),width=3.,source='TRANSIT.stops.targeted_polar_base_search',route=stop['id'],chainage=0.,spacing=0.,priority=-1,targeted_stop=True);targeted_seeds.append({'stop_id':stop['id'],'seed_trials':144,'safe_design_seeds':len(opts),'seed_rejections':dict(reject)})
  if opts:targeted.append((job,opts))
 staged=targeted+staged;print(f'Stage 1: {len(jobs)} design seeds; {len(staged)} viable groups',flush=True);surfaces=SurfaceIndex(args.raw_dir,staged);clear.add_legacy(surfaces.legacy);evidence.extend(surfaces.evidence);fixtures=[];selected=[];counts=Counter();quota={'road':310,'walk':145,'stairs':35,'parking':60,'transit':20};outcomes=[];miss=[]
 for ji,(job,opts) in enumerate(staged):
  kind=job['kind'];h=6.2 if kind in ['road','parking','transit'] else 4.2;radius=9 if kind in ['road','parking','transit'] else 6
  if counts[kind]>=quota[kind]:reasons['kind_quota']+=1;continue
  q=job['q'];spacing=16 if kind in ['road','parking'] else 11
  if any(np.linalg.norm(q[:2]-s[:2])<spacing and abs(q[2]-s[2])<3 for s in selected):reasons['target_spacing']+=1;continue
  found=None;before=reasons.copy()
  for base0,target0 in opts:
   target=surfaces.ray(target0[:2],target0[2],1.1,2.5,True)
   if target is None:reasons['actual_target_no_paved_hit']+=1;continue
   base=surfaces.ray(base0[:2],target['position'][2],1.5,2.5)
   if base is None:reasons['actual_base_no_support']+=1;continue
   p=np.array(base['position']);q=np.array(target['position']);d=q[:2]-p[:2];d/=np.linalg.norm(d);lamp=p+np.r_[d,h]
   if base['normal'][2]<.85:reasons['actual_base_steep']+=1;continue
   ok,vr,wr=clear.corridor(p,h)
   if not ok:reasons['grounded_corridor']+=1;continue
   ok,why,margin=clear.obstacle(p,h,lamp)
   if not ok:reasons['grounded_'+why]+=1;continue
   if lamp[2]-q[2]<(4.8 if kind in ['road','parking'] else 3.95):reasons['head_vertical_clearance']+=1;continue
   ring=[];hits=[]
   for angle in np.arange(8)*math.pi/4:
    rp=p[:2]+.19*np.array([math.cos(angle),math.sin(angle)]);hit=surfaces.ray(rp,p[2],.25,.35)
    if hit is None:break
    delta=hit['position'][2]-p[2];ring.append(delta);hit.pop('raw_index');hits.append(dict(hit,signed_height_delta_m=float(delta)))
   if len(ring)<8 or max(abs(v) for v in ring)>.11:reasons['footing_ring_unsupported_or_steep']+=1;continue
   if any(np.linalg.norm(p[:2]-np.array(f['base_position'][:2]))<3 and abs(p[2]-f['base_position'][2])<h for f in fixtures):reasons['fixture_base_spacing']+=1;continue
   triangles,refs,removed=surfaces.patch(target,radius);area=sum(abs(np.cross(np.array(t[1])-t[0],np.array(t[2])-t[0])[2])*.5 for t in triangles)
   if area<3:reasons['patch_too_small']+=1;continue
   ident=f'{kind.upper()}_{counts[kind]+1:03d}';target.pop('raw_index');base.pop('raw_index');legacy_margin=99.
   for xy,zlo,zhi,rad in clear.envelopes(p,h,lamp):
    for r in surfaces.legacy:
     lo=np.array(r['min']);hi=np.array(r['max'])
     if hi[2]>zlo+.08 and lo[2]<zhi:legacy_margin=min(legacy_margin,float(np.linalg.norm(np.maximum(np.maximum(lo[:2]-xy,xy-hi[:2]),0))-rad))
   found=dict(id=ident,kind=kind,base_position=np.round(p,6).tolist(),lamp_position=np.round(lamp,6).tolist(),target_position=np.round(q,6).tolist(),color=[1,.63,.32],cct_kelvin=3000,power_watts=350 if kind in ['road','parking','transit'] else 160,pool_radius=radius,intensity=250 if kind in ['road','parking','transit'] else 160,fixture_object_names=['RV6_LIGHT_'+ident+'_fixture'],beam_object_name='RV6_LIGHT_'+ident+'_beam',base_ground_hit=base,footing_ground_hits=hits,ground_hit=target,ground_patch_triangles=triangles,ground_patch_provenance={'file':target['file'],'object':target['object'],'primitive':target['primitive'],'triangles':refs,'connectivity_quantization_m':.0001,'clipping':'inscribed regular 16-gon preserving raw triangle planes; 0.0001m rounded-vertex adjacency within same primitive and bounded height layer','removed_exact_degenerates':removed},collision={'pole_radius_m':.085,'pole_height_m':h,'base_radius_m':.19,'base_height_m':.18,'foundation_burial_m':.2},route_source={'source':job['source'],'id':job['route'],'chainage_m':job['chainage'],'design_spacing_m':job['spacing'],'position_accuracy':'INFERRED LIGHTING DESIGN; not surveyed real lamp positions'},clearance={'vehicle_corridor_from_base_edge_m':vr,'walk_corridor_from_base_edge_m':wr,'obstacle_envelope_margin_m':margin,'legacy_lamp_margin_beyond_collision_envelope_m':legacy_margin,'lamp_above_target_m':float(lamp[2]-q[2]),'footing_support_max_delta_m':max(abs(v) for v in ring),'ground_patch_area_m2':area});break
  if job.get('targeted_stop'):outcomes.append({'stop_id':job['route'],'safe_fixture_id':found['id'] if found else None,'grounded_trial_rejections':dict(reasons-before),'design_alternates':len(opts)})
  if found:fixtures.append(found);counts[kind]+=1;selected.append(np.array(found['target_position']))
  else:miss.append({'kind':kind,'route':job['route'],'target':job['q'].tolist()});reasons['job_no_grounded_safe_alternate']+=1
  if ji%100==0:print(f'Ground support {ji}/{len(staged)}: {dict(counts)}',flush=True)
 manifest={'schema_version':1,'revision_id':'street_lighting_v6','status':'PENDING_INDEPENDENT_AUDIT','source_native_sha256':SHA,'coordinate_system':'Blender Z-up metres; game maps [x,y,z] to [x,z,-y]','accuracy':'Inferred lighting design, not surveyed installations or certified photometry. Regenerated result, no prior-coordinate identity claim.','power_watts_semantics':'Blender radiant-power visual parameter, not electrical consumption or measured illuminance.','cct_kelvin_semantics':'3000 K design color target; RGB artistic approximation.','fixture_geometry':{'pole_radius_m':.085,'base_radius_m':.19,'base_height_m':.18,'foundation_burial_m':.2,'arm_length_m':1.,'road_parking_height_m':6.2,'transit_height_m':6.2,'walk_stair_height_m':4.2,'emissive_material':'RV6_StreetLight_Emissive_Warm3000K'},'fixtures':fixtures,'evidence':evidence}
 report={'status':'PASS_PLACEMENT_PENDING_RAW_AUDIT','source_native_sha256':SHA,'fixtures':len(fixtures),'counts_by_kind':dict(counts),'staged_target_count':len(staged),'design_seed_count':len(jobs),'screened_corridor_segment_count':len(clear.sa),'native_obstacle_counts':dict(clear.inventory_counts),'raw_support_triangles_retained':len(surfaces.t),'legacy_lamp_local_bounds':surfaces.legacy,'legacy_lamp_local_bounds_count':len(surfaces.legacy),'skipped_reasons':dict(reasons),'targeted_stop_seed_search':targeted_seeds,'targeted_stop_grounded_outcomes':outcomes,'excluded_unverified_way_seeds':['1319139167'],'unplaced_targets':miss,'elapsed_seconds':time.time()-start,'max_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'script_sha256':sha(Path(__file__)),'core_script_sha256':sha(Path(__file__).with_name('lighting_core.py'))}
 assert len(fixtures)<=600 and report['max_rss_mib']<600
 (root/'contracts/street_lighting_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n');(root/'qa/placement_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n');print(json.dumps({k:report[k] for k in ['status','fixtures','counts_by_kind','max_rss_mib']}),flush=True)
if __name__=='__main__':main()
