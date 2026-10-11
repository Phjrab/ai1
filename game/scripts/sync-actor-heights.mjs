import {installCPUImageMetadata} from './gltf-cpu-images.mjs';
installCPUImageMetadata();
// Align existing spawn heights to the final GLB's physical ground surfaces.
// Coordinates in X/Z and actor counts remain unchanged. No WebGL is needed.
import fs from 'node:fs/promises';
import {BufferGeometry,Float32BufferAttribute,Group,Mesh,Ray,Vector3} from 'three';
import {GLTFLoader} from '../dist/vendor/addons/loaders/GLTFLoader.js';
import {MeshoptDecoder} from '../dist/vendor/addons/meshopt_decoder.module.js';
import {Octree} from '../dist/vendor/addons/math/Octree.js';
import {upwardSupportMesh,hasWalkableSupportTag,isCollisionDisabled} from '../dist/revision-colliders.js';
import {walkingFloorHeight} from '../dist/walking-floor.js';
const root=new URL('../',import.meta.url),path=new URL('dist/world-config.js',root);
let source=await fs.readFile(path,'utf8');const world=JSON.parse(source.split('export const WORLD = ')[1].replace(/;\s*$/,''));
const loader=new GLTFLoader().setMeshoptDecoder(MeshoptDecoder),colliders=new Group();
for(const name of ['building.glb','campus.glb']){
 const b=await fs.readFile(new URL('dist/assets/'+name,root));const gltf=await loader.parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.length),'');gltf.scene.updateMatrixWorld(true);
 gltf.scene.traverse(o=>{
  if(!o.isMesh||isCollisionDisabled(o))return;const name=(o.name+' '+o.parent?.name).toLowerCase();
  if(/parked|vehicle|tree|canopy|bus|shuttle/.test(name)&&!/road|asphalt|paving|pavement|path/.test(name)&&!hasWalkableSupportTag(o))return;
  const foundation=hasWalkableSupportTag(o)||/rv2[ _]foundation[ _]floor/.test(name);
  if(/campus_building/.test(name)&&!foundation)return;
  if(!foundation&&!/terrain|continuous|road|path|plaza|stair|walk|pavement|apron|entry_access|access[ _]road|ground[ _]floor/.test(name))return;
  colliders.add(upwardSupportMesh(o));
 });
}
for(const surface of world.walkableSurfaces||[]){const geometry=new BufferGeometry();geometry.setAttribute('position',new Float32BufferAttribute(surface.polygon.flat(),3));geometry.setIndex(surface.triangles.flat());colliders.add(upwardSupportMesh(new Mesh(geometry)));geometry.dispose();}
const octree=new Octree();octree.fromGraphNode(colliders);const ray=new Ray(),updates=[],missing=[],preservedForSafeArrival=[];
const actorSeeds=await optionalJSON('actor-grounding.json'),seedBy=new Map((actorSeeds?.actors||[]).map(r=>[r.kind+':'+r.index,r])),seedVerification=[];
for(const kind of ['extraNPCs','extraCars'])for(const [index,actor] of world[kind].entries()){
 const p=actor.position,old=p[1],seed=seedBy.get(kind+':'+index);ray.set(new Vector3(p[0],(seed?.floor_z??old)+(seed?.65:35),p[2]),new Vector3(0,-1,0));const hit=octree.rayIntersect(ray);
 if(!hit||hit.distance>70){missing.push({kind,index,position:p});continue;}
 if(seed){if(Math.abs(hit.position.y-seed.floor_z)>.08)throw new Error('Final actor support disagrees with native: '+kind+':'+index);seedVerification.push({kind,index,nativeFloor:seed.floor_z,gameFloor:hit.position.y});}
 if(!seed&&kind==='extraNPCs'&&hit.position.y<old-2.5){preservedForSafeArrival.push({kind,index,authoredHeight:old,directGroundHeight:hit.position.y,reason:'Keep approach elevation for the existing safe-arrival neighborhood search'});continue;}
 p[1]=hit.position.y;
 if(Math.abs(p[1]-old)>.001)updates.push({kind,index,networkHeight:old,finalGroundHeight:p[1],delta:p[1]-old,position:p.slice()});
}
if(actorSeeds){for(const seed of actorSeeds.actors.filter(s=>s.kind==='baseCars')){ray.set(new Vector3(seed.positionXY[0],seed.floor_z+.65,-seed.positionXY[1]),new Vector3(0,-1,0));const hit=octree.rayIntersect(ray);if(!hit||Math.abs(hit.position.y-seed.floor_z)>.08)throw new Error('Final base car support disagrees with native: '+seed.index);world.baseCarGroundHeights[seed.index]=hit.position.y;seedVerification.push({kind:seed.kind,index:seed.index,nativeFloor:seed.floor_z,gameFloor:hit.position.y});}const report=await optionalJSON('actor-grounding-report.json');report.finalGLBSupportVerification={status:'sampled_final_glb',samples:seedVerification,remaining:'Spawn body clearance, walking and driving remain runtime checks'};await fs.writeFile(new URL('data/actor-grounding-report.json',root),JSON.stringify(report,null,2)+'\n');}
if(missing.length)throw new Error('Final ground missing for actor spawns: '+JSON.stringify(missing));
// Ray-only exterior arrival candidates may predate the final paving overlay.
// Keep their source coordinates and record a bounded final-GLB height update.
const entranceFile=new URL('data/entrance-sync-report.json',root);let entranceReport=null;try{entranceReport=JSON.parse(await fs.readFile(entranceFile,'utf8'))}catch(error){if(error.code!=='ENOENT')throw error}
if(entranceReport){const entranceHeights=[];for(const record of entranceReport.records){if(record.geometryConnection)continue;
 for(const [label,point] of [['safe_arrival',record.safe_arrival],['outside_threshold',record.outside_threshold],...record.route.map((p,i)=>['route_'+i,p])]){
  const old=point[2];ray.set(new Vector3(point[0],old+.55,-point[1]),new Vector3(0,-1,0));const hit=octree.rayIntersect(ray);if(!hit||Math.abs(hit.position.y-old)>.5)throw new Error('Unresolved entrance support: '+record.id+' '+label);
  if(Math.abs(hit.position.y-old)>.001){point[2]=hit.position.y;entranceHeights.push({entrance:record.id,point:label,sourceZ:old,runtimeZ:point[2]});}
 }
 const path=world.pedestrianPaths.find(p=>p.entrance_id===record.id);if(path)path.points=record.route.map(p=>[p[0],p[2],-p[1]]);
 const destination=world.destinations.find(d=>d.entranceId===record.id);if(destination)destination.position=[record.safe_arrival[0],record.safe_arrival[2],-record.safe_arrival[1]];
 }
 entranceReport.finalGroundHeightUpdates=entranceHeights;await fs.writeFile(entranceFile,JSON.stringify(entranceReport,null,2)+'\n');
 const navFile=new URL('data/campus-navigation.json',root),navigation=JSON.parse(await fs.readFile(navFile,'utf8'));for(const record of entranceReport.records){const path=navigation.pedestrianPaths.find(p=>p.entrance_id===record.id);if(path)path.points=record.route;const landmark=navigation.landmarks.find(d=>d.entranceId===record.id);if(landmark)landmark.position=record.safe_arrival;}await fs.writeFile(navFile,JSON.stringify(navigation)+'\n');
}
// Source-reviewed public destinations and reconstructed gate branch heights
// are accepted only after sampling the same final visible support as gameplay.
async function optionalJSON(name){try{return JSON.parse(await fs.readFile(new URL('data/'+name,root),'utf8'))}catch(error){if(error.code!=='ENOENT')throw error;return null}}
const navPath=new URL('data/campus-navigation.json',root),finalNavigation=JSON.parse(await fs.readFile(navPath,'utf8'));
const publicReport=await optionalJSON('public-spaces-sync-report.json');
if(publicReport){const samples=[];for(const id of publicReport.finalGLBHeightSampling.destinationIds){
 const destination=world.destinations.find(d=>d.id===String(id));if(!destination)throw new Error('Public destination missing: '+id);
 const p=destination.position;ray.set(new Vector3(p[0],p[1]+1,p[2]),new Vector3(0,-1,0));const hit=octree.rayIntersect(ray);if(!hit||Math.abs(hit.position.y-p[1])>1.5)throw new Error('Unresolved public destination support: '+id);
 samples.push({id,sourceHeight:p[1],runtimeHeight:hit.position.y});p[1]=hit.position.y;const landmark=finalNavigation.landmarks.find(l=>String(l.id)===String(id));if(landmark)landmark.position=[p[0],-p[2],p[1]];
 }publicReport.finalGLBHeightSampling={...publicReport.finalGLBHeightSampling,pending:true,status:'destinations_sampled',sampled:false,destinationsSampled:true,samples,remaining:'Surviving support/path heights and traversals require final runtime QA'};await fs.writeFile(new URL('data/public-spaces-sync-report.json',root),JSON.stringify(publicReport,null,2)+'\n');}
