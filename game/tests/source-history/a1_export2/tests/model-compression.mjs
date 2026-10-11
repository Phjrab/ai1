import assert from 'node:assert/strict';
import {Document,NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {MeshoptEncoder,MeshoptDecoder} from 'meshoptimizer';
import {compressModel} from '../scripts/model-compression.mjs';
import {installCPUImageMetadata} from '../scripts/gltf-cpu-images.mjs';
import {GLTFLoader} from '../dist/vendor/addons/loaders/GLTFLoader.js';
await Promise.all([MeshoptEncoder.ready,MeshoptDecoder.ready]);
const doc=new Document(),buffer=doc.createBuffer(),scene=doc.createScene(),input=new Float32Array([-123.082729,-38.681461,248.440175,-123.106233,-38.681461,248.424142,-123.034610,-38.681461,248.554894,450,45,-800,451,45,-800,450,45,-799]);
const expected=new Map();
function add(name,extras,offset=0){const points=input.map((v,i)=>v+(i%3===0?offset:0));expected.set(name,points);const position=doc.createAccessor().setType('VEC3').setArray(points).setBuffer(buffer),primitive=doc.createPrimitive().setAttribute('POSITION',position),mesh=doc.createMesh(name).addPrimitive(primitive),node=doc.createNode(name).setMesh(mesh).setTranslation([2,3,4]).setExtras(extras);scene.addChild(node);return node;}
const inferred=add('INFERRED_GAME_WALK_CONNECTORS | precision regression',{}),tagged=add('semantic walk top',{walkable_support:true},.125),ordinary=add('ordinary wall',{},1),car=add('CAMPUS_CAR 000',{},2),tree=add('CAMPUS_TREE RV2_INFILL example',{tree_trunk:true},3),matrices=[...inferred.getMatrix(),...tagged.getMatrix(),...car.getMatrix(),...tree.getMatrix()];
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZxL8AAAAASUVORK5CYII=','base64'),texture=doc.createTexture('paver fixture').setImage(png).setMimeType('image/png'),material=doc.createMaterial('textured paver fixture').setBaseColorTexture(texture),uvExpected=new Map();
for(const [node,uv] of [[inferred,new Float32Array([.1,.2,.3,.4,.5,.6,.7,.8,.9,1,0,.1])],[tagged,new Float32Array([-.125,3.75,.03125,5.125,8.875,12.5,20.25,0,.875,45.5,80.25,36.125])]]){
 const primitive=node.getMesh().listPrimitives()[0],positions=expected.get(node.getName()),pairs=new Map();
 for(let i=0;i<positions.length/3;i++)pairs.set(Array.from(positions.slice(i*3,i*3+3)).join(','),Array.from(uv.slice(i*2,i*2+2)));
 uvExpected.set(node.getName(),pairs);primitive.setMaterial(material).setAttribute('TEXCOORD_0',doc.createAccessor().setType('VEC2').setArray(uv).setBuffer(buffer));
}
add('explicit vehicle top',{RV2_vehicle_surface:true},4);add('excluded vehicle slope',{RV2_no_vehicle:true},5);
const protectedMeshes=await compressModel(doc,MeshoptEncoder);assert.equal(protectedMeshes.length,6);assert.deepEqual([...inferred.getMatrix(),...tagged.getMatrix(),...car.getMatrix(),...tree.getMatrix()],matrices);assert.notEqual(ordinary.getMesh().listPrimitives()[0].getAttribute('POSITION').getComponentType(),5126,'Ordinary geometry still uses 16-bit positions');
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.encoder':MeshoptEncoder,'meshopt.decoder':MeshoptDecoder}),roundtrip=await io.readBinary(await io.writeBinary(doc));
const vertices=a=>Array.from({length:a.length/3},(_,i)=>Array.from(a.slice(i*3,i*3+3)).join(',')).sort();
for(const name of protectedMeshes){const mesh=roundtrip.getRoot().listMeshes().find(m=>m.getName()===name),primitive=mesh.listPrimitives()[0],position=primitive.getAttribute('POSITION');assert.equal(position.getComponentType(),5126);assert.equal(primitive.getAttribute('_SOURCE_POSITION'),null);assert.deepEqual(vertices(position.getArray()),vertices(expected.get(name)),'Every support coordinate survives the encoded GLB exactly');const uv=primitive.getAttribute('TEXCOORD_0');if(!uvExpected.has(name))continue;for(let i=0;i<position.getCount();i++){const reference=uvExpected.get(name).get(position.getElement(i,[]).join(',')),actual=uv.getElement(i,[]);assert.ok(actual.every((value,j)=>Math.abs(value-reference[j])<=1/4095+.000001),'Paver UV error must stay below 0.4 mm for a 1.6 m tile');}}
assert.deepEqual(Buffer.from(roundtrip.getRoot().listTextures()[0].getImage()),png,'Embedded texture bytes survive compression');
console.log('MODEL_COMPRESSION: protected Float32 support and authored tree/car origins survive Meshopt roundtrip exactly; other meshes retain 16-bit quantization');
console.log('MODEL_COMPRESSION: embedded paver texture retained; repeated and normalized UV coordinates remain within sub-millimetre tolerance');
installCPUImageMetadata();
const encoded=await io.writeBinary(doc),loaded=await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(encoded.buffer.slice(encoded.byteOffset,encoded.byteOffset+encoded.byteLength),'');let textured=0;
loaded.scene.traverse(o=>{if(o.isMesh&&o.material.map){assert.equal(o.material.map.image.width,1);assert.equal(o.material.map.image.height,1);assert.equal(o.material.map.image.cpuMetadataOnly,true);textured++;}});
assert.equal(textured,2);console.log('CPU_GLTF_PNG: Three texture bindings load with PNG dimensions; pixel/GPU rendering remains unverified');
