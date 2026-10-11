#!/usr/bin/env python3
"""Sync final grading, preserving actors and only accepting bound road changes.

Usage: python3 scripts/sync-grade-revision.py ../realism_v2/verification
The first run snapshots only the pre-revision configuration needed for idempotent
height updates. This is source data, not runtime state or private metadata.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
from road_grade_contract import previous_road_heights, runtime_roads, approved_landmark_relocations

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'realism_v2/verification'

def read(name):return json.loads((SOURCE/name).read_text())
def config(name,var):return json.loads((ROOT/'dist'/name).read_text().split('export const '+var+' = ')[1].rstrip(';\n'))
def write_config(name,var,data,comment):
    (ROOT/'dist'/name).write_text(comment+'\nexport const '+var+' = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n')
def cv(p):return [p[0],p[2],-p[1]]
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)

world=config('world-config.js','WORLD');transit=config('transit-config.js','TRANSIT')
nav=read('navigation_graded.json');graph=read('road_graph_3d_graded.json');placements=read('transit_placements_graded.json');alignment=read('local_level_alignment.json')
baseline_path=ROOT/'data/grade-sync-baseline.json'
if baseline_path.exists():baseline=json.loads(baseline_path.read_text())
else:
    old_graph=json.loads((ROOT/'data/road-graph-3d.json').read_text())
    baseline={'source_world_sha256':hashlib.sha256((ROOT/'dist/world-config.js').read_bytes()).hexdigest(),'bounds':world['bounds'].copy(),'vehicle':old_graph,'mainRoads':[r for r in world['roads'] if r['name'] in ['본관 앞길','본관 뒤편 길']],'extraNPCs':world['extraNPCs'],'extraCars':world['extraCars'],'collisionBoxes':world['collisionBoxes'],'destination_positions':{d['id']:d['position'] for d in world['destinations']}}
    baseline_path.write_text(json.dumps(baseline,ensure_ascii=False,separators=(',',':'))+'\n')
# Older immutable baselines predate the bounds field. Preserve their exact bytes
# because the native actor-support contract now binds this source file's hash.
# These are the original game extents; later source-bound school stages expand them.
world['bounds']=baseline.get('bounds',{'minX':-487,'maxX':657,'minZ':-237,'maxZ':1117}).copy()
world.pop('baseCarGroundHeights',None)
for key in ['vehicleSurfaceRules','collisionPolygons','staticColliders','waterHazards','walkingAccessZones','closedDoors']:world[key]=[]
old_graph=baseline['vehicle'];vehicle=graph['vehicle']
# Original route XY stays strict; added roads and exact local XY repairs require native contracts.
old_node_heights=previous_road_heights(old_graph,vehicle,alignment.get('added_vehicle_connections',[]),alignment.get('corrected_vehicle_nodes',[]))
controls=alignment['controls']
def intent(x,y):
    vals=[];envelope=0
    for a,b,d,r in controls:
        distance=math.hypot(x-a,y-b)
        if distance<.001:return d
        if distance<r:
            weight=1/distance**4;vals.append((weight,d));envelope=max(envelope,1-smooth(distance/r))
    return sum(w*d for w,d in vals)/sum(w for w,d in vals)*envelope if vals else 0
segments=[]
for e in vehicle['edges']:
    a,b=e['a'],e['b']
    if old_node_heights[a] is None or old_node_heights[b] is None:continue
    pa,pb=vehicle['nodes'][a],vehicle['nodes'][b];da=pa[2]-old_node_heights[a];db=pb[2]-old_node_heights[b]
    if max(abs(da),abs(db))>=1e-7:segments.append((pa,pb,da,db))
def delta(x,y):
    best=None
    for a,b,da,db in segments:
        dx=b[0]-a[0];dy=b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy or 1)));distance=math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)
        if distance<15 and (best is None or distance<best[0]):best=(distance,da*(1-t)+db*t)
    base=intent(x,y)
    if best:
        weight=1-smooth((best[0]-5)/10);return base*(1-weight)+best[1]*weight
    return base

world['roads']=baseline['mainRoads']+runtime_roads(vehicle)
landmarks={str(l['id']):l for l in nav['landmarks']}
approved_destinations={};destination_updates=[]
student_contract=SOURCE.parent/'student_union_levels/integration_contract.json'
if student_contract.exists():
    approved_destinations=approved_landmark_relocations(json.loads(student_contract.read_text()),json.loads((SOURCE.parent/'entrances_a_overlay.json').read_text()))
for d in world['destinations']:
    if d['id'] not in landmarks:continue
    d.pop('entranceId',None);d.pop('entranceEvidence',None)
    point=cv(landmarks[d['id']]['position']);original=baseline['destination_positions'][d['id']]
    if any(abs(original[i]-point[i])>=.001 for i in [0,2]):
        approval=approved_destinations.get(d['id']);assert approval is not None,'Unbound landmark XY revision: '+d['id']
        arrival=cv(approval['position']);assert all(abs(arrival[i]-point[i])<1e-5 for i in [0,2]),'Landmark differs from final named entrance: '+d['id']
        destination_updates.append({'id':d['id'],'before':original,'after':point,'entrance_id':approval['entrance_id']})
    d['position']=point
actor_updates=[]
for key in ['extraNPCs','extraCars']:
    world[key]=json.loads(json.dumps(baseline[key]))
    for index,item in enumerate(world[key]):
        p=item['position'];change=delta(p[0],-p[2]);p[1]+=change
        if abs(change)>1e-6:actor_updates.append({'kind':key,'index':index,'delta_y':change,'position':p.copy()})
def boxkey(b):return (b.get('label',''),*[round(b[k][i],4) for k in ['min','max'] for i in [0,2]])
new_boxes={}
for b in nav['collisionBoxes']+nav.get('railCollisionBoxes',[]):
    converted={'min':[b['min'][0],b['min'][2],-b['max'][1]],'max':[b['max'][0],b['max'][2],-b['min'][1]],'label':b.get('label','pedestrian handrail')};new_boxes[boxkey(converted)]=converted
world['collisionBoxes']=[new_boxes.get(boxkey(b),b) for b in baseline['collisionBoxes']]
world['walkableSurfaces']=[{**sf,'polygon':[cv(p) for p in sf['polygon']]} for sf in nav.get('walkableSurfaces',[])]
world['pedestrianPaths']=[{**p,'points':[cv(q) for q in p['points']]} for p in nav.get('pedestrianPaths',[])]
for stop in transit['stops']:
    revised=next(s for s in placements['stops'] if s['id']==stop['id'])
    stop['position']=cv(revised['position']);stop['waitingPosition']=cv(revised['waitingPosition'])
route=placements['route'];revised=next(r for r in transit['routes'] if r['id']==route['id']);revised['points']=[cv(p) for p in route['points']]
pads=read('terrain_building_pads_graded.json');parking=next(b for b in pads if b.get('id')==164)
world['vehicleUnderpasses']=[{'id':'parking164_ground_aisle','roadName':'CAMPUS_ROAD 479886698','footprintLabel':parking['name'],'floorHeight':parking['base']+.35,'ceilingHeight':parking['base']+3.1,'accuracy':'Photo-informed open parking level; modeled aisle placement and clearance are approximate, not surveyed.'}]
world['elevationRevision']='realism_v2: coordinated approximate local site levels; not surveyed elevations'
write_config('world-config.js','WORLD',world,'// Derived map coordinates: © OpenStreetMap contributors, ODbL 1.0. Revised vertical grading only; see LICENSES.md.')
write_config('transit-config.js','TRANSIT',transit,'// Source-informed game transit, not live operational routing or timetable. Revised vertical grading follows final model.')
for filename,data in [('campus-navigation.json',nav),('road-graph-3d.json',vehicle),('walking-road-graph-3d.json',graph['walking']),('transit-placements.json',placements)]:
    (ROOT/'data'/filename).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
report={'source':'realism_v2/verification','preserved':['XY coordinates','destination count','NPC/car counts','mapped vehicle-route XY (densification allowed)','shuttle stop order'],'actor_height_updates':actor_updates,'building_base_changes':alignment['building_deltas'],'vehicle_nodes_changed':alignment['road_graph_node_changes'],'vehicle_graph_node_count':len(vehicle['nodes']),'vehicle_graph_original_node_count':len(old_graph['nodes']),'maximum_vehicle_grade':alignment['vehicle_graph_final_max_grade'],'explicit_added_vehicle_connections':alignment.get('added_vehicle_connections',[]),'v5_building_changes':alignment.get('v5_building_deltas',{}),'source_files':{name:hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in ['navigation_graded.json','road_graph_3d_graded.json','transit_placements_graded.json','local_level_alignment.json','terrain_building_pads_graded.json']}}
report['explicit_corrected_vehicle_nodes']=alignment.get('corrected_vehicle_nodes',[])
report['explicit_landmark_xy_revisions']=destination_updates
report['preserved']=['actor XY coordinates','destination XY except exact final named entrance revisions','NPC/car counts','mapped vehicle-route XY except explicit native node corrections','shuttle stop order']
(ROOT/'data/grade-sync-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
