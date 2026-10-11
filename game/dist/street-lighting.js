import * as THREE from 'three';

// The original campus and its support meshes are never modified here. Ground
// pools use only the finite triangles recorded by the native lighting author.
export const LIGHTING_LIMITS = Object.freeze({realtimeLights:4,nearDistance:42,refreshSeconds:.25});
export const TIME_PRESETS = Object.freeze({
  day:{label:'낮',sky:'#b1d0df',hemiSky:'#f0f7ff',hemiGround:'#74745a',hemi:1.6,sun:'#fff2d6',sunIntensity:3.1,exposure:.95,lamps:0,pools:0},
  evening:{label:'저녁',sky:'#596880',hemiSky:'#bacbe3',hemiGround:'#7b7060',hemi:.85,sun:'#ffd6a2',sunIntensity:.65,exposure:1.05,lamps:1.8,pools:.24},
  night:{label:'야간',sky:'#18283e',hemiSky:'#8ca9d0',hemiGround:'#5e6159',hemi:.46,sun:'#bacff2',sunIntensity:.16,exposure:1.1,lamps:2.2,pools:.32},
});
const V=THREE.Vector3;
export const fromBlender = p => [p[0],p[2],-p[1]];
const finiteVector = p => Array.isArray(p)&&p.length===3&&p.every(Number.isFinite);
const positive = x => Number.isFinite(x)&&x>0;
const emitterPosition=(f,offset=[0,0,0])=>fromBlender(f.lamp_position.map((value,i)=>value+offset[i]));
const fixtureColor = value => Array.isArray(value)?new THREE.Color().setRGB(...value):new THREE.Color(value);

