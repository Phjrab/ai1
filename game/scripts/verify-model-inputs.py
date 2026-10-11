#!/usr/bin/env python3
"""Reject a mixed model/material/gameplay-sidecar revision before integration."""
from pathlib import Path
import hashlib,json,sys,os
from repair_provenance import verify_repair_provenance
ROOT=Path(os.environ.get('CHOSUN_INPUT_ROOT',Path(__file__).resolve().parents[2]))
EXPORT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'realism_v2/game_export'
manifest=json.loads((EXPORT/'manifest.json').read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(ROOT/manifest['source'])==manifest['source_sha256'],'Native source has changed since export'
for item in manifest['exports']:assert sha(ROOT/item['file'])==item['sha256'],'Export bytes changed: '+item['file']
selection=manifest.get('export_selection_revision')
if selection:
 assert selection['native_geometry_unchanged'] is True,'Export-only revision changed native geometry'
 assert sha(ROOT/selection['base_exporter_path'])==selection['base_exporter_sha256'],'Original native-bound exporter changed'
 previous_raw=(ROOT/selection['previous_manifest_path']).read_bytes();assert hashlib.sha256(previous_raw).hexdigest()==selection['previous_manifest_sha256'],'Previous export manifest changed'
 previous=json.loads(previous_raw)
 for key in ['source_sha256','module_sha256','sidecar_sha256']:assert previous[key]==manifest[key],'Export selection changed native authoring bindings: '+key
 assert previous['exporter_sha256']==selection['base_exporter_sha256'],'Export selection base exporter does not match its predecessor'
 assert manifest['exporter_sha256'] in manifest.get('export_tool_sha256',{}).values(),'Selected exporter is not bound as an export tool'
elif manifest.get('exporter_sha256'):assert sha(ROOT/'realism_v2/scripts/export_game.py')==manifest['exporter_sha256'],'Exporter source differs from the bound selection contract'
for item in manifest['exports']:
    if item.get('object_inventory_file'):assert sha(ROOT/item['object_inventory_file'])==item['object_inventory_sha256'],'Export object inventory changed'
if manifest.get('material_fallback_sha256'):assert sha(ROOT/'realism_v2/material_fallback.json')==manifest['material_fallback_sha256'],'Material fallback changed after export'
assert manifest.get('sidecar_sha256'),'Native export must bind its gameplay sidecars'
for path,expected in manifest.get('module_sha256',{}).items():assert sha(ROOT/path)==expected,'Model module changed after native freeze: '+path
for path,expected in manifest.get('sidecar_sha256',{}).items():assert sha(ROOT/path)==expected,'Gameplay sidecar changed after native freeze: '+path
for path,expected in manifest.get('export_tool_sha256',{}).items():
 target=(ROOT/path).resolve();assert target.is_relative_to(ROOT.resolve()),'Export tool escaped fixed input root'
 assert path not in manifest.get('module_sha256',{}) or manifest['module_sha256'][path]==expected,'Export tool conflicts with native source pin'
 assert sha(target)==expected,'Export tool source changed: '+path
repair=verify_repair_provenance(manifest,ROOT)
print(json.dumps({'verified':True,'boundedRepair':repair,'nativeSha256':manifest['source_sha256'],'exports':len(manifest['exports']),'boundSidecars':len(manifest.get('sidecar_sha256',{}))}))
