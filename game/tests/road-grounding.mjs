// Final repaired road geometry versus the actual procedural passenger car.
// This records rigid-wheel residuals separately from solid-body penetration.
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {Box3,Vector3} from 'three';
import {captureModelMeshes} from './helpers/capture-model.mjs';
import {parkingVolumeProbe} from './helpers/parking-volume.mjs';
import {shuttleVehicleOverlap} from '../dist/shuttle-system.js';
import {runtimeInputHashes} from './helpers/revision-hashes.mjs';
import {isCollisionDisabled,isOriginalCampusCar,hasWalkableSupportTag,hasVehicleSurfaceTag} from '../dist/revision-colliders.js';
async function read(name){try{return JSON.parse(await fs.readFile(new URL('../data/'+name,import.meta.url),'utf8'))}catch(e){if(e.code==='ENOENT')return null;throw e}}
const seams=await read('road-seam-routes.json'),student=await read('student-level-contract.json');
if(!seams&&!student){console.log('ROAD_GROUNDING: final repair contracts absent from this intermediate input set');process.exit(0)}
const sourceContractSha256={};for(const name of [...(seams?['road-seam-routes.json']:[]),...(student?['student-level-contract.json']:[])])sourceContractSha256[name]=createHash('sha256').update(await fs.readFile(new URL('../data/'+name,import.meta.url))).digest('hex');
const graph=await read('road-graph-3d.json'),regions=[],routes=[];
const corrected142=new Set((seams?.alignment_142?.corrected_vehicle_nodes||[]).map(r=>r.node_index));
const cv=p=>new Vector3(p[0],p[2],-p[1]);
function authoredPoses(samples,pairs){return samples.map(s=>{let best=null;for(const [a,b] of pairs){const dx=b.x-a.x,dz=b.z-a.z,u=Math.max(0,Math.min(1,((s.center_xy[0]-a.x)*dx+(-s.center_xy[1]-a.z)*dz)/(dx*dx+dz*dz||1))),p=a.clone().lerp(b,u),distance=Math.hypot(p.x-s.center_xy[0],p.z+s.center_xy[1]);if(!best||distance<best.distance)best={distance,y:p.y};}assert.ok(best&&best.distance<.02,'Authored road pose must remain on its final source XY line');return {p:new Vector3(s.center_xy[0],best.y,-s.center_xy[1]),yaw:s.heading_blender_rad-Math.PI/2,sourceEdge:s.edge_index};});}
function addRegion(points){const bounds=new Box3().setFromPoints(points).expandByScalar(7);bounds.min.y=-200;bounds.max.y=200;regions.push(bounds);}
for(const cluster of seams?.patch_specs||[]){
 assert.ok(cluster.route_samples?.length,'Final seam source poses required');const pairs=cluster.source_edges.map(e=>e.node_indices.map(i=>{assert.ok(graph.nodes[i],'Final source road node missing');return cv(graph.nodes[i]);})),poses=authoredPoses(cluster.route_samples,pairs);addRegion(poses.map(s=>s.p));routes.push({id:cluster.cluster_id,poses,offsets:[-.3,0,.3],narrow:cluster.source_edges.some(e=>e.node_indices.some(i=>corrected142.has(i)))});
}
if(seams?.alignment_142){const nodes=seams.alignment_142.route_node_indices;assert.ok(nodes?.length>1&&seams.alignment_142.route_samples?.length,'Complete corrected142 route required');const points=nodes.map(i=>cv(graph.nodes[i])),pairs=points.slice(1).map((p,i)=>[points[i],p]),poses=authoredPoses(seams.alignment_142.route_samples,pairs);addRegion(points);routes.push({id:'building142_complete_alignment',poses,offsets:[-.3,0,.3],narrow:true});}
if(student){const road=student.road;assert.equal(road.source_node_indices.length,road.polyline_xy.length);const points=road.source_node_indices.map((index,i)=>{const p=graph.nodes[index];assert.ok(p&&Math.hypot(p[0]-road.polyline_xy[i][0],p[1]-road.polyline_xy[i][1])<1e-5,'Student road XY must match the final bound graph');return cv(p)});const bounds=new Box3().setFromPoints(points).expandByScalar(7);bounds.min.y=-200;bounds.max.y=200;regions.push(bounds);routes.push({id:'student_union_front_road',points,offsets:[-2.7,0,2.7],within:()=>true});}
const selectedIds=process.env.CHOSUN_ROAD_IDS?.split(',').filter(Boolean);if(selectedIds){for(let i=routes.length-1;i>=0;i--)if(!selectedIds.includes(routes[i].id))routes.splice(i,1);assert.equal(routes.length,selectedIds.length,'Requested road fixture missing');}
const inRegion=box=>regions.some(region=>region.intersectsBox(box));
const solids=captureModelMeshes(o=>{if(isCollisionDisabled(o)||/campus_tree|canopy|prototype/i.test(o.name+' '+o.parent?.name))return false;if(!o.geometry.boundingBox)o.geometry.computeBoundingBox();return inRegion(o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld));});
await import('./simulate.mjs');delete globalThis.captureCampusTestGeometry;
const a=window.__campus,t=engineTest,car=a.cars[0],tyres=[];
a.player.position.copy(car.g.position).add(new Vector3(2.5,0,0));a.interact();assert.equal(a.state.mode,'driving');
car.g.traverse(o=>{if(o.isMesh&&o.geometry.type==='CylinderGeometry'&&Math.abs(o.geometry.parameters.radiusTop-.36)<1e-8)tyres.push(o)});assert.equal(tyres.length,4);
const tyreVertices=new Map(tyres.map(tyre=>{const unique=new Map(),p=tyre.geometry.attributes.position;for(let i=0;i<p.count;i++){const point=new Vector3().fromBufferAttribute(p,i);unique.set(point.toArray().join(','),point);}return [tyre,[...unique.values()]];}));
const tyreSet=new Set(tyres),probe=parkingVolumeProbe(solids,()=>true,inRegion,o=>!isOriginalCampusCar(o)&&(hasWalkableSupportTag(o)||hasVehicleSurfaceTag(o)||/terrain|continuous|road|asphalt|paving|parking/i.test(o.name+' '+o.parent?.name)));
const results=[],failures=[];let poseCount=0,minimumGap=Infinity,maximumGap=-Infinity;
function* routePoses(route,reverse,offset){
 if(route.poses){for(const sample of reverse?route.poses.toReversed():route.poses){const yaw=sample.yaw+(reverse?Math.PI:0),p=sample.p.clone();p.x+=Math.cos(yaw)*offset;p.z-=Math.sin(yaw)*offset;yield {p,yaw};}return;}
 const points=reverse?route.points.toReversed():route.points;
 for(let i=1;i<points.length;i++){const start=points[i-1],end=points[i],dx=end.x-start.x,dz=end.z-start.z,length=Math.hypot(dx,dz);if(length<1e-4)continue;const yaw=Math.atan2(-dx,-dz),count=Math.max(1,Math.ceil(length/.5));for(let j=0;j<count;j++){const p=start.clone().lerp(end,j/count);p.x+=Math.cos(yaw)*offset;p.z-=Math.sin(yaw)*offset;yield {p,yaw};}}
}
for(const route of routes)for(const reverse of [false,true])for(const offset of route.offsets){
 const row={id:route.id,reverse,lateralOffset:offset,required:!route.narrow||offset===0,poses:0,minimumTyreGap:Infinity,maximumTyreGap:-Infinity,missingSupports:0,bodyContacts:[],runtimeBlocked:[],trafficBlocked:[],suspensionFailures:[],maximumSuspensionTravel:0,contactOutliers:[],supportObjects:new Set()};delete car.g.userData.groundFit;
 for(const {p,yaw} of routePoses(route,reverse,offset)){
   const support=probe.support(p.x,p.z,p.y+1,2);if(!support){row.missingSupports++;continue;}
   car.g.position.copy(p);car.g.position.y=support.height;car.yaw=yaw;t.fitVehicleToGround(car.g,yaw);car.g.updateMatrixWorld(true);row.poses++;poseCount++;
   if(t.blockedDrivingPosition(car.g.position,yaw)){const traffic=a.cars.filter(other=>other!==car&&shuttleVehicleOverlap({position:car.g.position.toArray(),yaw},{position:other.g.position.toArray(),yaw:other.yaw},{width:2.28,length:4.38,otherWidth:2.28,otherLength:4.38,margin:.02}));const record={position:car.g.position.toArray(),yaw};if(traffic.length&&!t.staticDrivingBlockage(car.g.position,yaw))row.trafficBlocked.push({...record,otherCars:traffic.map(other=>a.cars.indexOf(other))});else row.runtimeBlocked.push(record);}
   for(const wheel of car.g.userData.groundFit.suspension?.wheels||[]){row.maximumSuspensionTravel=Math.max(row.maximumSuspensionTravel,Math.abs(wheel.offset));if(wheel.limited||wheel.missing||Math.abs(wheel.residualGap-.02)>.025)row.suspensionFailures.push({position:car.g.position.toArray(),yaw,wheel});}
   const hits=probe(car.g,o=>!tyreSet.has(o));if(hits.length)row.bodyContacts.push({position:car.g.position.toArray(),yaw,objects:hits});
   for(const [wheel,tyre] of tyres.entries()){
    let gap=Infinity,contact=null;const point=new Vector3();
    for(const vertex of tyreVertices.get(tyre)){
     point.copy(vertex).applyMatrix4(tyre.matrixWorld);const floor=probe.support(point.x,point.z,point.y+.4,.8);if(!floor)continue;
     const distance=point.y-floor.height;if(distance<gap){gap=distance;contact={position:point.toArray(),surface:floor.object};}
    }
    if(!contact){row.missingSupports++;continue;}
    row.supportObjects.add(contact.surface);row.minimumTyreGap=Math.min(row.minimumTyreGap,gap);row.maximumTyreGap=Math.max(row.maximumTyreGap,gap);minimumGap=Math.min(minimumGap,gap);maximumGap=Math.max(maximumGap,gap);
    if(gap<-.05||gap>.12)row.contactOutliers.push({wheel,gap,contact,carPosition:car.g.position.toArray(),yaw});
   }
 }
 if(!row.poses&&!row.missingSupports)continue; // A neighboring source edge may lie outside the repair disk.
 row.supportObjects=[...row.supportObjects];row.pass=row.poses>0&&!row.missingSupports&&!row.bodyContacts.length&&!row.runtimeBlocked.length&&!row.contactOutliers.length&&!row.suspensionFailures.length;results.push(row);if(row.required&&!row.pass)failures.push(row);
 console.log('ROAD_GROUNDING_ROUTE',JSON.stringify({id:row.id,reverse,offset,required:row.required,poses:row.poses,pass:row.pass,missing:row.missingSupports,body:row.bodyContacts.length,blocked:row.runtimeBlocked.length,trafficBlocked:row.trafficBlocked.length,suspensionFailures:row.suspensionFailures.length,tyreOutliers:row.contactOutliers.length}));
}
for(const cluster of (seams?.patch_specs||[]).filter(c=>!selectedIds||selectedIds.includes(c.cluster_id)))assert.ok(results.some(r=>r.id===cluster.cluster_id&&r.poses>0),'No final samples inside repaired road cluster '+cluster.cluster_id);
a.reset();const report={passed:!failures.length,selectedRouteIds:selectedIds||null,sourceContractSha256,inputSha256:await runtimeInputHashes(),poseCount,minimumTyreGap:minimumGap,maximumTyreGap:maximumGap,tyreContactToleranceMeters:[-.05,.12],maxRSS_MB:Math.round(process.resourceUsage().maxRSS/1024),results,method:'Actual fitVehicleToGround poses sampled at 0.5m in both directions. Actual tyre vertices against visible final GLB triangles; actual body and localized hub components against actual triangles. Bounded wheel/hub support residuals are reported separately from body collisions. Normal controllable-car obstruction remains active and is listed separately from static road failures. Initial ray reaches 1m above bound graph seed, covering the verified 0.76265m north-asphalt delta without selecting an arbitrary upper floor. No render geometry changes and no metadata support substitutes.'};
await fs.writeFile(new URL('road-grounding-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log('ROAD_GROUNDING',JSON.stringify({...report,results:failures}));assert.equal(failures.length,0,'Repaired road actual-car grounding failed');
