"""Package the photo/detail correction as reproducible sources + final GLB.
No reference photographs are redistributed. Run only after QA and final export.
"""
from pathlib import Path
import shutil, json, hashlib, zipfile
root=Path(__file__).resolve().parents[1]
out=root/'delivery'
stage=Path('/workspace/scratch/b09eacf6919d/Chosun_Campus_Final_20261008')
stage.mkdir(parents=True,exist_ok=True)
def copy(p,relative):
    dest=stage/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
copy(out/'Chosun_Campus.glb','Chosun_Campus.glb')
copy(out/'CAMPUS_README_KO.txt','README_KO.txt')
for part in ['building','site','campus','transit','materials','integration','lighting']:
    for p in (root/part).glob('*.py'):
        if not p.name.startswith('package_'):copy(p,Path('sources')/part/p.name)
for part in ['building','site','campus','transit','materials','lighting']:
    for p in (root/part).glob('*'):
        if p.is_file() and p.suffix.lower() in ['.json','.txt','.md']:
            copy(p,Path('sources')/part/p.name)
copy(out/'Chosun_Campus_materials.json','sources/materials/final_game_fallback_materials.json')
copy(out/'Chosun_Campus_pbr_report.json','verification/pbr_report.json')
for p in (root/'campus'/'source_data').rglob('*'):
    if p.is_file() and p.suffix.lower() not in ['.jpg','.jpeg','.png','.webp','.html']:
        copy(p,Path('sources/campus/source_data')/p.relative_to(root/'campus'/'source_data'))
# Exact runtime caches and reusable transit exchange assets accompany source scripts.
for p in (root/'campus').glob('*.json'):
    copy(p,Path('sources/campus')/p.name)
for p in (root/'transit').glob('*'):
    if p.is_file() and (p.suffix.lower()=='.glb' or p.name=='transit_placements.json'):
        copy(p,Path('sources/transit')/p.name)
for part in ['campus','transit']:
    for p in (root/part).glob('*'):
        if p.is_file() and p.suffix.lower() in ['.json','.txt','.md']:
            copy(p,Path('references')/part/p.name)
for p in Path('/workspace/shared/chosun_detail_refs').rglob('*'):
    if p.is_file() and p.suffix.lower() in ['.json','.md']:
        copy(p,Path('references/detail_research')/p.relative_to('/workspace/shared/chosun_detail_refs'))
copy(out/'campus_verification.json','verification/integrated.json')
qa=Path('/workspace/shared/chosun_final_qa/report.json')
if qa.exists():copy(qa,'verification/detail_qa.json')
for p,rel in [(Path('/workspace/shared/ai1_publish/THIRD_PARTY_NOTICES.md'),'THIRD_PARTY_NOTICES.md'),(Path('/workspace/shared/ai1_publish/licenses/Noto-CJK-COPYRIGHT.txt'),'licenses/Noto-CJK-COPYRIGHT.txt')]:
    if p.exists():copy(p,rel)
files={str(p.relative_to(stage)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(stage.rglob('*')) if p.is_file() and p.name!='SHA256.json'}
(stage/'SHA256.json').write_text(json.dumps(files,ensure_ascii=False,indent=2))
def makezip(path,items,prefix):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,6) as z:
        for p,rel in items:z.write(p,str(Path(prefix)/rel))
    with zipfile.ZipFile(path) as z:assert z.testzip() is None
    return {'path':str(path),'bytes':path.stat().st_size}
result=[]
result.append(makezip(stage.parent/'Chosun_Campus_Source_GLB.zip',[(p,p.relative_to(stage)) for p in sorted(stage.rglob('*')) if p.is_file()],'Chosun_Campus_Model'))
result.append(makezip(stage.parent/'Chosun_Campus_Building_Renders.zip',[(p,p.relative_to(out/'building_catalog')) for p in sorted((out/'building_catalog').rglob('*')) if p.is_file() and p.suffix in ['.jpg','.png','.json','.txt','.html'] and not p.name.startswith('review-sheet')]+[(p,Path('stair_details')/p.name) for p in sorted((out/'stair_details_final').glob('*')) if p.is_file() and p.suffix in ['.png','.json']], 'Chosun_Campus_Building_Renders'))
result.append(makezip(stage.parent/'Chosun_Campus_TimeOfDay_Renders.zip',[(p,p.name) for p in sorted((out/'time_of_day_final').glob('*')) if p.is_file() and p.suffix in ['.png','.json']],'Chosun_Campus_Model/renders/time_of_day'))
print(json.dumps(result,ensure_ascii=False))
