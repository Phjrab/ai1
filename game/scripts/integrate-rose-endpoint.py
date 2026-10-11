"""Use the final finite rose paving repair; keep other paths and layers intact."""
import argparse,copy,hashlib,importlib.util,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
KEY='realism_v2/final_rose_endpoint_join/rose_endpoint_paving_runtime.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cv(p):return[p[0],p[2],-p[1]]
def unc(p):return[p[0],-p[2],p[1]]
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')
def plane(t):
 a,b,c=t;u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
 assert abs(n[2])>1e-12,'Vertical source paving';x,y=-n[0]/n[2],-n[1]/n[2];return[x,y,a[2]-x*a[0]-y*a[1]]
def height(t,p):
 a,b,c=t;x,y=p[:2];d=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
 if abs(d)<1e-12:return None
 if any(p[k]<min(q[k] for q in t)-1e-7 or p[k]>max(q[k] for q in t)+1e-7 for k in [0,1]):return None
 u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/d;v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/d
 if min(u,v,1-u-v)<-1e-9:return None
 return u*a[2]+v*b[2]+(1-u-v)*c[2]
def clip_surfaces(surfaces,old,is_world,clip):
 masks=[(t,plane(t)) for t in old];out=[];changed=[]
 for sf in surfaces:
  poly=[unc(p) for p in sf['polygon']] if is_world else sf['polygon'];parts=[[poly[i] for i in f] for f in sf['triangles']];removed=0
  for t,pl in masks:
   if any(max(p[k] for p in poly)<min(p[k] for p in t)-1e-9 or min(p[k] for p in poly)>max(p[k] for p in t)+1e-9 for k in [0,1]):continue
   upper=[pl[0],pl[1],pl[2]+.001];lower=[pl[0],pl[1],pl[2]-.001];next_parts=[]
   for part in parts:
    pieces,cut=clip.retire_triangle(part,t,upper,lower);next_parts.extend(pieces);removed+=cut
   parts=next_parts
  if not removed:out.append(sf);continue
  points=[];faces=[]
  for part in parts:
   start=len(points);points.extend(part)
   for j in range(1,len(part)-1):
    if clip.area([part[0],part[j],part[j+1]])>1e-10:faces.append([start,start+j,start+j+1])
  if faces:out.append({**sf,'polygon':[cv(p) for p in points] if is_world else points,'triangles':faces})
  changed.append({'id':sf['id'],'removedProjectedAreaM2':removed,'beforeTriangles':len(sf['triangles']),'afterTriangles':len(faces)})
 return out,changed

def apply(root,source):
 data=json.loads(source.read_text());manifest=json.loads((root/'data/native-export-manifest.json').read_text());bound=manifest['sidecar_sha256'];source_sha=sha(source)
 assert bound.get(KEY)==source_sha and 'realism_v2/rose_endpoint_paving.py' in manifest['module_sha256'],'Rose source is not bound to native'
 assert data['schema']=='rose-endpoint-paving-runtime-1' and data['source_object']=='RV2_PS_rose_paths_and_circular_plaza'
 original=data['source_navigation'];assert bound.get(original['path'])==original['sha256'],'Source public path binding differs'
 old=data['removed_source_triangles'];new=data['replacement_triangles'];assert len(old)==18 and len(new)==200
 assert all(len(t)==3 and all(len(p)==3 and all(math.isfinite(v) for v in p) for p in t) for t in old+new)
 spec=importlib.util.spec_from_file_location('finite_clip',ROOT/'scripts/integrate-lower-paving-retirement.py');clip=importlib.util.module_from_spec(spec);spec.loader.exec_module(clip)
 source_route=original['public_rose_spine'];assert source_route['id']=='public_rose_spine';replacement=copy.deepcopy(source_route);samples=[]
 for i,p in enumerate(source_route['points']):
  if not any(height(t,p) is not None for t in old):continue
  heights=[z for t in new if (z:=height(t,p)) is not None];assert heights,'New finite paving does not cover original route point'
  z=max(heights);replacement['points'][i]=[p[0],p[1],z];samples.append({'index':i,'before':p,'position':replacement['points'][i]})
 assert samples and max(math.dist(x['before'][:2],x['position'][:2]) for x in samples)==0
 wp=root/'dist/world-config.js';text=wp.read_text();world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'));np=root/'data/campus-navigation.json';nav=json.loads(np.read_text());changes={}
 for target,is_world,label in [(world,True,'world'),(nav,False,'navigation')]:
  paths=[p for p in target['pedestrianPaths'] if p['id']=='public_rose_spine'];assert len(paths)==1
  expected=[cv(p) for p in source_route['points']] if is_world else source_route['points'];updated=[cv(p) for p in replacement['points']] if is_world else replacement['points'];assert paths[0]['points'] in [expected,updated],'Rose source path changed'
  paths[0]['points']=updated;paths[0]['roseEndpointSourceSha256']=source_sha
  target['walkableSurfaces'],changes[label]=clip_surfaces(target['walkableSurfaces'],old,is_world,clip)
 report={'sourceSha256':source_sha,'sourceNavigationSha256':original['sha256'],'replacedPathPointCount':len(samples),'pathPointUpdates':samples,'clippedCachedSupports':changes,'retirementHeightToleranceMeters':.001,'geometryModified':False,'XYAndOutsidePathPreserved':True,'newSupportPolicy':'Actual exported paving triangles supply runtime floors; no synthetic replacement floor is introduced.'}
 wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n');write(np,nav);write(root/'data/rose-endpoint-navigation.json',data);write(root/'data/rose-endpoint-sync-report.json',report);return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(apply(a.root,a.source)))
