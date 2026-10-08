"""Independent deterministic 2D triangle coverage and terrain-cell partition audit."""
import os,json,math
P=os.path.dirname(__file__);d=json.load(open(P+'/road_surface_cache.json'));r=json.load(open(P+'/road_continuity_report.json'))
for layer,out in zip(d['layers'],r['surface_meshes']):
 area=0;bad=0
 for face in layer['faces']:
  a,b,c=[layer['vertices'][i] for i in face];area+=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
  mx=(a[0]+b[0]+c[0])/3;my=(a[1]+b[1]+c[1])/3;x0=-490+math.floor((mx+490)/5)*5;y0=-1120+math.floor((my+1120)/5)*5;diag=(my-y0)<=(mx-x0)
  for x,y in [a,b,c]:
   if x<x0-1e-6 or x>x0+5+1e-6 or y<y0-1e-6 or y>y0+5+1e-6 or (diag and y-y0>x-x0+1e-6) or (not diag and y-y0<x-x0-1e-6):bad+=1;break
 out['triangle_area_error_m2']=abs(area-layer['area_m2']);out['faces_crossing_terrain_partition']=bad
 assert bad==0;assert out['triangle_area_error_m2']<.0001
json.dump(r,open(P+'/road_continuity_report.json','w'),indent=2)
print(json.dumps(r,indent=2))
