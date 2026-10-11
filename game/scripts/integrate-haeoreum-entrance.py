#!/usr/bin/env python3
"""Use the final Haeoreum physical portal and stair route after the A/B overlay."""
import argparse, copy, hashlib, json, math
from pathlib import Path

def cv(p): return [p[0],p[2],-p[1]]
def apply(root, source):
    raw=source.read_bytes(); data=json.loads(raw)
    wp=root/'dist/world-config.js'; text=wp.read_text(); world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'))
    np=root/'data/campus-navigation.json'; nav=json.loads(np.read_text())
    rp=root/'data/entrance-sync-report.json'; report=json.loads(rp.read_text())
    surface_ids={s['id'] for s in nav['walkableSurfaces']}
    assert all(s['id'] in surface_ids for s in data['walkableSurfaces']), 'Haeoreum stair support must already be in the graded navigation'
    updates=[]
    for entry in data['entrances']:
        assert entry['building_id']==128 and entry['is_landmark_destination']
        key=entry['entrance_id']; record=next(r for r in report['records'] if r['id']==key)
        leaf=entry['door_plane']; assert len(leaf)==3 and all(math.isfinite(v) for v in leaf), 'Exact final physical door plane required'
        assert math.isfinite(entry['threshold_z'])
        route=copy.deepcopy(entry['approach_path']); assert len(route)>1
        assert math.dist(route[0],entry['safe_arrival'])<.001 and math.dist(route[-1],entry['walk_stop'])<.001
        assert abs(entry['walk_stop'][2]-entry['threshold_z'])<.05, 'Walk stop must meet the physical threshold'
        previous=record['closed_leaf_plane']; collider=next(c for c in world['closedDoors'] if c['name']==key)
        delta=[a-b for a,b in zip(cv(leaf),cv(previous))]
        collider['center']=[v+delta[i] for i,v in enumerate(collider['center'])]
        record.update(safe_arrival=entry['safe_arrival'],outside_threshold=entry['walk_stop'],route=route,closed_leaf_plane=leaf,geometryConnection=True,verticalRevision='Final Haeoreum stair and physical portal')
        record['door'][2]=entry['threshold_z']
        for target,is_world in [(world,True),(nav,False)]:
            paths=[p for p in target['pedestrianPaths'] if p.get('entrance_id')==key]
            assert len(paths)==1, 'Expected one A/B portal approach to replace'
            paths[0]['points']=[cv(p) for p in route] if is_world else route
            paths[0]['doorPosition']=cv(record['door']) if is_world else record['door']
        destination=next(d for d in world['destinations'] if str(d['id'])=='128');destination['position']=cv(entry['safe_arrival'])
        landmark=next(d for d in nav['landmarks'] if str(d['id'])=='128');landmark['position']=entry['safe_arrival']
        change=next(c for c in report['destinationChanges'] if str(c['id'])=='128');change['new_position']=destination['position']
        updates.append({'id':key,'safe_arrival':entry['safe_arrival'],'physical_door_plane':leaf,'route_points':len(route)})
    assert len(updates)==1, 'Exactly one Haeoreum entrance revision expected'
    report['sourceHashes']['haeoreum_stair']=hashlib.sha256(raw).hexdigest()
    wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n')
    np.write_text(json.dumps(nav,ensure_ascii=False,separators=(',',':'))+'\n');rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (root/'data/haeoreum-stair.json').write_bytes(raw)
    summary={'sourceSha256':hashlib.sha256(raw).hexdigest(),'updates':updates,'surfacesDuplicated':0,'finalRuntimeTraversal':'pending combined GLB'}
    (root/'data/haeoreum-stair-sync-report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--game-root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();print(json.dumps(apply(args.game_root,args.source)))
