"""Standalone source/model contract audit for the remaining-building pass."""
import json,os,math,sys,collections
P=os.path.dirname(__file__);OUT=sys.argv[1] if len(sys.argv)>1 else P
load=lambda n:json.load(open(os.path.join(OUT,n)))
nav=load('navigation.json');cov=load('campus_coverage.json');cat=load('building_render_catalog.json');built=load('terrain_building_pads.json')
oldP='/workspace/shared/chosun_model_backups/20261008_pre_remaining/campus'
old=json.load(open(oldP+'/campus_coverage.json'));oldnav=json.load(open(oldP+'/navigation.json'))
key=lambda b:(b['id'],b['osm_id'])
missing=set(map(key,old['named_coverage']))-set(map(key,cov['named_coverage']))
missing_ids={d['id'] for d in oldnav['landmarks']}-{d['id'] for d in nav['landmarks']}
assert not missing,(missing,'lost original building');assert not missing_ids,(missing_ids,'lost destination')
assert len(cat)==cov['buildings']==len(cov['named_coverage'])==len(built)
assert {key(b) for b in cat}=={key(b) for b in cov['named_coverage']}
bad=[];winding=[]
for su in nav['walkableSurfaces']:
 p=su['polygon'];x=sum(a[0] for a in p)/len(p);y=sum(a[1] for a in p)/len(p);z=sum(a[2] for a in p)/len(p)
 cross=(p[1][0]-p[0][0])*(p[2][1]-p[0][1])-(p[1][1]-p[0][1])*(p[2][0]-p[0][0])
 if cross<=0:winding.append(su['id'])
 for bb in nav['collisionBoxes']:
  if bb['min'][0]<x<bb['max'][0] and bb['min'][1]<y<bb['max'][1] and bb['min'][2]<=z+1.0<=bb['max'][2]:bad.append([su['id'],bb['label']])
assert not winding,winding
# Exact central treads, not merely a texture or named proxy.
central=[s for s in nav['walkableSurfaces'] if s['id'].startswith('central108_tread_')]
assert len(central)==108
stair_steps=[{'id':p['id'],'steps':p.get('stepCount'),'max_riser':p.get('maxRiser')} for p in nav['pedestrianPaths']]
assert max(p['max_riser'] or 0 for p in stair_steps)<.30
area=lambda p:abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(p,p[1:]+p[:1]))/2)
osm=json.load(open(P+'/source_data/campus_osm_geometry.json'));original=next(f['points'] for f in osm['features'] if f['osm_id']=='503476184');original=original[:-1] if original[0]==original[-1] else original
split=[b for b in built if b['id'] in (139,152)];split_error=abs(sum(area(b['poly']) for b in split)-area(original));assert split_error<1e-6
report={'status':'pass' if not bad else 'needs correction','buildings':cov['buildings'],'destinations':len(nav['landmarks']),'original_buildings_preserved':len(old['named_coverage']),'original_destination_ids_preserved':len(oldnav['landmarks']),'building_catalog_entries':len(cat),'separate_main_building_catalog':'main_building_catalog.json','walkable_surfaces':len(nav['walkableSurfaces']),'positive_upward_winding':not winding,'walk_surface_center_collision_conflicts':bad,'central_individual_treads':len(central),'stair_paths':stair_steps,'dental_split_area_error_m2':split_error,'no_reference_photo_textures':'All new geometry procedural; researched photo pixels not embedded.','limits':['Exterior reconstruction, not a measurement survey.','Exact riser allocation, entrance alignment, footprint-less buildings and hidden elevations remain estimates.','Eighteen unnamed/accessory OSM records remain exterior-unverified.','Five CIT buildings use group evidence; individual wing attribution remains incomplete.','Official photo timestamps vary; many images predate 2026.']}
json.dump(report,open(OUT+'/remaining_verification.json','w'),ensure_ascii=False,indent=2)
print(json.dumps(report,ensure_ascii=False,indent=2))
if bad:sys.exit(2)
