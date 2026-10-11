#!/usr/bin/env python3
"""Copy the bound GLB tree-instance metadata; never spawn duplicate trees."""
import argparse,hashlib,json
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--game-root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();raw=args.source.read_bytes();data=json.loads(raw)
assert data['version']=='greenery_infill_1.0' and data['count']==len(data['plantings'])
assert data['game_contract']['sidecar_only_metadata'] and not data['game_contract']['native_render_instances_exported']
assert len({p['id'] for p in data['plantings']})==data['count']
assert all(p['tree_trunk'] and p['group']=='greenery_infill' and 0<p['trunk_radius_m']<2 for p in data['plantings'])
(args.game_root/'data/greenery-infill.json').write_bytes(raw)
report={'sourceSha256':hashlib.sha256(raw).hexdigest(),'sourceCount':data['count'],'spawnedFromSidecar':0,'expectedRenderStrategy':data['game_contract']['geometry'],'finalGLBInstanceAndGroundChecks':'pending'};(args.game_root/'data/greenery-sync-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
