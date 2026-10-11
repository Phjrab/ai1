import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {WORLD} from '../dist/world-config.js';
import {visibleFloorIndex} from './helpers/visible-floor-index.mjs';
import {isParkingStaticCar} from '../dist/parking-system.js';
import {isCollisionDisabled,isOriginalCampusCar} from '../dist/revision-colliders.js';
import {captureModelMeshes} from './helpers/capture-model.mjs';
const scene=captureModelMeshes(o=>!isCollisionDisabled(o)&&!isParkingStaticCar(o)&&!isOriginalCampusCar(o)&&!/campus[ _]tree|rv2[ _]canopy|foliage|leaves|prototype|parked[ _]car/i.test(o.name+' '+o.parent?.name));
await import('./simulate.mjs');
delete globalThis.captureCampusTestGeometry;
scene.updateMatrixWorld(true);const support=[];scene.traverse(o=>{if(o.isMesh)support.push(o)});
// All finite physical render faces, including rails, are eligible. The index
// excludes JSON overlays and uses compact arrays instead of a second Octree.
const visible=visibleFloorIndex(support),results=[];let nonFloorFaces=0;
const selected=process.env.CAMPUS_SURFACE_POINTS?new Set(JSON.parse(await fs.readFile(process.env.CAMPUS_SURFACE_POINTS,'utf8')).map(r=>r.id+':'+r.triangle)):null;
const precisionEdges=[],undersideObservations=[];
const floorFace=hit=>hit.normalY>=.1||hit.groundSupport||/terrain|inferred_game_walk|continuous.*paving|apron|walk.*top|walk.*floor/i.test(hit.sourceName);
// Use walkStep's actual prior-floor + 0.55 m probe origin. A 3 m origin would
// intentionally hit nearby handrail tops or an overhead deck, not walking floor.
for(const surface of WORLD.walkableSurfaces){for(const [index,triangle] of surface.triangles.entries()){if(selected&&!selected.has(surface.id+':'+index))continue;const [a,b,c]=triangle.map(i=>surface.polygon[i]);if(Math.abs((b[0]-a[0])*(c[2]-a[2])-(b[2]-a[2])*(c[0]-a[0]))<1e-10){nonFloorFaces++;continue;}const p=triangle.reduce((p,i)=>p.add(new THREE.Vector3(...surface.polygon[i])),new THREE.Vector3()).multiplyScalar(1/3);let hit=visible.query(p.x,p.z,p.y+.55);const runtime=window.__campus.floorHeight(p.x,p.z,p.y+.55),record={id:surface.id,triangle:index,point:p.toArray()};if(hit&&runtime!==null&&Math.abs(runtime-hit.height)>.025&&!floorFace(hit)){const floor=visible.query(p.x,p.z,p.y+.55,1.1,{accept:floorFace});record.nonStandingUnderside={...hit,reason:'Downward structural cap is an underside, not a standing surface. Actual body and closed-door traversal are tested separately.'};undersideObservations.push(record);hit=floor;}if(hit&&runtime!==null&&Math.abs(runtime-hit.height)>.025){const edge=visible.query(p.x,p.z,p.y+.55,1.1,{edgeTolerance:.0001,accept:h=>floorFace(h)&&Math.abs(h.height-runtime)<.002});if(edge&&edge.edgeDistance>0){record.finiteEdgeMatch={...edge,strictSurface:hit,basis:'Actual finite triangle is at most 0.1 mm from this float32 metadata boundary; height matches its physical adjacent tread.'};precisionEdges.push(record);hit=edge;}}Object.assign(record,{visibleHeight:hit?.height??null,supportObject:hit?.sourceName??null,runtimeHeight:runtime,runtimeVisibleGap:hit&&runtime!==null?runtime-hit.height:null,metadataVisibleGap:hit?p.y-hit.height:null});results.push(record);}}
// Some authored floor triangles extend beneath closed doors and door frames.
// Keep those observations, but judge standing height only where a player fits.
const allDifferences=results.filter(r=>r.runtimeVisibleGap===null||Math.abs(r.runtimeVisibleGap)>.025),obstructedSamples=[];
for(const record of allDifferences){const p=new THREE.Vector3(...record.point),bodyHits=[.65,1.3].map(height=>{const hit=engineTest.octree.sphereIntersect(new THREE.Sphere(p.clone().add(new THREE.Vector3(0,height,0)),.34));return hit&&hit.depth>.001?{height,depth:hit.depth,normal:hit.normal.toArray(),basis:'Actual collision at body height, including horizontal solid caps'}:null}).filter(Boolean),blocked=engineTest.blockedPosition(p);if(record.visibleHeight!==null&&(blocked||bodyHits.length)){record.obstructedBySolid={blocked,bodyHits};obstructedSamples.push(record);}}
const differences=allDifferences.filter(r=>!r.obstructedBySolid),report={maxRSS_MB:Math.round(process.resourceUsage().maxRSS/1024),samples:results.length,nonFloorFaces,focused:!!selected,precisionEdgeSampleCount:precisionEdges.length,precisionEdges,nonStandingUndersideCount:undersideObservations.length,undersideObservations,differenceCount:differences.length,obstructedSampleCount:obstructedSamples.length,maxRuntimeVisibleGap:Math.max(...results.map(r=>Math.abs(r.runtimeVisibleGap??0))),maxWalkableRuntimeVisibleGap:Math.max(...results.filter(r=>!r.obstructedBySolid).map(r=>Math.abs(r.runtimeVisibleGap??0))),differences,obstructedSamples,results,method:'Actual exported finite physical GLB triangles, including occupied rail surfaces, versus runtime collider at navigation triangle centroids. Floors under closed doors/solid body obstructions remain recorded but cannot be standing positions; missing native support always fails. DOM and renderer mocked, no WebGL/device QA.'};
await fs.writeFile(new URL('surface-conformity-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log('SURFACE_CONFORMITY',JSON.stringify({...report,results:undefined,obstructedSamples:undefined,differences:differences.slice(0,25)}));

assert.equal(differences.length,0,'Runtime support must match final visible exported surfaces within 25 mm');
