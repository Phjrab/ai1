import {installCPUImageMetadata} from '../scripts/gltf-cpu-images.mjs';
installCPUImageMetadata();
// Real GLB/geometry unit integration; no DOM, WebGL renderer, or device test.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {Ray,Vector3} from 'three';
import {GLTFLoader} from '../dist/vendor/addons/loaders/GLTFLoader.js';
import {MeshoptDecoder} from '../dist/vendor/addons/meshopt_decoder.module.js';
import {ParkingSupport,parkingCollisionBoxes,pointInStaticBox,staticBoxRayDistance} from '../dist/parking-system.js';
const asset=process.argv[2]||new URL('../dist/assets/campus.glb',import.meta.url),metadata=process.argv[3]||new URL('../data/parking-gameplay.json',import.meta.url),bytes=await fs.readFile(asset),raw=await fs.readFile(metadata),data=JSON.parse(raw);
const config={enabled:true,driveSurfaces:data.driveSurfaces,colliders:data.colliders.map(b=>({...b,center:[b.center[0],b.center[2],-b.center[1]],halfSize:[b.halfSize[0],b.halfSize[2],b.halfSize[1]]}))};
const scene=(await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.length),'')).scene,support=new ParkingSupport(config);support.attach(scene);assert.equal(support.meshCount,data.driveSurfaces.length);assert.equal(support.staticCarCount,data.parkedCars.length);
const boxes=parkingCollisionBoxes(config),results=[];
for(const [level,y] of data.levelTops.entries()){const p=new Vector3(138,y,750),height=support.height(p);results.push({kind:'deck',level,expected:y,actual:height,pass:height!==null&&Math.abs(height-y)<.04});assert.ok(height!==null&&Math.abs(height-y)<.04);}
let rampSamples=0;for(const ramp of data.rampConnections){for(let i=1;i<ramp.points.length;i++){const a=ramp.points[i-1],b=ramp.points[i],distance=Math.hypot(b[0]-a[0],b[1]-a[1]),count=Math.max(1,Math.ceil(distance/.25));for(let j=0;j<=count;j++){const t=j/count,p=new Vector3(a[0]+(b[0]-a[0])*t,a[2]+(b[2]-a[2])*t,-(a[1]+(b[1]-a[1])*t)),height=support.height(p);rampSamples++;if(height===null||Math.abs(height-p.y)>.06)results.push({kind:'ramp_failure',from:ramp.fromLevel,to:ramp.toLevel,point:p.toArray(),actual:height,pass:false});}}}
let levelSeparationChecks=0;for(const box of boxes.filter(b=>b.parkingKind==='car')){const level=box.parkingLevel,p=new Vector3(box.oriented.center.x,data.levelTops[level],box.oriented.center.z);assert.ok(pointInStaticBox(p,box,.34),'Same-level parked car must block');for(const [other,y] of data.levelTops.entries()){if(other===level)continue;p.y=y;assert.ok(!pointInStaticBox(p,box,.34),'Parked car must not block another deck');levelSeparationChecks++;}}
const upper=boxes.find(b=>b.parkingKind==='car'&&b.parkingLevel===1);assert.ok(upper);const origin=new Vector3(upper.oriented.center.x-8,data.levelTops[0]+1,upper.oriented.center.z);assert.equal(staticBoxRayDistance(new Ray(origin,new Vector3(1,0,0)),upper),Infinity,'Lower-level camera ray must not hit upper car');
const failures=results.filter(r=>r.pass===false),report={maxRSS_MB:Math.round(process.resourceUsage().maxRSS/1024),passed:failures.length===0,asset:path.basename(String(asset)),assetSha256:createHash('sha256').update(bytes).digest('hex'),metadataSha256:createHash('sha256').update(raw).digest('hex'),levels:data.levelTops.length,driveSurfaceMeshes:support.meshCount,parkedCars:boxes.filter(b=>b.parkingKind==='car').length,colliders:boxes.length,rampSamples,levelSeparationChecks,failures,results};await fs.writeFile(new URL('parking-support-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log('PARKING_SUPPORT',JSON.stringify({...report,results:undefined}));assert.equal(failures.length,0,'Layer-aware ramp/deck support regression failed');
