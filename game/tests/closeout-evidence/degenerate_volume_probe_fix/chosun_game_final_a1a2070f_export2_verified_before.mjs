import {Box3,Triangle,Vector3,Ray} from 'three';
import {isParkingStaticCar,isParkingDriveSurface} from '../../dist/parking-system.js';
export function componentIntersectsTriangle(box,triangle,geometry){
 if(!box.intersectsTriangle(triangle))return false;
 if(geometry.type!=='CylinderGeometry')return true;
 // The wheel's local AABB has square corners outside its actual tyre. Refine
 // against its authored convex polygon before classifying road contact as a
 // solid penetration. This also handles the rotated alloy hub cylinders.
 const {radiusTop,radiusBottom,height,radialSegments=8}=geometry.parameters;if(radiusTop!==radiusBottom)return true;
 let polygon=[triangle.a.clone(),triangle.b.clone(),triangle.c.clone()];
 const planes=[[new Vector3(0,1,0),height/2],[new Vector3(0,-1,0),height/2]];
 for(let i=0;i<radialSegments;i++){const angle=(i+.5)*Math.PI*2/radialSegments;planes.push([new Vector3(Math.sin(angle),0,Math.cos(angle)),radiusTop*Math.cos(Math.PI/radialSegments)]);}
 for(const [normal,d] of planes){const next=[];for(let i=0;i<polygon.length;i++){const a=polygon[i],b=polygon[(i+1)%polygon.length],da=normal.dot(a)-d,db=normal.dot(b)-d;if(da<=1e-7)next.push(a);if((da<0)!==(db<0))next.push(a.clone().lerp(b,da/(da-db)));}polygon=next;if(!polygon.length)return false;}
 return true;
}
export function parkingVolumeProbe(scene,include=o=>!isParkingDriveSurface(o)&&(/CAMPUS_BUILDING_164|CAMPUS_PARKING164/.test(o.name+' '+o.parent?.name)||isParkingStaticCar(o)),includeTriangle=()=>true,includeHeight=()=>true){
 scene.updateMatrixWorld(true);const grid=new Map(),cell=8,triangles=[];
 scene.traverse(o=>{if(!o.isMesh||!include(o))return;const p=o.geometry.attributes.position,index=o.geometry.index,vertices=[new Vector3(),new Vector3(),new Vector3()],bounds=new Box3();for(let i=0;i<(index?.count??p.count);i+=3){for(let j=0;j<3;j++)vertices[j].fromBufferAttribute(p,index?index.getX(i+j):i+j).applyMatrix4(o.matrixWorld);bounds.setFromPoints(vertices);if(includeTriangle(bounds,o))triangles.push({triangle:new Triangle(...vertices.map(v=>v.clone())),bounds:bounds.clone(),name:o.name,support:includeHeight(o)});}});
 for(const r of triangles){const b=r.bounds;for(let x=Math.floor(b.min.x/cell);x<=Math.floor(b.max.x/cell);x++)for(let y=Math.floor(b.min.y/4);y<=Math.floor(b.max.y/4);y++)for(let z=Math.floor(b.min.z/cell);z<=Math.floor(b.max.z/cell);z++){const key=x+':'+y+':'+z;if(!grid.has(key))grid.set(key,[]);grid.get(key).push(r);}}
 function nearby(b){const out=new Set();for(let x=Math.floor(b.min.x/cell);x<=Math.floor(b.max.x/cell);x++)for(let y=Math.floor(b.min.y/4);y<=Math.floor(b.max.y/4);y++)for(let z=Math.floor(b.min.z/cell);z<=Math.floor(b.max.z/cell);z++)for(const r of grid.get(x+':'+y+':'+z)||[])out.add(r);return out;}
 const probe=(car,includeComponent=()=>true)=>{car.updateMatrixWorld(true);const hits=new Set();car.traverse(o=>{if(!o.isMesh||!includeComponent(o))return;o.geometry.computeBoundingBox();const box=o.geometry.boundingBox,world=box.clone().applyMatrix4(o.matrixWorld),inverse=o.matrixWorld.clone().invert();for(const r of nearby(world)){if(!world.intersectsBox(r.bounds))continue;const tr=r.triangle.clone();tr.a.applyMatrix4(inverse);tr.b.applyMatrix4(inverse);tr.c.applyMatrix4(inverse);if(componentIntersectsTriangle(box,tr,o.geometry))hits.add(r.name);}});return [...hits];};
 // Independent rendered-triangle support. No WORLD navigation support mesh is
 // present in this capture, so stale invisible metadata cannot make it pass.
 probe.support=(x,z,from,depth=3)=>{const ray=new Ray(new Vector3(x,from,z),new Vector3(0,-1,0)),point=new Vector3(),bounds=new Box3(new Vector3(x-1e-5,from-depth,z-1e-5),new Vector3(x+1e-5,from,z+1e-5));let result=null;for(const r of nearby(bounds))if(r.support&&ray.intersectTriangle(r.triangle.a,r.triangle.b,r.triangle.c,false,point)&&point.y>=from-depth&&point.y<=from&&(!result||point.y>result.height))result={height:point.y,object:r.name};return result;};
 probe.height=(...args)=>probe.support(...args)?.height??null;
 return probe;
}
