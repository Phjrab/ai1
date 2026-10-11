import {runtimeInputHashes} from './helpers/revision-hashes.mjs';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {Vector3,Sphere} from 'three';
const input=new URL('../data/it-lounge.json',import.meta.url);
try{await fs.access(input)}catch{console.log('LOUNGE_ACCESS: no lounge in this explicitly intermediate input set');process.exit(0)}
await import('./simulate.mjs');
const raw=JSON.parse(await fs.readFile(input,'utf8')),bridge=JSON.parse(await fs.readFile(new URL('../data/it-rooftop-bridge.json',import.meta.url),'utf8')),a=window.__campus,t=engineTest,cv=p=>[p[0],p[2],-p[1]],results=[];
assert.equal(raw.table_count,6);assert.equal(bridge.bridge_terminal_osm_node,11134046237);assert.deepEqual(bridge.bridge_points.at(-1),raw.mapped_entrances.find(e=>e.osm_node===11134046237).point,'Primary bridge ends at the mapped doorway, not superseded shifted roof endpoint');
const bytes=await fs.readFile(new URL('../dist/assets/campus.glb',import.meta.url)),gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString()),tables=gltf.nodes.map(n=>n.name).filter(name=>/^R2_IT_LOUNGE_ROUND[ _]BENCH[ _]TABLE[ _]\d+$/.test(name));assert.equal(new Set(tables).size,6,'Exactly six round bench-table assemblies in final GLB');
for(const id of ['138','138_roof_bridge','138_lounge']){a.reset();const arrival=a.travelTo(id);results.push({kind:'destination',id,pass:!!arrival,position:arrival?.position});}
const branch=bridge.bridge_branches.find(b=>b.osm_entrance_node===4682911885),routes=[{id:'road_primary_door_lounge_roof',points:bridge.route},{id:'road_level5_door_lounge_roof',points:[...bridge.approach_points,...branch.points.slice(1),...raw.level5_entrance_route.slice(1),...raw.roof_to_lounge_route.toReversed().slice(1)]},...raw.table_approaches.map(item=>({id:'round_table_'+item.index,points:item.route}))];
for(const branch of bridge.bridge_branches){
 const route=branch.osm_entrance_node===11134046237?raw.mapped_entrance_route:raw.level5_entrance_route;
 const door=route[0],inside=route[1],outside=branch.points[0],length=Math.hypot(inside[0]-door[0],inside[1]-door[1]),ux=(inside[0]-door[0])/length,uy=(inside[1]-door[1])/length,bridgeLength=Math.hypot(outside[0]-door[0],outside[1]-door[1]);
 for(const offset of [-.3,0,.3])routes.push({id:'mapped_door_width_'+branch.osm_entrance_node+'_'+offset,points:[[door[0]+(outside[0]-door[0])*1.2/bridgeLength,door[1]+(outside[1]-door[1])*1.2/bridgeLength,door[2]],door,[door[0]+ux*1.2,door[1]+uy*1.2,door[2]]].map(p=>[p[0]-uy*offset,p[1]+ux*offset,p[2]])});
}
for(const offset of [-.3,.3])routes.push({id:'road_approach_width_'+offset,points:bridge.approach_points.map((p,i,points)=>{const a=points[Math.max(0,i-1)],b=points[Math.min(points.length-1,i+1)],length=Math.hypot(b[0]-a[0],b[1]-a[1]);return[p[0]-(b[1]-a[1])*offset/length,p[1]+(b[0]-a[0])*offset/length,p[2]]})});
for(const route of routes)for(const reverse of [false,true]){
 const points=(reverse?route.points.toReversed():route.points).map(cv);a.reset();a.player.position.set(...points[0]);let failed=null,maxJump=0,previous=a.player.position.y,samples=0;t.keys.add('KeyW');
 for(const target of points.slice(1)){
  let distance=Math.hypot(target[0]-a.player.position.x,target[2]-a.player.position.z),budget=Math.ceil(distance/.05)+90;
  while(distance>.075&&budget-->0){a.player.yaw=Math.atan2(-(target[0]-a.player.position.x),-(target[2]-a.player.position.z));t.walkStep(Math.min(.02,distance/3.5));samples++;maxJump=Math.max(maxJump,Math.abs(a.player.position.y-previous));previous=a.player.position.y;distance=Math.hypot(target[0]-a.player.position.x,target[2]-a.player.position.z);
   for(const height of [1.1,1.65]){const hit=t.octree.sphereIntersect(new Sphere(a.player.position.clone().add(new Vector3(0,height,0)),.2));if(hit&&Math.abs(hit.normal.y)<.7&&hit.depth>.025){failed={kind:'torso_head_clearance',height,depth:hit.depth,position:a.player.position.toArray()};break;}}
   if(failed)break;
  }
  if(failed)break;const vertical=Math.abs(a.player.position.y-target[1]);if(distance>.2||vertical>.25){failed={kind:'route',target,position:a.player.position.toArray(),horizontalError:distance,verticalError:vertical};break;}
 }
 t.keys.clear();results.push({kind:'walk',id:route.id,reverse,pass:!failed&&maxJump<=.56,samples,maxFrameHeightJump:maxJump,failed});
}
for(const table of raw.table_locations){const p=new Vector3(...cv(table.center));results.push({kind:'table_collision',index:table.index,pass:t.blockedPosition(p,.34)});p.y-=3.1;results.push({kind:'table_not_a_lower_floor_blocker',index:table.index,pass:!t.blockers.filter(b=>b.label?.startsWith('IT lounge table ')).some(b=>p.y+.65>b.min.y&&p.y<b.max.y)});}
a.reset();const failures=results.filter(r=>!r.pass),report={maxRSS_MB:Math.round(process.resourceUsage().maxRSS/1024),inputSha256:await runtimeInputHashes(),sceneAdditions:globalThis.campusTestExtraInputs||null,passed:!failures.length,tableAssemblies:tables.length,mappedDoorNodes:raw.mapped_entrances.map(e=>e.osm_node),results,verification:'Actual walkStep, height-aware collision and GLB body/head support checks; mocked DOM/renderer, no WebGL or device verification'};await fs.writeFile(new URL(globalThis.campusTestExtraInputs?'lounge-access-candidate-results.json':'lounge-access-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log('LOUNGE_ACCESS',JSON.stringify(report));assert.equal(failures.length,0,'Lounge door/table/roof access failed');
