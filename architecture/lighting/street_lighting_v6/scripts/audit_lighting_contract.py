"""Recovered independent finite-triangle audit and noncircular freeze writer.
Does not instantiate Blender or claim identity with the pre-reset 536-placement file.
"""
import argparse,gc,json,resource,time
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from lighting_core import GLB,sha,read_json,read_js,blender_xyz

def bary(points,tri):
 a=tri[:,0];b=tri[:,1]-a;c=tri[:,2]-a;q=points-a;den=b[:,0]*c[:,1]-b[:,1]*c[:,0];u=(q[:,0]*c[:,1]-q[:,1]*c[:,0])/den;v=(b[:,0]*q[:,1]-b[:,1]*q[:,0])/den;z=a[:,2]+u*b[:,2]+v*c[:,2];return u,v,abs(z-points[:,2])
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output-root',required=True,type=Path);ap.add_argument('--raw-dir',required=True,type=Path);ap.add_argument('--inventory',required=True,type=Path);ap.add_argument('--game-root',required=True,type=Path);a=ap.parse_args();root=a.output_root;t0=time.time();p=root/'contracts/street_lighting_manifest.json';m=read_json(p);f=m['fixtures'];assert f,'No fixtures';groups=defaultdict(list);removed=[]
 for fi,row in enumerate(f):
  kept=[];refs=[];pr=row['ground_patch_provenance']
  for ti,(triangle,ref) in enumerate(zip(row['ground_patch_triangles'],pr['triangles'])):
   ts=np.array(triangle)
   if np.linalg.norm(np.cross(ts[1]-ts[0],ts[2]-ts[0]))==0:removed.append({'fixture_id':row['id'],'original_patch_index':ti,'object':pr['object'],'primitive':pr['primitive'],'triangle':ref['source_triangle']});continue
   kept.append(triangle);refs.append(ref)
  row['ground_patch_triangles']=kept;pr['triangles']=refs
  for key in ['base_ground_hit','ground_hit']:
   h=row[key];groups[h['file'],h['object'],h['primitive']].append(('ray',fi,key,h['triangle']))
  for ri,h in enumerate(row['footing_ground_hits']):groups[h['file'],h['object'],h['primitive']].append(('footing',fi,ri,h['triangle']))
  for ti,ref in enumerate(pr['triangles']):groups[pr['file'],pr['object'],pr['primitive']].append(('patch',fi,ti,ref['source_triangle']))
  assert len(row['footing_ground_hits'])==8
  for h in row['footing_ground_hits']:assert abs(h['signed_height_delta_m'])<=.11+1e-9
 max_plane=0.;max_boundary=0.;rays=0;patches=0
 for filename in sorted(set(k[0] for k in groups)):
  g=GLB(a.raw_dir/filename);lookup={n.get('name'):i for i,n in enumerate(g.d['nodes'])}
  for (fn,obj,primitive),entries in groups.items():
   if fn!=filename:continue
   ids=np.array(sorted(set(x[3] for x in entries)),int);raw=g.triangles(lookup[obj],primitive,ids)
   for first in range(0,len(entries),20000):
    pts=[];tris=[]
    for kind,fi,key,tid in entries[first:first+20000]:
     tri=raw[np.searchsorted(ids,tid)]
     if kind=='patch':pts.extend(f[fi]['ground_patch_triangles'][key]);tris.extend([tri]*3);patches+=1
     else:pts.append(f[fi][key]['position'] if kind=='ray' else f[fi]['footing_ground_hits'][key]['position']);tris.append(tri);rays+=1
    tris=np.array(tris);u,v,dz=bary(np.array(pts),tris);b=tris[:,1,:2]-tris[:,0,:2];c=tris[:,2,:2]-tris[:,0,:2];den=abs(b[:,0]*c[:,1]-b[:,1]*c[:,0]);outside=np.maximum.reduce([-u*den/np.maximum(np.linalg.norm(c,axis=1),1e-20),-v*den/np.maximum(np.linalg.norm(b,axis=1),1e-20),(u+v-1)*den/np.maximum(np.linalg.norm(c-b,axis=1),1e-20),np.zeros(len(u))]);max_boundary=max(max_boundary,float(outside.max()));max_plane=max(max_plane,float(dz.max()));assert np.isfinite(dz).all() and np.isfinite(outside).all()
   del raw;g.discard_pages()
  g.close();gc.collect()
 assert max_plane<.0001 and max_boundary<.0001,(max_plane,max_boundary)
 bases=np.array([x['base_position'] for x in f]);targets=np.array([x['target_position'] for x in f]);dist=np.linalg.norm(bases[:,None,:2]-bases[None,:,:2],axis=2);np.fill_diagonal(dist,np.inf);dist[abs(bases[:,None,2]-bases[None,:,2])>=6.2]=np.inf;minimum=float(dist.min());assert minimum>=3
 inv=read_json(a.inventory);assert inv['input_sha256']==m['source_native_sha256'];garage=[]
 for name,o in inv['objects'].items():
  if o.get('render_visible_in_scene') and 'bounds_min' in o and any('CAMPUS_BUILDING 164' in c for c in o.get('collections',[])):garage.append((o['bounds_min'],o['bounds_max']))
 assert garage,'Garage envelope missing from inventory';low=np.min([v[0] for v in garage],axis=0);high=np.max([v[1] for v in garage],axis=0);inside=np.all((bases[:,:2]>=low[:2]-.39)&(bases[:,:2]<=high[:2]+.39),axis=1);assert not inside.any(),[f[i]['id'] for i in np.flatnonzero(inside)];del inv;gc.collect()
 spacing={}
 for kind in sorted(set(x['kind'] for x in f)):
  ids=np.array([i for i,row in enumerate(f) if row['kind']==kind]);d=np.linalg.norm(targets[ids,None,:2]-targets[None,:,:2],axis=2);d[np.arange(len(ids)),ids]=np.inf;d[abs(targets[ids,None,2]-targets[None,:,2])>3]=np.inf;n=d.min(axis=1);finite=n[np.isfinite(n)];spacing[kind]={'count':len(ids),'nearest_target_min_m':float(finite.min()) if len(finite) else None,'nearest_target_median_m':float(np.median(finite)) if len(finite) else None,'nearest_target_max_m':float(finite.max()) if len(finite) else None,'without_neighbor_in_3m_height_layer':int(np.sum(~np.isfinite(n)))}
 transit=read_js(a.game_root/'dist/transit-config.js');coverage=[]
 for stop in transit['stops']+[s for s in transit.get('cityStops',[]) if s.get('waitingPosition')]:
  q=blender_xyz(stop['waitingPosition']);covered=[];radial=[]
  for row in f:
   if np.linalg.norm(q[:2]-np.array(row['target_position'][:2]))>row['pool_radius']+.001 or abs(q[2]-row['target_position'][2])>3:continue
   radial.append(row['id']);ts=np.array(row['ground_patch_triangles']);u,v,dz=bary(np.broadcast_to(q,(len(ts),3)),ts)
   if np.any((u>=-1e-5)&(v>=-1e-5)&(u+v<=1+1e-5)&(dz<.16)):covered.append(row['id'])
  ds=np.linalg.norm(bases[:,:2]-q[:2],axis=1);ds[abs(bases[:,2]-q[2])>3]=np.inf;near=int(ds.argmin());coverage.append({'stop_id':stop['id'],'waiting_position':q.tolist(),'covered_by_actual_ground_patch':covered,'inside_nominal_pool_radius':radial,'nearest_fixture':f[near]['id'] if np.isfinite(ds[near]) else None,'nearest_fixture_base_distance_m':float(ds[near]) if np.isfinite(ds[near]) else None,'status':'covered_actual_finite_surface' if covered else 'nearby_lighting_only_no_exact_waiting_point_patch'})
 m['coverage']={'transit_stops':coverage,'metadata_only_stops_excluded':[s['id'] for s in transit.get('cityStops',[]) if not s.get('waitingPosition')],'meaning':'Finite patch hit at waiting point is coverage. Nominal radius alone is not coverage. This is design/game geometry, not certified illuminance.'};m['status']='PASS';m['qa_reports']=[{'path':'qa/placement_report.json'},{'path':'qa/final_placement_audit.json'}]
 report={'status':'PASS','fixture_count':len(f),'counts_by_kind':dict(Counter(x['kind'] for x in f)),'raw_finite_ray_supports_checked':rays,'raw_finite_patch_triangles_checked':patches,'footing_rays':sum(len(x['footing_ground_hits']) for x in f),'maximum_original_triangle_plane_error_m':max_plane,'maximum_finite_triangle_boundary_error_m':max_boundary,'finite_triangle_tolerance_m':.0001,'minimum_new_base_separation_m':minimum,'nearest_target_spacing':spacing,'removed_exact_degenerates_during_audit':removed,'removed_exact_degenerates_during_generation':sum(len(x['ground_patch_provenance'].get('removed_exact_degenerates',[])) for x in f),'garage_audit':{'min':low.tolist(),'max':high.tolist(),'expanded_xy_margin_m':.39,'fixtures_inside':0,'policy':'All poles outside garage footprint envelope; no parking164 roof or indoor support surfaces selected.'},'transit_coverage':coverage,'covered_waiting_points':sum(bool(c['covered_by_actual_ground_patch']) for c in coverage),'modeled_waiting_points':len(coverage),'excluded_way_seeds':['1319139167'],'elapsed_seconds':time.time()-t0,'max_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'script_sha256':sha(Path(__file__)),'limits':['Reconstructed algorithm rerun; original pre-reset manifest coordinates were not available for identity comparison.','Fixture/object visual and final game QA are separate.']}
 assert report['max_rss_mib']<600
 out=root/'qa/final_placement_audit.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n');p.write_text(json.dumps(m,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n');freeze={'status':'PASS','revision_id':'street_lighting_v6','source_native_sha256':m['source_native_sha256'],'manifest':{'path':'contracts/street_lighting_manifest.json','sha256':sha(p)},'reports':[{'path':'qa/'+n,'sha256':sha(root/'qa'/n)} for n in ['placement_report.json','final_placement_audit.json']],'scripts':[{'path':'scripts/'+n,'sha256':sha(root/'scripts'/n)} for n in ['lighting_core.py','plan_street_lighting.py','audit_lighting_contract.py']],'fixture_count':len(f),'recovery_status':'REGENERATED_AND_AUDITED_NOT_PRIOR_MANIFEST_IDENTITY'};(root/'qa/placement_freeze.json').write_text(json.dumps(freeze,indent=2,allow_nan=False)+'\n');print(json.dumps({'status':'PASS','manifest_sha256':sha(p),'fixture_count':len(f),'covered_waiting_points':report['covered_waiting_points'],'max_rss_mib':report['max_rss_mib']}),flush=True)
if __name__=='__main__':main()
