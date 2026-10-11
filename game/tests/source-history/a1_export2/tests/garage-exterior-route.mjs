// Actual low-speed exterior drive around the bounded garage asphalt trim.
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {Box3,Vector3,BufferGeometry,Float32BufferAttribute} from 'three';
import {captureModelMeshes} from './helpers/capture-model.mjs';
import {parkingVolumeProbe} from './helpers/parking-volume.mjs';
import {runtimeInputHashes} from './helpers/revision-hashes.mjs';
import {isCollisionDisabled,isOriginalCampusCar,hasWalkableSupportTag,hasVehicleSurfaceTag} from '../dist/revision-colliders.js';
const sourcePath=process.env.GARAGE_TRIM_SOURCE,routePath=process.env.GARAGE_ROUTE_SOURCE||new URL('../data/garage-exterior-navigation.json',import.meta.url);
let routeBytes;try{routeBytes=await fs.readFile(routePath)}catch(e){if(e.code==='ENOENT'&&!process.env.GARAGE_ROUTE_SOURCE){console.log('GARAGE_EXTERIOR: repair contract absent from intermediate input');process.exit(0)}throw e}
const route=JSON.parse(routeBytes),sourceBytes=sourcePath?await fs.readFile(sourcePath):null,source=sourceBytes?JSON.parse(sourceBytes):null;
const cv=p=>new Vector3(p[0],p[2],-p[1]);
const region=new Box3(new Vector3(72,-40,747),new Vector3(124,-25,811));
const canonicalTriangle=t=>t.map(v=>v.toArray().map(n=>Math.round(n*10000)).join(',')).sort().join(';');
let matched=0;
if(source)globalThis.patchCampusTestScene=(name,scene)=>{
 if(name!=='campus.glb')return;
 const removed=new Set(source.removed_source_triangles.map(t=>canonicalTriangle(t.map(cv))));
 scene.traverse(o=>{if(!o.isMesh||!o.name.includes('CAMPUS_CONTINUOUS_vehicle_asphalt'))return;
  const p=o.geometry.attributes.position,idx=o.geometry.index,vertices=[new Vector3(),new Vector3(),new Vector3()],keep=[];
  for(let i=0;i<(idx?.count??p.count);i+=3){for(let j=0;j<3;j++)vertices[j].fromBufferAttribute(p,idx?idx.getX(i+j):i+j).applyMatrix4(o.matrixWorld);const key=canonicalTriangle(vertices);if(removed.has(key)){matched++;continue;}keep.push(...vertices.flatMap(v=>v.toArray()));}
  if(matched){for(const t of source.retained_replacement_triangles)keep.push(...t.flatMap(p=>cv(p).toArray()));const g=new BufferGeometry();g.setAttribute('position',new Float32BufferAttribute(keep,3));g.computeVertexNormals();g.computeBoundingBox();o.geometry=g;o.matrix.identity();o.matrixAutoUpdate=false;assert.ok(!o.parent||o.parent.matrixWorld.equals(o.parent.matrixWorld.clone().identity()),'Road parent must be identity for bounded world-space patch');}
 });assert.equal(matched,8,'Exact original road triangles must match');
};
const solids=captureModelMeshes(o=>{if(isCollisionDisabled(o)||/campus_tree|canopy|prototype/i.test(o.name+' '+o.parent?.name))return false;o.geometry.computeBoundingBox();return region.intersectsBox(o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld));});
await import('./simulate.mjs');delete globalThis.patchCampusTestScene;delete globalThis.captureCampusTestGeometry;
const a=window.__campus,t=engineTest,car=a.cars[0],probe=parkingVolumeProbe(solids,()=>true,b=>region.intersectsBox(b),o=>!isOriginalCampusCar(o)&&(hasWalkableSupportTag(o)||hasVehicleSurfaceTag(o)||/terrain|continuous|road|asphalt|paving|parking/i.test(o.name+' '+o.parent?.name)));
const tyres=[];car.g.traverse(o=>{if(o.isMesh&&o.geometry.type==='CylinderGeometry'&&Math.abs(o.geometry.parameters.radiusTop-.36)<1e-8)tyres.push(o)});assert.equal(tyres.length,4);const tyreSet=new Set(tyres),wheelVertices=tyres.map(o=>{const p=o.geometry.attributes.position,out=[];for(let i=0;i<p.count;i++)out.push(new Vector3().fromBufferAttribute(p,i));return out});
const base=(route.verified_points||route.points).map(cv),grounded=[];for(const p of base){const hit=probe.support(p.x,p.z,p.y+1.5,3);assert.ok(hit,'Actual trimmed road support missing at '+p.toArray());grounded.push(new Vector3(p.x,hit.height,p.z));}
const rows=[],dt=1/60;
for(const reverse of [false,true])for(const lateral of [-.3,0,.3]){
 const ordered=reverse?grounded.toReversed():grounded,path=ordered.map((p,i)=>{const d=ordered[Math.min(i+1,ordered.length-1)].clone().sub(ordered[Math.max(0,i-1)]),n=new Vector3(-d.z,0,d.x).normalize();return p.clone().addScaledVector(n,lateral)});
 a.reset();car.g.position.copy(path[0]);let d=path[1].clone().sub(path[0]);car.yaw=Math.atan2(-d.x,-d.z);car.speed=0;delete car.g.userData.groundFit;t.fitVehicleToGround(car.g,car.yaw);a.player.position.copy(car.g.position).add(new Vector3(2.5,0,0));a.interact();assert.equal(a.state.mode,'driving');
 const row={reverse,lateral,steps:0,poses:0,bodyContacts:[],wheelFailures:[],blocked:[],minimumTyreGap:Infinity,maximumTyreGap:-Infinity,maximumTrackingError:0,maximumHeightJump:0,maximumYawJump:0,maximumSuspension:0};let index=0,stagnant=0,last=car.g.position.clone(),lastYaw=car.yaw,checked=last.clone();
 for(;row.steps<14000;row.steps++){
  let best=index,dist=Infinity;for(let j=index;j<Math.min(path.length,index+45);j++){const n=path[j].distanceTo(car.g.position);if(n<dist){dist=n;best=j;}}index=best;row.maximumTrackingError=Math.max(row.maximumTrackingError,dist);
  const target=path[Math.min(path.length-1,index+12)],delta=target.clone().sub(car.g.position),desired=Math.atan2(-delta.x,-delta.z),error=Math.atan2(Math.sin(desired-car.yaw),Math.cos(desired-car.yaw));t.keys.clear();t.stick.x=Math.max(-1,Math.min(1,-error*3));if(car.speed<1.5)t.keys.add('KeyW');t.driveStep(dt);
  row.maximumHeightJump=Math.max(row.maximumHeightJump,Math.abs(car.g.position.y-last.y));row.maximumYawJump=Math.max(row.maximumYawJump,Math.abs(Math.atan2(Math.sin(car.yaw-lastYaw),Math.cos(car.yaw-lastYaw))));lastYaw=car.yaw;
  if(car.g.position.distanceTo(checked)>.25){
   row.poses++;const hits=probe(car.g,o=>!tyreSet.has(o));if(hits.length)row.bodyContacts.push({position:car.g.position.toArray(),yaw:car.yaw,hits});
   if(t.staticDrivingBlockage(car.g.position,car.yaw))row.blocked.push({position:car.g.position.toArray(),yaw:car.yaw});
   for(const [i,wheel] of tyres.entries()){let gap=Infinity,contact=null;for(const v of wheelVertices[i]){const p=v.clone().applyMatrix4(wheel.matrixWorld),floor=probe.support(p.x,p.z,p.y+.4,.8);if(floor&&p.y-floor.height<gap){gap=p.y-floor.height;contact={point:p.toArray(),floor};}}row.minimumTyreGap=Math.min(row.minimumTyreGap,gap);row.maximumTyreGap=Math.max(row.maximumTyreGap,gap);if(!contact||gap<-.025||gap>.08)row.wheelFailures.push({position:car.g.position.toArray(),yaw:car.yaw,wheel:i,gap,contact});}
   for(const w of car.g.userData.groundFit.suspension?.wheels||[])row.maximumSuspension=Math.max(row.maximumSuspension,Math.abs(w.offset));checked.copy(car.g.position);
  }
  if(car.g.position.distanceTo(last)<.001)stagnant++;else stagnant=0;last.copy(car.g.position);if(index>=path.length-3&&car.g.position.distanceTo(path.at(-1))<1)break;if(stagnant>180||dist>5)break;
 }
 row.finalPosition=car.g.position.toArray();row.finalYaw=car.yaw;row.endpointError=car.g.position.distanceTo(path.at(-1));row.complete=index>=path.length-3&&row.endpointError<1;row.pass=row.complete&&!row.bodyContacts.length&&!row.wheelFailures.length&&!row.blocked.length&&row.maximumHeightJump<.25&&row.maximumYawJump<.1;rows.push(row);console.log('GARAGE_EXTERIOR',JSON.stringify(row));
}
t.keys.clear();t.stick.x=0;a.reset();const result={passed:rows.every(r=>r.pass),sourceSha256:sourceBytes?createHash('sha256').update(sourceBytes).digest('hex'):route.source_geometry_sha256,routeSha256:createHash('sha256').update(routeBytes).digest('hex'),inputSha256:await runtimeInputHashes(),patchedTriangles:matched,mode:source?'bounded-native-triangle-candidate':'final-export-as-rendered',groundedPoints:grounded.map(p=>[p.x,-p.z,p.y]),results:rows,method:'Actual continuous driveStep with unchanged 4.38x2.28m car, four actual tire meshes and all body/hub components against exact bounded native trim on the fixed GLB. Both directions and three lateral starts. DOM/renderer mocked; not browser QA.'};await fs.writeFile(process.env.GARAGE_ROUTE_RESULT||new URL('garage-exterior-route-results.json',import.meta.url),JSON.stringify(result,null,2)+'\n');assert.ok(result.passed,'Garage exterior actual drive failed');
