// Actual input/movement functions on the final full scene; renderer/DOM mocked.
import './simulate.mjs';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {Vector3} from 'three';
import {PARKING} from '../dist/parking-config.js';
const a=window.__campus,t=engineTest;assert.ok(PARKING.enabled&&t.parkingSupport.ready,'Final open-parking model required');
assert.equal(a.cars.length,11);assert.equal(a.npcs.length,19);assert.equal(a.shuttles.length,2);
const car=a.cars[0],results=[],dt=1/60;
a.reset();car.g.position.set(138,PARKING.levelTops[1],750);a.player.position.set(138,PARKING.levelTops[0],750);a.interact();assert.equal(a.state.mode,'walking','Cannot board a controllable car through the floor above');results.push({kind:'cross_level_boarding_rejected',pass:true});

function brake(){t.keys.clear();t.stick.x=t.stick.y=0;t.keys.add('Space');for(let i=0;i<180&&Math.abs(car.speed)>.025;i++)t.driveStep(dt);t.keys.clear();car.speed=0;}
function enterAt(point,yaw){a.reset();car.g.position.set(...point);car.yaw=yaw;car.speed=0;delete car.g.userData.groundFit;t.fitVehicleToGround(car.g,yaw);a.player.position.copy(car.g.position).add(new Vector3(Math.cos(yaw)*2.5,0,-Math.sin(yaw)*2.5));a.interact();assert.equal(a.state.mode,'driving','Enter existing controllable car inside garage');}
for(const ramp of PARKING.rampConnections){
 const start=ramp.points[0],end=ramp.points.find(p=>p[0]>=141.9&&Math.abs(p[2]-start[2])<.2);assert.ok(end);enterAt(start,-Math.PI/2);
 for(const reverse of [false,true]){
  let maxJump=0,steps=0,previousY=car.g.position.y;
  const target=reverse?start:end;
  while((reverse?car.g.position.x>target[0]+.12:car.g.position.x<target[0]-.12)&&steps++<3600){
   t.keys.clear();if(reverse?car.speed> -1.8:car.speed<2.1)t.keys.add(reverse?'KeyS':'KeyW');t.driveStep(dt);maxJump=Math.max(maxJump,Math.abs(car.g.position.y-previousY));previousY=car.g.position.y;
  }
  brake();const error=Math.abs(car.g.position.y-target[1]),horizontal=Math.abs(car.g.position.x-target[0]);results.push({kind:reverse?'drive_reverse_down':'drive_forward_up',fromLevel:ramp.fromLevel,toLevel:ramp.toLevel,pass:steps<3600&&error<.12&&horizontal<.8&&maxJump<.25,steps,verticalError:error,horizontalError:horizontal,maxFrameHeightJump:maxJump,position:car.g.position.toArray()});
 }
}
a.reset();
for(const stairs of PARKING.stairConnections){const raw=stairs.points,lower=PARKING.levelTops[stairs.fromLevel],upper=PARKING.levelTops[stairs.toLevel],points=[[149.5,lower,raw[0][2]],...raw,[156,upper,raw.at(-1)[2]]];
 for(const reverse of [false,true]){const route=reverse?points.toReversed():points;a.reset();a.player.position.set(...route[0]);let failed=null,maxJump=0,oldY=a.player.position.y;t.keys.add('KeyW');
  for(const target of route.slice(1)){let distance=Math.hypot(target[0]-a.player.position.x,target[2]-a.player.position.z),budget=Math.ceil(distance/.05)+60;
   while(distance>.075&&budget-->0){a.player.yaw=Math.atan2(-(target[0]-a.player.position.x),-(target[2]-a.player.position.z));t.walkStep(Math.min(dt,distance/3.5));maxJump=Math.max(maxJump,Math.abs(a.player.position.y-oldY));oldY=a.player.position.y;distance=Math.hypot(target[0]-a.player.position.x,target[2]-a.player.position.z);}
   const vertical=Math.abs(a.player.position.y-target[1]);if(distance>.2||vertical>.25){failed={target,position:a.player.position.toArray(),horizontalError:distance,verticalError:vertical};break;}
  }
  t.keys.clear();results.push({kind:reverse?'walk_stairs_down':'walk_stairs_up',fromLevel:stairs.fromLevel,toLevel:stairs.toLevel,pass:!failed,maxFrameHeightJump:maxJump,failed});
 }
}
a.reset();const failures=results.filter(r=>!r.pass),report={passed:failures.length===0,levels:PARKING.levelTops.length,decorativeParkedCars:PARKING.parkedCars.length,controllableCars:a.cars.length,npcs:a.npcs.length,shuttles:a.shuttles.length,results,verification:'Real driveStep/walkStep and GLB collisions; mocked DOM/renderer, not WebGL/device verification'};await fs.writeFile(new URL('parking-gameplay-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log('PARKING_GAMEPLAY',JSON.stringify(report));assert.equal(failures.length,0,'Multilevel parking drive/walk traversal regression failed');
