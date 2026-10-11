#!/usr/bin/env python3
"""Apply reversible lighting-only hooks to the preserved a65 game sources."""
from pathlib import Path
import os,json,hashlib
root=Path(__file__).resolve().parents[1]
base=root/'revision/a65-original'
changes=[]
def put(rel,text):
 p=root/rel;old=(base/rel).read_bytes()
 q=p.with_name(p.name+'.lighting-tmp');q.write_text(text);os.replace(q,p)
 changes.append({'path':rel,'before_sha256':hashlib.sha256(old).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'preserved':'revision/a65-original/'+rel})
game=(base/'dist/game.js').read_text()
assert hashlib.sha256(game.encode()).hexdigest()=='f435140b4755bf52cb0c44fad3d08c847307c1e92f4a23687bb4c0e4db73766e'
patches=[
('',"import {createStreetLighting,TIME_PRESETS} from './street-lighting.js';\nimport {STREET_LIGHTING_NATIVE} from './street-lighting-native.js';\n"),
("scene.add(new THREE.HemisphereLight('#f0f7ff','#74745a',1.6));", "const hemisphere=new THREE.HemisphereLight('#f0f7ff','#74745a',1.6);scene.add(hemisphere);"),
('renderer.render(scene,camera);}', 'streetLighting.update(camera.position,dt);renderer.render(scene,camera);}'),
('buildBlockerGrid();worldCollider.updateMatrixWorld(true);', 'blockers.push(...await streetLighting.load(loader));setLightingTime(\'evening\');buildBlockerGrid();worldCollider.updateMatrixWorld(true);'),
('scene,renderer,interact,reset,floorHeight,travelTo,ready:true,', 'scene,renderer,streetLighting,interact,reset,floorHeight,travelTo,ready:true,'),
('animate();loadWorld();', '''const streetLighting=createStreetLighting({scene,hemisphere,sun,renderer,mobileQuality,emitterOffset:STREET_LIGHTING_NATIVE.emitterOffset});
function setLightingTime(value){streetLighting.setTime(value);const select=$('#timeOfDay'),button=$('#timeToggle');if(select)select.value=value;if(button){button.disabled=false;button.textContent=TIME_PRESETS[value].label;button.setAttribute('aria-label','시간대: '+TIME_PRESETS[value].label+' · 눌러 변경');}}
if($('#timeOfDay'))$('#timeOfDay').onchange=e=>setLightingTime(e.target.value);
if($('#timeToggle'))$('#timeToggle').onclick=()=>{document.exitPointerLock?.();clearInputs();const modes=Object.keys(TIME_PRESETS);setLightingTime(modes[(modes.indexOf(streetLighting.state.time)+1)%modes.length]);};
if($('#nearLighting'))$('#nearLighting').onchange=e=>streetLighting.setDetail(e.target.checked);
animate();loadWorld();''')]
for before,after in patches:
 if not before:game=after+game;continue
 assert game.count(before)==1,(before,game.count(before))
 game=game.replace(before,after,1)
put('dist/game.js',game)
html=(base/'dist/index.html').read_text().replace('<div class="header-actions">','<div class="header-actions"><button id="timeToggle" disabled title="낮 / 저녁 / 야간 변경" aria-label="시간대 변경">저녁</button>',1)
needle='<h2>천천히 둘러보세요</h2>'
assert html.count(needle)==1
html=html.replace(needle,needle+'''<fieldset class="lighting-settings"><legend>캠퍼스 조명</legend><label for="timeOfDay">시간대</label><select id="timeOfDay"><option value="day">낮</option><option value="evening" selected>저녁</option><option value="night">야간</option></select><label class="lighting-detail"><input id="nearLighting" type="checkbox"> 가까운 조명 효과 높이기</label><p>기본 조명은 가볍게 표시됩니다. 가까운 조명 효과는 기기에 따라 느려질 수 있어요.</p></fieldset>''',1)
put('dist/index.html',html)
css=(base/'dist/style.css').read_text()+'''
/* Lighting controls share the existing menu and leave touch movement clear. */
.lighting-settings{border:1px solid #ffffff30;border-radius:8px;padding:12px;margin:0 0 22px;font-size:14px}.lighting-settings legend{color:#e9c876;padding:0 6px}.lighting-settings select{font:inherit;color:#fff;background:#24434c;border:1px solid #ffffff44;border-radius:5px;padding:6px;margin-left:10px}.lighting-settings select:focus-visible{outline:3px solid #edca75;outline-offset:3px}.lighting-detail{display:flex;align-items:center;gap:8px;margin-top:12px}.lighting-detail input{width:18px;height:18px;accent-color:#e9c876}.lighting-settings p{font-size:12px;line-height:1.6;margin-bottom:0;color:#c3d4db}#timeToggle{min-width:56px}
@media(max-width:430px){header{left:12px;right:12px}.header-actions button{padding:8px}.wordmark{gap:5px}.wordmark strong{font-size:14px}.wordmark div>span{font-size:7px}.crest{width:25px;height:30px;font-size:18px}#timeToggle{min-width:44px}}
'''
put('dist/style.css',css)
(root/'revision/game-patches.json').write_text(json.dumps({'base':'a65c2ae1','patches':[{'before':a,'after':b} for a,b in patches],'changed_files':changes},indent=2,ensure_ascii=False)+'\n')
print(json.dumps(changes,indent=2))
