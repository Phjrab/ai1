#!/usr/bin/env python3
"""Sync evidence-selected exterior portals and supported, closed-door approaches."""
from pathlib import Path
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[1]
revision=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'realism_v2'
inputs={key:(revision/path).read_bytes() for key,path in [('a','entrances_a_overlay.json'),('b','entrances_b_overlay.json'),('connections','entrance_connections/audit.json'),('surfaces','entrance_connections/navigation.json')]}
data={k:json.loads(v) for k,v in inputs.items()}
wp=ROOT/'dist/world-config.js';text=wp.read_text();world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'));nav=json.loads((ROOT/'data/campus-navigation.json').read_text())
connections={r['entrance_id']:r for r in data['connections']['records']}
def cv(p):return [p[0],p[2],-p[1]]
prefixes=tuple(data['surfaces']['remove_walkable_prefixes'])+('verified_entry_',)
for target in [world,nav]:
    target['walkableSurfaces']=[s for s in target.get('walkableSurfaces',[]) if not s['id'].startswith(prefixes)]
    target['pedestrianPaths']=[p for p in target.get('pedestrianPaths',[]) if not p['id'].startswith(prefixes)]
for surface in data['surfaces']['walkableSurfaces']:
    nav['walkableSurfaces'].append(surface);world['walkableSurfaces'].append({**surface,'polygon':[cv(p) for p in surface['polygon']]})
records=[];changes=[];world['closedDoors']=[]
for group in ['a','b']:
 for record in data[group]['records']:
    key=record['entrance_id'] if group=='a' else 'b_'+record['key'];identifier=str(record['building_id']);connection=connections.get(key)
    # B's two science doors are both tagged main in OSM. The audited western
    # portal is the named landmark; SW stays a separate physical access route.
    selected=record.get('is_landmark_destination',False) if group=='a' else record['key']!='science_southwest'
    arrival=connection['safe_arrival'] if connection else record['safe_arrival'];door=record['new_door'];normal=record['outward_normal'];length=math.hypot(*normal);normal=[v/length for v in normal]
    threshold=connection.get('walk_stop',connection.get('outside_threshold')) if connection else None
    if threshold is None:threshold=[door[0]+normal[0]*.65,door[1]+normal[1]*.65,door[2]]
    route=[list(p) for p in (connection['approach_path'] if connection else [arrival,door])]
    route[-1]=threshold
    width=record.get('width_m',record.get('width',2.4));height=record.get('height_m',2.7)
    recess=(.03 if group=='a' else 0)+(connection.get('portal_recess_m',0) if connection else 0)
    leaf=[door[0]-normal[0]*recess,door[1]-normal[1]*recess,door[2]]
    world['closedDoors'].append({'name':key,'kind':'closed_door','center':[leaf[0],leaf[2]+height/2,-leaf[1]],'halfSize':[width/2,height/2,.025],'yaw':math.atan2(normal[0],-normal[1])})
    # If the penultimate landing point is within the same small arrival pocket,
    # preserve it; support rays/runtime movement validate any remaining step.
    path={'id':'verified_entry_'+key,'kind':'closed_exterior_door_approach','points':route,'entrance_id':key,'building_id':record['building_id'],'closedDoor':True,'doorPosition':door,'stopBeforeDoorMeters':math.dist(threshold[:2],door[:2])}
    nav['pedestrianPaths'].append(path);world['pedestrianPaths'].append({**path,'points':[cv(p) for p in route],'doorPosition':cv(door)})
    destination=next((d for d in world['destinations'] if d['id']==identifier),None)
    if selected and destination:
        before=destination['position'];destination['position']=cv(arrival);destination['yaw']=math.atan2(normal[0],-normal[1]);destination['entranceId']=key
        destination['entranceEvidence']={'location':record.get('position_confidence',record.get('location_confidence')),'role':record['role'],'roleConfidence':record.get('role_confidence',record.get('role_confirmed_by_photo')),'thresholdLevel':record.get('level',record.get('source_node_tags',{}).get('level','unspecified; modeled exterior threshold'))}
        changes.append({'id':identifier,'entrance_id':key,'old_position':before,'new_position':destination['position']})
        for landmark in nav['landmarks']:
            if str(landmark['id'])==identifier:landmark['position']=arrival;landmark['entranceId']=key
    records.append({'id':key,'building_id':record['building_id'],'selectedLandmark':selected,'safe_arrival':arrival,'door':door,'closed_leaf_plane':leaf,'outside_threshold':threshold,'outward_normal':normal,'route':route,'closed':True,'geometryConnection':bool(connection),'sources':record.get('sources',[record.get('source_url'),record.get('source_photo_url')]),'locationConfidence':record.get('position_confidence',record.get('location_confidence')),'role':record['role']})
wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n');(ROOT/'data/campus-navigation.json').write_text(json.dumps(nav,ensure_ascii=False,separators=(',',':'))+'\n')
for key,filename in [('a','entrances-a.json'),('b','entrances-b.json'),('connections','entrance-connections.json'),('surfaces','entrance-surfaces.json')]: (ROOT/'data'/filename).write_bytes(inputs[key])
report={'coordinateSystem':'Blender XYZ metres','sourceHashes':{k:hashlib.sha256(v).hexdigest() for k,v in inputs.items()},'doorCount':len(records),'destinationChanges':changes,'preservedDestinationCount':len(world['destinations']),'records':records,'limitations':'Evidence supports exterior door location/role at varying confidence; thresholds, steps and local paths are reconstructed, not surveyed. Routes stop outside closed doors.'}
(ROOT/'data/entrance-sync-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'doors':len(records),'destinationUpdates':len(changes),'surfaces':len(data['surfaces']['walkableSurfaces'])}))
