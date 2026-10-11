import assert from 'node:assert/strict';
import {integrationPlan,integrationFeatures} from '../scripts/model-integration-plan.mjs';
const manifest={module_sha256:{},sidecar_sha256:{}};
function add(id){const f=integrationFeatures.find(f=>f.id===id);for(const m of [f.module,...(f.modules||[])])manifest.module_sha256['realism_v2/'+m]='bound';for(const s of f.files)manifest.sidecar_sha256['realism_v2/'+s]='bound';}
for(const f of integrationFeatures.filter(f=>f.required))add(f.id);
let plan=integrationPlan(manifest,'/fixture',{exists:()=>true});assert.equal(plan.public,false,'Unbound stale files must not activate a module');
add('public');delete manifest.sidecar_sha256['realism_v2/public_spaces_review/public_spaces_navigation.json'];assert.throws(()=>integrationPlan(manifest,'/fixture',{exists:()=>true}),/no bound runtime sidecar/);
add('public');assert.throws(()=>integrationPlan(manifest,'/fixture',{exists:p=>!p.endsWith('INTEGRATION_CONTRACT.json')}),/absent/);
add('track');plan=integrationPlan(manifest,'/fixture',{exists:()=>true});assert.equal(plan.track,true);
delete manifest.module_sha256['realism_v2/public_spaces.py'];assert.throws(()=>integrationPlan(manifest,'/fixture',{exists:()=>true}),/track requires public/);
add('public');add('roadSeams');add('studentLevels');plan=integrationPlan(manifest,'/fixture',{exists:()=>true});assert.equal(plan.roadSeams,true);assert.equal(plan.studentLevels,true);
delete manifest.sidecar_sha256['realism_v2/road_seam_repair_v5/game_cluster_routes.json'];assert.throws(()=>integrationPlan(manifest,'/fixture',{exists:()=>true}),/no bound runtime sidecar/);
add('roadSeams');add('itLowerRetirement');assert.throws(()=>integrationPlan(manifest,'/fixture',{exists:()=>true}),/itLowerRetirement requires itApproach/);
add('lounge');add('itApproach');assert.equal(integrationPlan(manifest,'/fixture',{exists:()=>true}).itLowerRetirement,true);
delete manifest.sidecar_sha256['realism_v2/it_approach_alignment_review/lower_paving_retirement.json'];assert.throws(()=>integrationPlan(manifest,'/fixture',{exists:()=>true}),/no bound runtime sidecar/);add('itLowerRetirement');
add('pedestrianResiduals');assert.throws(()=>integrationPlan(manifest,'/fixture',{exists:()=>true}),/pedestrianResiduals requires finitePaving/);add('finitePaving');assert.throws(()=>integrationPlan(manifest,'/fixture',{exists:()=>true}),/pedestrianResiduals requires walkAlignment/);add('entrances');add('walkAlignment');assert.equal(integrationPlan(manifest,'/fixture',{exists:()=>true}).pedestrianResiduals,true);
console.log('PASS: integration activates only native-bound modules and rejects missing sidecars/dependencies before mutation.');
