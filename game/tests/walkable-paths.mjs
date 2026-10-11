import './simulate.mjs';
import {WORLD} from '../dist/world-config.js';
import fs from 'node:fs/promises';
import {walkSurfaceHeightIndex} from './helpers/walk-surface-index.mjs';
import {runtimeInputHashes} from './helpers/revision-hashes.mjs';
const a=window.__campus,t=engineTest,results=[],surfaceObservations=[],nonFloorFaces=[],selected=process.env.WALK_PATH_IDS?.split(',').filter(Boolean),skipSurfaces=process.env.WALK_SKIP_SURFACES==='1';
const scope={partial:!!selected||skipSurfaces,selectedPathIds:selected||null,skipSurfaces};
const reportPath=new URL(scope.partial?'walkable-focused-results.json':'walkable-results.json',import.meta.url);
const paths=(WORLD.pedestrianPaths||[]).filter(path=>!selected||selected.includes(path.id));
if(selected&&selected.some(id=>!paths.some(path=>path.id===id)))throw new Error('Requested walk path missing from current input');
const inputSha256=await runtimeInputHashes(),began=performance.now();
const snapshot=async(phase)=>{const report={passed:phase==='complete'&&results.every(r=>r.pass),phase,scope,inputSha256,surfaceCount:(WORLD.walkableSurfaces||[]).length,pathCount:paths.length,elapsedSeconds:(performance.now()-began)/1000,nonFloorFaces,surfaceObservations,metadataHeightDifferences:surfaceObservations.filter(r=>!r.matchesMetadata).length,surfaceConformityRequirement:'surface-conformity.mjs separately verifies actual finite rendered faces against runtime support; stale buried metadata heights are observations, not walking elevations.',results};await fs.writeFile(reportPath,JSON.stringify(report,null,2)+'\n');return report;};
const explicitSurfaceHeight=walkSurfaceHeightIndex(WORLD.walkableSurfaces||[]);
if(!skipSurfaces){
 for(const surface of WORLD.walkableSurfaces||[])for(const [index,triangle] of surface.triangles.entries()){
  const [ta,tb,tc]=triangle.map(i=>surface.polygon[i]),projectedDoubleArea=Math.abs((tb[0]-ta[0])*(tc[2]-ta[2])-(tb[2]-ta[2])*(tc[0]-ta[0]));
  if(projectedDoubleArea<1e-10){nonFloorFaces.push({id:surface.id,triangle:index,reason:'Vertical or horizontally degenerate triangle; physical side remains in collider, not a downward-floor-height assertion.'});continue;}
  const p=triangle.reduce((sum,k)=>sum.map((v,i)=>v+surface.polygon[k][i]/3),[0,0,0]),expected=explicitSurfaceHeight(p[0],p[2],p[1]),h=a.floorHeight(p[0],p[2],expected+.3);
  surfaceObservations.push({id:surface.id,triangle:index,matchesMetadata:h!==null&&Math.abs(h-expected)<.09,expected,faceHeight:p[1],actual:h,point:p});
 }
 await snapshot('paths_pending');console.log('WALKABLE_SURFACES',JSON.stringify({samples:surfaceObservations.length,metadataHeightDifferences:surfaceObservations.filter(r=>!r.matchesMetadata).length,nonFloorFaces:nonFloorFaces.length}));
}
for(const path of paths)for(const reverse of [false,true]){
 const points=reverse?[...path.points].reverse():path.points;if(points.length<2)continue;
 const waypointTolerance=Math.min(.09,...points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[2]-points[i][2])/4).filter(d=>d>1e-6));
 a.reset();a.player.position.set(...points[0]);const startY=a.floorHeight(points[0][0],points[0][2],points[0][1]+.5);if(startY!==null)a.player.position.y=startY;
 let worst=0,failed=null,previousY=a.player.position.y,maxJump=0,steps=0;t.keys.add('KeyW');
 for(const target of points.slice(1)){
  let remaining=Math.hypot(target[0]-a.player.position.x,target[2]-a.player.position.z),budget=Math.ceil(remaining/.07)+30;
  while(remaining>waypointTolerance&&budget-->0){
   const dx=target[0]-a.player.position.x,dz=target[2]-a.player.position.z;a.player.yaw=Math.atan2(-dx,-dz);const dt=Math.min(.02,remaining/3.5);t.updateShuttles(dt);t.walkStep(dt);steps++;
   maxJump=Math.max(maxJump,Math.abs(a.player.position.y-previousY));previousY=a.player.position.y;remaining=Math.hypot(target[0]-a.player.position.x,target[2]-a.player.position.z);
  }
  const verticalError=Math.abs(a.player.position.y-target[1]);worst=Math.max(worst,remaining,verticalError);
  if(remaining>.25||verticalError>.45){failed={target,position:a.player.position.toArray(),horizontalError:remaining,verticalError};break;}
 }
 t.keys.clear();if(!failed&&maxJump>.56)failed={kind:'excessive_frame_height_change',maximum:maxJump,limit:.56};results.push({id:path.id,type:reverse?'walk_reverse':'walk_forward',pass:!failed,worstError:worst,maxFrameHeightJump:maxJump,steps,failed});
 await snapshot('walking');console.log('WALKABLE_PATH',JSON.stringify(results.at(-1)));
}
a.reset();const report=await snapshot('complete');console.log('WALKABLE',JSON.stringify({passed:report.passed,scope,surfaces:report.surfaceCount,paths:report.pathCount,failures:results.filter(r=>!r.pass).slice(0,12)}));if(!report.passed)throw new Error('Actual walking path regression failed');
