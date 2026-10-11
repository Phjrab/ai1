#!/usr/bin/env python3
"""Copy one hash-bound native export into an immutable, reviewable input folder."""
import argparse,hashlib,json,os,shutil,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source_root',type=Path);p.add_argument('destination',type=Path);p.add_argument('--export-dir',default='realism_v2/game_export');a=p.parse_args();src=a.source_root.resolve();dst=a.destination.resolve();assert not dst.exists(),'Input freeze destination already exists'
mp=(src/a.export_dir/'manifest.json').resolve();assert mp.is_relative_to(src),'Manifest escaped source root';manifest_relative=str(mp.relative_to(src));raw=mp.read_bytes();m=json.loads(raw)
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
files={m['source']:m['source_sha256'],**m.get('module_sha256',{}),**m.get('sidecar_sha256',{}),manifest_relative:hashlib.sha256(raw).hexdigest()}
for relative,expected in m.get('export_tool_sha256',{}).items():
 assert relative not in files or files[relative]==expected,'Export tool conflicts with native-bound source: '+relative
 files[relative]=expected
for e in m['exports']:
 files[e['file']]=e['sha256']
 if e.get('object_inventory_file'):files[e['object_inventory_file']]=e['object_inventory_sha256']
for path,key in [('realism_v2/material_fallback.json','material_fallback_sha256')]:
 if m.get(key):files[path]=m[key]
selection=m.get('export_selection_revision')
if selection:
 files[selection['base_exporter_path']]=selection['base_exporter_sha256']
 files[selection['previous_manifest_path']]=selection['previous_manifest_sha256']
elif m.get('exporter_sha256'):files['realism_v2/scripts/export_game.py']=m['exporter_sha256']
if m.get('bounded_repair_plan_sha256'):files['realism_v2/final_repairs/patch_plan.json']=m['bounded_repair_plan_sha256']
staging=dst.with_name(dst.name+'.incomplete');assert not staging.exists(),'Review previous incomplete freeze before continuing';staging.mkdir(parents=True);started=time.monotonic()
for relative,expected in sorted(files.items()):
 source=(src/relative).resolve();assert source.is_relative_to(src),'Source path escaped root';assert sha(source)==expected,'Input changed before copy: '+relative
 target=staging/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);assert sha(target)==expected,'Copied input differs: '+relative
assert mp.read_bytes()==raw,'Export manifest changed while freezing inputs'
report={'sourceRoot':str(src),'nativeSha256':m['source_sha256'],'exportManifestSha256':hashlib.sha256(raw).hexdigest(),'exportManifestPath':manifest_relative,'files':files,'elapsedSeconds':time.monotonic()-started,'preservation':'Each copied file independently matches its export-bound SHA256; original native and shared files untouched.'};(staging/'INPUT_FREEZE.json').write_text(json.dumps(report,indent=2)+'\n');staging.rename(dst);print(json.dumps({'destination':str(dst),'nativeSha256':m['source_sha256'],'files':len(files),'elapsedSeconds':report['elapsedSeconds']},indent=2))