const accessReport=await optionalJSON('campus-access-sync-report.json');
if(accessReport){const samples=[];const sample=(p,label)=>{const height=walkingFloorHeight(octree,p[0],p[2],p[1]);if(height===null||Math.abs(height-p[1])>1.5)throw new Error('Unresolved campus-access support: '+label);samples.push({label,sourceHeight:p[1],runtimeHeight:height,query:'finite edge <=0.1mm with source-level continuity'});p[1]=height;};
 for(const id of accessReport.schoolDestinationIds||[]){const destination=world.destinations.find(d=>String(d.id)===String(id));sample(destination.position,'school_destination:'+id);const landmark=finalNavigation.landmarks.find(d=>String(d.id)===String(id));if(landmark)landmark.position=[destination.position[0],-destination.position[2],destination.position[1]];}
 for(const road of world.roads.filter(r=>r.integrationSource==='campus-access-v1'))for(const [i,p] of road.points.entries())sample(p,(road.id||road.name)+':'+i);
 const lookup=new Map(world.roads.filter(r=>r.integrationSource==='campus-access-v1').map(r=>[r.id,r]));for(const target of [finalNavigation.roads,finalNavigation.pedestrianPaths])for(const r of target){if(r.integrationSource==='campus-access-v1'&&lookup.has(r.id))r.points=lookup.get(r.id).points.map(p=>[p[0],-p[2],p[1]])}
 for(const p of world.pedestrianPaths)if(p.integrationSource==='campus-access-v1'&&lookup.has(p.id))p.points=lookup.get(p.id).points.map(v=>v.slice());
 const graphPath=new URL('data/road-graph-3d.json',root),graph=JSON.parse(await fs.readFile(graphPath,'utf8'));const indices=new Set(graph.edges.filter(e=>e.integrationSource==='campus-access-v1').flatMap(e=>[e.a,e.b]));for(const index of indices){const p=graph.nodes[index],q=[p[0],p[2],-p[1]];sample(q,'graph:'+index);p[2]=q[1]}for(const e of graph.edges)e.length=Math.hypot(...graph.nodes[e.a].map((v,i)=>v-graph.nodes[e.b][i]));await fs.writeFile(graphPath,JSON.stringify(graph)+'\n');
 accessReport.finalGLBHeightSampling={required:true,sampled:true,samples,scope:'Final GLB support at every emitted school/gate road point and graph node; full swept traversal remains separate.'};await fs.writeFile(new URL('data/campus-access-sync-report.json',root),JSON.stringify(accessReport,null,2)+'\n');}
