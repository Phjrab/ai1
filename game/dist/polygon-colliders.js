import {Box3,Vector3} from 'three';

export function pointInPolygon(x,z,polygon){
 let inside=false;
 for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){
  const a=polygon[j],b=polygon[i],dx=b[0]-a[0],dz=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz||1)));
  if(Math.hypot(x-a[0]-t*dx,z-a[1]-t*dz)<1e-8)return true;
  if((a[1]>z)!==(b[1]>z)&&x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0])inside=!inside;
 }
 return inside;
}
export function circleIntersectsPolygon(x,z,radius,polygon){
 if(pointInPolygon(x,z,polygon))return true;
 for(let i=0;i<polygon.length;i++){const a=polygon[i],b=polygon[(i+1)%polygon.length],dx=b[0]-a[0],dz=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz||1)));if(Math.hypot(x-a[0]-t*dx,z-a[1]-t*dz)<radius)return true;}
 return false;
}
function intersection(a,u,b,v){const cross=u[0]*v[1]-u[1]*v[0];if(Math.abs(cross)<1e-12)return null;const dx=b[0]-a[0],dz=b[1]-a[1];return[(dx*v[1]-dz*v[0])/cross,(dx*u[1]-dz*u[0])/cross];}
export function rectangleIntersectsPolygon(position,yaw,width,length,polygon){
 const c=Math.cos(yaw),s=Math.sin(yaw),corners=[[-1,-1],[1,-1],[1,1],[-1,1]].map(([x,z])=>[position.x+x*width/2*c+z*length/2*s,position.z-x*width/2*s+z*length/2*c]);
 if(corners.some(p=>pointInPolygon(...p,polygon))||polygon.some(p=>pointInPolygon(...p,corners)))return true;
 for(let i=0;i<4;i++)for(let j=0;j<polygon.length;j++){
  const a=corners[i],b=corners[(i+1)%4],p=polygon[j],q=polygon[(j+1)%polygon.length],hit=intersection(a,[b[0]-a[0],b[1]-a[1]],p,[q[0]-p[0],q[1]-p[1]]);
  if(hit&&hit[0]>=0&&hit[0]<=1&&hit[1]>=0&&hit[1]<=1)return true;
 }
 return false;
}
export function polygonRayDistance(ray,box){
 const p=ray.origin,d=ray.direction,polygon=box.polygon;let nearest=Infinity;
 if(p.y>=box.min.y&&p.y<=box.max.y&&pointInPolygon(p.x,p.z,polygon))return 0;
 if(Math.abs(d.y)>1e-12)for(const y of [box.min.y,box.max.y]){const t=(y-p.y)/d.y;if(t>=0&&pointInPolygon(p.x+d.x*t,p.z+d.z*t,polygon))nearest=Math.min(nearest,t);}
 for(let i=0;i<polygon.length;i++){const a=polygon[i],b=polygon[(i+1)%polygon.length],hit=intersection([p.x,p.z],[d.x,d.z],a,[b[0]-a[0],b[1]-a[1]]);if(!hit||hit[0]<0||hit[1]<0||hit[1]>1)continue;const y=p.y+d.y*hit[0];if(y>=box.min.y&&y<=box.max.y)nearest=Math.min(nearest,hit[0]);}
 return nearest;
}
export function polygonCollisionBoxes(records=[]){
 return records.map(record=>{const xs=record.polygon.map(p=>p[0]),zs=record.polygon.map(p=>p[1]),box=new Box3(new Vector3(Math.min(...xs),record.minY,Math.min(...zs)),new Vector3(Math.max(...xs),record.maxY,Math.max(...zs)));box.polygon=record.polygon;box.label=record.label||record.id;box.preciseVehicle=record.preciseVehicle!==false;return box;});
}
