import os
import copy, importlib.util, json, pathlib, tempfile, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stop_walks',ROOT/'scripts/integrate-stop-walkways.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class StopWalkIntegration(unittest.TestCase):
 def fixture(self, root):
  source=pathlib.Path(os.environ.get('CHOSUN_REALISM_ROOT',ROOT.parent/'realism_v2'))/'hospital_stop_walkways/hospital_stop_walkways_overlay.json'
  if not source.exists(): self.skipTest('Native review fixture absent')
  data=json.loads(source.read_text());(root/'dist').mkdir();(root/'data').mkdir()
  connected=next(p for p in data['pedestrianPaths'] if str(p['stop_id'])=='1149')
  world={'destinations':[{'id':'162','position':module.cv(connected['points'][0])}],'roads':[{'name':'unchanged'}],'extraCars':[1,2],'extraNPCs':[3]}
  (root/'dist/world-config.js').write_text('// fixture\nexport const WORLD = '+json.dumps(world)+';\n')
  transit={'cityStops':[{'id':'fixture_'+c['stop_id'],'ars_id':c['stop_id'],'created_geometry':True,'waitingPosition':module.cv(c['waitingPosition'])} for c in data['stopConnections']],'routes':[{'stopIds':['preserved'],'vehicleCount':2}]}
  (root/'dist/transit-config.js').write_text('export const TRANSIT = '+json.dumps(transit)+';\n')
  (root/'data/campus-navigation.json').write_text('{}')
  i=connected['existingWalkingNodeIndex'];nodes=[[0,0,0] for _ in range(i+1)];nodes[i]=min(connected['points'],key=lambda p:sum((a-b)**2 for a,b in zip(p[:2],connected['existingWalkingNodeXY'])))[:];nodes[i][2]+=.02
  (root/'data/walking-road-graph-3d.json').write_text(json.dumps({'nodes':nodes,'edges':[{'a':0,'b':i,'length':1}]}))
  (root/'data/road-graph-3d.json').write_text('{"vehicle":"untouched"}')
  return source,data

 def test_real_geometry_idempotence_and_disconnected_opposite_stop(self):
  with tempfile.TemporaryDirectory(prefix='stop-walk-fixture-') as tmp:
   root=pathlib.Path(tmp);source,data=self.fixture(root)
   # A coincident graph node is not evidence of a verified road crossing.
   gp=root/'data/walking-road-graph-3d.json';graph=json.loads(gp.read_text())
   graph['nodes'][0]=next(p for p in data['pedestrianPaths'] if str(p['stop_id'])=='1150')['points'][0]
   gp.write_text(json.dumps(graph));report=module.apply(root,source)
   snapshots={p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
   module.apply(root,source)
   self.assertEqual(snapshots,{p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()})
   self.assertGreater(report['supportTriangles'],100)
   world=json.loads((root/'dist/world-config.js').read_text().split('export const WORLD = ')[1].rstrip(';\n'))
   self.assertEqual(world['roads'],[{'name':'unchanged'}]);self.assertEqual(world['extraCars'],[1,2])
   self.assertEqual((root/'data/road-graph-3d.json').read_text(),'{"vehicle":"untouched"}')
   graph=json.loads((root/'data/walking-road-graph-3d.json').read_text());first=next(p for p in data['pedestrianPaths'] if str(p['stop_id'])=='1149');anchor=first['existingWalkingNodeIndex']
   adjacent={}
   for e in graph['edges']:
    adjacent.setdefault(e['a'],set()).add(e['b']);adjacent.setdefault(e['b'],set()).add(e['a'])
   seen={anchor};pending=[anchor]
   while pending:
    for node in adjacent.get(pending.pop(),set())-seen:seen.add(node);pending.append(node)
   connected_edges=[e for e in graph['edges'] if e.get('stop_id')=='1149'];blocked_edges=[e for e in graph['edges'] if e.get('stop_id')=='1150']
   self.assertTrue(all(e['a'] in seen and e['b'] in seen for e in connected_edges))
   self.assertTrue(blocked_edges and all(e['a'] not in seen and e['b'] not in seen for e in blocked_edges))
   self.assertEqual(world['walkableSurfaces'][0]['triangles'],data['walkableSurfaces'][0]['triangles'])
   self.assertEqual(world['walkableSurfaces'][0]['polygon'][0],module.cv(data['walkableSurfaces'][0]['vertices'][0]))

 def test_rejects_unverified_crossing_before_write(self):
  with tempfile.TemporaryDirectory(prefix='stop-walk-reject-') as tmp:
   root=pathlib.Path(tmp);source,data=self.fixture(root);before=(root/'dist/world-config.js').read_bytes()
   next(c for c in data['stopConnections'] if str(c['stop_id'])=='1150')['connectToCampus']=True
   bad=root/'bad.json';bad.write_text(json.dumps(data))
   with self.assertRaisesRegex(AssertionError,'Unverified 1150'):module.apply(root,bad)
   self.assertEqual(before,(root/'dist/world-config.js').read_bytes())

if __name__=='__main__':unittest.main()
