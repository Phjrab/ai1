// Continuous steering inputs, including every landing loop, with full car geometry.
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {Vector3,Box3} from 'three';
import {runtimeInputHashes} from './helpers/revision-hashes.mjs';
import {VEHICLE_STEERING} from '../dist/vehicle-steering.js';
const inputSha256=await runtimeInputHashes();
import {PARKING} from '../dist/parking-config.js';
import {parkingVolumeProbe} from './helpers/parking-volume.mjs';
import {captureModelMeshes} from './helpers/capture-model.mjs';
import {isParkingStaticCar,isParkingDriveSurface} from '../dist/parking-system.js';
import {isCollisionDisabled} from '../dist/revision-colliders.js';
const garageRegion=new Box3(new Vector3(98,-36,727),new Vector3(183,-18,784));
const site=captureModelMeshes(o=>{if(isCollisionDisabled(o)||/tree|foliage/i.test(o.name+' '+o.parent?.name))return false;o.geometry.computeBoundingBox();return garageRegion.intersectsBox(o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld));});
const boundaryWatchPoints=[[107.509,-31.692,777.862],[106.212,-32.056,774.566],[106.951,-31.929,775.495],[106.172,-31.842,777.161],[107.814,-31.665,778.285]].map(p=>new Vector3(...p));
await import('./simulate.mjs');
delete globalThis.captureCampusTestGeometry;
const bytes=await fs.readFile(new URL('../dist/assets/campus.glb',import.meta.url)),probe=parkingVolumeProbe(site,o=>!isParkingDriveSurface(o),bounds=>garageRegion.intersectsBox(bounds)),a=window.__campus,t=engineTest,car=a.cars[0],dt=1/60,results=[];
const override=process.env.PARKING_WEST_ROUTE_X?Number(process.env.PARKING_WEST_ROUTE_X):null,original=PARKING.levelDriveRoutes[0].points,entry=override===null?original:[...original.map(p=>[p[0]===108.8?override:p[0],p[1],p[2]]),original.at(-1)],full=[...entry,...PARKING.rampConnections.flatMap(r=>r.points.slice(1))];
function samples(points){const out=[];for(let i=1;i<points.length;i++){const p=new Vector3(...points[i-1]),q=new Vector3(...points[i]),n=Math.max(1,Math.ceil(p.distanceTo(q)/.25));for(let j=0;j<n;j++)out.push(p.clone().lerp(q,j/n));}out.push(new Vector3(...points.at(-1)));return out;}
for(const reverse of [false,true]){
 const path=samples(reverse?full.toReversed():full),start=path[0],initial=path[1].clone().sub(start);a.reset();car.g.position.copy(start);car.yaw=Math.atan2(-initial.x,-initial.z);car.speed=0;delete car.g.userData.groundFit;t.fitVehicleToGround(car.g,car.yaw);a.player.position.copy(car.g.position).add(new Vector3(2.5,0,0));a.interact();assert.equal(a.state.mode,'driving');
 let index=0,stagnant=0,previous=car.g.position.clone(),worst=0,steps=0,volumeHits=[],checked=car.g.position.clone(),volumeSamples=0,maxHeightJump=0,nearestBoundaryWatch=boundaryWatchPoints.map(()=>({distance:Infinity,pose:null}));
 for(;steps<30000;steps++){
  let best=index,distance=Infinity;for(let j=index;j<Math.min(path.length,index+50);j++){const d=path[j].distanceTo(car.g.position);if(d<distance){distance=d;best=j;}}index=best;worst=Math.max(worst,distance);
  const target=path[Math.min(path.length-1,index+16)],delta=target.clone().sub(car.g.position),desired=Math.atan2(-delta.x,-delta.z),error=Math.atan2(Math.sin(desired-car.yaw),Math.cos(desired-car.yaw));t.keys.clear();t.stick.x=Math.max(-1,Math.min(1,-error*3));if(car.speed<1.5)t.keys.add('KeyW');t.driveStep(dt);
  maxHeightJump=Math.max(maxHeightJump,Math.abs(car.g.position.y-previous.y));if(car.g.position.distanceTo(checked)>.4){const hits=probe(car.g);volumeSamples++;for(const [wi,p] of boundaryWatchPoints.entries()){const distance=Math.hypot(car.g.position.x-p.x,car.g.position.z-p.z);if(distance<nearestBoundaryWatch[wi].distance)nearestBoundaryWatch[wi]={point:p.toArray(),distance,pose:car.g.position.toArray(),yaw:car.yaw};}if(hits.length)volumeHits.push({point:car.g.position.toArray(),yaw:car.yaw,hits});checked.copy(car.g.position);}
  if(car.g.position.distanceTo(previous)<.001)stagnant++;else stagnant=0;previous.copy(car.g.position);if(index>=path.length-3&&car.g.position.distanceTo(path.at(-1))<1)break;if(stagnant>240||distance>8)break;
 }
 t.keys.clear();t.stick.x=0;const endpointError=car.g.position.distanceTo(path.at(-1)),complete=index>=path.length-3&&endpointError<1,verticalError=Math.abs(car.g.position.y-path.at(-1).y);results.push({kind:reverse?'continuous_down':'continuous_up',pass:complete&&verticalError<.12&&!volumeHits.length&&maxHeightJump<.25,steps,simulatedSeconds:steps*dt,complete,endpointError,verticalError,maxHeightJump,maxCenterlineTrackingError:worst,volumeSamples,volumeHits,nearestBoundaryWatch,position:car.g.position.toArray()});
}
const report={inputSha256,steering:VEHICLE_STEERING,maxRSS_MB:Math.round(process.resourceUsage().maxRSS/1024),passed:results.every(r=>r.pass),levels:PARKING.levelTops.length,assetSha256:createHash('sha256').update(bytes).digest('hex'),diagnosticRouteOverride:override,results,method:'Continuous W/steering input using real driveStep and exact component/garage-and-nearby-exported-terrain-road-structure triangle volume probes at0.4m intervals. Box bodies and convex polygon tyres; no instantaneous heading edits during movement. DOM/renderer mocked.'};await fs.writeFile(process.env.PARKING_RESULT_FILE||new URL(override===null?'parking-turns-results.json':'parking-turns-candidate-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log('PARKING_TURNS',JSON.stringify(report));assert.ok(report.passed,'Continuous parking approach/landing-turn traversal failed');
