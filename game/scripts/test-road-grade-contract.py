import copy,json,pathlib,shutil,subprocess,tempfile,unittest
from road_grade_contract import previous_road_heights, runtime_roads, approved_landmark_relocations
class RoadContract(unittest.TestCase):
 def setUp(self):
  self.old={'nodes':[[0,0,1],[10,0,2]],'edges':[{'a':0,'b':1,'osm_id':'old','width':5}]}
  self.new=copy.deepcopy(self.old);self.new['nodes']+=[[5,0,3],[10,10,4]];self.new['edges']=[{'a':0,'b':2,'osm_id':'old','width':5},{'a':2,'b':1,'osm_id':'old','width':5},{'a':1,'b':3,'osm_id':'new','connection_id':'rear','width':5}]
  self.contract=[{'id':'rear','osm_id':'new','node_indices':[1,3],'width_m':5,'source':'user-confirmed connection; XY/width estimated'}]
 def test_original_densification_and_explicit_connection(self):self.assertEqual(previous_road_heights(self.old,self.new,self.contract),[1,2,1.5,None])
 def test_unbound_connection_rejected(self):
  with self.assertRaises(AssertionError):previous_road_heights(self.old,self.new,[])
 def test_unapproved_original_xy_change_rejected(self):
  self.new['nodes'][0][1]=1
  with self.assertRaises(ValueError):previous_road_heights(self.old,self.new,self.contract)
  self.new['nodes'][0]=[1,0,1]
  with self.assertRaises(ValueError):previous_road_heights(self.old,self.new,self.contract)
 def test_undeclared_node_or_wrong_width_rejected(self):
  self.contract[0]['node_indices']=[1]
  with self.assertRaises(AssertionError):previous_road_heights(self.old,self.new,self.contract)
  self.contract[0]['node_indices']=[1,3];self.new['edges'][-1]['width']=6
  with self.assertRaises(AssertionError):previous_road_heights(self.old,self.new,self.contract)
 def test_runtime_roads_retain_connection_and_support_identity(self):
  self.new['edges'][-1].update(oneway='yes',source='user-confirmed route, inferred width',support_surface_objects=['flat','lane'])
  before=copy.deepcopy(self.new);roads=runtime_roads(self.new)
  self.assertEqual(roads[-1]['connection_id'],'rear')
  self.assertEqual(roads[-1]['oneway'],'yes')
  self.assertEqual(roads[-1]['support_surface_objects'],['flat','lane'])
  self.assertEqual(roads[-1]['points'],[[10,2,0],[10,4,-10]])
  self.assertEqual(self.new,before)
 def test_only_level_revised_primary_landmarks_allow_xy_changes(self):
  contract={'version':'student_union_levels_1.0','buildings':[{'id':129},{'id':145}]}
  primary={'building_id':129,'student_union_level_version':contract['version'],'is_landmark_destination':True,'safe_arrival':[1,2,3],'entrance_id':'mapped129'}
  records=[primary,{**primary,'building_id':145,'is_landmark_destination':False},{**primary,'building_id':144},{**primary,'building_id':145,'student_union_level_version':'stale'}]
  self.assertEqual(approved_landmark_relocations(contract,{'records':records}),{'129':{'position':[1,2,3],'entrance_id':'mapped129'}})
  with self.assertRaises(AssertionError):approved_landmark_relocations(contract,{'records':[primary,primary]})
 def correction(self,index):
  original=self.new['nodes'][index].copy();self.new['nodes'][index][1]+=1.5
  return {'node_index':index,'original_position':original,'new_position':self.new['nodes'][index].copy(),'affected_edges':[i for i,e in enumerate(self.new['edges']) if index in [e['a'],e['b']]],'source':'Actual road centerline crossed building142; bounded correction'}
 def test_exact_original_node_correction(self):
  record=self.correction(0);before=copy.deepcopy(self.new)
  self.assertEqual(previous_road_heights(self.old,self.new,self.contract,[record]),[1,2,1.5,None]);self.assertEqual(self.new,before)
  with self.assertRaises(ValueError):previous_road_heights(self.old,self.new,self.contract)
  self.new['nodes'][1][1]+=1
  with self.assertRaises(ValueError):previous_road_heights(self.old,self.new,self.contract,[record])
 def test_exact_densified_node_correction(self):
  record=self.correction(2)
  self.assertEqual(previous_road_heights(self.old,self.new,self.contract,[record]),[1,2,1.5,None])
  record['original_position'][1]=.1
  with self.assertRaises(ValueError):previous_road_heights(self.old,self.new,self.contract,[record])
 def test_correction_wrong_position_or_edges_rejected(self):
  record=self.correction(0)
  for key,value in [('new_position',[0,1.6,1]),('original_position',[.1,0,1]),('affected_edges',[]),('affected_edges',[0,1]),('affected_edges',[0,0]),('source','')]:
   bad=copy.deepcopy(record);bad[key]=value
   with self.subTest(key=key,value=value),self.assertRaises(AssertionError):previous_road_heights(self.old,self.new,self.contract,[bad])
 def test_correction_duplicate_or_nonfinite_rejected(self):
  record=self.correction(0)
  with self.assertRaises(AssertionError):previous_road_heights(self.old,self.new,self.contract,[record,record])
  record['new_position'][2]=float('nan')
  with self.assertRaises(AssertionError):previous_road_heights(self.old,self.new,self.contract,[record])
 def test_existing_actor_baseline_remains_byte_identical(self):
  with tempfile.TemporaryDirectory(prefix='grade-baseline-preservation-') as tmp:
   root=pathlib.Path(tmp)
   for directory in ['data','dist','scripts','inputs']:(root/directory).mkdir()
   for name in ['sync-grade-revision.py','road_grade_contract.py']:shutil.copy2(pathlib.Path(__file__).parent/name,root/'scripts'/name)
   world={'bounds':{'minX':-590,'maxX':900,'minZ':-237,'maxZ':1117},'roads':[],'extraNPCs':[],'extraCars':[],'collisionBoxes':[],'destinations':[]}
   baseline={'vehicle':self.old,'mainRoads':[],'extraNPCs':[],'extraCars':[],'collisionBoxes':[],'destination_positions':{}}
   base=root/'data/grade-sync-baseline.json';base.write_text(json.dumps(baseline,indent=2));original=base.read_bytes()
   for name,var,data in [('world-config.js','WORLD',world),('transit-config.js','TRANSIT',{'stops':[],'routes':[{'id':'route','points':[]}]})]:(root/'dist'/name).write_text('// fixture\nexport const '+var+' = '+json.dumps(data)+';\n')
   inputs={'navigation_graded.json':{'landmarks':[],'collisionBoxes':[]},'road_graph_3d_graded.json':{'vehicle':self.old,'walking':self.old},'transit_placements_graded.json':{'stops':[],'route':{'id':'route','points':[]}},'terrain_building_pads_graded.json':[{'id':164,'name':'parking','base':-33.75}],'local_level_alignment.json':{'controls':[],'building_deltas':{},'road_graph_node_changes':0,'vehicle_graph_final_max_grade':.1}}
   for name,data in inputs.items():(root/'inputs'/name).write_text(json.dumps(data))
   for _ in range(2):
    subprocess.run(['python3','-B',str(root/'scripts/sync-grade-revision.py'),str(root/'inputs')],check=True,capture_output=True)
    self.assertEqual(base.read_bytes(),original)
   updated=json.loads((root/'dist/world-config.js').read_text().split('export const WORLD = ')[1].rstrip(';\n'));self.assertEqual(updated['bounds']['maxX'],657)
if __name__=='__main__':unittest.main()
