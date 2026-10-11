import importlib.util,json,pathlib,tempfile,unittest,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('actor_grounding',ROOT/'scripts/integrate-actor-grounding.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ActorGroundingContract(unittest.TestCase):
 def test_large_height_revision_keeps_xy_and_counts(self):
  with tempfile.TemporaryDirectory(prefix='actor-floor-contract-') as tmp:
   root=pathlib.Path(tmp);(root/'dist').mkdir();(root/'data').mkdir();world={'extraNPCs':[{'position':[50,-70,80]}],'extraCars':[{'position':[-10,-30,90]}]};wp=root/'dist/world-config.js';wp.write_text('// fixture\nexport const WORLD = '+json.dumps(world)+';\n')
   actors=[{'kind':kind,'index':index,'positionXY':xy,'floor_z':z,'support_object':'final actual surface'} for kind,index,xy,z in [('extraNPCs',0,[50,-80],20),('extraCars',0,[-10,-90],-12),('baseCars',0,[8,-20],.15),('baseCars',1,[-58,-21],.15)]]
   baseline=root/'data/grade-sync-baseline.json';baseline.write_text('immutable actor fixture');metadata={'schema':'actor_grounding_v5','version':1,'source_baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest()};source=root/'input.json';source.write_text(json.dumps({**metadata,'actors':actors}));module.apply(root,source);updated=json.loads(wp.read_text().split('export const WORLD = ')[1].rstrip(';\n'));self.assertEqual(updated['extraNPCs'],[{'position':[50,20,80]}]);self.assertEqual(updated['extraCars'],[{'position':[-10,-12,90]}]);self.assertEqual(updated['baseCarGroundHeights'],[.15,.15]);first=wp.read_bytes();module.apply(root,source);self.assertEqual(wp.read_bytes(),first)
   actors[0]['positionXY'][0]+=.01;source.write_text(json.dumps({**metadata,'actors':actors}))
   with self.assertRaisesRegex(AssertionError,'XY'):module.apply(root,source)
   self.assertEqual(wp.read_bytes(),first,'Reject mismatched actor XY before writing')
   actors[0]['positionXY'][0]-=.01;source.write_text(json.dumps({**metadata,'actors':actors[:-1]}))
   with self.assertRaisesRegex(AssertionError,'Every existing'):module.apply(root,source)
   self.assertEqual(wp.read_bytes(),first)

if __name__=='__main__':unittest.main()
