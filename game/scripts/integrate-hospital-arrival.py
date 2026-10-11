#!/usr/bin/env python3
"""Merge a native-bound hospital road/forecourt contract without guessed links."""
import argparse,copy,hashlib,json,math
from pathlib import Path

def cv(p):return [p[0],p[2],-p[1]]
def merge_graph(graph,overlay,kind):
    changed={}
    for record in overlay['updatedRoadNodes'][kind]:
        index=record['index'];point=graph['nodes'][index]
        assert math.dist(point,record['before'])<.001 or math.dist(point,record['position'])<.001, 'Hospital node input mismatch: '+kind+' '+str(index)
        assert math.dist(record['before'][:2],record['position'][:2])<1e-6,'Hospital regrading changed existing XY'
        graph['nodes'][index]=record['position'];changed[index]=record
    original_edges=[e for e in graph['edges'] if e.get('integration')!='hospital_arrival']
    graph['edges']=original_edges
    def node(point):
        matches=[i for i,p in enumerate(graph['nodes']) if math.dist(point[:2],p[:2])<.001 and abs(point[2]-p[2])<.025]
        if matches:return matches[0]
        graph['nodes'].append(point);return len(graph['nodes'])-1
    joins=[]
    for connection in overlay['connections']:
        point=connection['point'];osm=str(connection['existingOsmId'])
        eligible={i for edge in original_edges if str(edge.get('osm_id'))==osm for i in [edge['a'],edge['b']]}
        choices=[i for i in eligible if math.dist(graph['nodes'][i][:2],point[:2])<.001]
        assert len(choices)==1,'Hospital connection must match exactly one node on its declared existing OSM road'
        index=choices[0]
        if kind=='vehicle':assert index==connection['existingNodeIndex'],'Hospital source node index mismatch'
        assert abs(graph['nodes'][index][2]-point[2])<=connection.get('surfaceToleranceM',.025),'Hospital junction height mismatch'
        joins.append({'id':connection['addedRoadId'],'node':index,'osm_node':connection['osm_node']})
    for road in overlay['addedRoads']:
        if not road.get('vehicleAllowed' if kind=='vehicle' else 'pedestrianAllowed',False):continue
        indices=[node(p) for p in road['points']]
        for join in joins:
            if join['id']==road['id']:assert join['node'] in indices,'Added road does not physically meet its declared graph connection'
        for a,b in zip(indices,indices[1:]):
            if a==b:continue
            graph['edges'].append({'a':a,'b':b,'length':math.dist(graph['nodes'][a],graph['nodes'][b]),'width':road['width'],'osm_id':str(road['osm_id']),'highway':'service' if road.get('road_class') is None else road['road_class'],'oneway':road.get('oneway','unknown'),'source':road.get('source'),'integration':'hospital_arrival','connection_id':road['id']})
    for edge in graph['edges']:edge['length']=round(math.dist(graph['nodes'][edge['a']],graph['nodes'][edge['b']]),6)
    return changed,joins

