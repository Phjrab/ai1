import {circleIntersectsPolygon,rectangleIntersectsPolygon,polygonRayDistance} from './polygon-colliders.js';
import {Box3,Matrix4,Quaternion,Ray,Vector3,Group} from 'three';
import {Octree} from './vendor/addons/math/Octree.js';
import {upwardSupportMesh} from './revision-colliders.js';

export function isParkingStaticCar(object){for(let node=object;node;node=node.parent)if(node.userData?.RV2_parking_static_car)return true;return false;}
export function isParkingDriveSurface(object){return object.userData?.RV2_parking_drive_surface===true||/^CAMPUS_PARKING164_DRIVE_SURFACE/.test(object.name);}
export class ParkingSupport{
 constructor(config){this.config=config;this.octree=new Octree();this.ready=false;this.meshCount=0;this.staticCarCount=0;this.ray=new Ray();}
 attach(root){if(!this.config.enabled)return;root.updateMatrixWorld(true);const group=new Group();root.traverse(o=>{if(o.userData?.RV2_parking_static_car&&!isParkingStaticCar(o.parent))this.staticCarCount++;if(o.isMesh&&isParkingDriveSurface(o)){group.add(upwardSupportMesh(o));this.meshCount++;}});if(!this.meshCount)return;this.octree.fromGraphNode(group);group.traverse(o=>{if(o.isMesh)o.geometry.dispose();});this.ready=true;}
 height(point,rise=.65){if(!this.ready)return null;this.ray.set(new Vector3(point.x,point.y+rise,point.z),new Vector3(0,-1,0));const hit=this.octree.rayIntersect(this.ray);return hit&&hit.distance<rise+1.8?hit.position.y:null;}
 isDrivable(point){const h=this.height(point);return h!==null&&Math.abs(h-point.y)<1.8;}
}
export function parkingCollisionBoxes(config){
 if(!config.enabled)return [];
 return config.colliders.map(record=>{
  const center=new Vector3(...record.center),half=new Vector3(...record.halfSize),yaw=record.yaw||0,c=Math.abs(Math.cos(yaw)),s=Math.abs(Math.sin(yaw)),extent=new Vector3(c*half.x+s*half.z,half.y,s*half.x+c*half.z),box=new Box3(center.clone().sub(extent),center.clone().add(extent));
  box.label=(config.labelPrefix||'parking164')+' '+record.kind+' '+record.name;box.parkingKind=record.kind;box.parkingLevel=record.level;
  const matrix=new Matrix4().compose(center,new Quaternion().setFromAxisAngle(new Vector3(0,1,0),yaw),new Vector3(1,1,1));
  box.oriented={center,half,yaw,inverse:matrix.clone().invert(),localBox:new Box3(half.clone().multiplyScalar(-1),half.clone())};return box;
 });
}
function pointSegmentDistanceSquared(x,z,a,b){const dx=b.x-a.x,dz=b.z-a.z,t=Math.max(0,Math.min(1,((x-a.x)*dx+(z-a.z)*dz)/(dx*dx+dz*dz||1)));return (x-a.x-t*dx)**2+(z-a.z-t*dz)**2;}
function segmentRectangleDistanceSquared(a,b,hx,hz){
 let enter=0,leave=1;for(const [p,d,half] of [[a.x,b.x-a.x,hx],[a.z,b.z-a.z,hz]]){if(Math.abs(d)<1e-12){if(Math.abs(p)>half){enter=2;break;}}else{const t0=(-half-p)/d,t1=(half-p)/d;enter=Math.max(enter,Math.min(t0,t1));leave=Math.min(leave,Math.max(t0,t1));}}if(enter<=leave)return 0;
 let nearest=Math.min(...[a,b].map(p=>Math.max(0,Math.abs(p.x)-hx)**2+Math.max(0,Math.abs(p.z)-hz)**2));for(const x of [-hx,hx])for(const z of [-hz,hz])nearest=Math.min(nearest,pointSegmentDistanceSquared(x,z,a,b));return nearest;
}
export function pointInStaticBox(position,box,radius=0,height=1.7){
 if(position.y>=box.max.y||position.y+height<=box.min.y)return false;
 if(box.segmentCapsule){const {a,b,radius:r}=box.segmentCapsule;return pointSegmentDistanceSquared(position.x,position.z,a,b)<(r+radius)**2;}
 if(box.polygon)return circleIntersectsPolygon(position.x,position.z,radius,box.polygon);
 if(!box.oriented)return position.x>box.min.x-radius&&position.x<box.max.x+radius&&position.z>box.min.z-radius&&position.z<box.max.z+radius;
 const {center,half,yaw}=box.oriented,dx=position.x-center.x,dz=position.z-center.z,c=Math.cos(yaw),s=Math.sin(yaw),x=dx*c-dz*s,z=dx*s+dz*c;
 return Math.abs(x)<half.x+radius&&Math.abs(z)<half.z+radius;
}
export function staticBoxRayDistance(ray,box){
 if(box.polygon)return polygonRayDistance(ray,box);
 const local=box.oriented?ray.clone().applyMatrix4(box.oriented.inverse):ray,point=local.intersectBox(box.oriented?.localBox||box,new Vector3());return point?point.distanceTo(local.origin):Infinity;
}
export function vehicleOverlapsStaticBox(position,yaw,box,{width=2.28,length=4.38,height=1.68,margin=.02}={}){
 if(position.y>=box.max.y||position.y+height<=box.min.y)return false;
 if(box.segmentCapsule){const c=Math.cos(yaw),s=Math.sin(yaw),local=p=>{const x=p.x-position.x,z=p.z-position.z;return {x:x*c-z*s,z:x*s+z*c};};return segmentRectangleDistanceSquared(local(box.segmentCapsule.a),local(box.segmentCapsule.b),width/2,length/2)<(box.segmentCapsule.radius+margin)**2;}
 if(box.polygon)return rectangleIntersectsPolygon(position,yaw,width+2*margin,length+2*margin,box.polygon);
 const center=box.oriented?.center||box.getCenter(new Vector3()),half=box.oriented?.half||box.getSize(new Vector3()).multiplyScalar(.5),otherYaw=box.oriented?.yaw||0;
 const axes=[[Math.cos(yaw),-Math.sin(yaw)],[Math.sin(yaw),Math.cos(yaw)],[Math.cos(otherYaw),-Math.sin(otherYaw)],[Math.sin(otherYaw),Math.cos(otherYaw)]],dx=center.x-position.x,dz=center.z-position.z;
 for(const axis of axes){const project=Math.abs(dx*axis[0]+dz*axis[1]),a=(width/2+margin)*Math.abs(axis[0]*axes[0][0]+axis[1]*axes[0][1])+(length/2+margin)*Math.abs(axis[0]*axes[1][0]+axis[1]*axes[1][1]),b=half.x*Math.abs(axis[0]*axes[2][0]+axis[1]*axes[2][1])+half.z*Math.abs(axis[0]*axes[3][0]+axis[1]*axes[3][1]);if(project>=a+b)return false;}
 return true;
}
