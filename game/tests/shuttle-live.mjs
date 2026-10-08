import './simulate.mjs';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const a=window.__campus,t=engineTest;
assert.equal(a.shuttles.length,2);
let blockedFrames=0;const began=performance.now(),samples=[];
for(let i=0;i<6000;i++){
  t.updateShuttles(.2);
  if(a.shuttles.some(b=>b.state.phase==='blocked'))blockedFrames++;
  if(i%300===0)samples.push({seconds:i*.2,buses:a.shuttles.map(b=>({distance:b.state.distance,speed:b.state.speed,phase:b.state.phase,nextStop:b.state.route.stops[b.state.nextStopIndex].id,laps:b.state.laps}))});
}
const buses=a.shuttles.map(b=>({id:b.state.id,laps:b.state.laps,visits:b.state.stopsVisited,uniqueStops:[...new Set(b.state.stopsVisited)],phase:b.state.phase}));
let failure=null;try{for(const b of buses){assert.ok(b.laps>=2,b.id+' should complete two loops');assert.equal(b.uniqueStops.length,7,b.id+' should visit all seven stops');}}catch(error){failure=error;}
const report={passed:failure===null,simulatedSeconds:1200,realSourceUpdateSeconds:(performance.now()-began)/1000,blockedFrames,buses,samples,decorativeVehiclesCleared:a.trafficClearance,failure:failure?.message||null};
await fs.writeFile(new URL('shuttle-live-results.json',import.meta.url),JSON.stringify(report,null,2));console.log('LIVE_SHUTTLE',JSON.stringify({passed:report.passed,simulatedSeconds:1200,blockedFrames,buses,elapsedSeconds:report.realSourceUpdateSeconds,cleared:a.trafficClearance}));if(failure)throw failure;
