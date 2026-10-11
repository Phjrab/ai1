import {circleIntersectsPolygon,pointInPolygon} from './polygon-colliders.js';
function circleInsidePolygon(x,z,radius,polygon){
 if(!pointInPolygon(x,z,polygon))return false;
 for(let i=0;i<polygon.length;i++){const a=polygon[i],b=polygon[(i+1)%polygon.length],dx=b[0]-a[0],dz=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz||1)));if(Math.hypot(x-a[0]-t*dx,z-a[1]-t*dz)<radius-1e-5)return false;}
 return true;
}
// These are navigation hazards, not visible walls or camera occluders. The
// bridge exception requires both its bounded footprint and actual deck support.
export function createWaterConstraint(world,supportHeight){
 const zones=world.waterHazards||[];
 return (position,radius=.34,mode='pedestrian')=>zones.some(zone=>{
  if(!circleIntersectsPolygon(position.x,position.z,radius,zone.polygon))return false;
  const support=supportHeight(position.x,position.z,position.y+.55);
  if(mode!=='pedestrian'||support===null)return true;
  return !(zone.exceptions||[]).some(exception=>exception.mode==='pedestrian'&&support>=exception.minY&&support<=exception.maxY&&Math.abs(position.y-support)<=.56&&circleInsidePolygon(position.x,position.z,radius,exception.polygon));
 });
}
