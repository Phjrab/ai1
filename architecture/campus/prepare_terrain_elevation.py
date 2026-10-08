"""Reproduce conservative campus terrain from public Copernicus DSM.
Run with /usr/bin/python3 (GDAL, NumPy, SciPy), after downloading source_url.
The masked/smoothed result is an approximation, NOT surveyed bare earth.
"""
import os,json,math,hashlib
import numpy as np
from osgeo import gdal
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter
P=os.path.dirname(__file__);REF='/workspace/shared/chosun_detail_refs/terrain';os.makedirs(REF,exist_ok=True)
SOURCE=REF+'/N35E126.tif'
URL='https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N35_00_E126_00_DEM/Copernicus_DSM_COG_10_N35_00_E126_00_DEM.tif'
m=json.load(open(P+'/source_data/campus_manifest.json'));osm=json.load(open(P+'/source_data/campus_osm_geometry.json'))
t=m['transform'];ex,nx=t['x_axis_east_north'];ey,ny=t['y_axis_east_north'];lat0=t['origin_lat'];lon0=t['origin_lon'];off=t['offset_y'];R=6371000.;latmet=R*math.pi/180;lonmet=latmet*math.cos(math.radians(lat0))
def ll(x,y):return lat0+(x*nx+(y-off)*ny)/latmet,lon0+(x*ex+(y-off)*ey)/lonmet
def xy(lat,lon):
 e=(lon-lon0)*lonmet;n=(lat-lat0)*latmet;return e*ex+n*nx,e*ey+n*ny+off
polys=[f['points'] for f in osm['features'] if f['category']=='building']
def inside(x,y,p):
 c=False
 for a,b in zip(p,p[1:]+p[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:c=not c
 return c
def segdist(x,y,a,b):
 dx=b[0]-a[0];dy=b[1]-a[1];u=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy or 1)))
 return math.hypot(x-a[0]-u*dx,y-a[1]-u*dy)
# Expanded source-pixel mask includes main building and all mapped roofs.
bs=[(p,(min(v[0] for v in p)-18,min(v[1] for v in p)-18,max(v[0] for v in p)+18,max(v[1] for v in p)+18)) for p in polys]
def masked(x,y):
 for p,(a,b,c,d) in bs:
  if a<=x<=c and b<=y<=d and (inside(x,y,p) or min(segdist(x,y,q,r) for q,r in zip(p,p[1:]+p[:1]))<18):return True
 return False
gdal.UseExceptions();ds=gdal.Open(SOURCE);g=ds.GetGeoTransform();corners=[ll(x,y) for x in [-750,920] for y in [-1380,500]]
i0=math.floor((min(p[1] for p in corners)-g[0])/g[1])-3;i1=math.ceil((max(p[1] for p in corners)-g[0])/g[1])+3
j0=math.floor((max(p[0] for p in corners)-g[3])/g[5])-3;j1=math.ceil((min(p[0] for p in corners)-g[3])/g[5])+3
a=ds.ReadAsArray(i0,j0,i1-i0,j1-j0).astype(float);coords=[];mask=[]
for j in range(a.shape[0]):
 for i in range(a.shape[1]):
  pos=xy(g[3]+(j+j0+.5)*g[5],g[0]+(i+i0+.5)*g[1]);coords.append(pos);mask.append(masked(*pos))
coords=np.array(coords);mask=np.array(mask);vals=a.ravel().copy();tree=cKDTree(coords[~mask]);dist,inds=tree.query(coords[mask],k=8);weights=1/np.maximum(dist,1)**2;vals[mask]=np.sum(vals[~mask][inds]*weights,axis=1)/weights.sum(axis=1)
# 1-pixel Gaussian suppresses residual roof/tree-scale surface variation. Does not create new measured resolution.
filtered=gaussian_filter(vals.reshape(a.shape),sigma=1.,mode='nearest')
def sample(arr,x,y):
 lat,lon=ll(x,y);u=(lon-g[0])/g[1]-.5-i0;v=(lat-g[3])/g[5]-.5-j0;i=math.floor(u);j=math.floor(v);u-=i;v-=j
 return float(arr[j,i]*(1-u)*(1-v)+arr[j,i+1]*u*(1-v)+arr[j+1,i]*(1-u)*v+arr[j+1,i+1]*u*v)
# Near-main apron is the preserved model floor, not its DSM roof point.
anchor_pts=[(x,-25) for x in [-80,-40,0,40,80]];datum=float(np.median([sample(filtered,*p) for p in anchor_pts]))
x0,y0,step=-700,-1350,10;nxg,nyg=157,177
heights=[[round(sample(filtered,x0+i*step,y0+j*step)-datum,4) for i in range(nxg)] for j in range(nyg)]
notice='produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved'
meta={'dataset':'Copernicus DEM GLO-30 Public, AWS 2021 release','source_url':URL,'source_sha256':hashlib.sha256(open(SOURCE,'rb').read()).hexdigest(),'accessed':'2026-10-08','source_resolution_arcseconds':1,'source_resolution_m_approx':[25.3,30.9],'resampling_grid_m':10,'horizontal_crs':'EPSG:4326','vertical_datum':'EGM2008 orthometric meters (EPSG:3855)','attribution':notice,'license_url':'https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf','limitations':'DSM includes structures and canopy. OSM footprint + 18m masks are interpolated from 8 unaffected neighbors and smoothed sigma=1 source pixel. This is a relative approximate ground trend, not a surveyed DTM or step/retaining-wall measurement. Unmapped roofs and canopy may remain. 10m output grid does not improve source resolution.','mask_source':'OpenStreetMap footprints in campus_osm_geometry.json, ODbL 1.0','masked_pixels':int(mask.sum()),'source_crop_pixels':list(a.shape),'model_zero_method':'median of smoothed masked DSM at five main-building front-apron points; original detailed core geometry retained','datum_egm2008_m':datum,'anchor_apron_points':anchor_pts,'transform':t,'x0':x0,'y0':y0,'step':step,'nx':nxg,'ny':nyg,'heights':heights}
os.makedirs(P+'/source_data/terrain',exist_ok=True);json.dump(meta,open(P+'/source_data/terrain/elevation_grid.json','w'),ensure_ascii=False,separators=(',',':'))
samples=[]
for b in m['buildings']:
 if b.get('include'):
  x,y=b['x'],b['y'];samples.append({'id':b['id'],'name':b['name'],'x':x,'y':y,'dsm_egm2008_m':round(sample(a,x,y),3),'masked_smoothed_egm2008_m':round(sample(filtered,x,y),3),'relative_trend_m':round(sample(filtered,x,y)-datum,3)})
json.dump({'datum_egm2008_m':datum,'samples':samples,'metadata':{k:v for k,v in meta.items() if k!='heights'}},open(REF+'/terrain_source_samples.json','w'),ensure_ascii=False,indent=2)
print('datum',datum,'mask',int(mask.sum()),'crop',a.shape,'model range',min(map(min,heights)),max(map(max,heights)))
