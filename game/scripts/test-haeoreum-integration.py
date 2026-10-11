import importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('haeoreum',ROOT/'scripts/integrate-haeoreum-entrance.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class HaeoreumIntegration(unittest.TestCase):
 def test_portal_height_path_and_no_duplicate_surfaces(self):
  with tempfile.TemporaryDirectory(prefix='haeoreum-contract-') as tmp:
   root=pathlib.Path(tmp);(root/'dist').mkdir();(root/'data').mkdir();key='a_07_example'
   surface={'id':'stair_example','polygon':[[0,0,-5],[1,0,-5],[0,1,-5]],'triangles':[[0,1,2]]};path={'id':'verified_entry_'+key,'entrance_id':key,'points':[[0,0,0],[1,0,0]]}
   world={'destinations':[{'id':'128','position':[0,0,0]}],'closedDoors':[{'name':key,'center':[2,1.4,0],'halfSize':[1,1.4,.025],'yaw':.3}],'pedestrianPaths':[dict(path)],'walkableSurfaces':[surface]};nav={'pedestrianPaths':[dict(path)],'walkableSurfaces':[surface],'landmarks':[{'id':'128','position':[0,0,0]}]};report={'records':[{'id':key,'closed_leaf_plane':[2,0,0],'door':[2.03,0,0]}],'destinationChanges':[{'id':'128','new_position':[0,0,0]}],'sourceHashes':{}}
   wp=root/'dist/world-config.js';wp.write_text('// fixture\nexport const WORLD = '+json.dumps(world)+';\n');(root/'data/campus-navigation.json').write_text(json.dumps(nav));(root/'data/entrance-sync-report.json').write_text(json.dumps(report))
   data={'walkableSurfaces':[surface],'entrances':[{'building_id':128,'is_landmark_destination':True,'entrance_id':key,'safe_arrival':[0,0,-8],'walk_stop':[1.5,0,-5],'threshold_z':-5,'door_plane':[2,0,-5],'approach_path':[[0,0,-8],[1,0,-6],[1.5,0,-5]]}]};source=root/'input.json';source.write_text(json.dumps(data));module.apply(root,source)
   result=json.loads(wp.read_text().split('export const WORLD = ')[1].rstrip(';\n'));self.assertEqual(result['closedDoors'][0]['center'],[2,-3.6,0]);self.assertEqual(result['closedDoors'][0]['halfSize'],[1,1.4,.025]);self.assertEqual(len(result['walkableSurfaces']),1);self.assertEqual(result['pedestrianPaths'][0]['points'][-1],[1.5,-5,0]);self.assertEqual(result['destinations'][0]['position'],[0,-8,0])
   before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()};module.apply(root,source);self.assertEqual(before,{str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()})
if __name__=='__main__':unittest.main()
