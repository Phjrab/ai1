"""Apply final source-bound local walking corrections without synthetic floors."""
import argparse,copy,hashlib,importlib.util,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def cv(p):return[p[0],p[2],-p[1]]
def uncv(p):return[p[0],-p[2],p[1]]
def load_world(root):
 p=root/'dist/world-config.js';text=p.read_text();return p,text.split('\n')[0],json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'))
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
def validate_surface(surface):
 if not surface.get('triangles') or any(len(p)!=3 or not all(math.isfinite(v) for v in p) for p in surface['polygon']):raise ValueError('Exact finite surface triangles required')
 for face in surface['triangles']:
  if len(face)!=3 or any(type(i)!=int or not 0<=i<len(surface['polygon']) for i in face):raise ValueError('Invalid triangle index')
def validate_paving_xy_adjustments(data,replacements,graph):
 allowances=data.get('walking_node_xy_adjustments',[]);by_index={r['index']:r for r in replacements};allowed={}
 for row in allowances:
  index=row['index']
  if index!=1036 or index in allowed or row.get('source_way_id')!='947734765':raise ValueError('Paving XY exception escaped reviewed node1036/way947734765')
  if index not in by_index:raise ValueError('XY exception has no source node replacement')
  change=by_index[index]
  for key in ['original_position','new_position']:
   if row.get(key)!=change[key]:raise ValueError('XY exception does not match exact source/output position')
  limit=row.get('maximum_xy_shift_m');distance=math.dist(change['original_position'][:2],change['new_position'][:2])
  if not isinstance(limit,(int,float)) or not math.isfinite(limit) or not 0<limit<=.5 or not 0<distance<=limit+1e-6:raise ValueError('Paving XY exception exceeds reviewed half-metre displacement')
  mapped=data.get('mapped_connector_replacement')
  if not mapped or str(mapped.get('osm_id'))!='947734765' or not row.get('reason'):raise ValueError('XY exception needs the exact mapped connector and source explanation')
  shared=data.get('walking_shared_endpoint_adjustments',[])
  if len(shared)>1:raise ValueError('Unexpected extra shared endpoint exceptions')
  allowed_shared=[]
  for item in shared:
   edge=item['source_edge_record'];record=item['source_navigation_road_record'];nodes=item['source_node_positions'];samples=item['sampled_connector_points']
   if item['index']!=1036 or item['source_way_id']!='1485907463' or item['source_edge_index']!=1484 or item['source_navigation_road_index']!=236 or edge['a']!=1036 or edge['b']!=1390 or str(edge['osm_id'])!='1485907463' or str(record['osm_id'])!='1485907463':raise ValueError('Shared endpoint escaped the reviewed adjacent branch')
   if item['new_position']!=change['new_position'] or nodes[0]!=change['original_position'] or graph['nodes'][1390]!=nodes[1] or record['points'][1]!=item['unchanged_first_sample']:raise ValueError('Shared endpoint source/output coordinates differ')
   if item['source_graph_sha256']!=data['source_road_graph_sha256'] or item['source_navigation_sha256']!=mapped['source_navigation_sha256']:raise ValueError('Shared endpoint source hashes differ')
   if len(samples)<2 or samples[0]!=item['new_position'] or samples[-1]!=item['unchanged_first_sample'] or any(len(p)!=3 or any(not math.isfinite(v) for v in p) for p in samples):raise ValueError('Shared endpoint actual support samples differ')
   matches=[e for e in graph['edges'] if e['a']==edge['a'] and e['b']==edge['b'] and str(e.get('osm_id'))==item['source_way_id']]
   if len(matches)!=1 or {k:v for k,v in matches[0].items() if k!='length'}!={k:v for k,v in edge.items() if k!='length'}:raise ValueError('Shared endpoint edge is not the exact original branch')
   allowed_shared.append(matches[0])
  if any(index in (e['a'],e['b']) and str(e.get('osm_id'))!='947734765' and e not in allowed_shared for e in graph['edges']):raise ValueError('XY exception would move an unrelated adjacent way')
  allowed[index]=row
 return allowed
