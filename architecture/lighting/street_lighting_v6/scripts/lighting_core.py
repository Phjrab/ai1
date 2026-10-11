"""Recovered read-only geometry core. No Blender, no node, no new dependencies."""
import gc,hashlib,json,math,mmap,struct
from collections import defaultdict
from pathlib import Path
import numpy as np

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read_json(path):return json.loads(Path(path).read_text())
def read_js(path):
 s=Path(path).read_text();return json.JSONDecoder().raw_decode(s[s.index('{'):])[0]
def blender_xyz(p):return np.array([p[0],-p[2],p[1]],float)
def point_polygon(p,poly):
 inside=False
 for a,b in zip(poly,np.roll(poly,1,axis=0)):
  if ((a[1]>p[1])!=(b[1]>p[1])) and p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:inside=not inside
 return inside
def polygon_distance(p,poly):
 a=poly;b=np.roll(poly,-1,axis=0);d=b-a;t=np.clip(np.sum((p-a)*d,axis=1)/np.maximum(1e-12,np.sum(d*d,axis=1)),0,1)
 return float(np.linalg.norm(a+t[:,None]*d-p,axis=1).min())
class GLB:
 def __init__(self,path):
  self.path=Path(path);self.file=self.path.open('rb');self.mm=mmap.mmap(self.file.fileno(),0,access=mmap.ACCESS_READ);sz=struct.unpack_from('<I',self.mm,12)[0];self.d=json.loads(self.mm[20:20+sz]);self.off=20+sz+8;self.parents={c:i for i,n in enumerate(self.d['nodes']) for c in n.get('children',[])};self.ms={}
 def mat(self,i):
  if i in self.ms:return self.ms[i]
  n=self.d['nodes'][i]
  if 'matrix' in n:m=np.array(n['matrix']).reshape(4,4).T
  else:
   x,y,z,w=n.get('rotation',[0,0,0,1]);m=np.eye(4);m[:3,:3]=np.array([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],[2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],[2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]])@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0])
  if i in self.parents:m=self.mat(self.parents[i])@m
  self.ms[i]=m;return m
 def accessor(self,i):
  a=self.d['accessors'][i];v=self.d['bufferViews'][a['bufferView']];dt=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]);n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
  return np.ndarray((a['count'],n),dtype=dt,buffer=self.mm,offset=self.off+v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',dt.itemsize*n),dt.itemsize))
 def triangles(self,ni,pi,ids=None):
  pr=self.d['meshes'][self.d['nodes'][ni]['mesh']]['primitives'][pi];v=self.accessor(pr['attributes']['POSITION']);ix=self.accessor(pr['indices']).reshape(-1,3) if 'indices' in pr else np.arange(len(v)).reshape(-1,3)
  if ids is not None:ix=ix[ids]
  t=v[ix].astype(float);m=self.mat(ni);t=t@m[:3,:3].T+m[:3,3];t=t[:,:,[0,2,1]];t[:,:,1]*=-1;return t
 def discard_pages(self):
  try:self.mm.madvise(mmap.MADV_DONTNEED)
  except (AttributeError,OSError):pass
 def close(self):self.mm.close();self.file.close()

def surface_class(name,material):
 n=name.lower();m=material.lower()
 if any(x in n for x in ['paint','marking','curb','closure','rail','lamp','retaining','roof','interior','parking164','canopy','court','pitch','bay line']):return None
 if any(x in m for x in ['road paint','faded road','yellow road','white','metal','steel','wood','shadow','window','memorial']):return None
 if 'terrain' in n and any(x in m for x in ['grass','terrain','apron']):return 'terrain'
 if 'asphalt' in m:return 'paving'
 if any(x in n for x in ['paving','tread','landing','apron','paths','walk','steps','stair','approach','threshold','pedestrian','plaza','bridge solid']) and any(x in m for x in ['granite','concrete','floor','paver','pavement','threshold']):return 'paving'
 return None
class SurfaceIndex:
 def __init__(self,raw_dir,staged):
  active=set()
  for job,opts in staged:
   for p,q in opts:
    for v in [p,q]:
     cell=np.floor(np.array(v[:2])/20).astype(int)
     for dx in [-1,0,1]:
      for dy in [-1,0,1]:active.add(int(cell[0]+dx+10000*(cell[1]+dy)))
  active=np.array(sorted(active),np.int64);chunks=[];refs=[];self.sources=[];self.legacy=[];self.evidence=[]
  for filename in ['campus.glb','building.glb']:
   path=Path(raw_dir)/filename;self.evidence.append({'path':str(path),'sha256':sha(path)});g=GLB(path)
   for ni,node in enumerate(g.d['nodes']):
    if 'mesh' not in node:continue
    name=node.get('name','')
    for pi,pr in enumerate(g.d['meshes'][node['mesh']]['primitives']):
     material=g.d['materials'][pr['material']].get('name','') if 'material' in pr else '';sc=surface_class(name,material)
     if 'lamp' in name.lower() or 'street lighting' in name.lower():
      ts=g.triangles(ni,pi);cells=np.floor(ts.mean(axis=1)[:,:2]/2).astype(int);keys=cells[:,0]+10000*cells[:,1]
      for key in np.unique(keys):
       part=ts[keys==key];self.legacy.append({'min':part.min(axis=(0,1)).tolist(),'max':part.max(axis=(0,1)).tolist(),'object':name,'source_file':filename,'primitive':pi})
      del ts,cells,keys,part
     if sc is None:continue
     sid=len(self.sources);self.sources.append({'file':filename,'object':name,'primitive':pi,'material':material,'class':sc})
     count=g.d['accessors'][pr['indices']]['count']//3 if 'indices' in pr else g.d['accessors'][pr['attributes']['POSITION']]['count']//3
     for first in range(0,count,40000):
      ts=g.triangles(ni,pi,slice(first,min(first+40000,count))).astype(np.float32);cross=np.cross(ts[:,1]-ts[:,0],ts[:,2]-ts[:,0]);norm=np.linalg.norm(cross,axis=1);keep=(norm>1e-8)&(np.abs(cross[:,2])/np.maximum(norm,1e-20)>.68);cell=np.floor(ts.mean(axis=1)[:,:2]/20).astype(np.int64);keys=cell[:,0]+10000*cell[:,1];big=np.ptp(ts[:,:,:2],axis=1).max(axis=1)>10;keep&=np.isin(keys,active)|big;ix=np.flatnonzero(keep);chunks.append(ts[ix]);refs.append(np.c_[np.full(len(ix),sid,np.int32),first+ix].astype(np.int32))
      del ts,cross,norm,keep,cell,keys,big,ix
     g.discard_pages()
   g.close();gc.collect()
  self.t=np.concatenate(chunks);self.ref=np.concatenate(refs);del chunks,refs;gc.collect();self.lo=self.t.min(axis=1);self.hi=self.t.max(axis=1);cell=np.floor((self.lo[:,:2]+self.hi[:,:2])*.5/20).astype(np.int32);keys=cell[:,0]+10000*cell[:,1];self.order=np.argsort(keys,kind='stable');u,starts=np.unique(keys[self.order],return_index=True);ends=np.r_[starts[1:],len(keys)];self.bins={int(k):(int(a),int(b)) for k,a,b in zip(u,starts,ends)};self.large=np.flatnonzero((self.hi[:,:2]-self.lo[:,:2]).max(axis=1)>10)
 def nearby(self,xy,radius=0):
  low=np.floor((xy-radius-10)/20).astype(int);high=np.floor((xy+radius+10)/20).astype(int);parts=[self.large]
  for x in range(low[0],high[0]+1):
   for y in range(low[1],high[1]+1):
    se=self.bins.get(int(x+10000*y))
    if se:parts.append(self.order[se[0]:se[1]])
  ix=np.unique(np.concatenate(parts));return ix[(self.hi[ix,0]>=xy[0]-radius)&(self.lo[ix,0]<=xy[0]+radius)&(self.hi[ix,1]>=xy[1]-radius)&(self.lo[ix,1]<=xy[1]+radius)]
 def ray(self,xy,zref,up,down,paved=False):
  ix=self.nearby(np.array(xy))
  if not len(ix):return None
  t=self.t[ix].astype(float);a=t[:,0];b=t[:,1]-a;c=t[:,2]-a;q=np.array(xy)-a[:,:2];den=b[:,0]*c[:,1]-b[:,1]*c[:,0];valid=np.abs(den)>1e-10;u=np.divide(q[:,0]*c[:,1]-q[:,1]*c[:,0],den,out=np.zeros(len(ix)),where=valid);v=np.divide(b[:,0]*q[:,1]-b[:,1]*q[:,0],den,out=np.zeros(len(ix)),where=valid);z=a[:,2]+u*b[:,2]+v*c[:,2];valid&=(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)&(z<=zref+up)&(z>=zref-down)
  if paved:valid&=np.array([self.sources[s]['class']=='paving' for s in self.ref[ix,0]])
  if not np.any(valid):return None
  j=np.flatnonzero(valid)[np.argmax(z[valid])];k=int(ix[j]);n=np.cross(b[j],c[j]);n/=np.linalg.norm(n)
  if n[2]<0:n*=-1
  return {'position':[float(xy[0]),float(xy[1]),float(z[j])],'normal':n.tolist(),'raw_index':k,**{a:self.sources[int(self.ref[k,0])][a] for a in ['file','object','primitive','material']},'triangle':int(self.ref[k,1]),'ray_origin':[float(xy[0]),float(xy[1]),float(zref+up)],'ray_direction':[0,0,-1],'ray_max_distance':float(up+down)}
 def patch(self,hit,radius):
  center=np.array(hit['position']);ix=self.nearby(center[:2],radius);sid=int(self.ref[hit['raw_index'],0]);ix=ix[self.ref[ix,0]==sid];window=max(1.2,radius*.32);ix=ix[(self.lo[ix,2]<center[2]+window)&(self.hi[ix,2]>center[2]-window)];vmap=defaultdict(list)
  for k in ix:
   for v in self.t[k]:vmap[tuple(np.round(v.astype(float),4))].append(int(k))
  todo=[hit['raw_index']];seen=set(todo)
  while todo:
   k=todo.pop()
   for v in self.t[k]:
    for other in vmap.get(tuple(np.round(v.astype(float),4)),[]):
     if other not in seen:seen.add(other);todo.append(other)
  out=[];refs=[];removed=[]
  for k in sorted(seen):
   poly=clip_disc(self.t[k].astype(float),center[:2],radius)
   if len(poly)<3:continue
   for j in range(1,len(poly)-1):
    t=np.array([poly[0],poly[j],poly[j+1]])
    # Preserve every positive-area output triangle, however thin.
    rounded=np.round(t,6);cross=np.cross(rounded[1]-rounded[0],rounded[2]-rounded[0])
    if np.linalg.norm(cross)==0:removed.append({'source_triangle':int(self.ref[k,1]),'reason':'exact zero area after output rounding'});continue
    out.append(rounded.tolist());refs.append({'source_triangle':int(self.ref[k,1])})
  return out,refs,removed

def clip_disc(poly,center,radius):
 for k in range(16):
  theta=(k+.5)*2*math.pi/16;n=np.array([math.cos(theta),math.sin(theta)]);limit=radius*math.cos(math.pi/16);out=[]
  for a,b in zip(poly,np.roll(poly,-1,axis=0)):
   da=float((a[:2]-center)@n-limit);db=float((b[:2]-center)@n-limit)
   if da<=1e-8:out.append(a)
   if (da<0)!=(db<0):out.append(a+(b-a)*da/(da-db))
  if len(out)<3:return []
  poly=np.array(out)
 return poly
