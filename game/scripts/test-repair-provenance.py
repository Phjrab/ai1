import hashlib,json,pathlib,tempfile,unittest,copy
from repair_provenance import verify_repair_provenance
class RepairProvenance(unittest.TestCase):
 def test_second_phase_preserves_history_and_names_override(self):
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory);p=root/'realism_v2/final_repairs/patch_plan.json';p.parent.mkdir(parents=True)
   plan={'schema':'chosun.bounded-final-repair-plan.v1','ready_for_bounded_build':True,'pending':[],'base_native_sha256':'base','historical_integration_plan_sha256':'old-plan','base_module_hashes':{'helper.py':'old-source'},'source_overrides':{'helper.py':{'before_sha256':'old-source','after_sha256':'new-source'}}};p.write_text(json.dumps(plan));manifest={'bounded_repair_plan_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bounded_repair_base_native_sha256':'base','integration_plan_sha256':'old-plan','module_sha256':{'helper.py':'new-source'}}
   self.assertEqual(verify_repair_provenance(manifest,root)['baseNativeSha256'],'base')
   bad=copy.deepcopy(manifest);bad['module_sha256']['helper.py']='old-source'
   with self.assertRaisesRegex(AssertionError,'final native source'):verify_repair_provenance(bad,root)
   bad=copy.deepcopy(manifest);bad['integration_plan_sha256']='new-plan'
   with self.assertRaisesRegex(AssertionError,'Historical'):verify_repair_provenance(bad,root)
 def test_original_export_needs_no_second_phase(self):self.assertIsNone(verify_repair_provenance({},pathlib.Path('/unused')))
if __name__=='__main__':unittest.main()
