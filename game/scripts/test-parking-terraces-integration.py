import importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('terraces',ROOT/'scripts/integrate-parking-terraces.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class TerraceIntegration(unittest.TestCase):
 def test_only_actual_flat_tops_lane_triangles_and_exclusions(self):
  with tempfile.TemporaryDirectory(prefix='terrace-game-contract-') as tmp:
   root=pathlib.Path(tmp);(root/'dist').mkdir();(root/'data').mkdir();wp=root/'dist/world-config.js';wp.write_text('// fixture\nexport const WORLD = {"roads":[1],"extraCars":[2]};\n')
   t=lambda name,x:{'object':name,'vertices':[[x,0,2],[x+2,0,2],[x,2,3]]}
   data={'version':'parking_terraces_v5.1','parking_zones':[{'object':'flat','parking_allowed':True}],'transition_zones':[{'object':'slope','vehicle_allowed':True},{'object':'forbidden','vehicle_allowed':False}],'surface_top_triangles':[t('flat',0),t('slope',10),t('forbidden',20)],'lane_top_triangles':[t('slope',11)],'rejected_connections':[{'connection_id':'779_internal_hairpin'}]};source=root/'input.json';source.write_text(json.dumps(data));report=module.apply(root,source)
   world=json.loads(wp.read_text().split('export const WORLD = ')[1].rstrip(';\n'));self.assertEqual(world['roads'],[1]);self.assertEqual(world['extraCars'],[2]);self.assertEqual(len(world['vehicleSurfaceRules']),3);self.assertEqual(report['allowedTriangles'],2);self.assertEqual(report['excludedTriangles'],1);self.assertEqual(world['vehicleSurfaceRules'][1]['polygon'][0],[11,2,0]);self.assertEqual(world['vehicleSurfaceRules'][2]['mode'],'exclude')
   before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()};module.apply(root,source);self.assertEqual(before,{str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()})
 def test_reject_design_only_before_writes(self):
  with tempfile.TemporaryDirectory(prefix='terrace-no-design-') as tmp:
   root=pathlib.Path(tmp);source=root/'design.json';source.write_text('{"version":"parking_terraces_v5.1"}')
   with self.assertRaisesRegex(AssertionError,'Applied geometry'):module.apply(root,source)
if __name__=='__main__':unittest.main()
