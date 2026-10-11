import './simulate.mjs';
import {Vector3} from 'three';
import fs from 'node:fs/promises';
const a=window.__campus,t=engineTest,results=[];
a.start();
for(let frame=0;frame<72;frame++){t.setElapsed(frame*9);t.animate();for(const [index,n] of a.npcs.entries())if(t.blockedPosition(n.g.position,.34))results.push({type:'npcOverlap',frame,index,position:n.g.position.toArray()});}
const npcFailures=results.length;
for(const [index,c] of a.cars.entries()){
 a.reset();c.speed=0;let entered=false;
 for(const side of [1,-1]){const offset=new Vector3(Math.cos(c.yaw)*2.5,0,-Math.sin(c.yaw)*2.5);a.player.position.copy(c.g.position).addScaledVector(offset,side);a.interact();if(a.state.mode==='driving'){entered=true;break;}}
 const start=c.g.position.clone();if(entered){t.keys.add('KeyW');for(let n=0;n<120;n++)t.driveStep(1/60);t.keys.clear();t.keys.add('Space');for(let n=0;n<120;n++)t.driveStep(1/60);t.keys.clear();a.interact();}
 const distance=c.g.position.distanceTo(start),exited=a.state.mode==='walking';results.push({type:'car',index,entered,distance,exited,pass:entered&&distance>.1&&exited});
}
a.reset();const report={passed:npcFailures===0&&results.every(r=>r.pass!==false),npcCount:a.npcs.length,npcSampleTimes:72,npcFailures,carCount:a.cars.length,results};await fs.writeFile(new URL('actor-results.json',import.meta.url),JSON.stringify(report,null,2));console.log('ACTORS',JSON.stringify(report));if(!report.passed)throw new Error('Actor regression failed');
