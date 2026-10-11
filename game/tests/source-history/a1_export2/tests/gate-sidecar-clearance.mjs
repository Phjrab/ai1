import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {Vector3} from 'three';
import {polygonCollisionBoxes} from '../dist/polygon-colliders.js';
import {vehicleOverlapsStaticBox} from '../dist/parking-system.js';
const input=process.argv.find(a=>a.startsWith('--world='))?.slice(8)||new URL('../dist/world-config.js',import.meta.url),world=JSON.parse((await fs.readFile(input,'utf8')).split('export const WORLD = ')[1].replace(/;\s*$/,'')),routes=world.roads.filter(r=>r.kind?.startsWith('directed_gate'));
if(!routes.length){console.log('GATE_SIDECAR: no gate lanes in this native input set');process.exit(0)}
const boxes=polygonCollisionBoxes(world.collisionPolygons),failures=[];let samples=0;
for(const route of routes)for(let i=1;i<route.points.length;i++){
 const a=route.points[i-1],b=route.points[i],length=Math.hypot(b[0]-a[0],b[2]-a[2]),yaw=Math.atan2(a[0]-b[0],a[2]-b[2]);
 for(let d=0;d<=length;d+=.25){const point=new Vector3(...a).lerp(new Vector3(...b),d/length);samples++;for(const box of boxes)if(vehicleOverlapsStaticBox(point,yaw,box))failures.push({route:route.id,point:point.toArray(),box:box.label});}
}
const report={passed:!failures.length,routes:routes.length,samples,collisions:failures.length,failures,verification:'Authored sidecar solid polygons against whole 2.28×4.38×1.68m passenger-car envelope with 2cm margin; actual GLB tilt and driveStep tested separately.'};
const output=process.argv.find(a=>a.startsWith('--output='))?.slice(9)||new URL('gate-sidecar-clearance-results.json',import.meta.url);await fs.writeFile(output,JSON.stringify(report,null,2)+'\n');console.log('GATE_SIDECAR',JSON.stringify({...report,failures:failures.slice(0,10)}));assert.ok(report.passed);
