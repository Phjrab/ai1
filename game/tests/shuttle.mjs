import assert from 'node:assert/strict';
import {createRoute,createShuttle,stepShuttle,pointInShuttle} from '../dist/shuttle-system.js';
// Synthetic rectangle is a unit-test fixture, not a claimed Chosun shuttle route.
const route=createRoute({id:'test',label:'Synthetic test loop',points:[[0,0,0],[80,0,0],[80,0,40],[0,0,40]],stops:[{id:'a',position:[0,0,0]},{id:'b',position:[80,0,20]}],dwellSeconds:5,cruiseSpeed:6});
const s=createShuttle(route);assert.equal(s.phase,'dwelling');for(let i=0;i<149;i++)stepShuttle(s,1/30);assert.equal(s.distance,0);for(let i=0;i<4;i++)stepShuttle(s,1/30);assert.equal(s.phase,'driving');assert.ok(s.stopsVisited.includes('a'));
let dwellingAtB=false,wrapped=false;
for(let i=0;i<3600;i++){const before=s.distance;stepShuttle(s,1/30);assert.ok(s.speed<=6.00001);if(s.phase==='dwelling'&&s.nextStopIndex===1){dwellingAtB=true;assert.ok(Math.abs(s.distance-100)<.06)}if(s.distance<before-.01)wrapped=true;}
assert.ok(dwellingAtB);assert.ok(wrapped);assert.ok(s.stopsVisited.includes('b'));
const blocked=createShuttle(route,{distance:30,startDwelling:false});for(let i=0;i<120;i++)stepShuttle(blocked,1/30,{obstacleDistance:2});assert.equal(blocked.distance,30);assert.equal(blocked.phase,'blocked');for(let i=0;i<90;i++)stepShuttle(blocked,1/30);assert.ok(blocked.distance>33);
assert.ok(pointInShuttle(blocked.position,blocked));assert.ok(!pointInShuttle([999,0,999],blocked));assert.throws(()=>createRoute({points:[[0,0,0],[1,0,0],[2,0,0]],stops:[]}));assert.throws(()=>stepShuttle(blocked,-1));
console.log(JSON.stringify({passed:true,tests:['dwell','depart','brake at stop','visit ordered stops','loop','block safely','resume','speed limit','dynamic body footprint','invalid inputs'],simulatedSeconds:120}));
// A source route can arrive at its starting station without a verified turn.
// Preserve the inbound pose indefinitely instead of wrapping onto departure.
const terminalRoute=createRoute({id:'terminal-test',points:[[0,0,0],[30,0,0],[30,0,20],[0,0,20],[0,0,0]],stops:[{id:'start',position:[0,0,0]},{id:'middle',position:[30,0,20]}],terminalStopId:'start',headingSpanMeters:6.4,dwellSeconds:3});
const terminal=createShuttle(terminalRoute);for(let i=0;i<3000;i++)stepShuttle(terminal,.05);
assert.equal(terminal.phase,'terminal');assert.equal(terminal.distance,terminalRoute.total);assert.equal(terminal.laps,0);assert.equal(terminal.speed,0);assert.deepEqual(terminal.stopsVisited,['start','middle','start']);
const arrival=JSON.stringify({position:terminal.position,yaw:terminal.yaw,distance:terminal.distance});for(let i=0;i<1000;i++)stepShuttle(terminal,.05);assert.equal(JSON.stringify({position:terminal.position,yaw:terminal.yaw,distance:terminal.distance}),arrival);
assert.ok(Math.abs(terminal.yaw-terminalRoute.sample(terminalRoute.total-.01).yaw)<1e-9);assert.ok(Math.abs(terminal.yaw-terminalRoute.sample(0).yaw)>1);
let previous=terminalRoute.sample(0).yaw,maxJump=0;for(let d=.12;d<terminalRoute.total;d+=.12){const yaw=terminalRoute.sample(d).yaw,jump=Math.abs(Math.atan2(Math.sin(yaw-previous),Math.cos(yaw-previous)));maxJump=Math.max(maxJump,jump);previous=yaw;}assert.ok(maxJump<.08);
assert.deepEqual(terminalRoute.sample(30).position,[30,0,0]);assert.deepEqual(terminalRoute.sample(1e6).position,[0,0,0]);assert.equal(createShuttle(terminalRoute).phase,'dwelling');
console.log(JSON.stringify({passed:true,tests:['verified endpoint holds incoming pose','no terminal teleport or lap','restart begins initial dwell','continuous axle-span corner heading','centreline unchanged'],maximumHeadingStepRadians:maxJump}));
