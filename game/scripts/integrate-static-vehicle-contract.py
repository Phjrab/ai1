#!/usr/bin/env python3
"""Copy the final original-car pose mapping; the GLB already contains each car."""
import argparse,hashlib,json
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--game-root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();raw=args.source.read_bytes();data=json.loads(raw)
assert data['campus_count']==117 and len(data['original_campus_cars'])==117
assert len({c['name'] for c in data['original_campus_cars']})==117
assert all(len(c['position'])==3 and len(c['matrix_world'])==4 and c['wheel_contacts'] for c in data['original_campus_cars'])
(args.game_root/'data/static-vehicle-poses.json').write_bytes(raw)
report={'sourceSha256':hashlib.sha256(raw).hexdigest(),'originalCampusCars':117,'deckCars':len(data.get('deck_cars',[])),'spawnedFromSidecar':0,'controllableCars':11,'finalGLBPoseAndContactChecks':'pending','trafficClearanceExpectation':'No correctly grounded source car should be hidden as a substitute for fixing road intrusion.'};(args.game_root/'data/static-vehicle-sync-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
