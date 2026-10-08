import bpy,json,os,math
from mathutils import Vector
P=os.path.dirname(__file__);bpy.ops.wm.open_mainfile(filepath=P+'/campus.blend');g=json.load(open(P+'/ground_elevation.json'))
def height(x,y):
 u=(x-g['x0'])/g['step'];v=(y-g['y0'])/g['step'];i=math.floor(u);j=math.floor(v);u-=i;v-=j;i=max(0,min(g['nx']-2,i));j=max(0,min(g['ny']-2,j));a=g['heights'][j][i];c=g['heights'][j+1][i+1]
 return a*(1-u)+g['heights'][j][i+1]*(u-v)+c*v if v<=u else a*(1-v)+c*u+g['heights'][j+1][i]*(v-u)
areas=[];carcontact=[];treecontact=[]
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 if ob.name.startswith('CAMPUS_PLAZA'):
  bad=0;count=0;maxerr=0
  for face in ob.data.polygons:
   if face.normal.z<.2:continue
   v=face.center;clear=v.z-height(v.x,v.y);err=min(abs(clear-.04),abs(clear-.08));maxerr=max(maxerr,err);count+=1
   if err>.001:bad+=1
  areas.append({'name':ob.name,'tested_top_faces':count,'max_height_error_m':maxerr,'violations':bad})
 if ob.name.startswith('CAMPUS_CAR'):
  inds={i for face in ob.data.polygons if face.material_index==3 for i in face.vertices}
  gaps=[(ob.matrix_world@ob.data.vertices[i].co) for i in inds]
  gaps=[v.z-height(v.x,v.y)-.04 for v in gaps]
  if gaps:carcontact.append({'name':ob.name,'minimum_tire_clearance_m':min(gaps)})
 if ob.name.startswith('CAMPUS_TREE') or ob.name.startswith('Tree '):treecontact.append(abs(ob.location.z-(height(ob.location.x,ob.location.y)-.20)))
catalog=json.load(open(P+'/building_render_catalog.json'));missing=[r['collection'] for r in catalog if r['collection'] not in bpy.data.collections]
inf=[c.name for c in bpy.data.collections if 'INFERRED game terrain' in c.name];assert inf
transit=json.load(open(P+'/transit_placements.json'));errors=[]
for a in transit['assets']:
 ob=bpy.data.objects.get(a['name'])
 if ob:errors.append(max(abs(ob.location[i]-a['position'][i]) for i in range(3)))
report={'catalog_collections_missing':missing,'mapped_area_meshes':len(areas),'mapped_area_top_faces':sum(a['tested_top_faces'] for a in areas),'mapped_area_terrain_violations':sum(a['violations'] for a in areas),'max_area_height_error_m':max(a['max_height_error_m'] for a in areas),'parking_cars':len(carcontact),'minimum_car_tire_clearance_m':min(c['minimum_tire_clearance_m'] for c in carcontact),'cars_tires_below_paving_more_than_5cm':[c for c in carcontact if c['minimum_tire_clearance_m']<-.05],'max_tree_ground_error_m':max(treecontact),'inferred_collection':inf,'transit_native_json_max_position_error_m':max(errors),'areas':areas}
json.dump(report,open(P+'/final_native_verification.json','w'),ensure_ascii=False,indent=2);print(json.dumps({k:v for k,v in report.items() if k!='areas'},ensure_ascii=False,indent=2))
