#!/usr/bin/env python3
"""Use authored narrow frame/net primitives, never a whole-goal AABB."""
import argparse,hashlib,json
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--game-root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();root=args.game_root;raw=args.source.read_bytes();data=json.loads(raw)
assert data['schema']=='soccer-goals-v1' and len(data['goalPlacements'])==4
assert not data['walkableSurfaces'] and not data['pedestrianPaths'],'Unexpected goal support/navigation geometry'
wp=root/'dist/world-config.js';text=wp.read_text();world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'));colliders=[]
for i,c in enumerate(data['collisionBoxes']):
 assert c['kind'] in ['goal_frame','net'];assert min(c['halfSize'])<.25,'Goal primitive unexpectedly fills the open aperture'
 colliders.append({'name':'football_goal_'+str(i),'kind':c['kind'],'label':c['label'],'center':[c['center'][0],c['center'][2],-c['center'][1]],'halfSize':[c['halfSize'][0],c['halfSize'][2],c['halfSize'][1]],'yaw':c['yaw']})
world['staticColliders']=[c for c in world.get('staticColliders',[]) if not c['name'].startswith('football_goal_')]+colliders
wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n');(root/'data/football-goals.json').write_bytes(raw)
report={'sourceSha256':hashlib.sha256(raw).hexdigest(),'goals':4,'narrowColliders':len(colliders),'runtimeLOD':'Shared exported LOD0 and existing distance culling; no unimplemented LOD1 switch claimed','finalRuntimeTraversal':'pending combined GLB'};(root/'data/football-goals-sync-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
