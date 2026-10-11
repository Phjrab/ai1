#!/usr/bin/env python3
"""Add the user-confirmed IT roof bridge's final navigation contract."""
from pathlib import Path
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'realism_v2/it_roof_review/bridge_navigation.json'
raw=source.read_bytes();bridge=json.loads(raw)
wp=ROOT/'dist/world-config.js';text=wp.read_text();world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'))
nav=json.loads((ROOT/'data/campus-navigation.json').read_text())
def cv(p):return [p[0],p[2],-p[1]]
quads=[]
for branch in bridge.get('bridge_branches',[{'points':bridge['bridge_points'],'width':bridge['width']}]):
    for a,b in zip(branch['points'],branch['points'][1:]):
        dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy);nx=-dy/length*branch['width']/2;ny=dx/length*branch['width']/2
        quads.append([[a[0]-nx,a[1]-ny,a[2]],[b[0]-nx,b[1]-ny,b[2]],[b[0]+nx,b[1]+ny,b[2]],[a[0]+nx,a[1]+ny,a[2]]])
roof=[[*p,bridge['roof_z']] for p in bridge['roof_polygon']]
surfaces=[{'id':'rv2_it_roof_bridge_deck_'+str(i),'kind':'user_confirmed_bridge_approximate_geometry','polygon':quad,'triangles':[[0,1,2],[0,2,3]],'source':bridge['source']} for i,quad in enumerate(quads)]+[{'id':'rv2_it_annex_roof','kind':'low_annex_roof_walk','polygon':roof,'triangles':[[0,i,i+1] for i in range(1,len(roof)-1)],'source':bridge['source']}]
world['walkableSurfaces']=[s for s in world.get('walkableSurfaces',[]) if not s['id'].startswith('rv2_it_')]+[{**s,'polygon':[cv(p) for p in s['polygon']]} for s in surfaces]
nav['walkableSurfaces']=[s for s in nav.get('walkableSurfaces',[]) if not s['id'].startswith('rv2_it_')]+surfaces
path={'id':'rv2_it_roof_bridge_walk','kind':'roof_bridge','points':bridge['route'],'source':bridge['source']}
world['pedestrianPaths']=[p for p in world.get('pedestrianPaths',[]) if p['id']!=path['id']]+[{**path,'points':[cv(p) for p in path['points']]}]
nav['pedestrianPaths']=[p for p in nav.get('pedestrianPaths',[]) if p['id']!=path['id']]+[path]
world['walkingAccessZones']=[{'id':'it_low_annex_roof','labels':['IT융합대학'],'polygon':[[p[0],-p[1]] for p in bridge['roof_polygon']],'minY':bridge['collision_exemption_z_range'][0],'maxY':bridge['collision_exemption_z_range'][1]}]+[{'id':'it_roof_bridge_'+str(i),'labels':['IT융합대학'],'polygon':[[p[0],-p[1]] for p in quad],'minY':bridge['collision_exemption_z_range'][0],'maxY':bridge['collision_exemption_z_range'][1]} for i,quad in enumerate(quads)]
world['collisionBoxes']=[b for b in world['collisionBoxes'] if not b.get('label','').startswith(('IT rooftop bridge guard ','IT lounge '))]
for i,box in enumerate(bridge['guard_boxes']):
    record={'min':[box['min'][0],box['min'][2],-box['max'][1]],'max':[box['max'][0],box['max'][2],-box['min'][1]],'label':'IT rooftop bridge guard '+str(i)}
    if box.get('collision_shape')=='vertical_segment_capsule':
        if len(box['segment'])!=2 or not 0<box['radius']<.5:raise ValueError('Invalid exact rail segment')
        record['segmentCapsule']={'a':cv(box['segment'][0]),'b':cv(box['segment'][1]),'radius':box['radius']}
    world['collisionBoxes'].append(record)
destination={'id':'138_roof_bridge','label':'IT융합대학 낮은 별관 옥상 · 구름다리','position':cv(bridge['roof_destination']),'yaw':0,'source':bridge['source'],'heightBand':bridge['collision_exemption_z_range']}
world['destinations']=[d for d in world['destinations'] if d['id'] not in [destination['id'],'138_lounge']]+[destination]
wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n')
(ROOT/'data/campus-navigation.json').write_text(json.dumps(nav,ensure_ascii=False,separators=(',',':'))+'\n')
(ROOT/'data/it-rooftop-bridge.json').write_bytes(raw)
(ROOT/'data/rooftop-sync-report.json').write_text(json.dumps({'sourceSha256':hashlib.sha256(raw).hexdigest(),'addedDestination':destination['id'],'preservedExistingDestinations':len(world['destinations'])-1,'guardBoxes':len(bridge['guard_boxes']),'accuracy':bridge['confidence']},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'destination':destination['id'],'guardBoxes':len(bridge['guard_boxes']),'routePoints':len(bridge['route'])}))
