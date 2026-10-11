import {runtimeInputHashes} from './helpers/revision-hashes.mjs';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const source=new URL('../data/entrance-sync-report.json',import.meta.url);
try{await fs.access(source)}catch{console.log('ENTRANCE_ACCESS: entrance overlays absent from this intermediate input set');process.exit(0)}
await import('./simulate.mjs');
const {WORLD}=await import('../dist/world-config.js'),a=window.__campus,t=engineTest,report=JSON.parse(await fs.readFile(source,'utf8')),cv=p=>[p[0],p[2],-p[1]],results=[];
for(const change of report.destinationChanges){a.reset();const arrival=a.travelTo(change.id),target=cv(report.records.find(r=>r.id===change.entrance_id).safe_arrival),position=arrival?.position,offset=position?Math.hypot(position[0]-target[0],position[2]-target[2]):Infinity;results.push({kind:'evidence_selected_arrival',id:change.id,pass:!!arrival&&offset<.75,offset,position});}
for(const record of report.records){for(const reverse of [false,true]){
 const points=(reverse?record.route.toReversed():record.route).map(cv);a.reset();a.player.position.set(...points[0]);const initial=a.floorHeight(points[0][0],points[0][2],points[0][1]+.55);let failed=null,maxJump=0,previous=initial,samples=0;
 if(initial===null||Math.abs(initial-points[0][1])>.25)failed={kind:'unsupported_endpoint',point:points[0],actual:initial};else a.player.position.y=initial;
 t.keys.add('KeyW');if(!failed)for(const target of points.slice(1)){let distance=Math.hypot(target[0]-a.player.position.x,target[2]-a.player.position.z),budget=Math.ceil(distance/.05)+90;
  while(distance>.075&&budget-->0){a.player.yaw=Math.atan2(-(target[0]-a.player.position.x),-(target[2]-a.player.position.z));t.walkStep(Math.min(.02,distance/3.5));samples++;maxJump=Math.max(maxJump,Math.abs(a.player.position.y-previous));previous=a.player.position.y;distance=Math.hypot(target[0]-a.player.position.x,target[2]-a.player.position.z);}
  const vertical=Math.abs(a.player.position.y-target[1]);if(distance>.2||vertical>.35){failed={target,position:a.player.position.toArray(),horizontalError:distance,verticalError:vertical};break;}
 }
 t.keys.clear();results.push({kind:'outside_door_walk',id:record.id,building:record.building_id,reverse,pass:!failed,samples,maxFrameHeightJump:maxJump,failed});
 }
 a.reset();a.player.position.set(...cv(record.outside_threshold));const [nx,ny]=record.outward_normal;a.player.yaw=Math.atan2(nx,-ny);t.keys.add('KeyW');for(let i=0;i<80;i++)t.walkStep(.02);t.keys.clear();const signedDistance=(a.player.position.x-record.door[0])*nx+(-a.player.position.z-record.door[1])*ny;results.push({kind:'closed_door_remains_closed',id:record.id,pass:signedDistance>=-.05,signedOutwardDistance:signedDistance,position:a.player.position.toArray()});
}
const baseline=JSON.parse(await fs.readFile(new URL('../data/grade-sync-baseline.json',import.meta.url),'utf8')),changed=new Set(report.destinationChanges.map(c=>c.id));try{const publicSpaces=JSON.parse(await fs.readFile(new URL('../data/public-spaces-sync-report.json',import.meta.url),'utf8'));for(const d of publicSpaces.destinations)changed.add(d.id)}catch(error){if(error.code!=='ENOENT')throw error}for(const d of WORLD.destinations){const original=baseline.destination_positions[d.id];if(original&&!changed.has(d.id))results.push({kind:'unmoved_unrevised_landmark',id:d.id,pass:Math.hypot(d.position[0]-original[0],d.position[2]-original[2])<1e-5});}
a.reset();const failures=results.filter(r=>!r.pass),output={maxRSS_MB:Math.round(process.resourceUsage().maxRSS/1024),inputSha256:await runtimeInputHashes(),passed:failures.length===0,doors:report.doorCount,changedDestinations:report.destinationChanges.length,results,verification:'Actual game walkStep and closed-door blocking at evidence-selected exterior portals; inferred geometry and source confidence remain recorded, DOM/renderer mocked'};await fs.writeFile(new URL('entrance-access-results.json',import.meta.url),JSON.stringify(output,null,2)+'\n');console.log('ENTRANCE_ACCESS',JSON.stringify({...output,results:failures}));assert.equal(failures.length,0,'Exterior arrival/approach/closed-door regression failed');
