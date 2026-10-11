import {prepareRoadFaceProbe} from './road-tyre-face-probe.mjs';
const measureFaces=await prepareRoadFaceProbe();
await import('../tests/simulate.mjs');
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {Vector3} from 'three';
import {terraceDriveRoutes} from '../tests/helpers/terrace-routes.mjs';
const a=window.__campus,t=engineTest,car=a.cars[0],dt=1/60,contract=JSON.parse(await fs.readFile(new URL('../data/parking-terraces.json',import.meta.url),'utf8'));
contract.transition_zones=contract.transition_zones.filter(z=>z.connection?.connection_id?.startsWith('421_'));
const routes=terraceDriveRoutes(contract,a.floorHeight),results=[];
for(const route of routes){
 const path=route.points.map(p=>new Vector3(...p));a.reset();car.g.position.copy(path[0]);const direction=path[1].clone().sub(path[0]);car.yaw=Math.atan2(-direction.x,-direction.z);car.speed=0;delete car.g.userData.groundFit;t.fitVehicleToGround(car.g,car.yaw);a.player.position.copy(car.g.position).add(new Vector3(2.5,0,0));a.interact();assert.equal(a.state.mode,'driving');let index=0,steps=0,stagnant=0,previous=car.g.position.clone(),frameMS=[];
 for(;steps<12000;steps++){let best=index,distance=Infinity;for(let j=index;j<Math.min(path.length,index+40);j++){const d=path[j].distanceTo(car.g.position);if(d<distance){distance=d;best=j;}}index=best;const target=path[Math.min(path.length-1,index+10)],delta=target.clone().sub(car.g.position),desired=Math.atan2(-delta.x,-delta.z),error=Math.atan2(Math.sin(desired-car.yaw),Math.cos(desired-car.yaw));t.keys.clear();t.stick.x=Math.max(-1,Math.min(1,-error*3));if(car.speed<1.5)t.keys.add('KeyW');const began=performance.now();t.driveStep(dt);frameMS.push(performance.now()-began);stagnant=car.g.position.distanceTo(previous)<.001?stagnant+1:0;previous.copy(car.g.position);if(index>=path.length-3&&car.g.position.distanceTo(path.at(-1))<.8)break;if(stagnant>240||distance>5)break;}
 t.keys.clear();t.stick.x=0;const endpointError=car.g.position.distanceTo(path.at(-1)),complete=index>=path.length-3&&endpointError<.8;assert.ok(complete,route.id);const sorted=frameMS.toSorted((a,b)=>a-b);console.log('FRAME_ROUTE_COMPLETE',route.id,frameMS.length);results.push({id:route.id,frames:frameMS.length,complete,endpointError,meanMS:frameMS.reduce((a,b)=>a+b,0)/frameMS.length,medianMS:sorted[Math.floor(sorted.length*.5)],p95MS:sorted[Math.floor(sorted.length*.95)],maxMS:sorted.at(-1)});
}
console.log('FACE_CONTACT_PROBE_START');const roadTyreFaceContact=measureFaces(a,t);console.log('FACE_CONTACT_PROBE_COMPLETE',roadTyreFaceContact.poses,roadTyreFaceContact.affectedMeasurements);assert.ok(roadTyreFaceContact.pass,'Actual finite tyre face contact must explain the vertex-only gap');
const inputSha256={};for(const file of ['dist/game.js','dist/wheel-suspension.js','dist/assets/campus.glb','dist/world-config.js','data/parking-terraces.json','scripts/benchmark-car-grounding.mjs','scripts/road-tyre-face-probe.mjs']){const bytes=await fs.readFile(new URL('../'+file,import.meta.url));inputSha256[file]=crypto.createHash('sha256').update(bytes).digest('hex');}
const report={passed:true,scope:'Actual driveStep wall time on four421 slope directions; no GPU/rendering performance claim. Exact physics/contact regression is separately bound.',inputSha256,results,roadTyreFaceContact};await fs.writeFile(new URL('../tests/tyre-frame-performance-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log('TYRE_FRAME_PERFORMANCE',JSON.stringify(report));
