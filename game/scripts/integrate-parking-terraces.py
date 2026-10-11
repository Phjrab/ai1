#!/usr/bin/env python3
"""Use actual flat parking tops and narrow transition lanes, not design extents."""
import argparse, hashlib, json, math
from pathlib import Path

def cv(p):return [p[0],p[2],-p[1]]
def apply(root,source):
    raw=source.read_bytes();data=json.loads(raw)
    assert data['version'].startswith('parking_terraces_v5')
    assert 'surface_top_triangles' in data and 'lane_top_triangles' in data, 'Applied geometry contract required; design-only input is insufficient'
    wp=root/'dist/world-config.js';text=wp.read_text();world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'))
    flats={z['object'] for z in data['parking_zones'] if z['parking_allowed']}
    lanes={z['object'] for z in data['transition_zones'] if z['vehicle_allowed']}
    denied={z['object'] for z in data['transition_zones'] if not z['vehicle_allowed']}
    assert not flats.intersection(denied) and not lanes.intersection(denied)
    records=[];counts={name:0 for name in flats|lanes|denied}
    for values,accepted,mode in [(data['surface_top_triangles'],flats,'allow'),(data['lane_top_triangles'],lanes,'allow'),(data['surface_top_triangles'],denied,'exclude')]:
        for triangle in values:
            if triangle['object'] not in accepted:continue
            points=triangle['vertices'];assert len(points)==3 and all(len(p)==3 and all(math.isfinite(v) for v in p) for p in points)
            records.append({'id':'terrace_surface_'+str(len(records)),'object':triangle['object'],'mode':mode,'polygon':[cv(p) for p in points]});counts[triangle['object']]+=1
    assert records and all(counts.values()), 'Each declared vehicle area must have exact applied top triangles'
    world['vehicleSurfaceRules']=records
    report={'sourceSha256':hashlib.sha256(raw).hexdigest(),'triangleCounts':counts,'allowedTriangles':sum(r['mode']=='allow' for r in records),'excludedTriangles':sum(r['mode']=='exclude' for r in records),'transitionPolicy':'Only lane_top_triangles allow driving; the whole transition polygon is never a drive corridor. Nonvehicle actual top triangles reject vehicle entry.','rejectedConnections':data.get('rejected_connections',[]),'finalRuntimeTraversal':'pending final combined GLB'}
    wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n')
    (root/'data/parking-terraces.json').write_bytes(raw)
    (root/'data/parking-terraces-sync-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--game-root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();print(json.dumps(apply(args.game_root,args.source)))
