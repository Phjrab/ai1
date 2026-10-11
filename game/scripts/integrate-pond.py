#!/usr/bin/env python3
"""Integrate visible pond bridge support and explicitly nonwalkable water."""
import argparse,hashlib,json
from pathlib import Path

def cv(p):return [p[0],p[2],-p[1]]
def apply(root,source):
    raw=source.read_bytes();data=json.loads(raw);wp=root/'dist/world-config.js';text=wp.read_text();world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'));np=root/'data/campus-navigation.json';nav=json.loads(np.read_text())
    surfaces=[]
    for index,s in enumerate(data['walkable_surfaces']):
        assert s['vertices'] and all(len(t)==3 for t in s['triangles']),'Exact bridge/stair triangles required'
        surfaces.append({'id':'rv2_pond_surface_'+str(index),'label':s['name'],'polygon':s['vertices'],'triangles':s['triangles'],'kind':'pedestrian','vehicleAllowed':False})
    route={'id':'rv2_pond_cheongram_route','points':data['recommended_pedestrian_route'],'kind':'pedestrian','vehicleAllowed':False,'source':'Photo-informed pond bridge, modeled approach to existing OSM walking path'}
    assert data['recommended_pedestrian_route_reverse']==list(reversed(route['points']))
    for target,is_world in [(world,True),(nav,False)]:
        target['walkableSurfaces']=[s for s in target.get('walkableSurfaces',[]) if not s['id'].startswith('rv2_pond_surface_') and str(s.get('osm_id',''))!='468693339']+[{**s,'polygon':[cv(p) for p in s['polygon']]} if is_world else s for s in surfaces]
        target['pedestrianPaths']=[p for p in target.get('pedestrianPaths',[]) if p['id']!=route['id']]+[{**route,'points':[cv(p) for p in route['points']]} if is_world else route]
    def polygon(p):return [[q[0],-q[1]] for q in p]
    world['collisionPolygons']=[p for p in world.get('collisionPolygons',[]) if not p['id'].startswith('rv2_pond_')]+[{'id':'rv2_pond_'+p['id'],'label':p['id'],'polygon':polygon(p['polygon']),'minY':p['min_z'],'maxY':p['max_z'],'preciseVehicle':True} for p in data['obstacles'] if p['type']=='solid']
    water=data['water_nonwalkable'];exceptions=[{'id':e['id'],'mode':e['mode'],'polygon':polygon(e['polygon']),'minY':e['min_z'],'maxY':e['max_z'],'supportObject':e['support_object']} for e in water['exceptions']]
    assert exceptions and all(e['mode']=='pedestrian' for e in exceptions)
    world['waterHazards']=[p for p in world.get('waterHazards',[]) if p['id']!='pond468693339']+[{'id':'pond468693339','polygon':polygon(water['polygon']),'minY':water['min_z'],'maxY':water['max_z'],'exceptions':exceptions}]
    nav['waterHazards']=[p for p in nav.get('waterHazards',[]) if p['id']!='pond468693339']+[{'id':'pond468693339',**water}]
    wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n');np.write_text(json.dumps(nav,ensure_ascii=False,separators=(',',':'))+'\n');(root/'data/pond-overlay.json').write_bytes(raw)
    report={'sourceSha256':hashlib.sha256(raw).hexdigest(),'supportTriangles':sum(len(s['triangles']) for s in surfaces),'solidPolygons':len(data['obstacles']),'waterHazard':True,'pedestrianOnlyBridge':True,'routePoints':len(route['points']),'nativeNorthConnection':data['north_connection'],'finalRuntimeTraversal':'pending final combined GLB'}
    (root/'data/pond-sync-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');return report
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--game-root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();report=apply(args.game_root,args.source);print(json.dumps({k:v for k,v in report.items() if k!='nativeNorthConnection'}))
