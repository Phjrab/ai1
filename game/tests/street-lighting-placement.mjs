// Bounded addition-only audit: real lighting GLB, existing frozen route records,
// and the unchanged collision predicates. Does not load the campus Octree/GPU.
import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {GLTFLoader} from '../dist/vendor/addons/loaders/GLTFLoader.js';
import {STREET_LIGHTING_NATIVE} from '../dist/street-lighting-native.js';
import {WORLD} from '../dist/world-config.js';
import {TRANSIT} from '../dist/transit-config.js';
import {PARKING} from '../dist/parking-config.js';
import {validateLightingContract,fixtureCollisionBoxes,fromBlender,createStreetLighting} from '../dist/street-lighting.js';
import {vehicleOverlapsStaticBox} from '../dist/parking-system.js';
const started=performance.now(),root=new URL('../',import.meta.url),read=p=>fs.readFileSync(new URL(p,root));
const contract=validateLightingContract(JSON.parse(read('dist/street-lighting.json'))),boxes=fixtureCollisionBoxes(contract.fixtures);
const issues=[],counts={pedestrianSegments:0,destinations:0,vehiclePoses:0,busPoses:0};
function segmentHit(a,b,box,radius=.34,height=1.7){
  const dy=b[1]-a[1];let lo=0,hi=1;
  if(Math.abs(dy)<1e-12){if(a[1]>=box.max.y||a[1]+height<=box.min.y)return false;}
  else {const x=(box.min.y-height-a[1])/dy,y=(box.max.y-a[1])/dy;lo=Math.max(lo,Math.min(x,y));hi=Math.min(hi,Math.max(x,y));if(lo>=hi)return false;}
  const dx=b[0]-a[0],dz=b[2]-a[2],c=box.segmentCapsule.a;
  const t=Math.max(lo,Math.min(hi,((c.x-a[0])*dx+(c.z-a[2])*dz)/(dx*dx+dz*dz||1)));
  return (a[0]+t*dx-c.x)**2+(a[2]+t*dz-c.z)**2<(box.segmentCapsule.radius+radius)**2;
}
// Grid broadphase only. All candidate collisions retain the finite height span.
const grid=new Map(),cell=32;
for(const box of boxes){const k=Math.floor(box.min.x/cell)+':'+Math.floor(box.min.z/cell);if(!grid.has(k))grid.set(k,[]);grid.get(k).push(box);}
function nearby(a,b=a,margin=12){const result=[];for(let x=Math.floor((Math.min(a[0],b[0])-margin)/cell);x<=Math.floor((Math.max(a[0],b[0])+margin)/cell);x++)for(let z=Math.floor((Math.min(a[2],b[2])-margin)/cell);z<=Math.floor((Math.max(a[2],b[2])+margin)/cell);z++)result.push(...grid.get(x+':'+z)||[]);return result;}
for(const route of WORLD.pedestrianPaths)for(let i=1;i<route.points.length;i++){
  const a=route.points[i-1],b=route.points[i];counts.pedestrianSegments++;
  for(const box of nearby(a,b,1))if(segmentHit(a,b,box))issues.push({kind:'pedestrian',route:route.id,segment:i-1,blocker:box.label,a,b});
}
for(const d of WORLD.destinations){counts.destinations++;for(const box of nearby(d.position,d.position,1))if(segmentHit(d.position,d.position,box))issues.push({kind:'destination',id:d.id,blocker:box.label,position:d.position});}
function routeVehicles(route,kind,dimensions){
  for(let i=1;i<route.points.length;i++){
    const a=route.points[i-1],b=route.points[i],distance=Math.hypot(b[0]-a[0],b[2]-a[2]);if(distance<1e-8)continue;
    const candidates=nearby(a,b,12);if(!candidates.length)continue;
    const yaw=Math.atan2(b[0]-a[0],b[2]-a[2]),n=Math.max(1,Math.ceil(distance/.25));
    for(let j=0;j<=n;j++){
      const p=new THREE.Vector3().fromArray(a).lerp(new THREE.Vector3().fromArray(b),j/n);counts[kind==='bus'?'busPoses':'vehiclePoses']++;
      for(const box of candidates)if(vehicleOverlapsStaticBox(p,yaw,box,dimensions))issues.push({kind,route:route.id||route.name,segment:i-1,position:p.toArray(),blocker:box.label});
    }
  }
}
for(const road of WORLD.roads)if(road.vehicle!==false)routeVehicles(road,'vehicle',{width:2.28,length:4.38,height:1.68,margin:.02});
for(const route of TRANSIT.routes||[])routeVehicles(route,'bus',{width:TRANSIT.dimensions.width,length:TRANSIT.dimensions.length,height:TRANSIT.dimensions.height,margin:.05});
// Four actual garage paths are also checked whenever a new pole is near them.
for(const route of PARKING.levelDriveRoutes||[])if(route.points)routeVehicles(route,'garage',{width:2.28,length:4.38,height:1.68,margin:.02});
const glb=read('dist/assets/lighting.glb');
const asset=await new GLTFLoader().parseAsync(glb.buffer.slice(glb.byteOffset,glb.byteOffset+glb.byteLength),'');
const names=new Set();let meshCount=0,triangles=0;asset.scene.traverse(o=>{names.add(o.name);if(o.isMesh){meshCount++;triangles+=(o.geometry.index?.count||o.geometry.attributes.position.count)/3;}});
asset.scene.updateMatrixWorld(true);let maxFixturePositionError=0;
for(const f of contract.fixtures)for(const name of f.fixture_object_names){
  const object=asset.scene.getObjectByName(name)||asset.scene.getObjectByName(THREE.PropertyBinding.sanitizeNodeName(name));
  if(!object){issues.push({kind:'missing_fixture_mesh',fixture:f.id,name});continue;}
  const error=object.getWorldPosition(new THREE.Vector3()).distanceTo(new THREE.Vector3(...fromBlender(f.base_position)));
  maxFixturePositionError=Math.max(maxFixturePositionError,error);
  if(error>.0001)issues.push({kind:'fixture_contract_position_mismatch',fixture:f.id,error});
}
const scene=new THREE.Scene();scene.background=new THREE.Color();scene.fog=new THREE.FogExp2();const hemi=new THREE.HemisphereLight(),sun=new THREE.DirectionalLight();scene.add(hemi,sun);
const api=createStreetLighting({scene,hemisphere:hemi,sun,renderer:{toneMappingExposure:1},emitterOffset:STREET_LIGHTING_NATIVE.emitterOffset});
await api.load({loadAsync:async()=>asset},{fetcher:async()=>({ok:true,json:async()=>contract})});
if(api.state.fixtureBatches>12)issues.push({kind:'unexpected_fixture_batches',count:api.state.fixtureBatches,expectedMaximum:12});
const stateChecks=[];for(const time of ['evening','night','day','night']){api.setTime(time);api.setDetail(true);api.update(new THREE.Vector3(...fromBlender(contract.fixtures[0].target_position)),1);stateChecks.push(api.state);assert.ok(api.state.realtimeLights<=4);}
api.setDetail(false);assert.equal(api.state.realtimeLights,0);
const result={status:issues.length?'REVIEW_LIGHTING_PLACEMENT':'PASS_ADDITION_ONLY_LIGHTING_CHECKS',fixtures:contract.fixtures.length,meshes:meshCount,triangles,maxFixturePositionError,counts,issues,stateChecks,elapsedSeconds:(performance.now()-started)/1000,maxRSSMiB:process.resourceUsage().maxRSS/1024,browserWebGLVerified:false,mobilePerformanceVerified:false,pixelNightReadabilityVerified:false,poolNormalization:scene.getObjectByName('RV6_RenderOnly_FiniteLightPools').userData.poolNormalization,scope:'Only new lighting geometry and blockers against unchanged finite route records. No complete campus/Octree simulation.',sourceSha256:{}};
for(const p of ['dist/street-lighting-native.js','dist/street-lighting.json','dist/assets/lighting.glb','dist/street-lighting.js','dist/game.js','dist/world-config.js','dist/parking-system.js','dist/parking-config.js','dist/transit-config.js','tests/street-lighting-placement.mjs'])result.sourceSha256[p]=crypto.createHash('sha256').update(read(p)).digest('hex');
fs.writeFileSync(new URL('tests/street-lighting-placement-results.json',root),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({...result,issues:issues.slice(0,8)}));if(issues.length)process.exitCode=1;
