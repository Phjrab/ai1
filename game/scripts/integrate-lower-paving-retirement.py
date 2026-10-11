"""Retire only source-identified cached paving below the final IT bridge.

The actual GLB is already clipped by Blender. No new collider or floor is made.
"""
import argparse,copy,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EPS=1e-9

def area(poly):return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))*.5

def half(poly,plane,positive=True):
 result=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  sp=sum(plane[i]*p[i] for i in range(3))+plane[3];sq=sum(plane[i]*q[i] for i in range(3))+plane[3]
  ip=sp>=-EPS if positive else sp<=EPS;iq=sq>=-EPS if positive else sq<=EPS
  if ip:result.append(p)
  if ip!=iq:
   t=sp/(sp-sq);result.append([p[i]+t*(q[i]-p[i]) for i in range(3)])
 return result

def retire_triangle(triangle,mask,ceiling,floor=None):
 signed=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(mask,mask[1:]+mask[:1]));mask=mask if signed>0 else mask[::-1]
 planes=[[-(b[1]-a[1]),b[0]-a[0],0,(b[1]-a[1])*a[0]-(b[0]-a[0])*a[1]] for a,b in zip(mask,mask[1:]+mask[:1])]+[[ceiling[0],ceiling[1],-1,ceiling[2]]]
 if floor is not None:planes.append([-floor[0],-floor[1],1,-floor[2]])
 left=triangle;outside=[]
 for plane in planes:
  if len(left)<3:break
  piece=half(left,plane,False)
  if len(piece)>=3 and area(piece)>1e-10:outside.append(piece)
  left=half(left,plane,True)
 removed=area(left) if len(left)>=3 else 0
 if removed<1e-8:return [triangle],0
 if abs(area(triangle)-sum(area(p) for p in outside)-removed)>1e-6:raise ValueError('Finite retirement lost outside support area')
 return outside,removed

def apply(root,source):
 raw=source.read_bytes();data=json.loads(raw);sha=hashlib.sha256(raw).hexdigest();manifest=json.loads((root/'data/native-export-manifest.json').read_text());key='realism_v2/it_approach_alignment_review/lower_paving_retirement.json'
 if manifest['sidecar_sha256'].get(key)!=sha:raise ValueError('IT lower-paving retirement is not bound to this native export')
 if manifest['module_sha256'].get('realism_v2/final_it_lower_paving_retirement.py')!=data['source_module_sha256']:raise ValueError('IT lower-paving module binding differs')
 if data['version']!='1.0' or data['source_object']!='CAMPUS_CONTINUOUS pedestrian paving' or data['source_way_ids']!=['474301324'] or data['vehicle_access'] is not False or data['upper_geometry_and_pose_unchanged'] is not True:raise ValueError('IT retirement escaped its reviewed source scope')
 mask=data['retirement_polygon_xy'];ceiling=data['max_z_plane']
 if len(mask)<3 or len(ceiling)!=3 or any(not math.isfinite(v) for p in mask for v in p) or any(not math.isfinite(v) for v in ceiling) or data['minimum_below_bridge_top_m']<.30:raise ValueError('Invalid finite XY/height retirement bounds')
 wp=root/'dist/world-config.js';text=wp.read_text();header=text.split('\n')[0];world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'));np=root/'data/campus-navigation.json';nav=json.loads(np.read_text());changes=[]
 for target,is_world in [(nav,False),(world,True)]:
  retained=[]
  for sf in target['walkableSurfaces']:
   poly=[[p[0],-p[2],p[1]] for p in sf['polygon']] if is_world else sf['polygon'];pieces=[];removed=0
   if min(p[0] for p in poly)>max(p[0] for p in mask) or max(p[0] for p in poly)<min(p[0] for p in mask) or min(p[1] for p in poly)>max(p[1] for p in mask) or max(p[1] for p in poly)<min(p[1] for p in mask) or all(p[2]>ceiling[0]*p[0]+ceiling[1]*p[1]+ceiling[2]+EPS for p in poly):retained.append(sf);continue
   for face in sf['triangles']:
    parts,cut=retire_triangle([poly[i] for i in face],mask,ceiling);pieces.extend(parts);removed+=cut
   if not removed:retained.append(sf);continue
   source_identified=sf.get('source_object')==data['source_object'] or re.search(r'(?<!\d)474301324(?!\d)',json.dumps(sf)) is not None
   if not source_identified:raise ValueError('Unrelated cached support overlaps IT retirement; explicit role needed: '+sf['id'])
   points=[];faces=[]
   for piece in pieces:
    start=len(points);points.extend(piece)
    for j in range(1,len(piece)-1):
     if area([piece[0],piece[j],piece[j+1]])>1e-10:faces.append([start,start+j,start+j+1])
   if faces:retained.append({**sf,'polygon':[[p[0],p[2],-p[1]] for p in points] if is_world else points,'triangles':faces})
   if not is_world:changes.append({'id':sf['id'],'removed_projected_area_m2':removed,'before_triangles':len(sf['triangles']),'after_triangles':len(faces)})
  target['walkableSurfaces']=retained
 previous_path=root/'data/it-lower-paving-retirement-report.json'
 if not changes and previous_path.exists():
  previous=json.loads(previous_path.read_text())
  if previous.get('sourceSha256')==sha:changes=previous['clippedSupportRecords']
 report={'sourceSha256':sha,'sourceModuleSha256':data['source_module_sha256'],'sourceWayIds':data['source_way_ids'],'clippedSupportRecords':changes,'geometryModified':False,'graphAndPathsModified':False,'scope':'Exact finite same-way mask AND lower height plane. Actual raw GLB has the native retirement; higher layers, outside support, graph and paths are retained.'}
 wp.write_text(header+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n');np.write_text(json.dumps(nav,ensure_ascii=False,separators=(',',':'))+'\n');(root/'data/it-lower-paving-retirement.json').write_bytes(raw);(root/'data/it-lower-paving-retirement-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--game-root',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(apply(a.game_root,a.source)))
