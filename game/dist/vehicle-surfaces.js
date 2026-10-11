import {rectangleIntersectsPolygon} from './polygon-colliders.js';
import {Vector3} from 'three';
import {isCollisionDisabled} from './revision-colliders.js';

export function createVehicleSurfaceRules(world){
 const grid=new Map(),cell=8,attached=new WeakSet(),covered=new Set((world.vehicleSurfaceRules||[]).filter(r=>r.mode==='exclude').map(r=>r.object));
 function add(r){
  const p=r.polygon,xs=p.map(v=>v[0]),zs=p.map(v=>v[2]),ys=p.map(v=>v[1]);
  const record={...r,xz:p.map(v=>[v[0],v[2]]),minY:Math.min(...ys),maxY:Math.max(...ys)};
  for(let x=Math.floor(Math.min(...xs)/cell);x<=Math.floor(Math.max(...xs)/cell);x++)for(let z=Math.floor(Math.min(...zs)/cell);z<=Math.floor(Math.max(...zs)/cell);z++){
   const key=x+':'+z;if(!grid.has(key))grid.set(key,[]);grid.get(key).push(record);
  }
 }
 for(const r of world.vehicleSurfaceRules||[])add(r);
 function nearby(p,radius=0){const out=new Set();for(let x=Math.floor((p.x-radius)/cell);x<=Math.floor((p.x+radius)/cell);x++)for(let z=Math.floor((p.z-radius)/cell);z<=Math.floor((p.z+radius)/cell);z++)for(const r of grid.get(x+':'+z)||[])out.add(r);return out;}
 return {
  attach(root){
   root.updateMatrixWorld(true);let objects=0,triangles=0;
   root.traverse(object=>{
    if(!object.isMesh||attached.has(object)||isCollisionDisabled(object))return;
    let tagged=null;for(let node=object;node;node=node.parent)if(node.userData?.RV2_no_vehicle===true){tagged=node;break;}
    if(!tagged)return;const name=tagged.userData?.name||tagged.name;if(covered.has(name))return;
    const p=object.geometry.attributes.position,index=object.geometry.index,points=[new Vector3(),new Vector3(),new Vector3()];let count=0;
    for(let i=0;i<(index?.count??p.count);i+=3){
     for(let j=0;j<3;j++)points[j].fromBufferAttribute(p,index?index.getX(i+j):i+j).applyMatrix4(object.matrixWorld);
     const [a,b,c]=points,area=(b.z-a.z)*(c.x-a.x)-(b.x-a.x)*(c.z-a.z);if(Math.abs(area)<1e-8)continue;
     add({object:name,mode:'exclude',polygon:points.map(p=>p.toArray())});count++;
    }
    if(count){objects++;triangles+=count;attached.add(object);}
   });return {objects,triangles};
  },
  allows(point){for(const r of nearby(point)){
   if(r.mode!=='allow')continue;const [a,b,c]=r.polygon,den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2]);if(Math.abs(den)<1e-10)continue;
   const u=((b[2]-c[2])*(point.x-c[0])+(c[0]-b[0])*(point.z-c[2]))/den,v=((c[2]-a[2])*(point.x-c[0])+(a[0]-c[0])*(point.z-c[2]))/den;
   if(u>=-1e-6&&v>=-1e-6&&u+v<=1.000001&&Math.abs(point.y-(u*a[1]+v*b[1]+(1-u-v)*c[1]))<.6)return true;
  }return false;},
  blocks(point,yaw){for(const r of nearby(point,2.6))if(r.mode==='exclude'&&point.y>=r.minY-.6&&point.y<=r.maxY+.6&&rectangleIntersectsPolygon(point,yaw,2.28,4.38,r.xz))return true;return false;}
 };
}