const hospitalReport=await optionalJSON('hospital-sync-report.json');if(hospitalReport&&entranceReport){hospitalReport.finalGLBHeightSampling={...hospitalReport.finalGLBHeightSampling,pending:false,sampled:true};await fs.writeFile(new URL('data/hospital-sync-report.json',root),JSON.stringify(hospitalReport,null,2)+'\n');}
await fs.writeFile(navPath,JSON.stringify(finalNavigation)+'\n');
const comment=source.split('\n')[0];await fs.writeFile(path,comment+'\nexport const WORLD = '+JSON.stringify(world)+';\n');
const reportPath=new URL('data/grade-sync-report.json',root),report=JSON.parse(await fs.readFile(reportPath,'utf8'));
report.finalGroundActorUpdates=updates;report.preservedForSafeArrival=preservedForSafeArrival;report.actorGroundSampling=actorSeeds?'Source-bound final native floor seeds rechecked against exported support at unchanged actor X/Z. No old-height neighborhood fallback used.':'Final exported ground and explicit walkable triangle raycast, same source X/Z and actor counts; NPC approach levels retained for safe-arrival search when direct ground lies over 2.5 m below the authored approach';await fs.writeFile(reportPath,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({actorGroundUpdates:updates,preservedForSafeArrival,groundColliderMeshes:colliders.children.length}));
