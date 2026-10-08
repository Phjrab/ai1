import os,json,math
from PIL import Image,ImageDraw,ImageFont
P=os.path.dirname(__file__);data=json.load(open(P+'/road_surface_cache.json'));fs=json.load(open(P+'/source_data/campus_osm_geometry.json'))['features']
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
def draw(bounds,path,title):
 im=Image.new('RGB',(1800,1120),'#f6f3ea');d=ImageDraw.Draw(im);xmin,ymin,xmax,ymax=bounds;s=min(845/(xmax-xmin),980/(ymax-ymin))
 for panel in range(2):
  ox=30+panel*900;oy=95
  def xy(p):return (ox+(p[0]-xmin)*s,oy+(ymax-p[1])*s)
  d.rectangle([ox,oy,ox+(xmax-xmin)*s,oy+(ymax-ymin)*s],fill='#dbe3cf')
  for f in fs:
   if f['include'] and f['category']=='building' and all(xmin<=v[0]<=xmax and ymin<=v[1]<=ymax for v in f['points']):d.polygon([xy(p) for p in f['points']],fill='#b8b4aa',outline='#8c887d')
  if panel:
   for j,layer in enumerate(data['layers']):
    vs=layer['vertices']
    for face in layer['faces']:
     p=[vs[i] for i in face]
     if all(xmin<=v[0]<=xmax and ymin<=v[1]<=ymax for v in p):d.polygon([xy(v) for v in p],fill='#536372' if j==0 else '#afa288')
  else:
   for r in data['roads']:
    p=r['points'];w=r['width'];dense=[]
    for a,b in zip(p,p[1:]):
     n=max(1,math.ceil(math.dist(a,b)/2.2));dense.extend([(a[0]+(b[0]-a[0])*j/n,a[1]+(b[1]-a[1])*j/n) for j in range(n)])
    dense.append(p[-1])
    for i,(a,b) in enumerate(zip(dense,dense[1:])):
     mx,my=(a[0]+b[0])/2,(a[1]+b[1])/2
     if abs(mx)<232 and -128<my<123:continue
     if not all(xmin<=v[0]<=xmax and ymin<=v[1]<=ymax for v in [a,b]):continue
     d.line([xy(a),xy(b)],fill='#536372' if r['vehicle'] else '#afa288',width=max(1,round(w*s)))
   if xmin<-232<xmax:
    pts=[xy(v) for v in [(-232,-128),(232,-128),(232,123),(-232,123),(-232,-128)]];d.line(pts,fill='#c4513c',width=2)
  d.text((ox,55),'BEFORE: broad road omission' if not panel else 'AFTER: mapped paving restored',font=font,fill='#21333e')
 d.text((30,15),title,font=font,fill='#21333e');bottom=round(95+(ymax-ymin)*s);d.rectangle((0,bottom+1,1800,1120),fill='#f6f3ea');d.text((30,bottom+25),'OSM roads only; pre-existing main-building site roads omitted in BOTH panels. No new centerlines.',font=small,fill='#354550');im.crop((0,0,1800,bottom+65)).save(path)
draw((-490,-1120,660,240),P+'/road_continuity_topview.png','CAMPUS ROAD GEOMETRY | identical coordinates / before and after')
draw((-280,-155,280,145),P+'/road_continuity_main_closeup.png','MAIN CAMPUS | clipped OSM road sections restored at original coordinates')
