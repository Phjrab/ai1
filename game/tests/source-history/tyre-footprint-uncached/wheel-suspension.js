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

export function createWheelSuspension(octree,group,wheels,{maxTravel=.24,clearance=.002,refineTyreFaces=false}={}){
 group.updateMatrixWorld(true);
 const records=wheels.map(wheel=>{const inverse=wheel.matrixWorld.clone().invert(),points=new Map();wheel.traverse(mesh=>{if(!mesh.isMesh)return;const matrix=inverse.clone().multiply(mesh.matrixWorld),p=mesh.geometry.attributes.position;for(let i=0;i<p.count;i++){const v=new Vector3().fromBufferAttribute(p,i).applyMatrix4(matrix);points.set(v.toArray().map(x=>x.toFixed(6)).join(','),v);}});const tyre=wheel.children.filter(o=>o.isMesh&&o.geometry.type==='CylinderGeometry').sort((a,b)=>b.geometry.parameters.radiusTop-a.geometry.parameters.radiusTop)[0],fine=refineTyreFaces&&tyre?tyreContactProfile(tyre).fineVertices:[];return {wheel,baseY:wheel.position.y,vertices:[...points.values()],fineVertices:fine};});
 const groundCache=localGroundTriangles(octree),point=new Vector3(),up=new Vector3();
 const fit=()=>{
  for(const record of records)record.wheel.position.y=record.baseY;
  group.updateMatrixWorld(true);const ground=groundCache(group.position);up.set(0,1,0).transformDirection(group.matrixWorld);const diagnostics=[];
  for(const record of records){
   let offset=0,requested=0,gap=Infinity,samples=0;
   const minimum=()=>{let result=Infinity,low=Infinity,high=-Infinity;const pivot=record.wheel.getWorldPosition(new Vector3()),measure=vertex=>{point.copy(vertex).applyMatrix4(record.wheel.matrixWorld);if(point.y>pivot.y+.02)return;const height=ground(point,maxTravel+.15,1.5);samples++;if(height!==null){result=Math.min(result,point.y-height);low=Math.min(low,height);high=Math.max(high,height);}};for(const vertex of record.vertices)measure(vertex);if(high-low>maxTravel&&record.fineVertices.length)for(const vertex of record.fineVertices)measure(vertex);return result;};
   for(let iteration=0;iteration<3;iteration++){gap=minimum();if(!Number.isFinite(gap))break;requested=offset+(clearance-gap)/Math.max(.6,up.y);const next=Math.max(-maxTravel,Math.min(maxTravel,requested));record.wheel.position.y=record.baseY+next;record.wheel.updateMatrixWorld(true);offset=next;if(Math.abs(gap-clearance)<.0005)break;}
   gap=minimum();diagnostics.push({wheel:record.wheel.name,offset,requestedOffset:requested,residualGap:gap,limited:Math.abs(requested)>maxTravel+1e-6,missing:!Number.isFinite(gap),samples});
  }
  fit.last={maxTravel,clearance,wheels:diagnostics};return fit.last;
 };
 fit.records=records;fit.last=null;return fit;
}

// Uses only vertices on the authored tyre's lower half. Subtracting each
// vertex's real arc height prevents treating the tyre bounding box as a flat foot.
export function tyreContactProfile(tyre){
 tyre.updateMatrix();const attribute=tyre.geometry.attributes.position,index=tyre.geometry.index,points=new Map(),fine=new Map(),center=new Vector3().applyMatrix4(tyre.matrix);let minimum=Infinity;
 const keep=(map,p)=>{if(p.y<=center.y+1e-8)map.set(p.toArray().map(v=>v.toFixed(9)).join(','),p);};
 for(let i=0;i<attribute.count;i++){const p=new Vector3().fromBufferAttribute(attribute,i).applyMatrix4(tyre.matrix);if(p.y>center.y+1e-8)continue;minimum=Math.min(minimum,p.y);keep(points,p);}
 // Four equal subdivisions remain exactly on the existing triangle faces.
 for(let i=0;i<(index?.count??attribute.count);i+=3){const p=[0,1,2].map(j=>new Vector3().fromBufferAttribute(attribute,index?index.getX(i+j):i+j).applyMatrix4(tyre.matrix));for(let u=0;u<=4;u++)for(let v=0;v<=4-u;v++)keep(fine,p[0].clone().multiplyScalar(1-(u+v)/4).addScaledVector(p[1],u/4).addScaledVector(p[2],v/4));}
 const convert=p=>({x:p.x,z:p.z,arcHeight:p.y-minimum}),profile=[...points.values()].map(convert);profile.fine=[...fine.values()].map(convert);profile.fineVertices=[...fine.values()];return profile;
}
export function tyreContactHeight(sample,x,z,from,c,s,profile){
 const measure=p=>{const height=sample(x+c*p.x+s*p.z,z-s*p.x+c*p.z,from);return {...p,height,equivalentHeight:height===null?null:height-p.arcHeight};},contacts=(profile||[{x:0,z:0,arcHeight:0}]).map(measure);
 const raw=contacts.map(p=>p.height).filter(Number.isFinite);if(profile?.fine&&Math.max(...raw)-Math.min(...raw)>.12)contacts.push(...profile.fine.map(measure));
 const heights=contacts.map(p=>p.equivalentHeight).filter(Number.isFinite);return {height:heights.length?Math.max(...heights):null,contacts};
}
