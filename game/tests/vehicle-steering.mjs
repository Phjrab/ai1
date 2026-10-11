import assert from 'node:assert/strict';
import {VEHICLE_STEERING as p,steeringCurvature,steeringState} from '../dist/vehicle-steering.js';
const rearRadius=p.wheelbase/Math.tan(p.maxFrontSteer),centerRadius=Math.hypot(rearRadius,p.rearToCenter),outerWheelRadius=Math.hypot(rearRadius+p.track/2,p.wheelbase),conservativeBodySweep=Math.hypot(rearRadius+2.28/2,p.rearToCenter+4.38/2);
assert.ok(centerRadius>4.08&&centerRadius<4.1);assert.ok(outerWheelRadius>5.48&&outerWheelRadius<5.5);
for(const speed of [0,.2,1.5,2,-1.5])assert.ok(Math.abs(1/steeringCurvature(speed)-centerRadius)<1e-10);
for(const speed of [8,17,-8,-17])assert.ok(Math.abs(steeringCurvature(speed)-.047)<1e-12);
let previous=steeringCurvature(0);for(let speed=0;speed<=17;speed+=.01){const current=steeringCurvature(speed);assert.ok(current<=previous+1e-12);assert.ok(current>=.047-1e-12&&current<=1/centerRadius+1e-12);assert.equal(current,steeringCurvature(-speed));previous=current;}
for(const boundary of [2,8])assert.ok(Math.abs(steeringCurvature(boundary+.0001)-steeringCurvature(boundary-.0001))<1e-8);
assert.equal(steeringState(1,0).curvature,0);assert.equal(steeringState(1,0).slipAngle,0);assert.equal(steeringState(1,-1).curvature,-steeringState(1,1).curvature);assert.equal(steeringState(1,-1).slipAngle,-steeringState(1,1).slipAngle);assert.deepEqual(steeringState(1,2),steeringState(1,1));
console.log('PASS: modeled bicycle geometry, signed midpoint motion, and continuous speed-dependent steering',JSON.stringify({centerRadius,outerWheelRadius,conservativeBodySweep,frontDegrees:35}));
