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