def retire_exact_generic(surfaces,contract,is_world=False):
 """Remove only finite source-plane fragments; retain other layers/roles."""
 spec=importlib.util.spec_from_file_location('retire_clip',ROOT/'scripts/integrate-lower-paving-retirement.py');clip=importlib.util.module_from_spec(spec);spec.loader.exec_module(clip)
 tris=contract['world_triangles'];ranges=contract['per_triangle_z_ranges_m'];tolerance=contract['match_height_tolerance_m'];ways=contract['source_osm_ids']
 if len(tris)!=15 or len(ranges)!=15 or ways!=['1291221161','1485907425'] or contract['source_object']!='CAMPUS_CONTINUOUS pedestrian paving' or contract.get('preserve_group50') is not True or not 0<tolerance<=.03:raise ValueError('Generic retirement escaped the reviewed15 source triangles')
 masks=[]
 for tri,zrange in zip(tris,ranges):
  if len(tri)!=3 or any(len(p)!=3 or any(not math.isfinite(v) for v in p) for p in tri):raise ValueError('Invalid exact retirement triangle')
  if max(abs(a-b) for a,b in zip(zrange,[min(p[2] for p in tri),max(p[2] for p in tri)]))>1e-7:raise ValueError('Retirement height range differs from source triangle')
  a,b,c=tri;u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
  if abs(normal[2])<1e-10:raise ValueError('Retired support triangle is vertical')
  pa,pb=-normal[0]/normal[2],-normal[1]/normal[2];pc=a[2]-pa*a[0]-pb*a[1]
  masks.append((tri,[pa,pb,pc+tolerance],[pa,pb,pc-tolerance],zrange))
 out=[];changes=[]
 for sf in surfaces:
  poly=[uncv(p) for p in sf['polygon']] if is_world else sf['polygon'];parts=[[poly[i] for i in face] for face in sf['triangles']];removed=0
  for mask,upper,lower,zrange in masks:
   if any(max(p[i] for p in poly)<min(p[i] for p in mask)-1e-9 or min(p[i] for p in poly)>max(p[i] for p in mask)+1e-9 for i in (0,1)) or max(p[2] for p in poly)<zrange[0]-tolerance or min(p[2] for p in poly)>zrange[1]+tolerance:continue
   next_parts=[]
   for part in parts:
    pieces,cut=clip.retire_triangle(part,mask,upper,lower);next_parts.extend(pieces);removed+=cut
   parts=next_parts
  if not removed:out.append(sf);continue
  identified=sf.get('source_object')==contract['source_object'] or any(re.search(r'(?<!\d)'+way+r'(?!\d)',json.dumps(sf)) for way in ways)
  if not identified:raise ValueError('Unrelated support overlaps retired source-plane fragments: '+sf['id'])
  points=[];faces=[]
  for part in parts:
   start=len(points);points.extend(part)
   for j in range(1,len(part)-1):
    if clip.area([part[0],part[j],part[j+1]])>1e-10:faces.append([start,start+j,start+j+1])
  if faces:out.append({**sf,'polygon':[cv(p) for p in points] if is_world else points,'triangles':faces})
  changes.append({'id':sf['id'],'removed_projected_area_m2':removed,'before_triangles':len(sf['triangles']),'after_triangles':len(faces)})
 return out,changes
