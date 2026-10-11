import copy,hashlib,importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sp=importlib.util.spec_from_file_location('lower',ROOT/'scripts/integrate-lower-paving-retirement.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
class Tests(unittest.TestCase):
 def fixture(self,identified=True):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);r=pathlib.Path(temp.name);(r/'data').mkdir();(r/'dist').mkdir();sf={'id':'legacy474301324' if identified else 'unrelated_door','polygon':[[0,0,0],[2,0,0],[0,2,0]],'triangles':[[0,1,2]]};upper={**copy.deepcopy(sf),'id':'actual_bridge','polygon':[[0,0,2],[2,0,2],[0,2,2]]};outside={**copy.deepcopy(sf),'id':'outside','polygon':[[10,10,0],[12,10,0],[10,12,0]]};nav={'walkableSurfaces':[sf,upper,outside],'roads':[{'unchanged':True}],'pedestrianPaths':[{'unchanged':True}]};world=copy.deepcopy(nav)
  for rec in world['walkableSurfaces']:rec['polygon']=[[p[0],p[2],-p[1]] for p in rec['polygon']]
  (r/'data/campus-navigation.json').write_text(json.dumps(nav));(r/'dist/world-config.js').write_text('//fixture\nexport const WORLD = '+json.dumps(world)+';\n');data={'version':'1.0','source_object':'CAMPUS_CONTINUOUS pedestrian paving','source_way_ids':['474301324'],'vehicle_access':False,'upper_geometry_and_pose_unchanged':True,'retirement_polygon_xy':[[0,0],[1,0],[1,1],[0,1]],'max_z_plane':[0,0,1],'minimum_below_bridge_top_m':.3,'source_module_sha256':'source-sha'};source=r/'retirement.json';source.write_text(json.dumps(data));manifest={'sidecar_sha256':{'realism_v2/it_approach_alignment_review/lower_paving_retirement.json':hashlib.sha256(source.read_bytes()).hexdigest()},'module_sha256':{'realism_v2/final_it_lower_paving_retirement.py':'source-sha'}};(r/'data/native-export-manifest.json').write_text(json.dumps(manifest));return r,source,nav
 def test_finite_mask_height_layer_and_repetition(self):
  r,source,nav=self.fixture();report=m.apply(r,source);out=json.loads((r/'data/campus-navigation.json').read_text());self.assertEqual(out['walkableSurfaces'][1:],nav['walkableSurfaces'][1:]);self.assertEqual(out['roads'],nav['roads']);self.assertEqual(out['pedestrianPaths'],nav['pedestrianPaths']);self.assertAlmostEqual(report['clippedSupportRecords'][0]['removed_projected_area_m2'],1);first=(r/'data/campus-navigation.json').read_bytes();self.assertEqual(report,m.apply(r,source));self.assertEqual(first,(r/'data/campus-navigation.json').read_bytes())
 def test_unidentified_floor_is_not_silently_erased(self):
  r,source,nav=self.fixture(False)
  with self.assertRaisesRegex(ValueError,'Unrelated'):m.apply(r,source)
  self.assertEqual(json.loads((r/'data/campus-navigation.json').read_text()),nav)
 def test_unbound_contract_fails(self):
  r,source,_=self.fixture();source.write_text(source.read_text()+' ')
  with self.assertRaisesRegex(ValueError,'not bound'):m.apply(r,source)
 def test_sloped_height_plane_keeps_higher_fragment(self):
  tri=[[0,0,-1],[2,0,1],[0,2,-1]];pieces,cut=m.retire_triangle(tri,[[0,0],[2,0],[2,2],[0,2]],[0,0,0]);self.assertAlmostEqual(cut,1.5);self.assertAlmostEqual(sum(m.area(p) for p in pieces),.5);self.assertTrue(all(abs(p[2]-(p[0]-1))<1e-10 for q in pieces for p in q));self.assertTrue(all(p[2]>=-1e-9 for q in pieces for p in q))
if __name__=='__main__':unittest.main()
