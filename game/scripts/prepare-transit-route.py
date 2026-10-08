import json,math,heapq,pathlib,os
GAME_ROOT=pathlib.Path(__file__).resolve().parents[1];ROOT=pathlib.Path(os.environ.get('CHOSUN_MODEL_ROOT',GAME_ROOT.parent/'architecture')); base=ROOT/'campus';out=ROOT/'transit'
g=json.load(open(base/'road_graph_3d.json'))['vehicle'];nodes=[list(p) for p in g['nodes']];edges=g['edges'];nav=json.load(open(base/'navigation.json'));refs=json.load(open(pathlib.Path(os.environ.get('TRANSIT_REFERENCE_PATH',GAME_ROOT/'data/shuttle-sources.json'))));refmap={s['id']:s for s in refs['stops']}
# These are pictorial-map/landmark reference anchors, NOT surveyed bus-stop points.
anchors=[('monument',[-95.506,-578.035]),('art',[-220.55,-344.5]),('library',[55.83,-222.575]),('engineering2',[427.62,-197.364]),('law_business',[350,-12]),('main_north',[-170,-17]),('student_union',[-120,-83])]
def projection(p,a,b):
 d=[b[i]-a[i] for i in range(2)];l=sum(v*v for v in d);t=max(0,min(1,sum((p[i]-a[i])*d[i] for i in range(2))/(l or 1)));q=[a[i]+(b[i]-a[i])*t for i in range(3)];return math.dist(p,q[:2]),q,t
selected=[];splits={}
for sid,p in anchors+[('social_science',[-350.395,48.612])]:
 candidates=[]
 for ei,e in enumerate(edges):
  if e['width']<8:continue
  d,q,t=projection(p,nodes[e['a']],nodes[e['b']]);candidates.append((d,ei,q,t))
 d,ei,q,t=min(candidates);nid=len(nodes);nodes.append(q);splits.setdefault(ei,[]).append((t,nid));selected.append({'id':sid,'node':nid,'edge':ei,'position':q,'anchor_distance':d,'width':edges[ei]['width']})
adj=[[] for _ in nodes]
for i,e in enumerate(edges):
 chain=[(0,e['a'])]+sorted(splits.get(i,[]))+[(1,e['b'])]
 for (_,a),(_,b) in zip(chain,chain[1:]):
  length=math.dist(nodes[a],nodes[b]);cost=length*(1 if e['width']>=8 else 1.8)
  adj[a].append((b,cost,i));adj[b].append((a,cost,i))
def shortest(a,b):
 todo=[(0,a)];cost={a:0};prev={}
 while todo:
  d,u=heapq.heappop(todo)
  if u==b:break
  if d!=cost.get(u):continue
  for v,w,ei in adj[u]:
   nd=d+w
   if nd<cost.get(v,float('inf')):cost[v]=nd;prev[v]=(u,ei);heapq.heappush(todo,(nd,v))
 if b not in cost:raise Exception('Disconnected transit stop')
 ns=[b];es=[]
 while ns[-1]!=a:u,ei=prev[ns[-1]];ns.append(u);es.append(ei)
 return list(reversed(ns)),list(reversed(es))
route=[];route_edges=[];stop_distances=[];total=0
for i,stop in enumerate(selected[:7]):
 stop_distances.append(total);ns,es=shortest(stop['node'],selected[(i+1)%7]['node']);pts=[nodes[n] for n in ns]
 if not route:route.append(pts[0])
 for a,b in zip(pts,pts[1:]):
  length=math.dist(a,b);N=max(1,math.ceil(length/2))
  for k in range(1,N+1):route.append([a[j]+(b[j]-a[j])*k/N for j in range(3)])
  total+=length
 route_edges.extend(es)
# Snap furniture off the carriageway, rejecting known building footprints.
footprints=[(b['min'][0],b['min'][1],b['max'][0],b['max'][1]) for b in nav['collisionBoxes']]
def free_footprint(center,theta,w,d):
 c=math.cos(theta);s=math.sin(theta);a=w/2+.5;bb=d/2+.5
 for x0,y0,x1,y1 in footprints:
  dx=(x0+x1)/2-center[0];dy=(y0+y1)/2-center[1];hx=(x1-x0)/2;hy=(y1-y0)/2
  if abs(dx)<=hx+abs(c)*a+abs(s)*bb and abs(dy)<=hy+abs(s)*a+abs(c)*bb and abs(dx*c+dy*s)<=a+hx*abs(c)+hy*abs(s) and abs(-dx*s+dy*c)<=bb+hx*abs(s)+hy*abs(c):return False
 return True
