import os,glob,json,hashlib
from PIL import Image
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/delivery';outputs=[]
for folder,pattern in [('building_catalog','[0-9][0-9][0-9]_*.jpg'),('building_catalog','review-sheet-*.jpg'),('stair_details_final','*.png')]:
 out=R+'/github_preview/'+folder;os.makedirs(out,exist_ok=True)
 for p in sorted(glob.glob(R+'/'+folder+'/'+pattern)):
  im=Image.open(p).convert('RGB');native=im.size;im.thumbnail((1600,1600),Image.Resampling.LANCZOS);dest=out+'/'+os.path.splitext(os.path.basename(p))[0]+'.jpg'
  for q in [85,82,80,77,75,70,65]:
   im.save(dest,quality=q,optimize=True)
   if os.path.getsize(dest)<=393000:break
  assert os.path.getsize(dest)<=393000
  meta=os.path.splitext(p)[0]+'.json';meta=json.load(open(meta)) if os.path.exists(meta) else {}
  outputs.append({'file':os.path.relpath(dest,R+'/github_preview'),'source_render':os.path.relpath(p,R),'source_render_sha256':hashlib.sha256(open(p,'rb').read()).hexdigest(),'actual_render_source_sha256':meta.get('source_sha256'),'native_size':native,'preview_size':im.size,'quality':q,'bytes':os.path.getsize(dest),'sha256':hashlib.sha256(open(dest,'rb').read()).hexdigest()})
json.dump(outputs,open(R+'/github_preview/catalog-stair-preview-manifest.json','w'),ensure_ascii=False,indent=2)
print('Previews',len(outputs),'max bytes',max(o['bytes'] for o in outputs))
