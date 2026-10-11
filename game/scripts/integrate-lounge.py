#!/usr/bin/env python3
"""Integrate the six-table lounge, its two mapped doors and exact local guards."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'realism_v2/it_lounge_review/lounge_navigation.json'
raw=source.read_bytes();lounge=json.loads(raw)
assert lounge['table_count']==6 and len(lounge['table_objects'])==6 and len(lounge['table_blockers'])==6
wp=ROOT/'dist/world-config.js';text=wp.read_text();world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'))
nav=json.loads((ROOT/'data/campus-navigation.json').read_text())
def cv(p):return [p[0],p[2],-p[1]]
surfaces=[{'id':'rv2_it_lounge_floor_'+str(i),'kind':'user_confirmed_lounge_approximate_dimensions','polygon':[[*p,lounge['floor_z']] for p in polygon],'triangles':[[0,j,j+1] for j in range(1,len(polygon)-1)],'source':'User-confirmed lounge and mapped north entrances; inferred interior layout'} for i,polygon in enumerate(lounge['floor_polygons'])]
paths=[{'id':'rv2_it_lounge_'+key,'kind':'lounge_access','points':lounge[key]} for key in ['roof_to_lounge_route','mapped_entrance_route','level5_entrance_route']]
paths += [{'id':'rv2_it_lounge_table_'+str(item['index']),'kind':'round_table_access','points':item['route']} for item in lounge['table_approaches']]
for target,is_world in [(world,True),(nav,False)]:
    target['walkableSurfaces']=[s for s in target.get('walkableSurfaces',[]) if not s['id'].startswith('rv2_it_lounge_')]+[{**s,'polygon':[cv(p) for p in s['polygon']]} if is_world else s for s in surfaces]
    target['pedestrianPaths']=[p for p in target.get('pedestrianPaths',[]) if not p['id'].startswith('rv2_it_lounge_')]+[{**p,'points':[cv(v) for v in p['points']]} if is_world else p for p in paths]
exemption=lounge['coarse_IT_collision_exemption']
world['walkingAccessZones']=[z for z in world.get('walkingAccessZones',[]) if not z['id'].startswith('it_lounge_')]+[{'id':'it_lounge_'+str(i),'labels':['IT융합대학'],'polygon':[[p[0],-p[1]] for p in polygon],'minY':exemption['z_range'][0],'maxY':exemption['z_range'][1]} for i,polygon in enumerate(exemption['polygons'])]
world['collisionBoxes']=[b for b in world['collisionBoxes'] if not b.get('label','').startswith('IT lounge ')]
for kind,boxes in [('guard',lounge['guard_boxes']),('table',lounge['table_blockers'])]:
    for i,box in enumerate(boxes):world['collisionBoxes'].append({'min':[box['min'][0],box['min'][2],-box['max'][1]],'max':[box['max'][0],box['max'][2],-box['min'][1]],'label':'IT lounge '+kind+' '+str(i)})
destination={'id':'138_lounge','label':'IT융합대학 5층 휴게공간 · 원형 테이블 6개','position':cv(lounge['lounge_destination']),'yaw':0,'heightBand':exemption['z_range'],'source':'User-confirmed six round bench tables; OSM north main/level=5 entrances'}
world['destinations']=[d for d in world['destinations'] if d['id']!=destination['id']]+[destination]
wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n')
(ROOT/'data/campus-navigation.json').write_text(json.dumps(nav,ensure_ascii=False,separators=(',',':'))+'\n')
(ROOT/'data/it-lounge.json').write_bytes(raw)
(ROOT/'data/lounge-sync-report.json').write_text(json.dumps({'sourceSha256':hashlib.sha256(raw).hexdigest(),'addedDestination':destination['id'],'tableCount':6,'walkPaths':len(paths),'guardBoxes':len(lounge['guard_boxes']),'evidence':lounge['evidence']},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'destination':destination['id'],'tables':6,'walkPaths':len(paths)}))
