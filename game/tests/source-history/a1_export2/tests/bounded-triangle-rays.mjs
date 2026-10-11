import assert from 'node:assert/strict';
import {Box3,Vector3,Triangle,Ray} from 'three';
import {Octree} from '../dist/vendor/addons/math/Octree.js';
import {boundedDownRays} from './helpers/bounded-triangle-rays.mjs';
const tree=new Octree();for(const y of [0,3,9])for(let x=-10;x<10;x++)for(let z=-10;z<10;z++){if(x===2&&z===2)continue;const a=new Vector3(x,y+x*.1,z),b=new Vector3(x,y+x*.1,z+1),c=new Vector3(x+1,y+(x+1)*.1,z),d=new Vector3(x+1,y+(x+1)*.1,z+1);tree.addTriangle(new Triangle(a,b,c));tree.addTriangle(new Triangle(c,b,d));}tree.build();let count=0;
for(let k=0;k<20;k++){const x=-8+k*.7,bounds=new Box3(new Vector3(x,-1,-3),new Vector3(x+.8,4,3)),query=boundedDownRays(tree,bounds),ray=new Ray(new Vector3(),new Vector3(0,-1,0));for(let a=0;a<=8;a++)for(let b=0;b<=60;b++)for(const y of [1,2.8,4]){const px=x+a*.1,pz=-3+b*.1;ray.origin.set(px,y,pz);const hit=tree.rayIntersect(ray),expected=hit&&hit.position.y>=bounds.min.y-1e-7?hit.position.y:null,actual=query(px,pz,y);assert.ok(actual===expected||actual!==null&&expected!==null&&Math.abs(actual-expected)<1e-9);count++;}}
console.log('PASS exact bounded tyre rays match full Octree at '+count+' stacked/sloped/boundary/hole samples');
