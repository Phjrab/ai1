// Checks final game GLB material/geometry integration and source-runtime support.
// This does not instantiate a GPU renderer or certify visual/mobile performance.
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {Raycaster,Vector3,Matrix4,Box3} from 'three';
import {captureModelMeshes} from './helpers/capture-model.mjs';
const captured=captureModelMeshes(o=>/CAMPUS_CONTINUOUS_vehicle_asphalt|RV2[ _]foundation[ _]floor|RV2_PS_theatre_court_stage_steps/.test(o.name));
const inventory=JSON.parse(await fs.readFile(new URL('../data/native-export-campus-inventory.json',import.meta.url),'utf8')),expectedTrees=new Map(inventory.objects.filter(o=>o.proxy_root_world).map(o=>[o.name,o])),actualTrees=new Map(),capture=globalThis.captureCampusTestGeometry;
if(inventory.objects.some(o=>o.matrix_world))assert.ok(expectedTrees.size>=1314,'Final inventory must bind original1259 and central55 source tree roots');
globalThis.captureCampusTestGeometry=(name,scene)=>{capture(name,scene);if(name!=='campus.glb'||!expectedTrees.size)return;scene.traverse(o=>{const source=o.userData?.name||o.name;if(!expectedTrees.has(source))return;const points=new Map(),bounds=new Box3();o.traverse(part=>{if(!part.isMesh)return;const attribute=part.geometry.attributes.position,v=new Vector3();for(let i=0;i<attribute.count;i++){v.fromBufferAttribute(attribute,i).applyMatrix4(part.matrixWorld);bounds.expandByPoint(v);points.set(v.toArray().map(n=>n.toFixed(6)).join(','),v.clone());}});const lowest=bounds.min.y,feet=[...points.values()].filter(p=>p.y<=lowest+.0001),root=feet.reduce((sum,p)=>sum.add(p),new Vector3()).multiplyScalar(1/feet.length);actualTrees.set(source,{matrix:o.matrixWorld.clone(),root,bounds});});};
await import('./simulate.mjs');
delete globalThis.captureCampusTestGeometry;
const root=new URL('../',import.meta.url);
const profiles=JSON.parse(await fs.readFile(new URL('data/game-materials.json',root),'utf8'));
assert.equal(profiles.version,'campus-realism-v2','Run only after integrating final realism assets');
const assets=[],failures=[],slabs=[];let parkingProbes=[];const theatreReplacement={visible:false,samples:0,passed:0};
let maximumTreeRootError=0,maximumTreeGroundGap=0;const R=new Matrix4().makeRotationX(-Math.PI/2),inverseR=R.clone().invert();
for(const [name,expected] of expectedTrees){const actual=actualTrees.get(name);if(!actual){failures.push({reason:'Source tree omitted after unhide/export',name});continue;}const matrix=R.clone().multiply(new Matrix4().set(...expected.matrix_world.flat())).multiply(inverseR),matrixError=Math.max(...matrix.elements.map((v,i)=>Math.abs(v-actual.matrix.elements[i]))),root=new Vector3(expected.proxy_root_world[0],expected.proxy_root_world[2],-expected.proxy_root_world[1]),rootError=root.distanceTo(actual.root),ground=window.__campus.floorHeight(actual.root.x,actual.root.z,actual.root.y+.5),groundGap=ground===null?null:actual.root.y-ground;maximumTreeRootError=Math.max(maximumTreeRootError,rootError);if(groundGap!==null)maximumTreeGroundGap=Math.max(maximumTreeGroundGap,Math.abs(groundGap));if(matrixError>.001||rootError>.003||groundGap===null||Math.abs(groundGap)>.10)failures.push({reason:'Source tree transform/root/ground mismatch',name,matrixError,rootError,groundGap,actualRoot:actual.root.toArray(),expectedRoot:root.toArray()});}
const treeExport={sourceProxyRoots:expectedTrees.size,actualProxyRoots:actualTrees.size,maximumTreeRootError,maximumTreeGroundGap,verification:expectedTrees.size?'Actual pre-optimization GLB tree vertices and transforms versus the final native export inventory; ground ray uses runtime support.':'Intermediate inventory predates native tree-root binding; final check pending.'};
for(const name of ['building.glb','campus.glb','shuttle_bus.glb']){
 const buffer=await fs.readFile(new URL('dist/assets/'+name,root));
 const json=JSON.parse(buffer.subarray(20,20+buffer.readUInt32LE(12)).toString('utf8'));
 const matched=[];
 for(const m of json.materials||[]){const p=profiles.materials[m.name]||profiles.materials[m.name?.replace(/\.\d{3}$/,'')];if(!p)continue;const actual=m.pbrMetallicRoughness||{},color=actual.baseColorFactor||[1,1,1,1],textured=m.extras?.RV2_game_texture_material===true,expected=textured?{baseColorLinear:[1,1,1,1],roughness:1,metalness:0}:p;
  if(textured&&(!actual.baseColorTexture||!actual.metallicRoughnessTexture||!m.normalTexture))failures.push({asset:name,material:m.name,reason:'Explicit paver PBR image binding missing'});
  const okay=color.every((v,i)=>Math.abs(v-expected.baseColorLinear[i])<1e-5)&&Math.abs((actual.roughnessFactor??1)-expected.roughness)<1e-5&&Math.abs((actual.metallicFactor??1)-expected.metalness)<1e-5;
  if(!okay)failures.push({asset:name,material:m.name,reason:'PBR does not match final table'});
  if(p.emissiveColorLinear&&p.emissiveStrength>0){const actualEmission=m.emissiveFactor||[0,0,0],strength=m.extensions?.KHR_materials_emissive_strength?.emissiveStrength??1;if(actualEmission.some((v,i)=>Math.abs(v*strength-p.emissiveColorLinear[i]*p.emissiveStrength)>1e-4))failures.push({asset:name,material:m.name,reason:'Constant luminaire emission does not match native fallback'});}
  matched.push(m.name);
 }
 const dense=(json.nodes||[]).filter(n=>/^RV2[ _]canopy(?:[ _]infill)?[ _]+[|_]/i.test(n.name||''));if(dense.length)failures.push({asset:name,reason:'Dense native canopy accidentally exported',count:dense.length});
 const replaced=(json.nodes||[]).filter(n=>n.extras?.RV2_replaced_by_architecture);if(replaced.length)failures.push({asset:name,reason:'Hidden replaced architecture accidentally exported',count:replaced.length});
 assets.push({name,bytes:buffer.length,nodes:json.nodes?.length||0,materials:json.materials?.length||0,matched:matched.length,denseNativeCanopies:dense.length});
 if(name!=='campus.glb')continue;
 const gltf={scene:captured};gltf.scene.updateMatrixWorld(true);
 const roadMeshes=[];gltf.scene.traverse(o=>{if(o.isMesh&&/CAMPUS_CONTINUOUS_vehicle_asphalt/.test(o.name))roadMeshes.push(o);});
 const roadRay=new Raycaster();parkingProbes=JSON.parse(await fs.readFile(new URL('data/realism-road-probes.json',root),'utf8')).points.map((xyz,index)=>{roadRay.set(new Vector3(xyz[0],xyz[2]+20,-xyz[1]),new Vector3(0,-1,0));roadRay.far=40;const roadHit=roadRay.intersectObjects(roadMeshes,false)[0];const p=new Vector3(xyz[0],roadHit?.point.y??xyz[2],-xyz[1]),h=window.__campus.floorHeight(p.x,p.z,p.y+.55),blocked=engineTest.blockedPosition(p,1.25),passed=!!roadHit&&h!==null&&Math.abs(h-p.y)<.05&&!blocked;if(!passed)failures.push({reason:'Parking164 asphalt support or vehicle clearance',index,point:p.toArray(),ground:h,blocked});return {index,passed,actualAsphaltHeight:p.y,ground:h,blocked};});

 gltf.scene.traverse(o=>{if(!o.isMesh||!o.name.includes('RV2_foundation_floor')&&!o.name.includes('RV2 foundation floor'))return;
  const p=o.geometry.getAttribute('position'),indices=o.geometry.index;let samples=0,passed=0;const points=[new Vector3(),new Vector3(),new Vector3()],cross=new Vector3(),u=new Vector3(),v=new Vector3();
  for(let i=0;i<(indices?.count??p.count);i+=3){for(let j=0;j<3;j++)points[j].fromBufferAttribute(p,indices?indices.getX(i+j):i+j).applyMatrix4(o.matrixWorld);cross.crossVectors(u.subVectors(points[1],points[0]),v.subVectors(points[2],points[0]));if(cross.y<=1e-7)continue;const center=points[0].clone().add(points[1]).add(points[2]).multiplyScalar(1/3);const h=window.__campus.floorHeight(center.x,center.z,center.y+.07);samples++;if(h!==null&&Math.abs(h-center.y)<.08)passed++;else failures.push({reason:'Added floor support missing from runtime collider',object:o.name,point:center.toArray(),actual:h});}
  slabs.push({name:o.name,sourceName:o.userData.name||o.name,samples,passed});
 });
}
const sampleCount=slabs.reduce((n,s)=>n+s.samples,0),samplePassed=slabs.reduce((n,s)=>n+s.passed,0);
const expectedCaps=inventory.objects.filter(o=>o.name.includes('RV2 foundation floor')).map(o=>o.name).sort();assert.deepEqual(slabs.map(s=>s.sourceName).sort(),expectedCaps,'Every visible native foundation cap must be present exactly');
const publicTheatre=inventory.objects.some(o=>o.name==='RV2_PS_theatre_court_stage_steps');
if(publicTheatre){
 assert.equal(expectedCaps.length,66,'The public theatre replaces original167 cap; other66 caps remain');assert.ok(!expectedCaps.some(name=>/BUILDING[ _]167[ _]/.test(name)),'Superseded167 generic cap must stay hidden');
 captured.traverse(o=>{if(o.isMesh&&/RV2_PS_theatre_court_stage_steps/.test(o.name))theatreReplacement.visible=true;});assert.ok(theatreReplacement.visible,'Theatre physical floor replacement must be exported');
 const {WORLD}=await import('../dist/world-config.js');for(const sf of WORLD.walkableSurfaces.filter(s=>s.id.startsWith('public_theatre_')))for(const face of sf.triangles){const p=face.reduce((v,k)=>v.add(new Vector3(...sf.polygon[k])),new Vector3()).multiplyScalar(1/3),h=window.__campus.floorHeight(p.x,p.z,p.y+.15);theatreReplacement.samples++;if(h!==null&&Math.abs(h-p.y)<.08)theatreReplacement.passed++;else failures.push({reason:'Actual public theatre support missing',id:sf.id,point:p.toArray(),actual:h});}
 assert.ok(theatreReplacement.samples>20,'Theatre court, aisles and steps need independent support samples');
}else assert.equal(expectedCaps.length,67,'Intermediate pre-theatre native has67 generic caps');
assert.ok(sampleCount>=600,'Expected full footprint floor triangulation');
for(const id of [132,127])assert.ok(slabs.some(s=>new RegExp('BUILDING[ _]'+id+'[ _]').test(s.name)&&s.passed===s.samples),'Library/sports support floor must be present');
const supportBoxes=engineTest.blockers.filter(b=>/hospital_canopy_columns/.test(b.label||''));assert.equal(supportBoxes.length,2,'New hospital supports require individual vehicle blockers');assert.ok(supportBoxes.every(b=>b.max.x-b.min.x<1&&b.max.z-b.min.z<1),'Block only supports, not the open passage');

const npcSupport=window.__campus.npcs.map((npc,index)=>{const p=npc.g.position,h=window.__campus.floorHeight(p.x,p.z,p.y+.5);const passed=h!==null&&Math.abs(h-p.y)<.05;if(!passed)failures.push({reason:'NPC not grounded',index,y:p.y,ground:h});return {index,passed};});
const report={maxRSS_MB:Math.round(process.resourceUsage().maxRSS/1024),passed:failures.length===0,treeExport,assets,npcSupport,parkingProbes,canopySupportBlockers:supportBoxes.map(b=>({label:b.label,min:b.min.toArray(),max:b.max.toArray()})),grounding:{visibleGenericCaps:slabs.length,floors:slabs.length,samples:sampleCount,passed:samplePassed,slabs,theatre167Replacement:theatreReplacement,scope:'Visible generic cap closure only; standing garage deck/ramp heights are checked separately.'},failures,verification:'Actual GLB decoding and runtime collision rays; no WebGL/browser/device rendering test'};
await fs.writeFile(new URL('realism-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log('REALISM',JSON.stringify(report));assert.equal(failures.length,0,JSON.stringify(failures.slice(0,8)));
