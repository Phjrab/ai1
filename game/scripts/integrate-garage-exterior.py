"""Consume the exact garage SW exterior-road correction, preserving source records."""
import argparse,copy,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def cv(p):return[p[0],p[2],-p[1]]
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
def near(a,b):return math.dist(a,b)<1e-5
def apply(root,source):
 raw=source.read_bytes();d=json.loads(raw);sha=hashlib.sha256(raw).hexdigest();rp=root/'data/garage-exterior-sync-report.json'
 if d['schema']!='chosun.garage164.exterior_navigation.v1' or d['status']!='FROZEN_AFTER_ACTUAL_DRIVE_STEP':raise ValueError('Unverified exterior route')
 manifest=json.loads((root/'data/native-export-manifest.json').read_text())
 for kind in ['graph','navigation']:
  if manifest['sidecar_sha256'].get(d['source_'+kind+'_path'])!=d['source_'+kind+'_sha256']:raise ValueError('Garage source '+kind+' binding differs')
 if manifest['sidecar_sha256'].get(d['source_geometry_file'])!=d['source_geometry_sha256']:raise ValueError('Garage geometry binding differs')
 wp=root/'dist/world-config.js';txt=wp.read_text();head=txt.split('\n')[0];world=json.loads(txt.split('export const WORLD = ')[1].rstrip(';\n'));np=root/'data/campus-navigation.json';nav=json.loads(np.read_text());gp=root/'data/road-graph-3d.json';graph=json.loads(gp.read_text())
 if rp.exists() and json.loads(rp.read_text()).get('sourceSha256')==sha:
  nodes_applied=all(row['node_index']<len(graph['nodes']) and near(graph['nodes'][row['node_index']],row['position']) for row in d['node_bindings'])
  graph_applied=any(e.get('garage_boundary_alignment') and e.get('sourceSha256')==sha for e in graph['edges'])
  world_applied=any(r.get('garage_boundary_part')=='verified_curve' and r['points']==[cv(p) for p in d['verified_points']] and r['width']==d['width_m'] for r in world['roads'])
  nav_applied=any(r.get('garage_boundary_alignment',{}).get('sourceSha256')==sha for r in nav['roads'])
  if nodes_applied and graph_applied and world_applied and nav_applied:return json.loads(rp.read_text())
 initial_used={e[k] for e in graph['edges'] for k in ['a','b']};initial_retired=set(range(len(graph['nodes'])))-initial_used
 bindings=d['node_bindings'];points=d['replacement_points'];verified=d['verified_points'];start=d['verified_start_index'];width=d['width_m'];osm=d['osm_id'];original=copy.deepcopy(graph['nodes']);edge_ids=[]
 if points[start:]!=verified or width!=3.0:raise ValueError('Bounded route shape/width changed')
 for row in bindings:
  if not near(graph['nodes'][row['node_index']],row['original_position']):raise ValueError('Garage node precondition differs: '+str(row['node_index']))
  if row['position']!=points[row['point_index']]:raise ValueError('Garage node not on verified curve')
 for row in d['source_edges']:
  e=row['record'];matches=[i for i,x in enumerate(graph['edges']) if x['a']==e['a'] and x['b']==e['b'] and str(x.get('osm_id'))==osm]
  if len(matches)!=1:raise ValueError('Garage original edge absent or duplicated')
  ix=matches[0];current=graph['edges'][ix]
  if any(current.get(k)!=v for k,v in e.items() if k!='length'):raise ValueError('Garage edge attributes changed')
  edge_ids.append(ix)
 changed={row['node_index'] for row in bindings if not near(row['position'],row['original_position'])}
 for i,e in enumerate(graph['edges']):
  if i not in edge_ids and any(e[k] in changed-{bindings[-1]['node_index']} for k in ['a','b']):raise ValueError('Unreviewed side branch at corrected node')
 # Exact source road-span guards; other roads, destinations and actor poses stay untouched.
 road_matches=[r for r in nav['roads'] if str(r.get('osm_id'))==osm]
 if len(road_matches)!=1:raise ValueError('Garage navigation road is not unique')
 road=road_matches[0];lo,hi=d['source_road_span_indices'];source_road=d['source_road_record']
 if road['points'][lo:hi+1]!=source_road['points'][lo:hi+1]:raise ValueError('Garage navigation span changed')
 road['points']=road['points'][:lo]+copy.deepcopy(points)+road['points'][hi+1:];road['garage_boundary_alignment']={'sourceSha256':sha,'width_m':width,'source_span':[lo,hi],'verified_points':verified}
 # WORLD roads are edge records after campus access integration. Remove exactly
 # the eight source edge segments, then insert the same verified connection.
 world_edge_ids=[];runtime_template=None
 for row in d['source_edges']:
  e=row['record'];ends=[cv(original[e['a']]),cv(original[e['b']])]
  matches=[i for i,r in enumerate(world['roads']) if (str(r.get('osm_id'))==osm or r.get('name')=='CAMPUS_ROAD '+osm) and len(r['points'])==2 and r['points']==ends]
  if len(matches)!=1:raise ValueError('Garage runtime source edge absent or duplicated')
  world_edge_ids.append(matches[0]);runtime_template=world['roads'][matches[0]]
 retained=[r for i,r in enumerate(world['roads']) if i not in world_edge_ids]
 for r in retained:
  r['points']=[next((cv(b['position']) for b in bindings if near(p,cv(b['original_position']))),p) for p in r['points']]
 before={**runtime_template,'points':[cv(p) for p in points[:start+1]],'garage_boundary_part':'before'}
 middle={**runtime_template,'points':[cv(p) for p in verified],'width':width,'garage_boundary_part':'verified_curve','source_geometry_sha256':d['source_geometry_sha256']}
 world['roads']=retained+[before,middle]
 by_point={row['point_index']:row['node_index'] for row in bindings};new_node_indices=[]
 for i,p in enumerate(points):
  if i in by_point:ix=by_point[i];graph['nodes'][ix]=p
  else:ix=len(graph['nodes']);graph['nodes'].append(p)
  new_node_indices.append(ix)
 graph['edges']=[e for i,e in enumerate(graph['edges']) if i not in edge_ids];template=d['source_edges'][0]['record'];added=[]
 for i,(a,b) in enumerate(zip(new_node_indices,new_node_indices[1:])):
  e={**template,'a':a,'b':b,'length':math.dist(graph['nodes'][a],graph['nodes'][b]),'width':width if i>=start else d['source_width_m'],'garage_boundary_alignment':True,'sourceSha256':sha};graph['edges'].append(e);added.append(len(graph['edges'])-1)
 for e in graph['edges']:
  if e['a'] in changed or e['b'] in changed:e['length']=math.dist(graph['nodes'][e['a']],graph['nodes'][e['b']])
 # Recalculate connectivity from the actual graph, retaining every old node.
 neighbors=[[] for _ in graph['nodes']]
 for e in graph['edges']:neighbors[e['a']].append(e['b']);neighbors[e['b']].append(e['a'])
 seen=set();components=[]
 for i in range(len(neighbors)):
  if i in seen:continue
  todo=[i];seen.add(i);component=[]
  while todo:
   j=todo.pop();component.append(j)
   for k in neighbors[j]:
    if k not in seen:seen.add(k);todo.append(k)
  components.append(component)
 graph['components']=components
 if len([c for c in components if len(c)>1])!=1 or {c[0] for c in components if len(c)==1}!=initial_retired:raise ValueError('Garage correction changed active vehicle connectivity or retired-node set')
 report={'sourceSha256':sha,'sourceGraphSha256':d['source_graph_sha256'],'sourceNavigationSha256':d['source_navigation_sha256'],'removedEdges':d['source_edges'],'addedEdgeIndices':added,'newNodeIndices':[i for i in new_node_indices if i>=len(original)],'correctedOriginalNodes':bindings,'width_m':width,'activeComponents':len([c for c in components if len(c)>1]),'preservedRetiredNodes':sorted(initial_retired),'geometryModified':False,'actorPosesModified':False}
 wp.write_text(head+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n');write(np,nav);write(gp,graph);write(root/'data/garage-exterior-navigation.json',d);write(rp,report);return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(apply(a.root,a.source),ensure_ascii=False))
