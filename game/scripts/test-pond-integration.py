import os
import importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('pond',ROOT/'scripts/integrate-pond.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class PondIntegration(unittest.TestCase):
 def test_actual_triangles_and_no_vehicle_road(self):
  source=pathlib.Path(os.environ.get('CHOSUN_REALISM_ROOT',ROOT.parent/'realism_v2'))/'pond_fountain/overlay.json'
  if not source.exists():self.skipTest('Source fixture absent')
  with tempfile.TemporaryDirectory(prefix='pond-fixture-') as tmp:
   root=pathlib.Path(tmp);(root/'dist').mkdir();(root/'data').mkdir();world={'roads':[{'name':'keep','points':[[0,0,0],[10,0,0]]}],'walkableSurfaces':[],'pedestrianPaths':[],'extraCars':[1],'extraNPCs':[2]};nav={'walkableSurfaces':[],'pedestrianPaths':[]};(root/'dist/world-config.js').write_text('// fixture\nexport const WORLD = '+json.dumps(world)+';\n');(root/'data/campus-navigation.json').write_text(json.dumps(nav))
   report=module.apply(root,source);first={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()};module.apply(root,source);self.assertEqual(first,{str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()});result=json.loads((root/'dist/world-config.js').read_text().split('export const WORLD = ')[1].rstrip(';\n'));raw=json.loads(source.read_text());self.assertEqual(result['roads'],world['roads']);self.assertEqual(result['extraCars'],[1]);self.assertEqual(result['extraNPCs'],[2]);self.assertEqual(report['supportTriangles'],224);self.assertEqual(len(result['collisionPolygons']),59)
   for source_surface,target in zip(raw['walkable_surfaces'],result['walkableSurfaces']):self.assertEqual(target['triangles'],source_surface['triangles']);self.assertEqual(target['polygon'],[module.cv(p) for p in source_surface['vertices']])
   self.assertEqual(len(result['waterHazards'][0]['exceptions']),1);self.assertTrue(all(not s['vehicleAllowed'] for s in result['walkableSurfaces']))
if __name__=='__main__':unittest.main()