def apply(root,walk_source=None,it_source=None,public_source=None,pedestrian_source=None):
 wp,header,world=load_world(root);np=root/'data/campus-navigation.json';nav=json.loads(np.read_text());report_path=root/'data/walk-alignments-sync-report.json';report=json.loads(report_path.read_text()) if report_path.exists() else {'geometryModified':False,'walk':None,'it':None};writes={}
 if walk_source:
  raw=walk_source.read_bytes();data=json.loads(raw);prefix=tuple(data['remove_surface_prefixes']);surfaces=data['walkableSurfaces'];paths=data['pedestrianPaths'];ids={s['id'] for s in surfaces}
  if data.get('geometry_modified') is not False:raise ValueError('Walking contract must be geometry-backed metadata only')
  for s in surfaces:validate_surface(s)
  if any(not s['id'].startswith(prefix) for s in surfaces):raise ValueError('Support replacement escaped its explicit scope')
  if any(row['requires_geometry_review'] for row in data['route_audit']):raise ValueError('Walking geometry still has unresolved support discontinuities')
  for target,is_world in [(nav,False),(world,True)]:
   previous={s['id'] for s in target['walkableSurfaces'] if s['id'].startswith(prefix)}
   if previous!=ids:raise ValueError('Scoped support ID set changed unexpectedly')
   target['walkableSurfaces']=[s for s in target['walkableSurfaces'] if not s['id'].startswith(prefix)]+[{**s,'polygon':[cv(p) for p in s['polygon']]} if is_world else copy.deepcopy(s) for s in surfaces]
   mapping={p['id']:p for p in target['pedestrianPaths']}
   for path in paths:
    if path['id'] not in mapping:raise ValueError('Scoped path missing: '+path['id'])
    mapping[path['id']]['points']=[cv(p) for p in path['points']] if is_world else copy.deepcopy(path['points'])
  ep=root/'data/entrance-sync-report.json';entries=json.loads(ep.read_text())
  for item in data.get('entrance_route_overrides',[]):
   record=next(r for r in entries['records'] if r['id']==item['entrance_id']);path=next(p for p in paths if p['id']==item['path_id'])
   if math.dist(record['outside_threshold'][:2],item['outside_threshold'][:2])>1e-6:raise ValueError('Physical door XY cannot be moved by metadata projection')
   record.update(route=path['points'],safe_arrival=item['safe_arrival'],outside_threshold=item['outside_threshold'])
   for change in entries['destinationChanges']:
    if change['entrance_id']!=item['entrance_id']:continue
    destination=next(d for d in world['destinations'] if str(d['id'])==str(change['id']));destination['position']=cv(item['safe_arrival']);change['new_position']=destination['position']
    for landmark in nav['landmarks']:
     if str(landmark['id'])==str(change['id']):landmark['position']=item['safe_arrival']
  entries.setdefault('sourceHashes',{})['final_walk_alignment']=hashlib.sha256(raw).hexdigest();writes[ep]=entries
  report['walk']={'sourceSha256':hashlib.sha256(raw).hexdigest(),'surfaces':len(surfaces),'paths':[p['id'] for p in paths],'nativeGeometryReviewFlags':[x['id'] for x in data['route_audit'] if x['requires_geometry_review']]};writes[root/'data/walk-route-alignment.json']=data
 if it_source:
  raw=it_source.read_bytes();data=json.loads(raw)
  if data['vehicle_access'] is not False:raise ValueError('IT upper approach is walking only')
  spec=importlib.util.spec_from_file_location('public_clip',ROOT/'scripts/integrate-public-spaces.py');clip=importlib.util.module_from_spec(spec);spec.loader.exec_module(clip)
  masks=data['replacement_polygon_xy'];far=[[1e8,1e8],[1e8+1,1e8],[1e8,1e8+1]];changed=[]
  for target,is_world in [(nav,False),(world,True)]:
   retained=[]
   for record in target['walkableSurfaces']:
    sf={**record,'polygon':[uncv(p) for p in record['polygon']]} if is_world else copy.deepcopy(record)
    for mask in masks:
     sf,change=clip.clip_surface(sf,mask,far)
     if change and not is_world:changed.append(change)
     if sf is None:break
    if sf:retained.append({**sf,'polygon':[cv(p) for p in sf['polygon']]} if is_world else sf)
   added=[]
   for sf in data['walkableSurfaces']:
    validate_surface(sf);added.append({**sf,'polygon':[cv(p) for p in sf['polygon']]} if is_world else copy.deepcopy(sf))
   added_ids={s['id'] for s in added};target['walkableSurfaces']=[s for s in retained if s['id'] not in added_ids]+added
   added_paths=[{**p,'points':[cv(v) for v in p['points']]} if is_world else copy.deepcopy(p) for p in data['updatedPedestrianPaths']];path_ids={p['id'] for p in added_paths};target['pedestrianPaths']=[p for p in target['pedestrianPaths'] if p['id'] not in path_ids]+added_paths
   node_xy={tuple(r['position'][:2]):r['position'] for r in data['updatedWalkingNodes']};roads=[]
   for road in target['roads']:
    way=str(road.get('osm_id') or next((w for w in data['source_way_ids'] if w in road.get('name','')),''))
    if way not in data['source_way_ids']:roads.append(road);continue
    pts=[uncv(p) for p in road['points']] if is_world else copy.deepcopy(road['points']);parts=[[]]
    for index,p in enumerate(pts):
     if index and any(math.dist(pts[index-1][:2],r['before_endpoints'][0][:2])<1e-5 and math.dist(p[:2],r['before_endpoints'][1][:2])<1e-5 or math.dist(pts[index-1][:2],r['before_endpoints'][1][:2])<1e-5 and math.dist(p[:2],r['before_endpoints'][0][:2])<1e-5 for r in data['retiredWalkingEdges']):parts.append([])
     replacement=next((v for k,v in node_xy.items() if math.dist(k,p[:2])<1e-5),p);parts[-1].append(replacement)
    for part in parts:
     if len(part)>1:roads.append({**road,'points':[cv(p) for p in part] if is_world else part})
   target['roads']=roads
  gp=root/'data/walking-road-graph-3d.json';graph=json.loads(gp.read_text());old_nodes=copy.deepcopy(graph['nodes'])
  for row in data['updatedWalkingNodes']:
   old=graph['nodes'][row['index']]
   if min(math.dist(old,row[k]) for k in ['before','position'])>1e-4:raise ValueError('Walking node precondition mismatch: '+str(row['index']))
   if math.dist(row['before'][:2],row['position'][:2])>1e-8:raise ValueError('IT node XY changed')
   graph['nodes'][row['index']]=row['position']
  removed=[]
  for row in data['retiredWalkingEdges']:
   matches=[e for e in graph['edges'] if {e['a'],e['b']}=={row['a'],row['b']} and str(e.get('osm_id'))==row['osm_id']]
   if len(matches)>1:raise ValueError('Retired edge not unique')
   if matches:graph['edges'].remove(matches[0]);removed.append(matches[0])
   else:
    previous=report.get('it') or {};prior=[e for e in previous.get('retiredEdges',[]) if {e['a'],e['b']}=={row['a'],row['b']} and str(e.get('osm_id'))==row['osm_id']]
    if previous.get('sourceSha256')!=hashlib.sha256(raw).hexdigest() or len(prior)!=1:raise ValueError('Retired edge absent without a matching prior application')
    removed.append(prior[0])
  for edge in graph['edges']:
   if edge['a'] in {r['index'] for r in data['updatedWalkingNodes']} or edge['b'] in {r['index'] for r in data['updatedWalkingNodes']}:edge['length']=math.dist(graph['nodes'][edge['a']],graph['nodes'][edge['b']])
  writes[gp]=graph;writes[root/'data/it-approach-alignment.json']=data;report['it']={'sourceSha256':hashlib.sha256(raw).hexdigest(),'clippedSupportRecords':changed,'updatedNodes':data['updatedWalkingNodes'],'retiredEdges':removed}
 if pedestrian_source:
  raw=pedestrian_source.read_bytes();data=json.loads(raw)
  if data['schema']!='final-pedestrian-finite-surface-1':raise ValueError('Unknown finite paving correction schema')
  manifest=json.loads((root/'data/native-export-manifest.json').read_text())
  if manifest['sidecar_sha256'].get(data['source_road_graph'])!=data['source_road_graph_sha256']:raise ValueError('Finite paving source graph binding differs')
  replacements=data['walking_node_replacements'];gp=root/'data/walking-road-graph-3d.json';graph=json.loads(gp.read_text());changed=set();xy_adjustments=validate_paving_xy_adjustments(data,replacements,graph)
  for row in replacements:
   old,new=row['original_position'],row['new_position'];index=row['index']
   if len(old)!=3 or len(new)!=3 or any(not math.isfinite(v) for p in (old,new) for v in p):raise ValueError('Finite paving correction needs finite XYZ source nodes')
   if math.dist(old[:2],new[:2])>1e-8 and index not in xy_adjustments:raise ValueError('Finite paving XY change lacks the exact reviewed exception')
   if min(math.dist(graph['nodes'][index],p) for p in (old,new))>1e-4:raise ValueError('Finite paving node source mismatch')
   graph['nodes'][index]=new;changed.add(index)
  for edge in graph['edges']:
   if edge['a'] in changed or edge['b'] in changed:edge['length']=math.dist(graph['nodes'][edge['a']],graph['nodes'][edge['b']])
  for target,is_world in [(nav,False),(world,True)]:
   for key in ['roads','pedestrianPaths']:
    for record in target.get(key,[]):
     if key=='roads' and data.get('mapped_connector_replacement') and str(record.get('osm_id'))==str(data['mapped_connector_replacement']['osm_id']):continue
     if key=='roads' and any(str(record.get('osm_id'))==x['source_way_id'] for x in data.get('walking_shared_endpoint_adjustments',[])):continue
     pts=[uncv(p) for p in record['points']] if is_world else record['points']
     for j,point in enumerate(pts):
      for row in replacements:
       if math.dist(point,row['original_position'])<1e-4:pts[j]=row['new_position'];break
     record['points']=[cv(p) for p in pts] if is_world else pts
  mapped=data.get('mapped_connector_replacement');mapped_summary=None
  if mapped:
   if manifest['sidecar_sha256'].get(mapped['source_navigation_path'])!=mapped['source_navigation_sha256']:raise ValueError('Mapped connector navigation binding differs')
   if str(mapped['osm_id'])!='947734765':raise ValueError('Mapped connector escaped its single reviewed way')
   prior=report.get('finitePaving') or {};same_prior=prior.get('sourceSha256')==hashlib.sha256(raw).hexdigest()
   for target,is_world in [(nav,False),(world,True)]:
    matches=[r for r in target['roads'] if str(r.get('osm_id'))==mapped['osm_id']]
    # WORLD.roads is the vehicle-only routing set in the normal build.
    # Keep this footway out of it; its exact walking path is added below.
    if is_world and not matches and mapped['source_road_record'].get('vehicle') is False:continue
    if len(matches)!=1:raise ValueError('Mapped connector road is not unique')
    road=matches[0];points=[uncv(v) for v in road['points']] if is_world else road['points']
    source_points=mapped['source_road_record']['points']
    matches_xy=lambda expected:len(points)==len(expected) and all(math.dist(a[:2],b[:2])<=1e-5 for a,b in zip(points,expected))
    # A full rebuild resets the road to its bound original even while the
    # previous report remains. Accept only that exact original, or the exact
    # reviewed output when its matching prior application is recorded.
    if not(matches_xy(source_points) or same_prior and matches_xy(mapped['points'])):raise ValueError('Mapped connector source XY differs')
    road['points']=[cv(v) for v in mapped['points']] if is_world else copy.deepcopy(mapped['points']);road['width']=mapped['width_m'];road['support_surface_objects']=mapped['support_surface_objects']
   generated=[e for e in graph['edges'] if e.get('final_paving_connector')==mapped['osm_id']]
   if generated:
    if not same_prior:raise ValueError('Mapped connector already changed by another input')
    mapped_summary=prior['mappedConnector']
   else:
    removed=[];new_edges=[];before_nodes=len(graph['nodes'])
    for replacement in mapped['source_graph_edges']:
     source_record=replacement['source_record'];matches=[e for e in graph['edges'] if e['a']==source_record['a'] and e['b']==source_record['b'] and str(e.get('osm_id'))==mapped['osm_id']]
     if len(matches)!=1:raise ValueError('Mapped source graph edge is not unique')
     edge=matches[0];points=replacement['points'];a,b=edge['a'],edge['b']
     if math.dist(graph['nodes'][a],points[0])>.001 or math.dist(graph['nodes'][b],points[-1])>.001:raise ValueError('Mapped connector endpoints leave their actual source nodes')
     chain=[a]
     for point in points[1:-1]:chain.append(len(graph['nodes']));graph['nodes'].append(point)
     chain.append(b)
     for a,b in zip(chain,chain[1:]):new_edges.append({**edge,'a':a,'b':b,'length':math.dist(graph['nodes'][a],graph['nodes'][b]),'width':mapped['width_m'],'final_paving_connector':mapped['osm_id'],'source_edge_index':replacement['index']})
     graph['edges'].remove(edge);removed.append(replacement['index'])
    graph['edges']+=new_edges;mapped_summary={'sourceEdgeIndices':removed,'addedNodes':len(graph['nodes'])-before_nodes,'replacementEdges':len(new_edges),'sourceRoadIndex':mapped['source_road_index']}
  shared_summary=[]
  for item in data.get('walking_shared_endpoint_adjustments',[]):
   original=item['source_navigation_road_record'];updated={**copy.deepcopy(original),'points':[item['new_position']]+copy.deepcopy(original['points'][1:])}
   for target,is_world in [(nav,False),(world,True)]:
    matches=[r for r in target['roads'] if str(r.get('osm_id'))==item['source_way_id']]
    if is_world and not matches and original.get('vehicle') is False:continue
    if len(matches)!=1:raise ValueError('Shared branch road is not unique')
    record=matches[0];converted={**record,'points':[uncv(p) for p in record['points']]} if is_world else record
    if converted!=original and converted!=updated:raise ValueError('Shared branch original road record differs')
    record['points']=[cv(p) for p in updated['points']] if is_world else copy.deepcopy(updated['points'])
   shared_summary.append({'node':item['index'],'sourceWayId':item['source_way_id'],'sourceEdgeIndex':item['source_edge_index'],'sourceRoadIndex':item['source_navigation_road_index'],'before':original['points'][0],'after':item['new_position'],'otherRoadPointChanges':0,'otherNodeChanges':0})
  connector=data.get('added_connector_path')
  if connector:
   if len(connector)<2 or any(len(p)!=3 or not all(math.isfinite(v) for v in p) for p in connector):raise ValueError('Invalid exact mapped connector path')
   width=data['added_connector_width_m']
   if not math.isfinite(width) or width<=0:raise ValueError('Invalid mapped connector width')
   record={'id':'final_mapped_footway_947734765','label':'트랙–장미원 보행 연결','points':connector,'width':width,'source_way_id':'947734765','vehicle_access':False,'model_alignment_not_surveyed':True}
   for target,is_world in [(nav,False),(world,True)]:
    target['pedestrianPaths']=[p for p in target['pedestrianPaths'] if p['id']!=record['id']]+[{**record,'points':[cv(p) for p in connector]} if is_world else copy.deepcopy(record)]
  retirement=data.get('retired_generic_surfaces');retirement_report=None
  if retirement:
   rawsha=hashlib.sha256(raw).hexdigest();sidecars=manifest['sidecar_sha256']
   if sidecars.get('realism_v2/final_pedestrian_residuals/resolved_navigation_overlay.json')!=rawsha or sidecars.get('realism_v2/final_pedestrian_contacts/legacy_navigation_overlay.json')!=rawsha or 'realism_v2/final_pedestrian_residuals.py' not in manifest.get('module_sha256',{}):raise ValueError('Exact generic retirement lacks final native-bound residual source and identical sidecars')
   nav['walkableSurfaces'],cuts=retire_exact_generic(nav['walkableSurfaces'],retirement)
   world['walkableSurfaces'],worldcuts=retire_exact_generic(world['walkableSurfaces'],retirement,True)
   if cuts!=worldcuts:raise ValueError('World/navigation retirement outputs differ')
   retirement_report={'sourceTriangleCount':len(retirement['world_triangles']),'clippedSupportRecords':cuts,'cachedSupportTriangleChanges':sum(r['before_triangles']-r['after_triangles'] for r in cuts),'geometryModified':False,'preservedGroup50':True}
   previous=report.get('finitePaving') or {}
   if not cuts and previous.get('sourceSha256')==rawsha and previous.get('retiredGeneric'):retirement_report=previous['retiredGeneric']
  # The affected mapped footways have no cached floor polygons. Their visible
  # final triangles remain the support authority; do not create a virtual pad.
  writes[gp]=graph;writes[root/'data/final-pedestrian-navigation.json']=data
  report['finitePaving']={'sourceSha256':hashlib.sha256(raw).hexdigest(),'nodeReplacements':replacements,'xyAdjustments':list(xy_adjustments.values()),'sharedEndpointAdjustments':shared_summary,'retiredGeneric':retirement_report,'addedConnector':('final_mapped_footway_947734765' if connector else None),'mappedConnector':mapped_summary,'supportSource':'Final rendered geometry; no synthetic floor added'}
 if public_source:
  raw=public_source.read_bytes();data=json.loads(raw)
  expected={'public_rose_spine','red_track_perimeter_loop'}
  if data.get('schema')!='public-walk-clearance-v1' or set(data['replacePedestrianPathIds'])!=expected:raise ValueError('Unexpected public walking replacement scope')
  if data.get('walkableSurfaces') or data.get('collisionBoxes'):raise ValueError('Public route correction must retain physical support and existing primitive blockers')
  paths=data['pedestrianPaths']
  if {p['id'] for p in paths}!=expected or len(paths)!=len(expected):raise ValueError('Public route replacement IDs differ')
  for path in paths:
   if len(path['points'])<2 or any(len(p)!=3 or not all(math.isfinite(v) for v in p) for p in path['points']):raise ValueError('Invalid actual public walking route')
  for target,is_world in [(nav,False),(world,True)]:
   if {p['id'] for p in target['pedestrianPaths'] if p['id'] in expected}!=expected:raise ValueError('Public route missing before replacement')
   target['pedestrianPaths']=[p for p in target['pedestrianPaths'] if p['id'] not in expected]+[{**p,'points':[cv(v) for v in p['points']]} if is_world else copy.deepcopy(p) for p in paths]
  writes[root/'data/public-walk-clearance.json']=data;report['public']={'sourceSha256':hashlib.sha256(raw).hexdigest(),'replacedPaths':sorted(expected),'primitiveCollisionsPreserved':True}
 wp.write_text(header+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n');write(np,nav)
 for path,data in writes.items():write(path,data)
 write(root/'data/walk-alignments-sync-report.json',report);return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--walk-source',type=Path);p.add_argument('--it-source',type=Path);p.add_argument('--public-source',type=Path);p.add_argument('--pedestrian-source',type=Path);p.add_argument('--game-root',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(apply(a.game_root,a.walk_source,a.it_source,a.public_source,a.pedestrian_source)))
