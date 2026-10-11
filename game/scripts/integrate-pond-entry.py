#!/usr/bin/env python3
"""Consume only the native-bound two-tread pond entry repair."""
import argparse,hashlib,json,math
from pathlib import Path

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cv(p):return [p[0],p[2],-p[1]]
def apply(root,source):
    data=json.loads(source.read_text());manifest=json.loads((root/'data/native-export-manifest.json').read_text())
    key='realism_v2/pond_entry_steps/overlay.json'
    assert manifest['sidecar_sha256'].get(key)==digest(source),'Pond entry overlay must be bound to the native export'
    assert data['source_pond_overlay_sha256']==digest(root/'data/pond-overlay.json'),'Pond entry source overlay changed'
    assert data['water_exceptions_unchanged'] and data['water_polygon_y_separation_m']>0
    assert data['source_originals_preserved'] and not data['modified_existing_objects']
    route_id=data['source_route_id'];assert route_id=='rv2_pond_cheongram_route'
    surfaces=[]
    for item in data['walkableSurfaces']:
        assert item['mesh'] in data['support_object_names'] and item['walkable'] and item['vehicle'] is False
        points=item['polygon'];assert all(len(p)==3 and all(math.isfinite(x) for x in p) for p in points)
        assert all(len(t)==3 and all(isinstance(i,int) and 0<=i<len(points) for i in t) for t in item['triangles'])
        surfaces.append({**item,'kind':'pedestrian','vehicleAllowed':False,'label':item['mesh']})
    assert sum(len(s['triangles']) for s in surfaces)==4,'Expected exact two-tread top geometry'
    wp=root/'dist/world-config.js';text=wp.read_text();world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'));np=root/'data/campus-navigation.json';nav=json.loads(np.read_text())
    for target,is_world in [(world,True),(nav,False)]:
        routes=[p for p in target['pedestrianPaths'] if p['id']==route_id];assert len(routes)==1
        expected=[cv(p) for p in data['source_route_points']] if is_world else data['source_route_points']
        replacement=[cv(p) for p in data['replacement_route_points']] if is_world else data['replacement_route_points']
        assert routes[0]['points'] in [expected,replacement],'Exact original pond route changed'
        routes[0]['points']=replacement;routes[0]['entryRepairSource']=key
        ids={s['id'] for s in surfaces};target['walkableSurfaces']=[s for s in target['walkableSurfaces'] if s['id'] not in ids]+[{**s,'polygon':[cv(p) for p in s['polygon']]} if is_world else s for s in surfaces]
    wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n');np.write_text(json.dumps(nav,ensure_ascii=False,separators=(',',':'))+'\n')
    (root/'data/pond-entry-steps.json').write_bytes(source.read_bytes())
    report={'sourceSha256':digest(source),'sourcePondOverlaySha256':data['source_pond_overlay_sha256'],'routeId':route_id,'sourcePoints':len(data['source_route_points']),'finalPoints':len(data['replacement_route_points']),'supportTriangles':4,'waterAndExistingSupportPreserved':True,'runtimeTraversal':'pending combined native export'}
    (root/'data/pond-entry-sync-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--game-root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();print(json.dumps(apply(args.game_root,args.source)))
