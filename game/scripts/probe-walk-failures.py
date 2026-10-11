"""Bounded raw-GLB triangle diagnostics for recorded runtime path failures."""
import json, pathlib, mmap, struct, hashlib, resource, time
import numpy as np
root=pathlib.Path(__file__).resolve().parents[1]
import os
raw=pathlib.Path(os.environ['CHOSUN_REALISM_ROOT'])/'game_export/campus.glb'
source=pathlib.Path(os.environ.get('CHOSUN_WALK_PROBE_SOURCE',root/'tests/walkable-failure-classification.json')); d=json.loads(source.read_text());rows=[]
for group in d['groups']:
 for outcome in group['outcomes']:rows.append({'id':group['id'],'direction':outcome['type'],'point':outcome['failed']['position'],'target':outcome['failed']['target']})
f=raw.open('rb');mem=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ);jn=struct.unpack_from('<I',mem,12)[0];doc=json.loads(mem[20:20+jn]);binary=28+jn
DT={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'};DM={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}
def acc(i):
 a=doc['accessors'][i];b=doc['bufferViews'][a['bufferView']];dt=np.dtype(DT[a['componentType']]);dm=DM[a['type']]
 return np.ndarray((a['count'],dm),dtype=dt,buffer=mem,offset=binary+b.get('byteOffset',0)+a.get('byteOffset',0),strides=(b.get('byteStride',dt.itemsize*dm),dt.itemsize))
parents={c:i for i,n in enumerate(doc['nodes']) for c in n.get('children',[])};matrices={};extras={}
def matrix(i):
 if i in matrices:return matrices[i]
 n=doc['nodes'][i]
 if 'matrix' in n:m=np.array(n['matrix']).reshape(4,4).T
 else:
  x,y,z,w=n.get('rotation',[0,0,0,1]);m=np.eye(4);m[:3,:3]=np.array([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],[2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],[2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]])@np.diag(n.get('scale',[1]*3));m[:3,3]=n.get('translation',[0]*3)
 if i in parents:m=matrix(parents[i])@m
 matrices[i]=m;return m
def extra(i):
 if i not in extras:extras[i]={**(extra(parents[i]) if i in parents else {}),**doc['nodes'][i].get('extras',{})}
 return extras[i]
points=np.array([r['point'] for r in rows]);lower=points-np.array([1.5,3,1.5]);upper=points+np.array([1.5,3.2,1.5]);triangles=[[] for r in rows];names=[[] for r in rows]
began=time.monotonic()
for i,n in enumerate(doc['nodes']):
 e=extra(i)
 if 'mesh' not in n or e.get('collision') is False or e.get('visual_only') or e.get('RV2_replaced_by_architecture'):continue
 m=matrix(i);name=n.get('name','')
 for primitive in doc['meshes'][n['mesh']]['primitives']:
  if primitive.get('mode',4)!=4:continue
  a=doc['accessors'][primitive['attributes']['POSITION']];lo=a['min'];hi=a['max'];corners=np.array([[x,y,z,1] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])@m.T
  cand=np.where(np.all(upper>=corners[:,:3].min(axis=0),axis=1)&np.all(lower<=corners[:,:3].max(axis=0),axis=1))[0]
  if not len(cand):continue
  positions=acc(primitive['attributes']['POSITION']);indices=acc(primitive['indices']).reshape(-1,3) if 'indices' in primitive else np.arange(len(positions)).reshape(-1,3)
  for start in range(0,len(indices),8192):
   t=positions[indices[start:start+8192]].astype(float)@m[:3,:3].T+m[:3,3];tl=t.min(axis=1);th=t.max(axis=1)
   for ri in cand:
    select=np.all(th>=lower[ri],axis=1)&np.all(tl<=upper[ri],axis=1)
    if select.any():triangles[ri].extend(t[select]);names[ri].extend([name]*int(select.sum()))
