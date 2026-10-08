"""Assemble checked render metadata. QA decisions must be made visually, not inferred."""
import os,json,hashlib,argparse
from PIL import Image,ImageDraw,ImageFont
P=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap=argparse.ArgumentParser();ap.add_argument('--out',default=P+'/delivery/building_catalog');ap.add_argument('--sha',required=True);ap.add_argument('--count',type=int,default=69);ap.add_argument('--allow-pending',action='store_true');a=ap.parse_args()
rows=[]
for f in sorted(os.listdir(a.out)):
 if not f.endswith('.json') or not f[:3].isdigit():continue
 r=json.load(open(a.out+'/'+f))
 if r['source_sha256']!=a.sha:
  eq=r.get('release_equivalence',{});r['release_validation']=bool(eq.get('verified') and eq.get('final_release_source_sha256')==a.sha);assert a.allow_pending or r['release_validation'],(r['index'],'unverified source reuse')
 else:r['release_validation']=True
 if not r.get('file'):continue
 path=a.out+'/'+r['file'];assert hashlib.sha256(open(path,'rb').read()).hexdigest()==r['file_sha256']
 with Image.open(path) as im:assert im.size==(r['width'],r['height']);im.verify()
 status=r['catalog_record'].get('review_status','');r['evidence_label_ko']=('공개사진 미확인 · 주변 맥락용 추정 부속동' if r['catalog_record'].get('id') is None else '기존 공식사진 참고·단순화 / 이번 개별 대조 미검증') if 'unidentified accessory' in status else ('그룹사진 확인 · 개별 동 식별 불완전' if 'group photo' in status else '사진 참고 재구성 · 치수·가려진 면은 추정');rows.append(r)
assert len({r['index'] for r in rows})==len(rows)
rows.sort(key=lambda r:r['index']);missing=sorted(set(range(1,a.count+1))-{r['index'] for r in rows})
manifest={'source_sha256':a.sha,'expected_count':a.count,'actual_count':len(rows),'missing_indices':missing,'all_present':not missing,'all_visually_reviewed':all(r['visual_review']=='accepted' for r in rows),'all_release_consistent':all(r['release_validation'] for r in rows),'images':rows}
json.dump(manifest,open(a.out+'/catalog-manifest.json','w'),ensure_ascii=False,indent=2)
fontpath='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc';font=ImageFont.truetype(fontpath,18)
for offset in range(0,a.count,9):
 page=Image.new('RGB',(1440,1170),'#ededed');draw=ImageDraw.Draw(page)
 for j in range(9):
  idx=offset+j+1
  if idx>a.count:continue
  x=(j%3)*480;y=(j//3)*390;r=next((r for r in rows if r['index']==idx),None)
  if not r:
   draw.text((x+12,y+12),f"{idx:03d} PENDING",font=font,fill='gray');continue
  im=Image.open(a.out+'/'+r['file']);im.thumbnail((480,360));page.paste(im,(x+(480-im.width)//2,y));draw.text((x+8,y+361),f"{r['index']:03d} {r['name'][:24]}",font=font,fill='black')
 page.save(a.out+f'/review-sheet-{offset//9+1:02d}.jpg',quality=94)
print(json.dumps({'actual':len(rows),'expected':a.count,'missing':missing,'all_reviewed':manifest['all_visually_reviewed']}))
