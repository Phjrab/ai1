import json,math,os,time
from functools import lru_cache
import terrain_elevation as te
from terrain_roadbeds import Roadbeds
P=os.path.dirname(__file__)
# Execute only the model's pure data/footprint assembly, not Blender operations.
s=open(P+'/build_campus.py').read();start=s.index('def cleanpoly(');end=s.index('# Flatten building terraces')
ns={'json':json,'math':math,'os':os,'P':P,'DATA':P+'/source_data','rawheight':te.rawheight,'rect':lambda cx,cy,w,d:[(cx-w/2,cy-d/2),(cx+w/2,cy-d/2),(cx+w/2,cy+d/2),(cx-w/2,cy+d/2)]}
ns['FLOORS']={139:4,152:6};ns['HEIGHTS']={}
ns['manifest']=json.load(open(P+'/source_data/campus_manifest.json'));ns['osm']=json.load(open(P+'/source_data/campus_osm_geometry.json'));ns['features']=[f for f in ns['osm']['features'] if f['include']];ns['landmarks']=[b for b in ns['manifest']['buildings'] if b['include']];ns['photos']={b['id']:b for b in json.load(open(P+'/source_data/facades/source_index.json'))}
exec(s[start:end],ns);built=ns['built'];pads=te.prepare_pads(built)
base=lambda x,y:te.padded_height(x,y,pads)
bed=Roadbeds(base,pads);bed.write_report('/workspace/shared/chosun_detail_refs/terrain/roadbed_corrections.json')
@lru_cache(None)
def g(x,y):return bed(x,y)
def height(x,y):
 x0=-490+math.floor((x+490)/5)*5;y0=-1120+math.floor((y+1120)/5)*5;u=(x-x0)/5;v=(y-y0)/5;a=g(x0,y0);c=g(x0+5,y0+5)
 return a*(1-u)+g(x0+5,y0)*(u-v)+c*v if v<=u else a*(1-v)+c*u+g(x0,y0+5)*(v-u)
d=json.load(open(P+'/road_surface_cache.json'));grades=[]
for r in d['roads']:
 if not r['vehicle']:continue
 for path in r['paths']:
  for a,b in zip(path,path[1:]):
   le=math.dist(a,b);n=max(1,math.ceil(le/2))
   for j in range(n):
    p=(a[0]+(b[0]-a[0])*j/n,a[1]+(b[1]-a[1])*j/n);q=(a[0]+(b[0]-a[0])*(j+1)/n,a[1]+(b[1]-a[1])*(j+1)/n);dz=abs(height(*p)-height(*q));grades.append({'grade':dz/(le/n or 1),'road':r['osm_id'],'point':p})
report={'max_grade':max(v['grade'] for v in grades),'segments_gt_30':sum(v['grade']>.30 for v in grades),'segments_gt_35':sum(v['grade']>.35 for v in grades),'worst':sorted(grades,key=lambda v:-v['grade'])[:30],'bed_report':bed.report}
json.dump(report,open('/workspace/shared/chosun_detail_refs/terrain/roadbed_grade_test.json','w'),ensure_ascii=False,indent=2)
print('buildings',len(built),'max_grade',report['max_grade'],'>30',report['segments_gt_30'],'>35',report['segments_gt_35']);print(report['worst'][:10]);print(bed.report)
found=[]
for b in built:
 vals=[height(*v[:2])-b['base'] for v in b['poly']]
 found.append({'id':b['id'],'name':b['name'],'min_ground_minus_base_m':round(min(vals),3),'max_ground_minus_base_m':round(max(vals),3)})
json.dump(found,open('/workspace/shared/chosun_detail_refs/terrain/foundation_terrain_offsets.json','w'),ensure_ascii=False,indent=2)
print('largest foundations',sorted(found,key=lambda b:b['min_ground_minus_base_m'])[:8]);print('buried edges',sorted(found,key=lambda b:-b['max_ground_minus_base_m'])[:8])
