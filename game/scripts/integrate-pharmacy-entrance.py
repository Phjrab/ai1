#!/usr/bin/env python3
"""Merge the locally verified pharmacy exterior approach; keep the portal closed."""
import argparse, hashlib, json, math
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('source',type=Path)
parser.add_argument('--game-root',type=Path,default=Path(__file__).resolve().parents[1])
args=parser.parse_args();root=args.game_root
raw=args.source.read_bytes();data=json.loads(raw)
assert data['replace_landmark_id']==156
wp=root/'dist/world-config.js';text=wp.read_text()
world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'))
np=root/'data/campus-navigation.json';nav=json.loads(np.read_text())
rp=root/'data/entrance-sync-report.json';report=json.loads(rp.read_text())
cv=lambda p:[p[0],p[2],-p[1]]
surfaces=[]
for surface in data['walkableSurfaces']:
    assert len(surface['polygon'])==3, 'Supplement must supply actual native triangles'
    surfaces.append({**surface,'triangles':[[0,1,2]]})
key='supp156_main';identifier='156';prefixes=['supp156_']+data['remove_walkable_prefixes']
door=data['closed_door'];normal=door['normal'];assert abs(math.hypot(*normal)-1)<1e-5
leaf=[*door['xy'],door['threshold_z']]
route=data['approach_path'];arrival=data['safe_arrival'];stop=data['outside_threshold']
assert math.dist(route[0],arrival)<1e-5 and math.dist(route[-1],stop)<1e-5
path={'id':'supp156_verified_side_approach','kind':'closed_exterior_door_approach','entrance_id':key,'building_id':156,'closedDoor':True,'points':route,'doorPosition':leaf}
for target,is_world in [(world,True),(nav,False)]:
    target['walkableSurfaces']=[s for s in target.get('walkableSurfaces',[]) if not any(s['id'].startswith(p) for p in prefixes)]+[{**s,'polygon':[cv(p) for p in s['polygon']]} if is_world else s for s in surfaces]
    target['pedestrianPaths']=[p for p in target.get('pedestrianPaths',[]) if not p['id'].startswith('supp156_')]+[{**path,'points':[cv(p) for p in route],'doorPosition':cv(leaf)} if is_world else path]
destination=next(d for d in world['destinations'] if d['id']==identifier)
prior=next((r for r in report['destinationChanges'] if r['id']==identifier and r['entrance_id']==key),None)
before=prior['old_position'] if prior else destination['position']
destination.update(position=cv(arrival),yaw=math.atan2(normal[0],-normal[1]),entranceId=key,entranceEvidence={'location':'photo_supported_facade_station_approximate','role':'closed exterior pharmacy portal','thresholdLevel':'modeled local forecourt; not surveyed'})
for landmark in nav['landmarks']:
    if str(landmark['id'])==identifier:landmark.update(position=arrival,entranceId=key)
world['walkingAccessZones']=[z for z in world.get('walkingAccessZones',[]) if not z['id'].startswith('pharmacy156_')]
for i,surface in enumerate(surfaces):
    polygon=surface['polygon'];world['walkingAccessZones'].append({'id':'pharmacy156_'+str(i),'labels':[destination['label']],'polygon':[[p[0],-p[1]] for p in polygon],'minY':min(p[2] for p in polygon)-.25,'maxY':max(p[2] for p in polygon)+.65})
world['closedDoors']=[d for d in world.get('closedDoors',[]) if d['name']!=key]+[{'name':key,'kind':'closed_door','center':[leaf[0],leaf[2]+door['height_m']/2,-leaf[1]],'halfSize':[door['width_m']/2,door['height_m']/2,.025],'yaw':math.atan2(normal[0],-normal[1])}]
record={'id':key,'building_id':156,'selectedLandmark':True,'safe_arrival':arrival,'door':leaf,'closed_leaf_plane':leaf,'outside_threshold':stop,'outward_normal':normal,'route':route,'closed':True,'geometryConnection':True,'sources':['entrances_supplement/overlay.json'],'locationConfidence':'photo_supported_facade_station_approximate','role':'closed exterior pharmacy portal'}
report['records']=[r for r in report['records'] if r['id']!=key]+[record]
report['destinationChanges']=[r for r in report['destinationChanges'] if r['id']!=identifier]+[{'id':identifier,'entrance_id':key,'old_position':before,'new_position':destination['position']}]
report['doorCount']=len(report['records']);report['sourceHashes']['pharmacy_supplement']=hashlib.sha256(raw).hexdigest()
wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n')
np.write_text(json.dumps(nav,ensure_ascii=False,separators=(',',':'))+'\n');rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(root/'data/pharmacy-entrance.json').write_bytes(raw)
summary={'sourceSha256':hashlib.sha256(raw).hexdigest(),'destinationId':identifier,'walkableTriangles':len(surfaces),'closedPortal':True,'heightScopedProxyZones':len(surfaces),'approach':'Verified side route; front steps remain a secondary physical route. Final combined GLB/runtime QA required.'}
(root/'data/pharmacy-sync-report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary))
