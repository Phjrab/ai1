#!/usr/bin/env python3
"""Use the final source-reviewed stop overlay without regenerating route XY."""
from pathlib import Path
import argparse,copy,hashlib,json,math
DEFAULT_ROOT=Path(__file__).resolve().parents[1]
def cv(p):return [p[0],p[2],-p[1]]
def convert_stop(record):
    """Convert runtime geometry; source XY/GPS and evidence remain verbatim."""
    stop=copy.deepcopy(record)
    for key in ['position','waitingPosition','shelterPosition','boardingPosition','roadCenterlinePosition']:
        if stop.get(key) is not None: stop[key]=cv(stop[key])
    for key in ['travelTangent','outwardBoardingNormal']:
        if stop.get(key) is not None:
            vector=stop[key];stop[key]=cv(vector) if len(vector)==3 else [vector[0],-vector[1]]
    for box in stop.get('collisionBoxes',[]):
        box['center']=cv(box['center'])
        for key in ['halfExtents','halfSize']:
            if key in box: box[key]=[box[key][0],box[key][2],box[key][1]]
    return stop

def main():
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--issues-source',type=Path);parser.add_argument('--game-root',type=Path,default=DEFAULT_ROOT);args=parser.parse_args()
    ROOT=args.game_root;source=args.source;raw=source.read_bytes();overlay=json.loads(raw)
    issue_bytes=args.issues_source.read_bytes() if args.issues_source else None
    issues=json.loads(issue_bytes) if issue_bytes else None
    if issues is not None: assert isinstance(issues['issues'],list)
    def load(name,var):return json.loads((ROOT/'dist'/name).read_text().split('export const '+var+' = ')[1].rstrip(';\n'))
    def write(name,var,data): (ROOT/'dist'/name).write_text('// Derived source-reviewed game metadata; not live operations.\nexport const '+var+' = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n')
    transit=load('transit-config.js','TRANSIT');world=load('world-config.js','WORLD');nav=json.loads((ROOT/'data/campus-navigation.json').read_text());route=next(r for r in transit['routes'] if r['id']==overlay['route']['id'])
    assert route['stopIds']==overlay['route']['stopIds'],'The established seven-stop service order must be preserved'
    assert len(route['points'])==len(overlay['route']['points'])
    assert all(math.dist([a[0],a[2]],[b[0],-b[1]])<1e-5 for a,b in zip(route['points'],overlay['route']['points'])),'Unexpected shuttle route XY change'
    assert overlay['game_operating_parameters']['vehicleCount']==2
    transit['stops']=[]
    for record in overlay['stops']:
        stop=convert_stop(record)
        # createRoute projects the new stop position against the final grounded
        # 3D route; source routeDistance remains provenance, not an old metric.
        stop.pop('distance',None);transit['stops'].append(stop)
    route['points']=[cv(p) for p in overlay['route']['points']]
    route['terminalStopId']=route['stopIds'][0]
    route['headingSpanMeters']=6.4  # Actual model axle span; no route XY change.
    route['repeatCirculation']=False
    transit['timingLabel']='게임용 셔틀 2대 · 종점 정차 · 실제 시간표와 다릅니다'
    transit['terminalNotice']='종점 회차 동선 미확인으로 반복 순환 미구현'
    transit['sources']=list(dict.fromkeys([overlay['route_source'],*transit.get('sources',[])]))
    transit['notice']='현재 공식 안내의 7개 정류장 순서를 참고한 게임용 운행입니다. 종점 회차 동선 미확인으로 반복 순환 미구현. 두 차량은 종점 도착 후 정차하며 게임을 다시 시작하면 초기 운행을 볼 수 있습니다. 정류장 좌표·방향·형상은 근사 재구성이며 실시간 운행 정보가 아닙니다. 버스는 기존 도로 중심선을 따라 달리고, 연석 접근과 실제 탑승 애니메이션은 구현하지 않았습니다.'
    transit['additionalFacilityNote']='사회대 쉼터와 시내버스 정류장은 이 7개 정류장 교내 운행 시연과 별도입니다. 시내버스 표지는 출처·방향·모델 범위에 따라 일부만 표현하며 운행 상태를 실시간 제공하지 않습니다.'
    transit['cityStops']=[convert_stop(s) for s in overlay.get('cityStops',[])]
    transit['sourceReviewDate']=overlay['source_review_date'];transit['curbApproachAnimated']=False
    surfaces=[{**s,'id':'rv2_transit_landing_'+str(i)} for i,s in enumerate(overlay.get('walkableSurfaces',[]))]
    for target,is_world in [(world,True),(nav,False)]:
        target['walkableSurfaces']=[s for s in target.get('walkableSurfaces',[]) if not s['id'].startswith('rv2_transit_landing_')]+[{**s,'polygon':[cv(p) for p in s['polygon']]} if is_world else s for s in surfaces]
    write('transit-config.js','TRANSIT',transit);write('world-config.js','WORLD',world)
    (ROOT/'data/campus-navigation.json').write_text(json.dumps(nav,ensure_ascii=False,separators=(',',':'))+'\n');(ROOT/'data/transit-placements.json').write_bytes(raw);(ROOT/'data/transit-alignment-overlay.json').write_bytes(raw)
    report={'sourceSha256':hashlib.sha256(raw).hexdigest(),'routeXYUnchanged':True,'stopOrder':route['stopIds'],'simulatedBusCount':2,'terminalStopId':route['terminalStopId'],'repeatCirculation':False,'headingSpanMeters':6.4,'cityMarkers':sum(bool(s.get('created_geometry')) for s in overlay.get('cityStops',[])),'metadataOnlyCityStops':sum(not s.get('created_geometry') for s in overlay.get('cityStops',[])),'rightHandWaiting':[s['id'] for s in overlay['stops'] if s.get('boardingSide')=='right'],'curbApproachAnimated':False,'source':overlay['route_source'],'sourceReviewDate':overlay['source_review_date']}
    if issues is not None:
        (ROOT/'data/transit-integration-issues.json').write_bytes(issue_bytes)
        report['geometryReview']={'sourceSha256':hashlib.sha256(issue_bytes).hexdigest(),'issues':issues['issues'],'status':issues.get('status'),'scope':'Source review issues retained verbatim; geometry closure requires final native/runtime evidence.'}
    (ROOT/'data/transit-revision-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__': main()
