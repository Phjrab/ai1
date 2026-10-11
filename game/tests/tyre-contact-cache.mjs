import assert from 'node:assert/strict';
import {Triangle,Vector3,Ray} from 'three';
import {Octree} from '../dist/vendor/addons/math/Octree.js';
import {createTyreContactSampler} from '../dist/wheel-suspension.js';
const tree=new Octree();
for(let x=-12;x<12;x++)for(let z=-12;z<12;z++)for(const base of [-85,-4,0,3]){if(base===3&&x>1)continue;const y=(x,z)=>base+.13*x-.05*z,p=[[x,y(x,z),z],[x+1,y(x+1,z),z],[x+1,y(x+1,z+1),z+1],[x,y(x,z+1),z+1]].map(v=>new Vector3(...v));tree.addTriangle(new Triangle(p[0],p[2],p[1]));tree.addTriangle(new Triangle(p[0],p[3],p[2]));}tree.build();
const sampler=createTyreContactSampler(tree),ray=new Ray(new Vector3(),new Vector3(0,-1,0));let count=0;
for(let i=0;i<10000;i++){const x=10*Math.sin(i*.191),z=10*Math.cos(i*.137),from=[-86,-3,.6,3.6,76][i%5]+.13*x-.05*z;ray.origin.set(x,from,z);const h=tree.rayIntersect(ray),expected=h&&h.distance<70?h.position.y:null,actual=sampler(new Vector3(x,0,z))(x,z,from);assert.equal(actual,expected);count++;}
for(const [x,z,from] of [[0,0,.55],[1,1,3.6],[1.00000001,1,3.6],[30,30,0],[0,0,100]]){ray.origin.set(x,from,z);const h=tree.rayIntersect(ray),expected=h&&h.distance<70?h.position.y:null;assert.equal(sampler(new Vector3(x,0,z))(x,z,from),expected);count++;}
console.log('TYRE_CONTACT_CACHE PASS',JSON.stringify({rays:count,exactHeightEquality:true,geometryChanged:false,originalBackfaceAnd70mDepth:true,layersAndOutside:true}));
