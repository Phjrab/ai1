// Rebuild the runnable game from one verified native export/sidecar revision.
// Does not modify the native model, publish Git, or deploy the Site.
import path from 'node:path';
import {existsSync,unlinkSync,readFileSync,mkdirSync,cpSync,copyFileSync,symlinkSync,readdirSync,renameSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {integrationPlan} from './model-integration-plan.mjs';
const game=path.resolve(import.meta.dirname,'..'),project=path.dirname(game),revision=process.env.CHOSUN_REALISM_ROOT||path.join(project,'realism_v2'),model=process.env.CHOSUN_MODEL_ROOT||path.join(project,'architecture');
const exportRoot=process.env.CHOSUN_GAME_EXPORT_ROOT||path.join(revision,'game_export');
// A reviewed staging build keeps the current runnable export intact on failure.
const stageOption=process.argv.find(arg=>arg.startsWith('--stage='));
if(stageOption){
 const stage=path.resolve(stageOption.slice(8));if(existsSync(stage))throw new Error('Staging destination already exists: '+stage);
 mkdirSync(stage,{recursive:true});for(const directory of ['dist','data','scripts','tests'])cpSync(path.join(game,directory),path.join(stage,directory),{recursive:true});
 for(const file of ['package.json','package-lock.json','README.md','QA.md','LICENSES.md','MODEL_PROVENANCE.json'])if(existsSync(path.join(game,file)))copyFileSync(path.join(game,file),path.join(stage,file));
 // Keep inherited results visibly separate from this target model's checks.
 // These are staging copies; the original runnable workspace remains intact.
 const previous=JSON.parse(readFileSync(path.join(stage,'MODEL_PROVENANCE.json'),'utf8')).native_scene?.sha256?.slice(0,12)||'previous-build';let history=path.join(stage,'tests','historical-results',previous);for(let n=2;existsSync(history);n++)history=path.join(stage,'tests','historical-results',previous+'-'+n);
 for(const name of readdirSync(path.join(stage,'tests'))){if(!name.endsWith('results.json'))continue;mkdirSync(history,{recursive:true});renameSync(path.join(stage,'tests',name),path.join(history,name));}
 const oldRuns=path.join(stage,'tests','runtime-runs');if(existsSync(oldRuns)){mkdirSync(history,{recursive:true});renameSync(oldRuns,path.join(history,'runtime-runs'));}
 symlinkSync(path.join(game,'node_modules'),path.join(stage,'node_modules'),'dir');
 console.log('Building isolated game staging directory:',stage);
 const result=spawnSync(process.execPath,[path.join(stage,'scripts/build-realism.mjs'),...process.argv.slice(2).filter(arg=>arg!==stageOption)],{cwd:stage,stdio:'inherit',env:{...process.env,CHOSUN_REALISM_ROOT:revision,CHOSUN_MODEL_ROOT:model,CHOSUN_GAME_EXPORT_ROOT:exportRoot}});
 if(result.error)throw result.error;if(result.status!==0)throw new Error('Staged build failed; review retained outputs at '+stage+' ('+(result.signal||result.status)+')');
 console.log(process.argv.includes('--check-inputs')?'Staged input preflight completed; assets were not rebuilt:':'Staged build completed:',stage);process.exit(0);
}
function run(command,args,extra={}){const result=spawnSync(command,args,{cwd:game,stdio:'inherit',env:{...process.env,...extra}});if(result.error)throw result.error;if(result.status!==0)throw new Error(command+' failed with '+(result.signal||result.status));}
function clearGenerated(names){for(const name of names){const file=path.join(game,'data',name);if(existsSync(file))unlinkSync(file);}}
run('python3',['scripts/verify-model-inputs.py',exportRoot],{CHOSUN_INPUT_ROOT:path.dirname(revision)});
const manifest=JSON.parse(readFileSync(path.join(exportRoot,'manifest.json'),'utf8')),plan=integrationPlan(manifest,revision);
const stages=[
 ['grade','sync-grade-revision.py',[path.join(revision,'verification')]],
 ['actorGrounding','integrate-actor-grounding.py',[path.join(revision,'terrain_v5/actor_grounding_v5.json')]],
 ['parking','integrate-parking.py',[path.join(revision,'verification/parking_gameplay.json')]],
 ['roof','integrate-rooftop.py',[path.join(revision,'it_roof_review/bridge_navigation.json')]],
 ['lounge','integrate-lounge.py',[path.join(revision,'it_lounge_review/lounge_navigation.json')]],
 ['entrances','integrate-entrances.py',[revision]],
 ['haeoreum','integrate-haeoreum-entrance.py',[path.join(revision,'terrain_v5/haeoreum_stair_navigation.json')]],
 ['public','integrate-public-spaces.py',[path.join(revision,'public_spaces_review/public_spaces_navigation.json'),'--contract',path.join(revision,'public_spaces_review/INTEGRATION_CONTRACT.json'),'--module-source',path.join(revision,'public_spaces.py'),...(plan.track?['--track-source',path.join(revision,'track_perimeter_review/track_navigation.json')]:[])]],
 ['pharmacy','integrate-pharmacy-entrance.py',[path.join(revision,'entrances_supplement/navigation.json')]],
 ['hospital','integrate-hospital-arrival.py',[path.join(revision,'hospital_arrival_review/hospital_arrival_overlay.json')]],
 ['schools','integrate-campus-access.py',['--school-source',path.join(revision,'affiliated_schools/overlay.json'),'--school-boundaries',path.join(revision,'affiliated_schools/source_geometry.json'),'--gate-source',path.join(revision,'gates_access/overlay.json'),...(plan.schoolRoadRepair?['--school-road-source',path.join(revision,'final_foundation_contacts/school_road_overlay.json')]:[])]],
 ['pond','integrate-pond.py',[path.join(revision,'pond_fountain/overlay.json')]],
 ['pondEntry','integrate-pond-entry.py',[path.join(revision,'pond_entry_steps/overlay.json')]],
 ['goals','integrate-football-goals.py',[path.join(revision,'football_goals_review/goal_navigation.json')]],
 ['terraces','integrate-parking-terraces.py',[path.join(revision,'parking_terraces_v5/contract.json')]],
 ['terraceDriveAlignment','integrate-terrace-drive-alignment.py',[path.join(revision,'terrace_drive_alignment/navigation.json')]],
 ['staticVehicles','integrate-static-vehicle-contract.py',[path.join(revision,'static_vehicle_v5/final_vehicle_poses.json')]],
 ['greenery','integrate-tree-contract.py',[path.join(revision,'greenery_infill/game_tree_sidecar.json')]],
 ['transit','integrate-transit-revision.py',[path.join(revision,'transit_alignment_overlay.json'),'--issues-source',path.join(revision,'transit_review/integration_issues.json')]],
 ['stopWalkways','integrate-stop-walkways.py',[path.join(revision,'hospital_stop_walkways/hospital_stop_walkways_overlay.json')]],
 ['garageRoadRepair','integrate-garage-exterior.py',[path.join(revision,'final_garage_road_boundary/exterior_navigation.json')]],
 ['publicWalkRepair','integrate-walk-alignments.py',['--public-source',path.join(revision,'public_walk_clearance_review/navigation.json')]],
 ['roseEndpoint','integrate-rose-endpoint.py',[path.join(revision,'final_rose_endpoint_join/rose_endpoint_paving_runtime.json')]],
 ['walkAlignment','integrate-walk-alignments.py',['--walk-source',path.join(revision,'walk_route_alignment/navigation_overlay.json')]],
 ['finitePaving','integrate-walk-alignments.py',['--pedestrian-source',path.join(revision,'final_pedestrian_contacts/legacy_navigation_overlay.json')]],
 ['itApproach','integrate-walk-alignments.py',['--it-source',path.join(revision,'it_approach_alignment_review/navigation_overlay.json')]],
 ['itLowerRetirement','integrate-lower-paving-retirement.py',[path.join(revision,'it_approach_alignment_review/lower_paving_retirement.json')]]
].filter(([feature])=>plan[feature]);
for(const [,script] of stages)if(!existsSync(path.join(game,'scripts',script)))throw new Error('Missing native-module integration implementation: '+script);
if(process.argv.includes('--check-inputs')){console.log(JSON.stringify({verified:true,plan,stages:stages.map(([feature,script])=>({feature,script}))},null,2));process.exit(0);}
// Preflight all contracts before the first derived-file write.
// Overlay consumers validate against this exact target export, never the
// previous runnable build's manifest. Isolated staging contains partial work.
copyFileSync(path.join(exportRoot,'manifest.json'),path.join(game,'data/native-export-manifest.json'));
run('python3',['scripts/prepare-realism-materials.py',path.join(revision,'material_fallback.json')]);
const generated={roseEndpoint:['rose-endpoint-navigation.json','rose-endpoint-sync-report.json'],terraceDriveAlignment:['terrace-drive-alignment.json','terrace-drive-alignment-report.json'],pondEntry:['pond-entry-steps.json','pond-entry-sync-report.json'],itLowerRetirement:['it-lower-paving-retirement.json','it-lower-paving-retirement-report.json'],garageRoadRepair:['garage-road-boundary.json','garage-road-boundary-source.json','garage-exterior-navigation.json','garage-exterior-sync-report.json'],finitePaving:['final-pedestrian-navigation.json'],publicWalkRepair:['public-walk-clearance.json'],schoolRoadRepair:['campus-access-school-road-replacement.json'],itApproach:['it-approach-alignment.json'],walkAlignment:['walk-route-alignment.json','walk-alignments-sync-report.json'],actorGrounding:['actor-grounding.json','actor-grounding-report.json'],terraces:['parking-terraces.json','parking-terraces-sync-report.json'],haeoreum:['haeoreum-stair.json','haeoreum-stair-sync-report.json'],lounge:['it-lounge.json','lounge-sync-report.json'],entrances:['entrances-a.json','entrances-b.json','entrance-connections.json','entrance-surfaces.json','entrance-sync-report.json'],public:['public-spaces.json','public-spaces-integration-contract.json','public-spaces-sync-report.json'],track:['track-perimeter.json'],pharmacy:['pharmacy-entrance.json','pharmacy-sync-report.json'],hospital:['hospital-arrival-overlay.json','hospital-sync-report.json'],schools:['campus-access-schools.json','campus-access-gates.json','campus-access-school-boundaries.json','campus-access-sync-report.json'],pond:['pond-overlay.json','pond-sync-report.json'],goals:['football-goals.json','football-goals-sync-report.json'],staticVehicles:['static-vehicle-poses.json','static-vehicle-sync-report.json'],stopWalkways:['hospital-stop-walkways.json','hospital-stop-walkways-sync-report.json'],greenery:['greenery-infill.json','greenery-sync-report.json'],transit:['transit-alignment-overlay.json','transit-revision-report.json','transit-integration-issues.json']};
for(const [feature,files] of Object.entries(generated))if(!plan[feature])clearGenerated(files);
for(const [,script,args] of stages)run('python3',['scripts/'+script,...args]);
// Diagnostic routes are source-bound inputs to the final actual-mesh vehicle QA.
// Preserve them in the runnable source archive; do not synthesize game roads here.
for(const [feature,input,output] of [['roadSeams','road_seam_repair_v5/game_cluster_routes.json','road-seam-routes.json'],['studentLevels','student_union_levels/integration_contract.json','student-level-contract.json'],['garageRoadRepair','final_garage_road_boundary/applied_contract.json','garage-road-boundary.json'],['garageRoadRepair','final_garage_road_boundary/source_geometry.json','garage-road-boundary-source.json']]){
 if(plan[feature])copyFileSync(path.join(revision,input),path.join(game,'data',output));else clearGenerated([output]);
}
run('python3',['scripts/align-exported-inferred-support.py',path.join(exportRoot,'campus.glb')]);
if(process.argv.includes('--metadata-only')){console.log('Final source-bound metadata stages completed; binary compression and runtime checks remain pending.');process.exit(0);}
for(const [name,input,options] of [['building',path.join(exportRoot,'building.glb'),[]],['campus',path.join(exportRoot,'campus.glb'),[]],['shuttle',path.join(model,'transit/shuttle_bus.glb'),['--no-compress']]]){
 const asset=name==='shuttle'?'shuttle_bus':name;
 run('node',['scripts/compress-campus.mjs',input,'dist/assets/'+asset+'.glb','data/game-materials.json',...options,'--report=data/'+name+'-material-application.json']);
}
run('node',['scripts/sync-actor-heights.mjs']);
run('python3',['scripts/record-provenance.py'],{CHOSUN_MODEL_ROOT:model,CHOSUN_GAME_EXPORT_ROOT:exportRoot,CHOSUN_GROUND_ELEVATION_PATH:path.join(revision,'verification/ground_elevation_graded.json')});
if(!process.argv.includes('--assets-only'))run('npm',['run','test:all']);
