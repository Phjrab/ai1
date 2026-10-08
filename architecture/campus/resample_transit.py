"""Derive final-Z transit data without altering authorized stop XY/order or source assets."""
import json,math

def _inside(x,y,p):
 c=False
 for a,b in zip(p,p[1:]+p[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:c=not c
 return c

def _seg(x,y,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy or 1)))
 return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)

def resample(source,out,height,nav,features):
 d=json.load(open(source))
 def walk(x,y):
  z=height(x,y)-.20
  for r in nav['roads']:
   if any(_seg(x,y,a,b)<=r['width']/2 for a,b in zip(r['points'],r['points'][1:])):z=max(z,height(x,y)+(.095 if r.get('vehicle') else .155))
  for f in features:
   if f['category']=='area' and (f['tags'].get('amenity')=='parking' or f['tags'].get('leisure')=='pitch') and _inside(x,y,f['points']):z=max(z,height(x,y)+.04)
  for s in nav.get('walkableSurfaces',[]):
   p=s['polygon']
   if _inside(x,y,p):
    # Triangular barycentric interpolation for sloped approaches.
    for inds in s['triangles']:
     a,b,c=[p[i] for i in inds];den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
     if abs(den)<1e-9:continue
     u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den;v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;w=1-u-v
     if min(u,v,w)>=-1e-7:z=max(z,u*a[2]+v*b[2]+w*c[2])
  return z
 for stop in d['stops']:
  x,y,_=stop['position'];stop['position'][2]=height(x,y)+.105
  x,y,_=stop['waitingPosition'];stop['waitingPosition'][2]=walk(x,y)+.02
  if stop.get('shelterPosition'):
   x,y,_=stop['shelterPosition'];stop['shelterPosition'][2]=height(x,y)-.18
  if stop.get('approach_qa'):
   a=stop['position'];b=stop['waitingPosition'];dist=math.dist(a[:2],b[:2]);n=max(1,math.ceil(dist/.5));pts=[]
   for k in range(n+1):
    t=k/n;x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t;pts.append({'distance_m':dist*t,'position':[x,y,height(x,y)-.20]})
   grade=max(abs(bb['position'][2]-aa['position'][2])/(dist/n) for aa,bb in zip(pts,pts[1:]))
   stop['approach_qa']={'terrain_samples':pts,'max_terrain_slope_degrees':math.degrees(math.atan(grade)),'waiting_vs_bus_contact_dz_m':b[2]-a[2],'road_paving_above_terrain_m':.295,'vehicle_contact_above_paving_m':.01,'finding':'Resampled against final DSM-derived earthworked surface; geometry is estimated, not a surveyed stop.'}
 for a in d['assets']:
  x,y,_=a['position'];mode=a.get('height_mode')
  if mode=='groundHeight':a['position'][2]=height(x,y)+a.get('height_offset',.025)
  elif mode=='roadHeight':a['position'][2]=height(x,y)+a.get('height_offset',.105)
  if a.get('role')=='shelter':
   ww,dd=(9.8,3.35) if a['file']=='shelter_reference.glb' else (4.95,2.8);ang=a.get('yaw',0);co,si=math.cos(ang),math.sin(ang)
   a['position'][2]=max(height(x+xx*co-yy*si,y+xx*si+yy*co)-.20 for xx,yy in [(-ww/2,-dd/2),(ww/2,-dd/2),(ww/2,dd/2),(-ww/2,dd/2)])+.01
   sid=a['name'].replace('TRANSIT_SHELTER_','')
   for stop in d['stops']:
    if stop['id']==sid and stop.get('shelterPosition'):stop['shelterPosition'][2]=a['position'][2]
 for p in d['route']['points']:p[2]=height(p[0],p[1])+.095
 d['route']['final_length_3d_m']=sum(math.dist(a,b) for a,b in zip(d['route']['points'],d['route']['points'][1:]))
 d['xy_ground_resample_required']=False
 d['height_note']='Final Z resampled from campus height (DSM trend, protected main core, vehicle and pedestrian grade corrections). All XY, stop identities/order and source route metrics preserved. Runtime should recompute 3D cumulative distances.'
 d['final_surface_offsets']={'terrain':-.20,'vehicle_paving':.095,'bus_tire_contact':.105,'pedestrian_paving':.155,'waiting_foot_clearance':.02}
 with open(out,'w') as f:json.dump(d,f,ensure_ascii=False,indent=2)
 return d