def apply(root,source):
    raw=source.read_bytes();data=json.loads(raw)
    wp=root/'dist/world-config.js';text=wp.read_text();world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'));np=root/'data/campus-navigation.json';nav=json.loads(np.read_text());rp=root/'data/entrance-sync-report.json';report=json.loads(rp.read_text())
    graphs={kind:json.loads((root/'data'/filename).read_text()) for kind,filename in [('vehicle','road-graph-3d.json'),('walking','walking-road-graph-3d.json')]}
    # All input validation precedes any filesystem mutations.
    changes={};joins={}
    for kind,graph in graphs.items():changes[kind],joins[kind]=merge_graph(graph,data,kind)
    vehicle=graphs['vehicle'];world['roads']=[r for r in world['roads'] if r['name'] in ['본관 앞길','본관 뒤편 길']]+[{'name':'CAMPUS_ROAD '+str(e.get('osm_id','')),'width':e['width'],'oneway':e.get('oneway','unknown'),'points':[cv(vehicle['nodes'][e['a']]),cv(vehicle['nodes'][e['b']])]} for e in vehicle['edges']]
    changed_edges={}
    for edge in vehicle['edges']:
        if any(edge[k] in changes['vehicle'] for k in ['a','b']):changed_edges.setdefault(str(edge.get('osm_id')),[]).append(edge)
    # Re-sample only nav points on the locally changed original edge segments.
    for road in nav['roads']:
        for point in road['points']:
            candidates=[]
            for edge in changed_edges.get(str(road.get('osm_id')),[]):
                a,b=[vehicle['nodes'][edge[k]] for k in ['a','b']];dx=b[0]-a[0];dy=b[1]-a[1];t=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/(dx*dx+dy*dy or 1)))
                distance=math.hypot(point[0]-a[0]-t*dx,point[1]-a[1]-t*dy)
                if distance<.001:candidates.append((distance,a[2]+t*(b[2]-a[2])))
            if candidates:point[2]=min(candidates)[1]
    identifiers={r['id'] for r in data['addedRoads']};nav['roads']=[r for r in nav['roads'] if r.get('id') not in identifiers]+[{**r,'vehicle':r.get('vehicleAllowed',False),'type':'service'} for r in data['addedRoads']]
    surfaces=[]
    for source_surface in data['walkableSurfaces']:
        vertices=source_surface.get('vertices') or source_surface.get('polygon');triangles=source_surface['triangles']
        assert vertices and all(len(t)==3 and all(0<=i<len(vertices) for i in t) for t in triangles),'Hospital surface requires native indexed triangles'
        surfaces.append({k:v for k,v in {**source_surface,'polygon':vertices}.items() if k!='vertices'})
    ids={s['id'] for s in surfaces}
    for target,is_world in [(world,True),(nav,False)]:target['walkableSurfaces']=[s for s in target.get('walkableSurfaces',[]) if s['id'] not in ids]+[{**s,'polygon':[cv(p) for p in s['polygon']]} if is_world else s for s in surfaces]
    target=next(d for d in data['destinations'] if d['buildingId']==162);door=next(r for r in report['records'] if r['building_id']==162 and r['selectedLandmark']);delta=target['thresholdZ']-door['closed_leaf_plane'][2]
    for key in ['door','closed_leaf_plane']:door[key][2]=target['thresholdZ']
    # Preserve known capsule-safe XY; source's position lies only 0.2m outside
    # the leaf. Exact final GLB sampling below resolves final landing height.
    if target.get('safe_arrival'):door['safe_arrival']=target['safe_arrival']
    else:door['safe_arrival'][2]+=delta
    if target.get('walk_stop'):door['outside_threshold']=target['walk_stop']
    else:door['outside_threshold'][2]+=delta
    door['route']=[door['safe_arrival'],door['outside_threshold']];door['geometryConnection']=False
    for collider in world['closedDoors']:
        if collider['name']==door['id']:collider['center'][1]+=delta
    for path in world['pedestrianPaths']:
        if path.get('entrance_id')==door['id']:path['points']=[cv(p) for p in door['route']]
    for path in nav['pedestrianPaths']:
        if path.get('entrance_id')==door['id']:path['points']=door['route']
    for destination in world['destinations']:
        if destination['id']=='162':destination['position']=cv(door['safe_arrival'])
    for landmark in nav['landmarks']:
        if str(landmark['id'])=='162':landmark['position']=door['safe_arrival']
    for change in report['destinationChanges']:
        if change['id']=='162':change['new_position']=cv(door['safe_arrival'])
    report['sourceHashes']['hospital_arrival']=hashlib.sha256(raw).hexdigest()
    for kind,filename in [('vehicle','road-graph-3d.json'),('walking','walking-road-graph-3d.json')]: (root/'data'/filename).write_text(json.dumps(graphs[kind],ensure_ascii=False,separators=(',',':'))+'\n')
    wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n');np.write_text(json.dumps(nav,ensure_ascii=False,separators=(',',':'))+'\n');rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (root/'data/hospital-arrival-overlay.json').write_bytes(raw)
    summary={'sourceSha256':hashlib.sha256(raw).hexdigest(),'addedRoads':len(data['addedRoads']),'exactGraphConnections':joins,'changedNodes':{k:len(v) for k,v in changes.items()},'walkableTriangles':sum(len(s['triangles']) for s in surfaces),'destinationId':'162','finalGLBHeightSampling':{'pending':True,'entranceId':door['id']},'pedestrianStopNetworkContinuity':'Requires final platform-to-sidewalk traversal; road endpoints alone do not verify access.'}
    (root/'data/hospital-sync-report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');return summary
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--game-root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();print(json.dumps(apply(args.game_root,args.source),ensure_ascii=False))
