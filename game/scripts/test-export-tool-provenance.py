import hashlib,json,os,pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ExportTools(unittest.TestCase):
 def test_separate_export_freeze_and_tamper_rejection(self):
  with tempfile.TemporaryDirectory() as temp:
   base=pathlib.Path(temp);src=base/'source';out=base/'fixed';exp='realism_v2/game_export_supported_surfaces';tool='realism_v2/scripts/export_game_supported_surfaces.py';paths={'native.blend':b'native unchanged','realism_v2/metadata.json':b'{}',tool:b'# export selection only\n',exp+'/campus.glb':b'raw glb'}
   for name,raw in paths.items():p=src/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
   h=lambda name:hashlib.sha256(paths[name]).hexdigest();manifest={'source':'native.blend','source_sha256':h('native.blend'),'module_sha256':{},'sidecar_sha256':{'realism_v2/metadata.json':h('realism_v2/metadata.json')},'export_tool_sha256':{tool:h(tool)},'exports':[{'file':exp+'/campus.glb','sha256':h(exp+'/campus.glb')}]};(src/exp/'manifest.json').write_text(json.dumps(manifest))
   freeze=subprocess.run(['python3',str(ROOT/'scripts/freeze-model-inputs.py'),str(src),str(out),'--export-dir',exp],capture_output=True,text=True);self.assertEqual(freeze.returncode,0,freeze.stderr);self.assertEqual((out/tool).read_bytes(),paths[tool]);self.assertTrue((out/exp/'manifest.json').exists());self.assertFalse((out/'realism_v2/game_export/manifest.json').exists())
   env={**os.environ,'CHOSUN_INPUT_ROOT':str(out)};command=['python3',str(ROOT/'scripts/verify-model-inputs.py'),str(out/exp)];check=subprocess.run(command,env=env,capture_output=True,text=True);self.assertEqual(check.returncode,0,check.stderr)
   (out/tool).write_text('# changed after export\n');check=subprocess.run(command,env=env,capture_output=True,text=True);self.assertNotEqual(check.returncode,0);self.assertIn('Export tool source changed',check.stderr)
if __name__=='__main__':unittest.main()
