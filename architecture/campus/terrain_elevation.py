"""Pure-Python relative hillside elevation, retaining the authored main site.
Source: masked/smoothed 1 arcsec Copernicus DSM; see terrain metadata JSON.
Not a surveyed bare-earth surface. Roof heights MUST remain separate.
"""
import json,math,os
from functools import lru_cache
P=os.path.dirname(__file__)
@lru_cache(maxsize=1)
def data():
 with open(os.path.join(P,'source_data','terrain','elevation_grid.json')) as f:return json.load(f)
def legacy_height(x,y):
 if y<0:
  z=-18*max(0,min(1,(-y-27)/65))
  if y<-118:z-=(-y-118)*.052
 else:z=max(0,(y-33)*.34)*(1+.12*math.sin(max(-235,min(235,x))*.034))
 if abs(x)>235:z+=min(10,(abs(x)-235)*.018)
 return z
def trend_height(x,y):
 """Relative masked DSM trend; no building pads or core preservation."""
 d=data();u=(x-d['x0'])/d['step'];v=(y-d['y0'])/d['step']
 u=max(0,min(d['nx']-1.000001,u));v=max(0,min(d['ny']-1.000001,v));i=int(u);j=int(v);u-=i;v-=j;a=d['heights']
 return a[j][i]*(1-u)*(1-v)+a[j][i+1]*u*(1-v)+a[j+1][i]*(1-u)*v+a[j+1][i+1]*u*v
def preservation_weight(x,y):
 """Keep the entire imported near-main site exact, blend over 150m."""
 dx=max(abs(x)-235,0);dy=max(-128-y,y-123,0);t=min(1,math.hypot(dx,dy)/150.)
 return t*t*(3-2*t)
def rawheight(x,y):
 if not math.isfinite(x) or not math.isfinite(y):raise ValueError('Non-finite terrain coordinate')
 w=preservation_weight(x,y);return legacy_height(x,y)*(1-w)+trend_height(x,y)*w
def metadata():
 d=data();return {k:v for k,v in d.items() if k!='heights'}
def export_ground(height,path,x0=-490,y0=-1120,step=5,nx=231,ny=273):
 """Export FINAL callable after pads+triangle interpolation for runtime parity."""
 out={'version':1,'coordinate_system':'Blender Z-up meters; glTF [x,z,-y]','x0':x0,'y0':y0,'step':step,'nx':nx,'ny':ny,'interpolation':'triangles SW-SE-NE / SW-NE-NW, same as build_campus height','surface_offset_m':-.20,'heights':[[round(height(x0+i*step,y0+j*step),5) for i in range(nx)] for j in range(ny)],'elevation_metadata':metadata()}
 with open(path,'w') as f:json.dump(out,f,ensure_ascii=False,separators=(',',':'))
 return out

def _inpoly(x,y,p):
 c=False
 for a,b in zip(p,p[1:]+p[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:c=not c
 return c

def _distance(x,y,p):
 if _inpoly(x,y,p):return 0.
 best=float('inf')
 for a,b in zip(p,p[1:]+p[:1]):
  dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy or 1.)))
  best=min(best,math.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
 return best

def prepare_pads(buildings):
 """Use FINAL split footprints and bases. No change to caller building records.
 Width is a model design value: 12m minimum, up to 65m for steep sites.
 """
 pads=[]
 for b in buildings:
  p=[tuple(v[:2]) for v in b['poly']];base=b['base']
  relief=max(abs(rawheight(x,y)-base) for x,y in p)
  width=min(65.,max(12.,relief/.28))
  box=(min(x for x,y in p),min(y for x,y in p),max(x for x,y in p),max(y for x,y in p))
  pads.append({'poly':p,'base':base,'width':width,'bbox':box,'id':str(b.get('id') or b.get('osm_id') or b.get('name')),'cx':b['cx'],'cy':b['cy']})
 return sorted(pads,key=lambda b:b['id'])

def padded_height(x,y,pads):
 """Order-independent footprint pads; inverse-odds continuous blending.
 Existing near-main footprint/apron is unchanged. Not a retaining-wall survey.
 """
 z=rawheight(x,y)
 if abs(x)<200 and -30<y<33:return z
 hits=[];weighted=[]
 for p in pads:
  a,b,c,d=p['bbox'];width=p['width']
  if x<a-width or x>c+width or y<b-width or y>d+width:continue
  dist=_distance(x,y,p['poly'])
  if dist<1e-7:hits.append(p);continue
  if dist>=width:continue
  t=1-dist/width;w=t*t*(3-2*t);weight=w/max(1e-12,1-w);weighted.append((weight,p['base']))
 if hits:
  # A mapped overlap requires upstream footprint splitting; deterministic fallback.
  return min(hits,key=lambda p:((p['cx']-x)**2+(p['cy']-y)**2,p['id']))['base']
 den=1+sum(w for w,v in weighted)
 return (z+sum(w*v for w,v in weighted))/den