export function validateLightingContract(data){
  if(data?.schema_version!==1||data.revision_id!=='street_lighting_v6'||!Array.isArray(data.fixtures))throw Error('Invalid street-lighting contract');
  if(!/^[a-f0-9]{64}$/.test(data.source_native_sha256||''))throw Error('Missing street-lighting source hash');
  const ids=new Set();
  for(const f of data.fixtures){
    if(typeof f.id!=='string'||ids.has(f.id))throw Error('Duplicate or missing lamp id');ids.add(f.id);
    for(const key of ['base_position','lamp_position','target_position'])if(!finiteVector(f[key]))throw Error(`${f.id}: invalid ${key}`);
    if(f.lamp_position[2]<=f.target_position[2]+.5)throw Error(`${f.id}: lamp is not above its finite ground target`);
    if(!positive(f.pool_radius)||f.pool_radius>20||!positive(f.intensity)||f.intensity>5000)throw Error(`${f.id}: invalid light range`);
    if(!(finiteVector(f.color)&&f.color.every(v=>v>=0&&v<=1))&&!/^#[a-f0-9]{6}$/i.test(f.color||''))throw Error(`${f.id}: invalid linear RGB light color`);
    if(!Array.isArray(f.fixture_object_names)||!f.fixture_object_names.length)throw Error(`${f.id}: missing fixture objects`);
    const c=f.collision;
    if(!c||!['pole_radius_m','pole_height_m','base_radius_m','base_height_m'].every(k=>positive(c[k])))throw Error(`${f.id}: invalid collision dimensions`);
    if(!Array.isArray(f.ground_patch_triangles)||!f.ground_patch_triangles.length)throw Error(`${f.id}: missing finite light-pool surface`);
    for(const tri of f.ground_patch_triangles){
      if(!Array.isArray(tri)||tri.length!==3||!tri.every(finiteVector))throw Error(`${f.id}: invalid pool triangle`);
      const a=new V(...tri[0]),b=new V(...tri[1]),d=new V(...tri[2]);
      const areaSquared=b.sub(a).cross(d.sub(a)).lengthSq();
      if(!Number.isFinite(areaSquared)||areaSquared<=0)throw Error(`${f.id}: degenerate pool triangle`);
    }
  }
  if(!ids.size)throw Error('Lighting contract has no fixtures');
  return data;
}

export function fixtureCollisionBoxes(fixtures){
  const boxes=[];
  for(const f of fixtures){
    const base=new V(...fromBlender(f.base_position));
    for(const [kind,r,h] of [['pole',f.collision.pole_radius_m,f.collision.pole_height_m],['base',f.collision.base_radius_m,f.collision.base_height_m]]){
      const box=new THREE.Box3(new V(base.x-r,base.y,base.z-r),new V(base.x+r,base.y+h,base.z+r));
      box.label=`street lighting ${f.id} ${kind}`;
      box.segmentCapsule={a:base.clone(),b:base.clone(),radius:r};
      box.preciseVehicle=true;boxes.push(box);
    }
  }
  return boxes;
}

export function nearestFixtures(fixtures,position,maxCount=LIGHTING_LIMITS.realtimeLights,emitterOffset=[0,0,0]){
  return fixtures.map((f,index)=>({index,distance:position.distanceToSquared(new V(...emitterPosition(f,emitterOffset)))}))
    .filter(f=>f.distance<LIGHTING_LIMITS.nearDistance**2).sort((a,b)=>a.distance-b.distance||a.index-b.index)
    .slice(0,Math.max(0,Math.min(LIGHTING_LIMITS.realtimeLights,maxCount))).map(f=>f.index);
}

export function createGroundPools(fixtures){
  const vertices=fixtures.reduce((n,f)=>n+f.ground_patch_triangles.length*3,0);
  const p=new Float32Array(vertices*3),centers=new Float32Array(vertices*2),radii=new Float32Array(vertices),colors=new Float32Array(vertices*3);let cursor=0;const excluded=[];
  for(const f of fixtures){
    const center=fromBlender(f.target_position),color=fixtureColor(f.color);
    for(let triangleIndex=0;triangleIndex<f.ground_patch_triangles.length;triangleIndex++){
      const tri=f.ground_patch_triangles[triangleIndex],start=cursor;
      for(const point of tri){
        p.set([point[0],point[2]+.002,-point[1]],cursor*3);centers.set([center[0],center[2]],cursor*2);radii[cursor]=f.pool_radius;colors.set([color.r,color.g,color.b],cursor*3);cursor++;
      }
      // Cull only exact degeneracy after the same Float32 conversion uploaded
      // to WebGL. Positive finite source slivers remain in the bound contract.
      const a=new V().fromArray(p,start*3),b=new V().fromArray(p,(start+1)*3),c=new V().fromArray(p,(start+2)*3);
      if(b.sub(a).cross(c.sub(a)).lengthSq()===0){excluded.push({fixtureId:f.id,sourceTriangleIndex:triangleIndex,float32Triangle:Array.from(p.subarray(start*3,cursor*3))});cursor=start;}
    }
  }
  const geometry=new THREE.BufferGeometry();
  for(const [name,values,size] of [['position',p.subarray(0,cursor*3),3],['poolCenter',centers.subarray(0,cursor*2),2],['poolRadius',radii.subarray(0,cursor),1],['poolColor',colors.subarray(0,cursor*3),3]])geometry.setAttribute(name,new THREE.BufferAttribute(values,size));
  const material=new THREE.ShaderMaterial({transparent:true,depthWrite:false,depthTest:true,side:THREE.DoubleSide,blending:THREE.AdditiveBlending,toneMapped:true,
    uniforms:{strength:{value:0}},
    vertexShader:'attribute vec2 poolCenter; attribute float poolRadius; attribute vec3 poolColor; varying vec2 vOffset; varying vec3 vColor; void main(){vOffset=(position.xz-poolCenter)/poolRadius; vColor=poolColor; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader:'uniform float strength; varying vec2 vOffset; varying vec3 vColor; void main(){float falloff=max(0.0,1.0-dot(vOffset,vOffset)); gl_FragColor=vec4(vColor,strength*falloff*falloff);\n#include <tonemapping_fragment>\n#include <colorspace_fragment>\n}',
  });
  const mesh=new THREE.Mesh(geometry,material);mesh.name='RV6_RenderOnly_FiniteLightPools';mesh.userData.visual_only=true;mesh.userData.collision=false;mesh.userData.walkable_support=false;mesh.renderOrder=2;mesh.visible=false;mesh.userData.poolNormalization={sourceTriangles:vertices/3,renderedTriangles:cursor/3,excludedExactFloat32Degenerates:excluded};
  return mesh;
}

export function batchFixtures(root){
  root.updateMatrixWorld(true);const groups=new Map(),result=new THREE.Group();
  root.traverseVisible(o=>{if(!o.isMesh)return;
    const materials=Array.isArray(o.material)?o.material:[o.material];
    for(let i=0;i<materials.length;i++){
      const ranges=Array.isArray(o.material)?o.geometry.groups.filter(g=>g.materialIndex===i):[null];
      for(const group of ranges){
      const key=o.geometry.uuid+'|'+materials[i].uuid+'|'+(group?.start||0);
      if(!groups.has(key))groups.set(key,{geometry:o.geometry,material:materials[i],group,objects:[]});
      groups.get(key).objects.push(o);
      }
    }
  });
  for(const entry of groups.values()){
    let geometry=entry.geometry;
    if(entry.group){geometry=geometry.clone();if(geometry.index)geometry.setIndex(Array.from(geometry.index.array.slice(entry.group.start,entry.group.start+entry.group.count)));else geometry.setDrawRange(entry.group.start,entry.group.count);geometry.clearGroups();}
    const mesh=new THREE.InstancedMesh(geometry,entry.material,entry.objects.length);
    entry.objects.forEach((o,i)=>mesh.setMatrixAt(i,o.matrixWorld));mesh.instanceMatrix.needsUpdate=true;mesh.computeBoundingSphere();mesh.castShadow=false;mesh.receiveShadow=true;result.add(mesh);
  }
  return result;
}

export function createStreetLighting({scene,hemisphere,sun,renderer,mobileQuality=false,emitterOffset=[0,0,0]}){
  if(!finiteVector(emitterOffset))throw Error('Invalid native light emitter offset');
  emitterOffset=[...emitterOffset];
  let data=null,fixtureRoot=null,pools=null,time='day',detail=false,timer=Infinity,ready=false;
  const emissiveMaterials=new Set(),spots=[],selected=[];
  function applyTime(){
    const p=TIME_PRESETS[time];scene.background.set(p.sky);if(scene.fog)scene.fog.color.set(p.sky);
    hemisphere.color.set(p.hemiSky);hemisphere.groundColor.set(p.hemiGround);hemisphere.intensity=p.hemi;
    sun.color.set(p.sun);sun.intensity=p.sunIntensity;renderer.toneMappingExposure=p.exposure;
    for(const m of emissiveMaterials)m.emissiveIntensity=p.lamps;
    if(pools){pools.visible=time!=='day';pools.material.uniforms.strength.value=p.pools;}
    for(const light of spots)light.visible=detail&&time!=='day'&&light.userData.fixtureIndex!==undefined;
    timer=Infinity;
  }
  function setTime(next){if(!Object.hasOwn(TIME_PRESETS,next))throw Error('Unknown lighting time');time=next;applyTime();return time;}
  function setDetail(value){detail=value===true;if(detail&&!spots.length){
    for(let i=0;i<LIGHTING_LIMITS.realtimeLights;i++){
      const light=new THREE.SpotLight('#ffdfae',0,30,.8,.75,2);light.name=`RV6_NearLight_${i}`;light.castShadow=false;light.visible=false;scene.add(light,light.target);spots.push(light);
    }
  }applyTime();return detail;}
  function update(position,dt=0){
    if(!ready||!detail||time==='day')return;
    timer+=dt;if(timer<LIGHTING_LIMITS.refreshSeconds)return;timer=0;
    const nearest=nearestFixtures(data.fixtures,position,LIGHTING_LIMITS.realtimeLights,emitterOffset);selected.splice(0,selected.length,...nearest);
    spots.forEach((light,i)=>{
      const index=nearest[i];light.visible=index!==undefined;light.userData.fixtureIndex=index;
      if(index===undefined){light.intensity=0;return;}
      const f=data.fixtures[index],lamp=emitterPosition(f,emitterOffset),target=fromBlender(f.target_position),drop=Math.max(.5,lamp[1]-target[1]);
      light.position.set(...lamp);light.target.position.set(...target);light.color.copy(fixtureColor(f.color));light.intensity=f.intensity;
      light.angle=Math.min(1.25,Math.atan2(f.pool_radius,drop));light.distance=Math.hypot(drop,f.pool_radius)*1.5;light.target.updateMatrixWorld();
    });
  }
  async function load(loader,{contractUrl='./street-lighting.json',assetUrl='./assets/lighting.glb',fetcher=fetch}={}){
    if(ready)throw Error('Street lighting is already loaded');
    const response=await fetcher(contractUrl);if(!response.ok)throw Error(`Street-lighting contract HTTP ${response.status}`);
    const contract=validateLightingContract(await response.json());
    const asset=await loader.loadAsync(assetUrl),remove=[];
    asset.scene.traverse(o=>{if(o.isLight)remove.push(o);if(!o.isMesh)return;
      for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.name==='RV6_StreetLight_Emissive_Warm3000K'){if(!m.emissive)throw Error('Lamp diffuser has no emissive channel');emissiveMaterials.add(m);}
    });
    for(const light of remove)light.removeFromParent();
    if(!emissiveMaterials.size)throw Error('Emissive lamp material is missing');
    // Keep only compact fixture metadata after creating the GPU buffers; the
    // large finite-triangle JSON can be collected instead of staying in memory.
    data={...contract,fixtures:contract.fixtures.map(({ground_patch_triangles,ground_patch_provenance,...f})=>f)};fixtureRoot=batchFixtures(asset.scene);fixtureRoot.name='RV6_StreetLightingFixtures';
    fixtureRoot.traverse(o=>{if(o.isMesh){o.castShadow=false;o.receiveShadow=true;}});
    pools=createGroundPools(contract.fixtures);scene.add(fixtureRoot,pools);ready=true;applyTime();
    return fixtureCollisionBoxes(data.fixtures);
  }
  return {load,setTime,setDetail,update,get state(){return {ready,time,detail,mobileQuality,fixtures:data?.fixtures.length||0,fixtureBatches:fixtureRoot?.children.length||0,poolTriangles:pools?.geometry.attributes.position.count/3||0,excludedFloat32PoolTriangles:pools?.userData.poolNormalization.excludedExactFloat32Degenerates.length||0,realtimeLights:spots.filter(x=>x.visible).length,maxRealtimeLights:LIGHTING_LIMITS.realtimeLights,selectedIds:selected.map(i=>data.fixtures[i].id)};}};
}
