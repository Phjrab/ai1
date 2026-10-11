import assert from 'node:assert/strict';
import {Group,Mesh,CylinderGeometry,MeshBasicMaterial,Triangle,Vector3} from 'three';
import {Octree} from '../dist/vendor/addons/math/Octree.js';
import {createWheelSuspension} from '../dist/wheel-suspension.js';
function fixture(heights){const octree=new Octree(),group=new Group(),wheels=[];for(const [i,[x,z]] of [[-1.205,-3.24],[1.205,-3.24],[-1.205,3.16],[1.205,3.16]].entries()){
 const wheel=new Group();wheel.name='wheel_'+i;wheel.position.set(x,.51,z);const mesh=new Mesh(new CylinderGeometry(.51,.51,.25,32).rotateZ(Math.PI/2),new MeshBasicMaterial());wheel.add(mesh);group.add(wheel);wheels.push(wheel);
 for(const y of [heights[i],3]){const p=[[x-.7,y,z-.8],[x+.7,y,z-.8],[x+.7,y,z+.8],[x-.7,y,z+.8]].map(v=>new Vector3(...v));octree.addTriangle(new Triangle(p[0],p[2],p[1]));octree.addTriangle(new Triangle(p[0],p[3],p[2]));}}
 octree.build();group.updateMatrixWorld(true);return {octree,group,wheels};}
for(const heights of [[0,0,0,0],[.09,-.09,-.09,.09]]){
 const {octree,group,wheels}=fixture(heights),pose=group.matrixWorld.toArray(),assemblies=wheels.map(w=>w.children[0].matrix.toArray()),fit=createWheelSuspension(octree,group,wheels),result=fit();
 for(const [i,w] of result.wheels.entries()){assert.ok(!w.missing&&!w.limited);assert.ok(Math.abs(w.residualGap-.002)<.0006);assert.ok(Math.abs(w.offset-(heights[i]+.002))<.0006);assert.deepEqual(wheels[i].children[0].matrix.toArray(),assemblies[i]);}
 assert.deepEqual(group.matrixWorld.toArray(),pose);const again=fit();assert.deepEqual(again,result);
}
const {octree,group,wheels}=fixture([.3,0,0,0]),fit=createWheelSuspension(octree,group,wheels),r=fit();assert.equal(r.wheels[0].offset,.24);assert.equal(r.wheels[0].limited,true);
console.log('PASS: exact wheel contact, bounded independent travel, full assembly preservation, unchanged chassis, overhead deck rejection and repeatability.');
