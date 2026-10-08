import json,math,pathlib,sys,hashlib,os
root=pathlib.Path(__file__).resolve().parents[1];model_root=pathlib.Path(os.environ.get('CHOSUN_MODEL_ROOT',root.parent/'architecture'));source=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else model_root/'campus';nav=json.load(open(source/'navigation.json'));base=json.loads((root/'dist/world-config.js').read_text().split('export const WORLD = ')[1].rstrip(';\n'))
def cv(p):return [round(p[0],4),round(p[2],4),round(-p[1],4)]
def dist(p,a,b):
 dx=b[0]-a[0];dy=b[1]-a[1];l=dx*dx+dy*dy;t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(l or 1)));return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
def reduce(p):
 if len(p)<3:return p
 ds=[dist(q,p[0],p[-1]) for q in p[1:-1]];v=max(ds,default=0)
 if v<.08:return [p[0],p[-1]]
 i=ds.index(v)+1;return reduce(p[:i+1])[:-1]+reduce(p[i:])
roads=[r for r in base['roads'] if r['name'] in ['본관 앞길','본관 뒤편 길']]
road_graph=json.load(open(source/'road_graph_3d.json'))['vehicle']
for e in road_graph['edges']:
 roads.append({'name':'CAMPUS_ROAD '+str(e.get('osm_id','')),'width':e['width'],'points':[cv(road_graph['nodes'][e['a']]),cv(road_graph['nodes'][e['b']])]})
boxes=[{'min':[b['min'][0],b['min'][2],-b['max'][1]],'max':[b['max'][0],b['max'][2],-b['min'][1]],'label':b['label']} for b in nav['collisionBoxes']]
main_geometry=json.load(open(source.parent/'building/geometry.json'))
for b in main_geometry['boxes']:boxes.append({'min':[b['min'][0],b['min'][2],-b['max'][1]],'max':[b['max'][0],b['max'][2],-b['min'][1]],'label':'본관 '+b['name']})
def blocked(p,margin=1):return any(b['min'][0]-margin<p[0]<b['max'][0]+margin and b['min'][2]-margin<p[2]<b['max'][2]+margin and p[1]<b['max'][1] and p[1]+2>b['min'][1] for b in boxes)
priority=['126','138','136','135','145','141','134','150','142','147','127','cit_main','cit_1','cit_2','cit_3','cit_4','162'];landmarks=sorted(nav['landmarks'],key=lambda x:priority.index(x['id']) if x['id'] in priority else 100)
dests=[]
for l in landmarks:
 p=cv(l['position']);target=[l['pin'][0],-l['pin'][1]];dx=target[0]-p[0];dz=target[1]-p[2];yaw=math.atan2(-dx,-dz);label=l['label']+(' · 공유 건물' if l['id']=='139' else ' · 대표 위치' if l['id']=='176' else '');dests.append({'id':l['id'],'label':label,'position':p,'yaw':yaw,'source':l['source']})
npcs=[]
for d in [q for q in dests if q['id'] in priority[1:11]+['cit_main','cit_1','162']]:
 for dx,dz in [(4,2),(-4,2),(0,4),(4,-4)]:
  p=[d['position'][0]+dx,d['position'][1],d['position'][2]+dz]
  if not blocked(p,4):npcs.append({'position':p,'label':d['label']});break
cars=[]
for d in [q for q in dests if q['id'] in ['138','136','145','134','142','147','127','cit_main','162']]:
 candidates=[]
 for r in roads:
  for a,b in zip(r['points'],r['points'][1:]):
   if r['width']<7:continue
   for t in [.25,.5,.75]:
    p=[a[k]+(b[k]-a[k])*t for k in range(3)];dd=math.hypot(p[0]-d['position'][0],p[2]-d['position'][2]);
    if dd<140 and not blocked(p,3) and all(math.hypot(p[0]-c['position'][0],p[2]-c['position'][2])>55 for c in cars):candidates.append((dd,p,math.atan2(-(b[0]-a[0]),-(b[2]-a[2]))))
 if candidates:
  _,p,yaw=min(candidates,key=lambda v:v[0]);cars.append({'position':[round(v,4) for v in p],'yaw':yaw,'color':'#b9cdd4','near':d['label']})
b=nav['bounds'];world={'bounds':{'minX':b['min'][0]+3,'maxX':b['max'][0]-3,'minZ':-b['max'][1]+3,'maxZ':-b['min'][1]-3},'minimumElevation':b['min'][2]-20,'siteAsset':'campus.glb','assets':[],'roads':roads,'destinations':dests,'footprints':[{'x':b['min'][0],'z':b['min'][2],'width':b['max'][0]-b['min'][0],'depth':b['max'][2]-b['min'][2],'label':b['label']} for b in boxes]+[{'x':-166,'z':-17,'width':332,'depth':17,'label':'본관'}],'extraNPCs':npcs,'extraCars':cars,'collisionBoxes':boxes,'attribution':'© OpenStreetMap contributors, ODbL 1.0; campus labels from Chosun University official campus map.'}
world['walkableSurfaces']=[{**surface,'polygon':[cv(p) for p in surface['polygon']]} for surface in nav.get('walkableSurfaces',[])]
world['pedestrianPaths']=[{**path,'points':[cv(p) for p in path['points']]} for path in nav.get('pedestrianPaths',[])]
for b in nav.get('railCollisionBoxes',[]):world['collisionBoxes'].append({'min':[b['min'][0],b['min'][2],-b['max'][1]],'max':[b['max'][0],b['max'][2],-b['min'][1]],'label':b.get('label','pedestrian handrail')})
(root/'dist/world-config.js').write_text('// Derived map coordinates: © OpenStreetMap contributors, ODbL 1.0. See LICENSES.md.\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n')
(root/'data').mkdir(exist_ok=True);(root/'data/road-graph-3d.json').write_text(json.dumps(road_graph,ensure_ascii=False));(root/'data/campus-navigation.json').write_text(json.dumps(nav,ensure_ascii=False));print({'landmarks':len(dests),'roads':len(roads),'road_points':sum(len(r['points']) for r in roads),'npc_spawns':len(npcs),'car_spawns':len(cars),'collision_boxes':len(boxes)})
