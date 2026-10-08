import './simulate.mjs';
import fs from 'node:fs/promises';
import {shuttleBoxOverlap,shuttleVehicleOverlap,pointInShuttle,stepShuttle,createShuttle} from '../dist/shuttle-system.js';
const a=window.__campus,t=engineTest,route=a.shuttles[0]?.state.route;
if(!route)throw new Error('No active shuttle route');
const collisions=[],dynamic=[];let count=0;
for(let s=0;s<route.total;s+=.25){const pose=route.sample(s);count++;for(const b of t.blockers)if(shuttleBoxOverlap(pose,{min:b.min.toArray(),max:b.max.toArray()})){collisions.push({distance:Math.round(s),position:pose.position,label:b.label||'tree or unnamed proxy',box:[b.min.toArray(),b.max.toArray()]});break;}for(const [i,c] of a.cars.entries())if(shuttleVehicleOverlap(pose,{position:c.g.position.toArray(),yaw:c.yaw}))dynamic.push({distance:Math.round(s),car:i,position:c.g.position.toArray()});for(const [i,n] of a.npcs.entries())if(pointInShuttle(n.g.position.toArray(),pose,{margin:.45}))dynamic.push({distance:Math.round(s),npc:i,position:n.g.position.toArray()});}
const state=createShuttle(route);for(let i=0;i<12000;i++)stepShuttle(state,.1);const unique=[...new Set(state.stopsVisited)];
const passed=collisions.length===0&&dynamic.length===0&&unique.length===7;const report={passed,samples:count,lengthMeters:route.total,staticOverlapSamples:collisions.length,staticExamples:collisions.filter((c,i)=>!i||c.label!==collisions[i-1].label).slice(0,30),dynamicOverlapSamples:dynamic.length,dynamicActors:[...new Set(dynamic.map(d=>d.car!==undefined?'car '+d.car:'npc '+d.npc))],dynamicExamples:dynamic.slice(0,12),orderedStops:route.stops.map(s=>s.id),pureRouteStopsVisited:unique,simulatedSeconds:1200};
console.log('TRANSIT_REPORT',JSON.stringify(report,null,2));await fs.writeFile(new URL('transit-integration-results.json',import.meta.url),JSON.stringify(report,null,2));

if(!passed)throw new Error('Transit path clearance or stop-cycle validation failed');
