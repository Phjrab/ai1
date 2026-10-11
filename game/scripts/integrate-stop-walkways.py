#!/usr/bin/env python3
"""Merge source-bound hospital stop walks without inventing a road crossing."""
import argparse, copy, hashlib, json, math
from pathlib import Path

OWNER = 'hospital_stop_walkways'
def cv(point): return [point[0], point[2], -point[1]]
def finite_point(point): return len(point) == 3 and all(math.isfinite(x) for x in point)

def apply(root, source):
    raw = source.read_bytes(); data = json.loads(raw)
    wp = root/'dist/world-config.js'; text = wp.read_text()
    world = json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'))
    np = root/'data/campus-navigation.json'; nav = json.loads(np.read_text())
    tp = root/'dist/transit-config.js'; transit = json.loads(tp.read_text().split('export const TRANSIT = ')[1].rstrip(';\n'))
    gp = root/'data/walking-road-graph-3d.json'; graph = json.loads(gp.read_text())
    assert data['module'] == OWNER
    paths = copy.deepcopy(data['pedestrianPaths']); by_id = {p['id']:p for p in paths}
    assert len(by_id) == len(paths), 'Duplicate hospital stop path'
    connections = {str(c['stop_id']):c for c in data['stopConnections']}
    assert {'1149','1150'} <= connections.keys(), 'Both hospital stop statuses must be explicit'
    blocked = connections['1150']
    assert blocked['status'] == 'blocked_unverified_crossing' and blocked.get('connectToCampus') is False and blocked.get('hospital_route') is None, 'Unverified 1150 crossing must remain disconnected'
    surfaces = []
    for s in data['walkableSurfaces']:
        vertices = s['vertices']; triangles = s['triangles']
        assert vertices and all(finite_point(p) for p in vertices)
        assert triangles and all(len(t)==3 and all(isinstance(i,int) and 0<=i<len(vertices) for i in t) for t in triangles), 'Actual indexed walk triangles required'
        surfaces.append({**{k:v for k,v in s.items() if k!='vertices'}, 'polygon':vertices, 'integration':OWNER, 'vehicleAllowed':False, 'kind':'pedestrian'})
    for p in paths:
        assert len(p['points'])>1 and all(finite_point(q) for q in p['points'])
        assert p.get('roadCrossingCreated') is False, 'This contract cannot create an unverified crossing'
        p.update(integration=OWNER, vehicleAllowed=False, pedestrianAllowed=True)
        if str(p['stop_id']) == '1150':
            assert p.get('connectToCampus') is False and p.get('hospital_route') is None and 'existingWalkingNodeIndex' not in p, '1150 must stay on its own side'
    for stop_id, c in connections.items():
        p = by_id[c['path_id']]
        assert str(p['stop_id']) == stop_id
        assert math.dist(p['points'][-1], c['waitingPosition']) < .001, 'Stop path must reach its actual waiting surface'
        matches = [s for s in transit['cityStops'] if str(s.get('ars_id')) == stop_id]
        assert len(matches)==1 and matches[0].get('created_geometry'), 'Path must name one rendered city stop'
        stop = matches[0]
        assert math.dist(stop['waitingPosition'], cv(c['waitingPosition'])) < .03, 'Transit and walkway inputs have different waiting positions'
        stop['pedestrianConnection'] = {**c, 'waitingPosition':cv(c['waitingPosition'])}
    connected = by_id[connections['1149']['path_id']]
    arrival = next(d['position'] for d in world['destinations'] if str(d['id'])=='162')
    assert math.dist([arrival[0],arrival[2]], [connected['points'][0][0],-connected['points'][0][1]]) < .01, 'Hospital walk must start at the retained safe arrival'
    # The producer supplies an exact source-node anchor on the shared drive.
    # The opposite-side path is its own component; no proximity links are made.
    graph['edges'] = [e for e in graph['edges'] if e.get('integration')!=OWNER]
    isolated=graph.setdefault('hospitalStopWalkwayIsolatedNodes',{})
    isolated_indices={i for indices in isolated.values() for i in indices}
    if any(i in isolated_indices for e in graph['edges'] for i in [e['a'],e['b']]):
        raise ValueError('An unverified opposite-side walk was joined to another graph route')
    joins = []
    for p in paths:
        anchor = p.get('existingWalkingNodeIndex'); anchor_position = None
        if anchor is not None:
            expected = p['existingWalkingNodeXY']
            assert math.dist(graph['nodes'][anchor][:2],expected)<.001, 'Hospital source walking node mismatch'
            nearest = min(p['points'], key=lambda q:math.dist(q[:2],expected))
            assert math.dist(nearest[:2],expected)<.001, 'Walk path never meets its exact graph anchor'
            assert abs(graph['nodes'][anchor][2]-nearest[2])<.5, 'Anchor is on a different vertical surface'
            graph['nodes'][anchor][2]=nearest[2]; anchor_position=nearest
            joins.append({'path':p['id'],'node':anchor,'position':graph['nodes'][anchor]})
        disconnected=p.get('connectToCampus') is False
        eligible=isolated.get(p['id'],[]) if disconnected else [i for i in range(len(graph['nodes'])) if i not in isolated_indices]
        cache = {tuple(round(v,6) for v in graph['nodes'][i]):i for i in eligible}
        indices=[]
        for point in p['points']:
            if anchor_position is not None and math.dist(point,anchor_position)<.001: index=anchor
            else:
                key=tuple(round(v,6) for v in point); index=cache.get(key)
                if index is None: index=len(graph['nodes']); graph['nodes'].append(point); cache[key]=index
            indices.append(index)
        if disconnected:
            isolated[p['id']]=list(dict.fromkeys(indices));isolated_indices.update(indices)
        for a,b in zip(indices,indices[1:]):
            if a!=b: graph['edges'].append({'a':a,'b':b,'length':math.dist(graph['nodes'][a],graph['nodes'][b]),'width':p['width'],'highway':'footway','oneway':False,'pedestrian':True,'vehicle':False,'integration':OWNER,'connection_id':p['id'],'stop_id':str(p['stop_id']),'evidence':p['kind']})
    for e in graph['edges']: e['length']=round(math.dist(graph['nodes'][e['a']],graph['nodes'][e['b']]),6)
    adjacency={}
    for e in graph['edges']:
        adjacency.setdefault(e['a'],set()).add(e['b']);adjacency.setdefault(e['b'],set()).add(e['a'])
    reached={j['node'] for j in joins};pending=list(reached)
    while pending:
        for node in adjacency.get(pending.pop(),set())-reached:reached.add(node);pending.append(node)
    assert not reached.intersection(isolated_indices), 'Stop 1150 must not gain an unverified hospital graph connection'
    for target,is_world in [(world,True),(nav,False)]:
        target['walkableSurfaces']=[s for s in target.get('walkableSurfaces',[]) if s.get('integration')!=OWNER]+[{**s,'polygon':[cv(p) for p in s['polygon']]} if is_world else s for s in surfaces]
        target['pedestrianPaths']=[p for p in target.get('pedestrianPaths',[]) if p.get('integration')!=OWNER]+[{**p,'points':[cv(q) for q in p['points']],'safe_arrival':cv(p['safe_arrival']) if p.get('safe_arrival') else None} if is_world else p for p in paths]
        target['cityStopPedestrianConnections']=[{**c,'waitingPosition':cv(c['waitingPosition'])} if is_world else c for c in connections.values()]
    polygons=[]
    for p in data['collisionPolygons']:
        assert p['max_z']>p['min_z'] and len(p['polygon'])>=3
        polygons.append({'id':'hospital_walk_'+p['id'],'label':p['id'],'polygon':[[q[0],-q[1]] for q in p['polygon']],'minY':p['min_z'],'maxY':p['max_z'],'integration':OWNER,'preciseVehicle':True})
    world['collisionPolygons']=[p for p in world.get('collisionPolygons',[]) if p.get('integration')!=OWNER]+polygons
    report={'sourceSha256':hashlib.sha256(raw).hexdigest(),'supportTriangles':sum(len(s['triangles']) for s in surfaces),'pedestrianPaths':len(paths),'exactWalkingGraphAnchors':joins,'stopConnections':list(connections.values()),'vehicleGraphUnchanged':True,'limitations':data.get('limitations',[]),'runtimeTraversal':'pending final combined GLB'}
    # Validation is complete before any derived file is written.
    wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n')
    tp.write_text('// Source-reviewed city stop pedestrian connectivity.\nexport const TRANSIT = '+json.dumps(transit,ensure_ascii=False,separators=(',',':'))+';\n')
    for path,value in [(np,nav),(gp,graph)]: path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n')
    (root/'data/hospital-stop-walkways.json').write_bytes(raw)
    (root/'data/hospital-stop-walkways-sync-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--game-root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args()
    print(json.dumps(apply(args.game_root,args.source),ensure_ascii=False))
