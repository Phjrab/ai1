import './simulate.mjs';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {shuttleVehicleOverlap} from '../dist/shuttle-system.js';
const a=window.__campus,t=engineTest;
assert.equal(a.shuttles.length,2);
const expectedVisits=a.shuttles.map(b=>b.state.route.stops.filter(s=>s.distance>=b.state.distance-.05).map(s=>s.id).concat(b.state.route.terminalStopId));
let blockedFrames=0;const began=performance.now(),samples=[];
for(let i=0;i<6000;i++){
  t.updateShuttles(.2);
  if(a.shuttles.some(b=>b.state.phase==='blocked'))blockedFrames++;
  if(i%300===0)samples.push({seconds:i*.2,buses:a.shuttles.map(b=>({distance:b.state.distance,speed:b.state.speed,phase:b.state.phase,nextStop:b.state.route.stops[b.state.nextStopIndex].id,laps:b.state.laps}))});
}
const buses=a.shuttles.map(b=>({id:b.state.id,laps:b.state.laps,visits:b.state.stopsVisited,uniqueStops:[...new Set(b.state.stopsVisited)],phase:b.state.phase,position:b.state.position,yaw:b.state.yaw,speed:b.state.speed}));
const stoppedVehicleOverlap=shuttleVehicleOverlap(a.shuttles[0].state,a.shuttles[1].state,{width:2.5,length:10.7,otherWidth:2.5,otherLength:10.7,margin:0});let failure=null;try{assert.equal(stoppedVehicleOverlap,false,'Stopped buses must retain distinct physical space');for(const [i,b] of buses.entries()){assert.ok(['terminal','terminal_queue'].includes(b.phase),b.id+' should safely stop at the unverified turnaround');assert.equal(b.laps,0,'No instant endpoint reset');for(const id of expectedVisits[i])assert.ok(b.uniqueStops.includes(id)||b.phase==='terminal_queue'&&id===a.shuttles[i].state.route.terminalStopId,b.id+' omitted an expected stop '+id);}}catch(error){failure=error;}
const report={passed:failure===null,simulatedSeconds:1200,realSourceUpdateSeconds:(performance.now()-began)/1000,blockedFrames,buses,samples,expectedVisits,stoppedVehicleOverlap,terminalPolicy:'종점 회차 동선 미확인으로 반복 순환 미구현',decorativeVehiclesCleared:a.trafficClearance,failure:failure?.message||null};
await fs.writeFile(new URL('shuttle-live-results.json',import.meta.url),JSON.stringify(report,null,2));console.log('LIVE_SHUTTLE',JSON.stringify({passed:report.passed,simulatedSeconds:1200,blockedFrames,buses,elapsedSeconds:report.realSourceUpdateSeconds,cleared:a.trafficClearance}));if(failure)throw failure;
