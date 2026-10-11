import {Box3,Ray,Vector3} from 'three';

// A small exact-triangle cache follows one vehicle. It does not resample the
// road or replace its height with a fitted plane.
export function localGroundTriangles(octree){
 let previous='',grid=new Map();const ray=new Ray(new Vector3(),new Vector3(0,-1,0)),hit=new Vector3();
 return (center)=>{
  const key=[Math.floor(center.x/4),Math.floor(center.y/2),Math.floor(center.z/4)].join(':');
  if(key!==previous){
   previous=key;grid=new Map();const anchor=new Vector3(Math.floor(center.x/4)*4+2,Math.floor(center.y/2)*2+1,Math.floor(center.z/4)*4+2),bounds=new Box3(anchor.clone().add(new Vector3(-11,-5,-11)),anchor.clone().add(new Vector3(11,5,11))),found=new Set();
   const visit=node=>{if(node.box&&!node.box.intersectsBox(bounds))return;for(const triangle of node.triangles||[])found.add(triangle);for(const child of node.subTrees||[])visit(child);};visit(octree);
   for(const triangle of found){const points=[triangle.a,triangle.b,triangle.c],normal=triangle.getNormal(new Vector3());if(normal.y<=.15)continue;
    const x0=Math.max(Math.floor(bounds.min.x),Math.floor(Math.min(...points.map(p=>p.x))-1e-6)),x1=Math.min(Math.floor(bounds.max.x),Math.floor(Math.max(...points.map(p=>p.x))+1e-6)),z0=Math.max(Math.floor(bounds.min.z),Math.floor(Math.min(...points.map(p=>p.z))-1e-6)),z1=Math.min(Math.floor(bounds.max.z),Math.floor(Math.max(...points.map(p=>p.z))+1e-6));
    for(let x=x0;x<=x1;x++)for(let z=z0;z<=z1;z++){const cell=x+':'+z;if(!grid.has(cell))grid.set(cell,[]);grid.get(cell).push(triangle);}
   }
  }
  return (point,rise=.35,depth=1.5)=>{ray.origin.copy(point).y+=rise;let highest=null;for(const triangle of grid.get(Math.floor(point.x)+':'+Math.floor(point.z))||[])if(ray.intersectTriangle(triangle.a,triangle.b,triangle.c,true,hit)&&hit.y>=point.y-depth&&(highest===null||hit.y>highest))highest=hit.y;return highest;};
 };
}

export function createWheelSuspension(octree,group,wheels,{maxTravel=.24,clearance=.002}={}){
 group.updateMatrixWorld(true);
 const records=wheels.map(wheel=>{const inverse=wheel.matrixWorld.clone().invert(),points=new Map();wheel.traverse(mesh=>{if(!mesh.isMesh)return;const matrix=inverse.clone().multiply(mesh.matrixWorld),p=mesh.geometry.attributes.position;for(let i=0;i<p.count;i++){const v=new Vector3().fromBufferAttribute(p,i).applyMatrix4(matrix);points.set(v.toArray().map(x=>x.toFixed(6)).join(','),v);}});return {wheel,baseY:wheel.position.y,vertices:[...points.values()]};});
 const groundCache=localGroundTriangles(octree),point=new Vector3(),up=new Vector3();
 const fit=()=>{
  for(const record of records)record.wheel.position.y=record.baseY;
  group.updateMatrixWorld(true);const ground=groundCache(group.position);up.set(0,1,0).transformDirection(group.matrixWorld);const diagnostics=[];
  for(const record of records){
   let offset=0,requested=0,gap=Infinity,samples=0;
   const minimum=()=>{let result=Infinity;const pivot=record.wheel.getWorldPosition(new Vector3());for(const vertex of record.vertices){point.copy(vertex).applyMatrix4(record.wheel.matrixWorld);if(point.y>pivot.y+.02)continue;const height=ground(point,maxTravel+.15,1.5);samples++;if(height!==null)result=Math.min(result,point.y-height);}return result;};
   for(let iteration=0;iteration<3;iteration++){gap=minimum();if(!Number.isFinite(gap))break;requested=offset+(clearance-gap)/Math.max(.6,up.y);const next=Math.max(-maxTravel,Math.min(maxTravel,requested));record.wheel.position.y=record.baseY+next;record.wheel.updateMatrixWorld(true);offset=next;if(Math.abs(gap-clearance)<.0005)break;}
   gap=minimum();diagnostics.push({wheel:record.wheel.name,offset,requestedOffset:requested,residualGap:gap,limited:Math.abs(requested)>maxTravel+1e-6,missing:!Number.isFinite(gap),samples});
  }
  fit.last={maxTravel,clearance,wheels:diagnostics};return fit.last;
 };
 fit.records=records;fit.last=null;return fit;
}
