"""Apply two source-bound inferred driving centerlines without changing geometry."""
import argparse,copy,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
KEY='realism_v2/terrace_drive_alignment/navigation.json'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cv(p):return [p[0],p[2],-p[1]]
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
def apply(root,source):
 d=json.loads(source.read_text());sha=digest(source);manifest=json.loads((root/'data/native-export-manifest.json').read_text());bound=manifest['sidecar_sha256']
 assert d['schema']=='chosun.terrace421.drive_alignment.v1' and d['status']=='FROZEN_REQUIRED_DRIVING_PASS_WITH_TYRE_VISUAL_LIMIT'
 assert bound.get(KEY)==sha,'Unbound terrace driving overlay'
 for kind in ['parking','graph']:assert bound.get(d['source_'+kind+'_path'])==d['source_'+kind+'_sha256'],'Terrace source binding changed'
 assert bound.get(d['validation_path'])==d['validation_sha256'],'Terrace validation binding changed'
 assert {r['id'] for r in d['routes']}=={'421_front_to_middle','421_middle_to_east'}
 wp=root/'dist/world-config.js';text=wp.read_text();world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'));pp=root/'data/parking-terraces.json';parking=json.loads(pp.read_text());gp=root/'data/road-graph-3d.json';graph=json.loads(gp.read_text());rp=root/'data/terrace-drive-alignment-report.json'
 if rp.exists() and json.loads(rp.read_text()).get('sourceSha256')==sha:
  for r in d['routes']:
   matches=[x for x in world['roads'] if x.get('terrace_drive_alignment')==r['id']]
   assert len(matches)==1 and matches[0]['points']==[cv(p) for p in r['verified_points_xyz']]
   z=next(z for z in parking['transition_zones'] if z.get('connection',{}).get('connection_id')==r['id']);assert z['connection']['centerline_xy']==r['revised']
  return json.loads(rp.read_text())
 before_graph=copy.deepcopy({'nodes':graph['nodes'],'edges':graph['edges']});changed=[]
 for r in d['routes']:
  assert r['width_m']==4.5 and r['lateralOffsetMeters']==.25 and r['terminalTrimMeters'] in [0,1]
  assert all(len(p)==3 and all(math.isfinite(v) for v in p) for p in r['verified_points_xyz'])
  zone=next(z for z in parking['transition_zones'] if z.get('connection',{}).get('connection_id')==r['id']);assert zone['connection']==r['source_connection'],'Original inferred route changed'
  for node in r['source_graph_nodes']:
   current=graph['nodes'][node['index']];expected=node['position'];assert current[:2]==expected[:2] and abs(current[2]-expected[2])<.06,'Source graph node changed'
  for edge in r['source_graph_edges']:
   e=edge['record'];matches=[x for x in graph['edges'] if x['a']==e['a'] and x['b']==e['b'] and x.get('connection_id')==e['connection_id']]
   assert len(matches)==1 and all(matches[0].get(k)==v for k,v in e.items() if k!='length'),'Source graph edge changed'
  name='CAMPUS_ROAD '+r['source_way_id'];current=[x for x in world['roads'] if x.get('name')==name];assert len(current)==len(r['source_world_roads'])
  for a,b in zip(current,r['source_world_roads']):
   assert a['width']==b['width'] and len(a['points'])==len(b['points'])
   assert all(p[0]==q[0] and p[2]==q[2] and abs(p[1]-q[1])<.06 for p,q in zip(a['points'],b['points'])),'Source runtime road changed'
  template=current[0];world['roads']=[x for x in world['roads'] if x.get('name')!=name]+[{**template,'points':[cv(p) for p in r['verified_points_xyz']],'terrace_drive_alignment':r['id'],'sourceSha256':sha,'knownTyreVisualOverlapUpperBoundMeters':d['knownTyreVisualOverlapUpperBoundMeters']}]
  zone['source_connection_before_runtime_alignment']=copy.deepcopy(zone['connection']);zone['connection']['centerline_xy']=r['revised'];zone['runtime_drive_alignment']={'sourceSha256':sha,'verified_points_xyz':r['verified_points_xyz'],'required_driving_pass':True,'zero_tyre_contact':False}
  changed.append({'id':r['id'],'replacedRuntimeSegments':len(current),'verifiedPointCount':len(r['verified_points_xyz'])})
 # This is the preserved authoring/source graph, not the active game's road
 # grid. Keep surveyed shared nodes and topology; publish exact preferred
 # runtime routes for downstream readers without silently moving a junction.
 graph['verifiedRuntimeDrivingRoutes']=[{'id':r['id'],'sourceWayId':r['source_way_id'],'points':r['verified_points_xyz'],'width':r['width_m'],'sourceSha256':sha} for r in d['routes']]
 assert before_graph=={'nodes':graph['nodes'],'edges':graph['edges']}
 report={'sourceSha256':sha,'sourceParkingSha256':d['source_parking_sha256'],'sourceGraphSha256':d['source_graph_sha256'],'changes':changed,'graphNodesChanged':0,'graphEdgesChanged':0,'physicalGeometryChanged':False,'actorPosesChanged':False,'requiredDrivingPassed':True,'allTyreContactsZero':False,'knownTyreVisualOverlapUpperBoundMeters':d['knownTyreVisualOverlapUpperBoundMeters'],'policy':'Actual game WORLD centerlines and derived terrace driving routes use the verified path. Original surveyed/source graph topology is preserved with explicit preferred runtime route records.'}
 wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n');dump(pp,parking);dump(gp,graph);dump(root/'data/terrace-drive-alignment.json',d);dump(rp,report);return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(apply(a.root,a.source)))
