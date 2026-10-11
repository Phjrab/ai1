import assert from 'node:assert/strict';
import {Mesh,BufferGeometry,Float32BufferAttribute,MeshBasicMaterial,DoubleSide,Raycaster,Vector3} from 'three';
import {visibleFloorIndex} from './helpers/visible-floor-index.mjs';
const material=new MeshBasicMaterial({side:DoubleSide}),meshes=[];
for(let y of [0,3,8]){const geometry=new BufferGeometry().setAttribute('position',new Float32BufferAttribute([-3,y,-3,3,y,-3,-3,y,3,3,y,-3,3,y,3,-3,y,3],3)),m=new Mesh(geometry,material);m.rotation.z=.1;m.scale.set(1.2,.9,1.1);m.updateMatrixWorld(true);m.name='level'+y;meshes.push(m);}
const index=visibleFloorIndex(meshes),ray=new Raycaster(),direction=new Vector3(0,-1,0);let samples=0;for(let x=-4.1;x<4;x+=.23)for(let z=-4.1;z<4;z+=.23)for(let from of [1,3.5,7,10]){ray.set(new Vector3(x,from,z),direction);ray.far=1.1;const hit=ray.intersectObjects(meshes,false)[0],actual=index.query(x,z,from);assert.equal(!!actual,!!hit);if(hit)assert.ok(Math.abs(actual.height-hit.point.y)<1e-8);samples++;}
const sliver=new Mesh(new BufferGeometry().setAttribute('position',new Float32BufferAttribute([250,-40,350,249.389633,-40,350.61035,249.389648,-40,350.61035],3)),material);sliver.updateMatrixWorld(true);assert.equal(visibleFloorIndex([sliver]).query(255,345,-39,2),null);console.log('PASS compact visible-floor index matches actual rendered triangle rays for '+samples+' transformed/stacked/gap poses and rejects the far sliver.');

const near=index.query(3.000001,0,1,3,{edgeTolerance:.0001});
const cap=new Mesh(new BufferGeometry().setAttribute('position',new Float32BufferAttribute([-1,.4,-1,1,.4,-1,-1,.4,1],3)),material);cap.updateMatrixWorld(true);cap.name='closed_wall_lower_cap';
const floor=new Mesh(new BufferGeometry().setAttribute('position',new Float32BufferAttribute([-1,0,-1,-1,0,1,1,0,-1],3)),material);floor.updateMatrixWorld(true);floor.name='floor';
const layers=visibleFloorIndex([cap,floor]);assert.equal(layers.query(-.2,-.2,.55).sourceName,cap.name);assert.equal(layers.query(-.2,-.2,.55,1.1,{accept:h=>h.normalY>.1}).height,0);
const exact=visibleFloorIndex([floor]);assert.equal(exact.query(-1.000003,-.2,.55),null);assert.ok(exact.query(-1.000003,-.2,.55,1.1,{edgeTolerance:.0001}).edgeDistance<.000004);assert.equal(exact.query(-1.001,-.2,.55,1.1,{edgeTolerance:.0001}),null);console.log('PASS downward solid cap separated from actual floor; 3 micron boundary accepted, 1 mm real gap rejected.');
