"""Independent scoped raw support check. Reads recorded faces, never a global scene index."""
import gc,hashlib,json,mmap,resource,struct,time
from collections import defaultdict
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1]
RAW=R.parent/'inputs/raw_glb'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

class RawFile:
 def __init__(self,path):
  self.file=path.open('rb');self.mem=mmap.mmap(self.file.fileno(),0,access=mmap.ACCESS_READ)
  assert self.mem[:4]==b'glTF'
  size,kind=struct.unpack_from('<II',self.mem,12);assert kind==0x4e4f534a
  self.data=json.loads(self.mem[20:20+size]);self.start=28+size
  self.parents={c:i for i,o in enumerate(self.data['nodes']) for c in o.get('children',[])}
  self.matrix_cache={};self.names={n.get('name'):i for i,n in enumerate(self.data['nodes'])}
 def matrix(self,i):
  if i in self.matrix_cache:return self.matrix_cache[i]
  n=self.data['nodes'][i]
  if 'matrix' in n:m=np.array(n['matrix'],float).reshape(4,4,order='F')
  else:
   x,y,z,w=n.get('rotation',[0,0,0,1]);m=np.eye(4)
   m[:3,:3]=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])@np.diag(n.get('scale',[1,1,1]))
   m[:3,3]=n.get('translation',[0,0,0])
  if i in self.parents:m=self.matrix(self.parents[i])@m
  self.matrix_cache[i]=m;return m
 def accessor(self,i):
  a=self.data['accessors'][i];assert 'sparse' not in a
  b=self.data['bufferViews'][a['bufferView']]
  dt=np.dtype({5121:'u1',5123:'<u2',5125:'<u4',5126:'<f4'}[a['componentType']])
  count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
  return np.ndarray((a['count'],count),dtype=dt,buffer=self.mem,offset=self.start+b.get('byteOffset',0)+a.get('byteOffset',0),strides=(b.get('byteStride',count*dt.itemsize),dt.itemsize))
 def triangles(self,name,primitive,ids):
  n=self.names[name];p=self.data['meshes'][self.data['nodes'][n]['mesh']]['primitives'][primitive]
  assert p.get('mode',4)==4
  pos=self.accessor(p['attributes']['POSITION']);idx=self.accessor(p['indices']).reshape(-1,3)
  points=pos[idx[ids]].astype(float);transform=self.matrix(n)
  points=points@transform[:3,:3].T+transform[:3,3]
  # glTF Y-up -> original Blender Z-up.
  points=points[:,:,[0,2,1]];points[:,:,1]*=-1
  material=self.data['materials'][p['material']]['name']
  return points,material
 def close(self):self.mem.close();self.file.close()

t0=time.monotonic();mp=R/'contracts/street_lighting_manifest.json';manifest_sha=sha(mp)
m=json.loads(mp.read_text());native=m['source_native_sha256'];assert m['status']=='PASS'
count=len(m['fixtures']);groups=defaultdict(list)
for f in m['fixtures']:
 for role,h in [('base',f['base_ground_hit']),('target',f['ground_hit'])]+[(f'footing_{i}',h) for i,h in enumerate(f['footing_ground_hits'])]:
  groups[h['file'],h['object'],h['primitive']].append({'fixture':f['id'],'role':role,'triangle':h['triangle'],'point':h['position'],'material':h['material'],'origin':h['ray_origin'],'direction':h['ray_direction'],'ray_max':h['ray_max_distance']})
expected_raw={Path(e['path']).name:e['sha256'] for e in m['evidence'] if e['path'].endswith('.glb')}
del m;gc.collect()
maximum_plane=0.;maximum_distance=0.;tested=0;worst=[];objects=set();raw_records=[]
for filename in sorted({key[0] for key in groups}):
 path=RAW/filename;assert sha(path)==expected_raw[filename]
 raw_records.append({'path':str(path),'sha256':expected_raw[filename]})
 g=RawFile(path)
 for (fn,name,primitive),rows in groups.items():
  if fn!=filename:continue
  ids=np.array([r['triangle'] for r in rows]);tri,material=g.triangles(name,primitive,ids)
  points=np.array([r['point'] for r in rows]);a=tri[:,0];e1=tri[:,1]-a;e2=tri[:,2]-a
  normal=np.cross(e1,e2);length=np.linalg.norm(normal,axis=1);assert np.all(length>0)
  normal/=length[:,None];signed=np.einsum('ij,ij->i',points-a,normal);plane=np.abs(signed)
  projected=points-signed[:,None]*normal
  inside=np.ones(len(rows),bool);edge_dist=[]
  for k in range(3):
   start=tri[:,k];end=tri[:,(k+1)%3];edge=end-start
   inside &= np.einsum('ij,ij->i',np.cross(edge,projected-start),normal)>=0
   denominator=np.einsum('ij,ij->i',edge,edge)
   u=np.divide(np.einsum('ij,ij->i',points-start,edge),denominator,out=np.zeros(len(rows)),where=denominator>0)
   closest=start+np.clip(u,0,1)[:,None]*edge
   edge_dist.append(np.linalg.norm(points-closest,axis=1))
  distance=np.where(inside,plane,np.min(edge_dist,axis=0))
  assert np.all(distance<=.0001),(name,float(distance.max()))
  for i,row in enumerate(rows):
   assert row['material']==material and row['direction']==[0,0,-1]
   assert np.linalg.norm(np.array(row['origin'][:2])-points[i,:2])<1e-8
   ray_t=row['origin'][2]-points[i,2]
   assert -.000001<=ray_t<=row['ray_max']+.000001
   worst.append({'fixture':row['fixture'],'role':row['role'],'object':name,'primitive':primitive,'triangle':row['triangle'],'point':row['point'],'finite_triangle_distance_m':float(distance[i]),'plane_error_m':float(plane[i])})
  maximum_plane=max(maximum_plane,float(plane.max()));maximum_distance=max(maximum_distance,float(distance.max()));tested+=len(rows);objects.add(name)
 g.close();gc.collect()
assert tested==count*10==5360
report={'status':'PASS_RECORDED_FINITE_SUPPORT','source_native_sha256':native,'placement_manifest':{'path':str(mp),'sha256':manifest_sha},'scope':'Independently decoded original raw GLB transforms/accessors and tested the5360 recorded base/target/footing points against their exact finite source triangles. No global support index, native load, Node, or geometry mutation.',
 'fixture_count':count,'actual_support_points':tested,'source_objects':len(objects),'maximum_plane_error_m':maximum_plane,'maximum_finite_triangle_distance_m':maximum_distance,'physical_tolerance_m':.0001,'worst_ten':sorted(worst,key=lambda x:x['finite_triangle_distance_m'],reverse=True)[:10],
 'raw_files':raw_records,'elapsed_seconds':time.monotonic()-t0,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'script_sha256':sha(Path(__file__)),
 'limits':['This proves each recorded support point belongs to the named original finite surface. It does not perform a global ray search for all possible intervening layers or a full traversal simulation.','The reconstructed placement is bound to its new hash; no prior coordinate identity is claimed.']}
(R/'qa/independent_recorded_support.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','actual_support_points','maximum_finite_triangle_distance_m','elapsed_seconds','peak_rss_mib']}))