def raycast(ts,o):
 if not len(ts):return []
 t=np.array(ts);d=np.array([0,-1,0]);e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];h=np.cross(d,e2);det=(e1*h).sum(axis=1);good=np.abs(det)>1e-10;inv=np.divide(1.,det,out=np.zeros_like(det),where=good);s=o-t[:,0];u=(s*h).sum(axis=1)*inv;q=np.cross(s,e1);v=(q*d).sum(axis=1)*inv;dist=(e2*q).sum(axis=1)*inv;good&=(u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)&(dist>=0)&(dist<8)
 return [(int(ix),float(dist[ix])) for ix in np.where(good)[0][np.argsort(dist[good])]][:8]
def sphere_nearest(ts,point):
 t=np.array(ts);a,b,c=t[:,0],t[:,1],t[:,2];ab=b-a;ac=c-a;n=np.cross(ab,ac);ns=(n*n).sum(axis=1);height=np.divide(((point-a)*n).sum(axis=1),ns,out=np.zeros(len(t)),where=ns>1e-14);projected=point-height[:,None]*n
 d00=(ab*ab).sum(axis=1);d01=(ab*ac).sum(axis=1);d11=(ac*ac).sum(axis=1);v2=projected-a;d20=(v2*ab).sum(axis=1);d21=(v2*ac).sum(axis=1);den=d00*d11-d01*d01;v=np.divide(d11*d20-d01*d21,den,out=np.zeros(len(t)),where=np.abs(den)>1e-14);w=np.divide(d00*d21-d01*d20,den,out=np.zeros(len(t)),where=np.abs(den)>1e-14);inside=(v>=0)&(w>=0)&(v+w<=1)&(ns>1e-14)
 dist=np.full(len(t),np.inf);dist[inside]=np.linalg.norm(projected[inside]-point,axis=1)
 for pa,pb in [(a,b),(b,c),(c,a)]:
  edge=pb-pa;dot=(edge*edge).sum(axis=1);frac=np.clip(np.divide(((point-pa)*edge).sum(axis=1),dot,out=np.zeros(len(t)),where=dot>1e-14),0,1);dist=np.minimum(dist,np.linalg.norm(pa+frac[:,None]*edge-point,axis=1))
 normals=np.divide(n,np.sqrt(ns)[:,None],out=np.zeros_like(n),where=ns[:,None]>1e-14);return [(int(i),float(dist[i]),normals[i].tolist()) for i in np.where(dist<.37)[0][np.argsort(dist[dist<.37])]][:12]
for ri,r in enumerate(rows):
 t=triangles[ri];p=points[ri];r['localTriangles']=len(t);r['floorHits']=[{'object':names[ri][i],'height':float(p[1]+.55-distance)} for i,distance in raycast(t,p+[0,.55,0])];r['higherFloorHits']=[{'object':names[ri][i],'height':float(p[1]+3-distance)} for i,distance in raycast(t,p+[0,3,0])];r['bodyContacts']=[]
 for height in [.65,1.3]:
  for i,distance,normal in sphere_nearest(t,p+[0,height,0]):r['bodyContacts'].append({'bodyHeight':height,'object':names[ri][i],'distance':distance,'normal':normal,'triangle':np.array(t[i]).tolist()})
result={'nativeSourceSha256':d['nativeSourceSha256'],'rawGLBPath':str(raw),'sourceReportSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'rows':rows,'elapsedSeconds':time.monotonic()-began,'maxRSS_MB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'method':'Actual raw GLB triangles in bounded neighborhoods. Diagnostic two-sided rays and capsule-near triangles; final runtime eligibility/combined collision response must still be cross-checked.'}
pathlib.Path(os.environ.get('CHOSUN_WALK_PROBE_OUTPUT',root/'tests/walkable-local-triangle-probes.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({**result,'rows':[{'id':r['id'],'direction':r['direction'],'floorHits':r['floorHits'][:2],'bodyObjects':list(dict.fromkeys(h['object'] for h in r['bodyContacts']))} for r in rows]},indent=2))
