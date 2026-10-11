#!/usr/bin/env python3
import importlib.util, json, math, pathlib, shutil, subprocess, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('transit_revision',ROOT/'scripts/integrate-transit-revision.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class TransitContract(unittest.TestCase):
 def test_runtime_coordinates_and_source_evidence(self):
  source={'position':[1,2,3],'waitingPosition':[4,5,6],'boardingPosition':[7,8,9],'roadCenterlinePosition':[10,11,12],'shelterPosition':[13,14,15],'travelTangent':[.6,.8],'outwardBoardingNormal':[.8,-.6],'collisionBoxes':[{'center':[1,2,4],'halfExtents':[.07,.08,1.38]}],'sourcePositionXY':[99,100],'platformSourceXY':[88,89],'platformSourceGPS':{'latitude':35,'longitude':126}}
  converted=module.convert_stop(source)
  for key in ['position','waitingPosition','boardingPosition','roadCenterlinePosition','shelterPosition']:self.assertEqual(converted[key],module.cv(source[key]))
  self.assertEqual(converted['travelTangent'],[.6,-.8]);self.assertEqual(converted['outwardBoardingNormal'],[.8,.6]);self.assertAlmostEqual(sum(a*b for a,b in zip(converted['travelTangent'],converted['outwardBoardingNormal'])),0)
  self.assertEqual(converted['collisionBoxes'][0]['halfExtents'],[.07,1.38,.08]);self.assertEqual(converted['collisionBoxes'][0]['center'],[1,4,-2])
  for key in ['sourcePositionXY','platformSourceXY','platformSourceGPS']:self.assertEqual(converted[key],source[key])
  self.assertEqual(source['position'],[1,2,3]);self.assertEqual(source['collisionBoxes'][0]['halfExtents'],[.07,.08,1.38])
 def test_actual_overlay_isolated_and_repeatable(self):
  overlay=ROOT.parent/'realism_v2/transit_alignment_overlay.json'
  if not overlay.exists():self.skipTest('Final source overlay not supplied')
  with tempfile.TemporaryDirectory(prefix='chosun-transit-fixture-') as temp:
   target=pathlib.Path(temp);(target/'dist').mkdir();(target/'data').mkdir()
   for name in ['dist/world-config.js','dist/transit-config.js','data/campus-navigation.json']:shutil.copy2(ROOT/name,target/name)
   original=json.loads((target/'dist/world-config.js').read_text().split('export const WORLD = ')[1].rstrip(';\n'))
   command=['python3','-B',str(ROOT/'scripts/integrate-transit-revision.py'),str(overlay),'--game-root',str(target),'--issues-source',str(overlay.parent/'transit_review/integration_issues.json')]
   subprocess.run(command,check=True,stdout=subprocess.DEVNULL);first={str(p.relative_to(target)):p.read_bytes() for p in target.rglob('*') if p.is_file()}
   subprocess.run(command,check=True,stdout=subprocess.DEVNULL);self.assertEqual(first,{str(p.relative_to(target)):p.read_bytes() for p in target.rglob('*') if p.is_file()})
   world=json.loads((target/'dist/world-config.js').read_text().split('export const WORLD = ')[1].rstrip(';\n'));transit=json.loads((target/'dist/transit-config.js').read_text().split('export const TRANSIT = ')[1].rstrip(';\n'));raw=json.loads(overlay.read_text());self.assertEqual((target/'data/transit-integration-issues.json').read_bytes(),(overlay.parent/'transit_review/integration_issues.json').read_bytes())
   self.assertEqual(world['extraCars'],original['extraCars']);self.assertEqual(world['extraNPCs'],original['extraNPCs']);self.assertEqual(world['roads'],original['roads'])
   for stop in transit['cityStops']:
    source=next(s for s in raw['cityStops'] if s['id']==stop['id'])
    if source.get('waitingPosition'):self.assertEqual(stop['waitingPosition'],module.cv(source['waitingPosition']))
    if source.get('collisionBoxes'):self.assertGreater(stop['collisionBoxes'][0]['halfExtents'][1],1)
if __name__=='__main__': unittest.main()
