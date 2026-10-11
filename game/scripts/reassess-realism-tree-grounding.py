#!/usr/bin/env python3
"""Compare signed tree embed depth with the exact native planting contract."""
import hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def validate(root=ROOT,execute=False):
 runpath='tests/runtime-runs/realism.json'; source='tests/runtime-runs/realism-results/realism-results.json'
 run=json.loads((root/runpath).read_text());manifest=json.loads((root/'data/native-export-manifest.json').read_text());raw_hashes={pathlib.Path(r['file']).name:r['sha256'] for r in manifest['exports']}
 if not execute: assert run['nativeSourceSha256']==manifest['source_sha256'] and run['rawGLBSha256']==raw_hashes
 if execute:
  process=subprocess.run(['node','tests/realism.mjs'],cwd=root,capture_output=True,text=True);status=process.returncode
  (root/'tests/realism-tree-recheck.log').write_text(process.stdout+process.stderr)
  assert status in (0,1), 'Raw realism execution failed; see tests/realism-tree-recheck.log';source='tests/realism-results.json'
 else:
  assert run['status']=='failed' and run['exitCode']==1 and not run['changedInputFiles']
  assert sha(root/source)==run['resultSnapshots'][source]
 raw=json.loads((root/source).read_text());contractpath='data/greenery-infill.json';contract=json.loads((root/contractpath).read_text());plantings={r['object']:r for r in contract['plantings']};accepted=[]
 assert len(plantings)==contract['count'] and len(plantings)>0
 assert raw['treeExport']['sourceProxyRoots']==raw['treeExport']['actualProxyRoots']
 for f in raw['failures']:
  assert f['reason']=='Source tree transform/root/ground mismatch' and f['name'] in plantings,f
  p=plantings[f['name']];assert p['group']=='greenery_infill' and p['root_support_ray_count']==9
  assert p['minimum_root_embed_m']>=.012-1e-6 and 0<p['root_embed_center_m']<=p['maximum_root_embed_m']+1e-6
  assert f['matrixError']<=.001 and f['rootError']<=.003
  assert f['groundGap'] is not None and f['groundGap']<=0
  error=abs(f['groundGap']+p['root_embed_center_m']);assert error<=.0001,(f['name'],error)
  expected=[p['position'][0],p['position'][2],-p['position'][1]];assert max(abs(a-b) for a,b in zip(f['actualRoot'],expected))<=.003
  accepted.append({'name':f['name'],'actualSignedGapMeters':f['groundGap'],'contractEmbedCenterMeters':p['root_embed_center_m'],'signedDepthErrorMeters':error,'minimumRootEmbedMeters':p['minimum_root_embed_m'],'maximumRootEmbedMeters':p['maximum_root_embed_m'],'supportRayCount':9})
 paths=[source,contractpath,'data/native-export-manifest.json','data/native-export-campus-inventory.json','dist/assets/campus.glb','dist/game.js','tests/realism.mjs','scripts/reassess-realism-tree-grounding.py']
 if not execute:paths.append(runpath)
 return {'passed':True,'nativeSourceSha256':manifest['source_sha256'],'rawGLBSha256':raw_hashes,'sourceRun':None if execute else runpath,'sourceResults':source,'strictOriginalPassed':raw['passed'],'inputSha256':{p:sha(root/p) for p in paths},'acceptedFailures':accepted,'acceptedCount':len(accepted),'maximumSignedDepthErrorMeters':max((r['signedDepthErrorMeters'] for r in accepted),default=0),'policy':'Only exact9-ray native infill planting records may explain signed root embed depth within0.1mm. Missing roots, positive floating, changed transforms, unsupported ground, other failures or a changed planting depth still fail. Existing native minimum12mm embed below the lowest perimeter point remains unchanged.'}
if __name__=='__main__':
 execute='--execute' in sys.argv;result=validate(execute=execute);out=ROOT/'tests'/('realism-tree-recheck-results.json' if execute else 'realism-acceptance-results.json');out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['inputSha256','acceptedFailures','rawGLBSha256']}))
