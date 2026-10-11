"""Project only the diagnosed944 connector metadata onto its actual raw triangles.

Read-only GLB; exact clipping preserves each metadata XY domain and all other
surfaces. This is a derived game contract, not a native geometry mutation.
"""
import argparse,ast,copy,hashlib,json,math,mmap,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PREFIX='inferred_walk_connector_944569946_0_'
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def matrix_mul(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def source_triangles(path):
 with path.open('rb') as stream:
  raw=mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ);size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size]);start=28+size;parents={c:i for i,n in enumerate(doc['nodes']) for c in n.get('children',[])};cache={}
  def matrix(i):
   if i in cache:return cache[i]
   n=doc['nodes'][i]
   if 'matrix' in n:m=[[n['matrix'][j*4+k] for j in range(4)] for k in range(4)]
   else:
    x,y,z,w=n.get('rotation',[0,0,0,1]);s=n.get('scale',[1,1,1]);t=n.get('translation',[0,0,0]);r=[[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],[2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],[2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]];m=[[r[k][j]*s[j] for j in range(3)]+[t[k]] for k in range(3)]+[[0,0,0,1]]
   if i in parents:m=matrix_mul(matrix(parents[i]),m)
   cache[i]=m;return m
  def accessor(i):
   a=doc['accessors'][i];b=doc['bufferViews'][a['bufferView']];fmt={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']];dim={'VEC3':3,'SCALAR':1}[a['type']];unpack=struct.Struct('<'+fmt*dim);offset=start+b.get('byteOffset',0)+a.get('byteOffset',0);stride=b.get('byteStride',unpack.size);return [unpack.unpack_from(raw,offset+j*stride) for j in range(a['count'])]
  out=[];names=[]
  for i,node in enumerate(doc['nodes']):
   name=node.get('name','')
   if 'mesh' not in node or not name.lower().startswith('inferred_game_walk_connectors'):continue
   names.append(name);m=matrix(i)
   for primitive in doc['meshes'][node['mesh']]['primitives']:
    points=[]
    for p in accessor(primitive['attributes']['POSITION']):
     v=[sum(m[k][j]*p[j] for j in range(3))+m[k][3] for k in range(3)];points.append([v[0],-v[2],v[1]])
    indices=[p[0] for p in accessor(primitive['indices'])] if 'indices' in primitive else list(range(len(points)))
    for j in range(0,len(indices),3):out.append([points[k] for k in indices[j:j+3]])
  raw.close();return out,names

def apply(root,raw_path):
 manifest=json.loads((root/'data/native-export-manifest.json').read_text());expected=next(e['sha256'] for e in manifest['exports'] if e['file'].endswith('/campus.glb'));actual=digest(raw_path)
 if actual!=expected:raise ValueError('Actual raw source does not match the native export manifest')
 helper=ROOT/'scripts/reconcile-walk-support.py';tree=ast.parse(helper.read_text());functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'area','clip_value','intersect','subtract','plane','height'}];scope={};exec(compile(ast.Module(body=functions,type_ignores=[]),str(helper),'exec'),scope)
 area,intersect,subtract,plane,height=[scope[k] for k in ['area','intersect','subtract','plane','height']]
 triangles,names=source_triangles(raw_path)
 if not triangles or not names:raise ValueError('Expected inferred source geometry missing from raw export')
 np=root/'data/campus-navigation.json';nav=json.loads(np.read_text());wp=root/'dist/world-config.js';text=wp.read_text();header=text.split('\n')[0];world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'));input_navigation_sha=digest(np);input_world_sha=digest(wp);records=[];changes={}
 for sf in nav['walkableSurfaces']:
  if not sf['id'].startswith(PREFIX):continue
  poly=sf['polygon'];xmin,xmax=min(p[0] for p in poly),max(p[0] for p in poly);ymin,ymax=min(p[1] for p in poly),max(p[1] for p in poly);zmin,zmax=min(p[2] for p in poly)-1,max(p[2] for p in poly)+1;candidates=[]
  for tri in triangles:
   if max(p[0] for p in tri)<xmin or min(p[0] for p in tri)>xmax or max(p[1] for p in tri)<ymin or min(p[1] for p in tri)>ymax or max(p[2] for p in tri)<zmin or min(p[2] for p in tri)>zmax:continue
   eq=plane(tri)
   if eq:candidates.append(([p[:2] for p in tri],eq))
  def query(p):
   values=[]
   for xy,eq in candidates:
    sign=1 if area(xy)>0 else -1
    if any(p[i]<min(v[i] for v in xy)-1e-7 or p[i]>max(v[i] for v in xy)+1e-7 for i in (0,1)):continue
    inside=all(sign*((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))>=0 for a,b in zip(xy,xy[1:]+xy[:1]))
    if not inside:
     distances=[]
     for a,b in zip(xy,xy[1:]+xy[:1]):
      dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy or 1)));distances.append(math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy))
     if min(distances)>1e-7:continue
    values.append(height(eq,p))
   return max(values) if values else None
  maximum=0
  for face in sf['triangles']:
   for weights in [(1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)]:
    p=[sum(poly[i][k]*w for i,w in zip(face,weights)) for k in range(3)];h=query(p)
    if h is not None:maximum=max(maximum,abs(p[2]-h))
  if maximum<=.002:continue
  vertices=[];faces=[]
  for face in sf['triangles']:
   mask=[poly[i][:2] for i in face]
   for ci,(xy,eq) in enumerate(candidates):
    start=intersect(xy,mask)
    if len(start)<3 or abs(area(start))<1e-8:continue
    pieces=[start]
    for cj,(other,oeq) in enumerate(candidates):
     if ci==cj or not pieces:continue
     diff=lambda p:height(oeq,p)-height(eq,p)
     if max(diff(p) for p in other)<1e-6:
      if cj>ci or max(abs(diff(p)) for p in other)>1e-6:continue
      upper=other
     else:upper=scope['clip_value'](other,lambda p:diff(p)-1e-7)
     if len(upper)<3 or abs(area(upper))<1e-8:continue
     next_pieces=[]
     for piece in pieces:
      overlap=intersect(piece,upper)
      next_pieces.extend(subtract(piece,upper) if len(overlap)>=3 and abs(area(overlap))>=1e-8 else [piece])
     pieces=next_pieces
    for piece in pieces:
     offset=len(vertices);vertices.extend([[x,y,height(eq,[x,y])] for x,y in piece])
     for j in range(1,len(piece)-1):
      if abs(area([piece[0],piece[j],piece[j+1]]))>1e-8:faces.append([offset,offset+j,offset+j+1])
  before_area=sum(abs(area([poly[i][:2] for i in f])) for f in sf['triangles']);after_area=sum(abs(area([vertices[i][:2] for i in f])) for f in faces)
  if not faces or abs(before_area-after_area)>max(.002,before_area*.002):raise ValueError('Actual surface projection does not cover the exact source domain: '+sf['id'])
  errors=[]
  for face in faces:
   p=[sum(vertices[i][k] for i in face)/3 for k in range(3)];h=query(p)
   if h is None:raise ValueError('Projected support is outside actual source triangles')
   errors.append(abs(p[2]-h))
  if max(errors)>.0001:raise ValueError('Projection disagrees with actual finite source top')
  changes[sf['id']]={**sf,'polygon':vertices,'triangles':faces,'support_basis':'Exact final raw GLB finite triangles; same XY domain; no scene geometry mutation.'};records.append({'id':sf['id'],'beforeMaximumGap':maximum,'afterMaximumGap':max(errors),'sourceArea':before_area,'outputArea':after_area,'triangles':len(faces)})
 for target,convert in [(nav,False),(world,True)]:target['walkableSurfaces']=[({**changes[s['id']],'polygon':[[p[0],p[2],-p[1]] for p in changes[s['id']]['polygon']]} if convert else changes[s['id']]) if s['id'] in changes else s for s in target['walkableSurfaces']]
 report={'nativeSourceSha256':manifest['source_sha256'],'rawGLBSha256':actual,'inputNavigationSha256':input_navigation_sha,'inputWorldSha256':input_world_sha,'helperSha256':digest(helper),'consumerSha256':digest(Path(__file__)),'geometryModified':False,'scopePrefix':PREFIX,'sourceObjects':names,'records':records,'walkableSurfaces':list(changes.values()),'path':'inferred_walk_connector_944569946_0','pathXYUnchanged':True,'runtimeBidirectionalValidation':'pending'}
 np.write_text(json.dumps(nav,ensure_ascii=False,separators=(',',':'))+'\n');wp.write_text(header+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n');(root/'data/exported-inferred-support.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('--game-root',type=Path,default=ROOT);a=p.parse_args();r=apply(a.game_root,a.raw);print(json.dumps({k:v for k,v in r.items() if k!='walkableSurfaces'}))
