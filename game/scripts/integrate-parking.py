#!/usr/bin/env python3
"""Convert the final native open-parking contract to game coordinates."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'realism_v2/verification/parking_gameplay.json'
raw=source.read_bytes();data=json.loads(raw);assert data['schema']=='chosun.parking164.v1'
def cv(p):return [p[0],p[2],-p[1]]
def route(r):return {**r,'points':[cv(p) for p in r['points']]}
colliders=[{**b,'center':cv(b['center']),'halfSize':[b['halfSize'][0],b['halfSize'][2],b['halfSize'][1]]} for b in data['colliders']]
config={'enabled':True,'schema':data['schema'],'buildingId':164,'sourceSha256':hashlib.sha256(raw).hexdigest(),'accuracy':data['accuracy'],'levelTops':data['levelTops'],'floorClearHeight':data['floorClearHeight'],'beamClearHeight':data['beamClearHeight'],'driveSurfaces':[{'name':s['name'],'kind':s['kind'],**({'level':s['level']} if 'level' in s else {'fromLevel':s['fromLevel'],'toLevel':s['toLevel'],'maximumGrade':s['maximumGrade']})} for s in data['driveSurfaces']],'colliders':colliders,'parkedCars':[{'name':c['name'],'level':c['level'],'position':cv(c['position']),'yaw':c['yaw']} for c in data['parkedCars']],'rampConnections':[route(r) for r in data['rampConnections']],'stairConnections':[route(r) for r in data['stairConnections']],'levelDriveRoutes':[route(r) for r in data['levelDriveRoutes']]}
(ROOT/'data/parking-gameplay.json').write_bytes(raw)
(ROOT/'dist/parking-config.js').write_text('// Open parking geometry contract. Internal layout and occupancy are inferred, not surveyed.\nexport const PARKING = '+json.dumps(config,ensure_ascii=False,separators=(',',':'))+';\n')
print(json.dumps({'levels':len(config['levelTops']),'ramps':len(config['rampConnections']),'parkedCars':len(config['parkedCars']),'colliders':len(colliders),'sourceSha256':config['sourceSha256']}))