assets=[];stops=[]
for index,st in enumerate(selected):
 sid=st['id'];p=st['position'];e=edges[st['edge']];a,b=nodes[e['a']],nodes[e['b']]
 if index<7:
  # Forward tangent follows the routed segment leaving this stop.
  ns,_=shortest(st['node'],selected[(index+1)%7]['node']);a=nodes[ns[0]];b=next((nodes[n] for n in ns[1:] if math.dist(nodes[n][:2],a[:2])>.01),nodes[ns[-1]])
 dx=b[0]-a[0];dy=b[1]-a[1];n=math.hypot(dx,dy);tx,ty=dx/n,dy/n;normal=(-ty,tx);heading=math.atan2(-tx,ty)
 shelter=sid in ['monument','social_science'];w,depth=(9.8,3.35) if sid=='monument' else (4.95,2.8) if shelter else (1.1,.4)
 found=None
 for offset in [9,11,14,17,20]:
  for side in [1,-1]:
   center=[p[0]+normal[0]*offset*side,p[1]+normal[1]*offset*side,p[2]-.30];theta=math.atan2(ty,tx)+(0 if side==1 else math.pi)
   if free_footprint(center,theta,w,depth):found=(center,theta,side);break
  if found:break
 if not found:raise Exception('No clear roadside furniture place for '+sid)
 center,theta,side=found;c=math.cos(theta);s=math.sin(theta)
 if shelter:
  file='shelter_reference.glb' if sid=='monument' else 'shelter_education.glb';assets.append({'file':file,'name':'TRANSIT_SHELTER_'+sid,'position':center,'yaw':theta,'role':'shelter','source':'2021 photo-informed, dimensions and placement approximate'})
  pole=[center[0]+s*1.8,center[1]-c*1.8,center[2]];waiting=[center[0]+c*2.2+s,center[1]+s*2.2-c,center[2]+.08]
 else:pole=center;waiting=[center[0]+normal[0]*side*1.4,center[1]+normal[1]*side*1.4,center[2]]
 assets.append({'file':'bus_stop_sign.glb' if sid=='monument' else 'bus_stop_generic.glb','name':'TRANSIT_SIGN_'+sid,'position':pole,'yaw':theta,'role':'sign','source':'Photo-informed sign type; game placement, not surveyed'})
 stops.append({'id':sid,'name':refmap[sid]['name'],'position':p,'yaw':heading,'waitingPosition':waiting,'shelterPosition':center if shelter else None,'roadWidth':e['width'],'graphEdge':st['edge'],'source':refs['sources'][0]['url'],'placementAccuracy':'Road-snapped game reconstruction, not surveyed stop coordinates','routeDistance':stop_distances[index] if index<7 else None})
assets.append({'file':'shuttle_bus.glb','name':'TRANSIT_DISPLAY_BUS_monument','position':stops[0]['position'],'yaw':stops[0]['yaw'],'role':'display_bus','source':'2015 photo-informed vehicle; static architectural display only; remove from game before animated fleet'})
result={'coordinate_system':'Blender x/y/z meters; yaw radians about +Z','xy_ground_resample_required':True,'route_label':'공식 정류장 순서 기반 게임용 주행 경로','route_source':refs['sources'][0]['url'],'stops':stops,'assets':assets,'route':{'id':'main_loop','name':'교내 순환 셔틀','points':route,'stopIds':[s['id'] for s in stops[:7]],'length_m':total,'minimum_road_width':min(edges[i]['width'] for i in route_edges),'graph_source':'road_graph_3d.json','actual_route_geometry_verified':False,'stop_order_verified':True},'game_operating_parameters':{'cruiseSpeed':6,'dwellSeconds':10,'vehicleCount':2,'nominalHeadwaySeconds':round((total/6+70)/2)}}
(out/'transit_placements.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'length':total,'points':len(route),'min_width':result['route']['minimum_road_width'],'stops':[{'id':s['id'],'position':s['position'],'waiting':s['waitingPosition']} for s in stops],'assets':len(assets)},ensure_ascii=False))
