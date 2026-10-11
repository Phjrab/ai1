import {Box3,Vector3,Matrix4,Mesh,BufferGeometry,Float32BufferAttribute} from 'three';
export function hasWalkableSupportTag(object){for(let node=object;node;node=node.parent)if(['walkable_support','RV2_walkable_surface','walkable','RV2_parking_walk_surface'].some(key=>node.userData?.[key]===true))return true;return false;}
export function hasVehicleSurfaceTag(object){let tagged=false;for(let node=object;node;node=node.parent){if(node.visible===false||node.userData?.RV2_replaced_by_architecture===true||node.userData?.RV2_no_vehicle===true||node.userData?.collision===false||node.userData?.visual_only===true)return false;if(node.userData?.RV2_vehicle_surface===true)tagged=true;}return tagged;}
export function isVisualOnly(object){for(let node=object;node;node=node.parent)if(node.userData?.visual_only===true)return true;return false;}
export function isCollisionDisabled(object){for(let node=object;node;node=node.parent)if(node.userData?.collision===false||node.userData?.visual_only===true)return true;return false;}

export function isOriginalCampusCar(object){for(let node=object;node;node=node.parent)if(/^CAMPUS_CAR[ _]\d/.test(node.userData?.name||node.name))return true;return false;}

// glTF normalizes spaces in runtime names. Identify the original car root once,
// then bound its actual vertices in a horizontal frame at its own heading.
// Pitch/roll still contribute to the height range and conservative footprint.
export function originalCampusCarBoxes(root){
 const boxes=[];root.updateMatrixWorld(true);
 root.traverse(object=>{
  if(!isOriginalCampusCar(object)||isOriginalCampusCar(object.parent)||isCollisionDisabled(object))return;
  const origin=object.getWorldPosition(new Vector3()),forward=new Vector3(0,0,1).transformDirection(object.matrixWorld),yaw=Math.atan2(forward.x,forward.z),frame=new Matrix4().makeRotationY(yaw).setPosition(origin),inverse=frame.clone().invert(),bounds=new Box3(),point=new Vector3();
  object.traverse(mesh=>{if(!mesh.isMesh||isCollisionDisabled(mesh))return;const p=mesh.geometry.attributes.position;for(let i=0;i<p.count;i++)bounds.expandByPoint(point.fromBufferAttribute(p,i).applyMatrix4(mesh.matrixWorld).applyMatrix4(inverse));});
  if(bounds.isEmpty())throw new Error('Original campus car has no collision geometry: '+object.name);
  const center=bounds.getCenter(new Vector3()).applyMatrix4(frame),half=bounds.getSize(new Vector3()).multiplyScalar(.5),matrix=new Matrix4().makeRotationY(yaw).setPosition(center),box=bounds.clone().applyMatrix4(frame);
  box.label=(object.userData?.name||object.name)+' static vehicle';box.originalCampusCar=true;box.preciseVehicle=true;
  box.oriented={center,half,yaw,inverse:matrix.clone().invert(),localBox:new Box3(half.clone().multiplyScalar(-1),half.clone())};boxes.push(box);
 });return boxes;
}

// The revised hospital canopy has two thin piers beyond the old footprint.
// Recover each disconnected solid, never one broad box across the open entrance.
export function revisionColumnBoxes(root){
 const boxes=[];
 root.updateMatrixWorld(true);
 root.traverse(object=>{
  if(!object.isMesh||!/hospital_canopy_columns/i.test(object.name))return;
  const position=object.geometry.getAttribute('position'),index=object.geometry.index;
  const parent=Array.from({length:position.count},(_,i)=>i),firstAt=new Map();
  const find=i=>{while(parent[i]!==i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
  const union=(a,b)=>{a=find(a);b=find(b);if(a!==b)parent[b]=a;};
  for(let i=0;i<position.count;i++){
   const key=[position.getX(i),position.getY(i),position.getZ(i)].map(v=>Math.round(v*100000)).join(',');
   if(firstAt.has(key))union(i,firstAt.get(key));else firstAt.set(key,i);
  }
  for(let i=0;i<(index?.count??position.count);i+=3){const a=index?index.getX(i):i,b=index?index.getX(i+1):i+1,c=index?index.getX(i+2):i+2;union(a,b);union(a,c);}
  const components=new Map(),point=new Vector3();
  for(let i=0;i<position.count;i++){const key=find(i);if(!components.has(key))components.set(key,new Box3());point.fromBufferAttribute(position,i).applyMatrix4(object.matrixWorld);components.get(key).expandByPoint(point);}
  for(const box of components.values()){
   const size=box.getSize(new Vector3());
   if(size.x>2||size.z>2||size.y<1.5)continue;
   box.label=object.name+' support '+boxes.length;
   boxes.push(box);
  }
 });
 return boxes;
}

// A mapped parking aisle occupies an open ground level inside an approximate
// full-height footprint proxy. Exempt only this height band and road corridor;
// actual building, guard, and support triangles remain in the collision octree.
export function createPassageClearance(world){
 const passages=(world.vehicleUnderpasses||[]).map(p=>({...p,segments:world.roads.filter(r=>r.name===p.roadName).flatMap(r=>r.points.slice(1).map((b,i)=>({a:r.points[i],b,width:r.width})))}));
 return (position,box)=>passages.some(p=>{
  if(box.label!==p.footprintLabel||position.y<p.floorHeight-.7||position.y+1.7>p.ceilingHeight-.1)return false;
  return p.segments.some(({a,b,width})=>{const dx=b[0]-a[0],dz=b[2]-a[2],t=Math.max(0,Math.min(1,((position.x-a[0])*dx+(position.z-a[2])*dz)/(dx*dx+dz*dz||1)));return Math.hypot(position.x-a[0]-t*dx,position.z-a[2]-t*dz)<width/2;});
 });
}

// Dedicated support copy: source render buffers, normals and winding stay intact.
export function upwardSupportMesh(object){
 const source=object.geometry.attributes.position,index=object.geometry.index,count=index?.count??source.count,values=new Float32Array(count*3),point=new Vector3();let flipped=0;
 for(let i=0;i<count;i++){point.fromBufferAttribute(source,index?index.getX(i):i).applyMatrix4(object.matrixWorld);point.toArray(values,i*3);}
 for(let i=0;i<count*3;i+=9){const x1=values[i+3]-values[i],z1=values[i+5]-values[i+2],x2=values[i+6]-values[i],z2=values[i+8]-values[i+2];if(z1*x2-x1*z2<0){for(let j=0;j<3;j++){const t=values[i+3+j];values[i+3+j]=values[i+6+j];values[i+6+j]=t;}flipped++;}}
 const geometry=new BufferGeometry();geometry.setAttribute('position',new Float32BufferAttribute(values,3));const mesh=new Mesh(geometry);mesh.userData.supportTrianglesFlipped=flipped;return mesh;
}

export function createWalkingAccessClearance(world){
 const zones=world.walkingAccessZones||[];
 return (position,box,radius=.34)=>{
  if(radius>.7)return false;
  return zones.some(zone=>{
   if(!zone.labels.includes(box.label)||position.y<zone.minY||position.y>zone.maxY)return false;
   let inside=false,nearest=Infinity;const poly=zone.polygon;
   for(let i=0,j=poly.length-1;i<poly.length;j=i++){
    const a=poly[j],b=poly[i],x=position.x,z=position.z;
    if((a[1]>z)!==(b[1]>z)&&x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0])inside=!inside;
    const dx=b[0]-a[0],dz=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz||1)));
    nearest=Math.min(nearest,Math.hypot(x-a[0]-t*dx,z-a[1]-t*dz));
   }
   return inside||nearest<.4;
  });
 };
}

export function treeTrunkBoxes(root){
 const boxes=[];root.updateMatrixWorld(true);
 const tagged=node=>node.userData?.tree_trunk===true||/^Tree\s|^CAMPUS_TREE[ _]RV2_CENTRAL[ _]/.test(node.name);
 root.traverse(object=>{
  // The source marks the foliage mesh collision=false while explicitly
  // requesting a separate narrow trunk primitive. Never add its canopy mesh.
  if(!tagged(object)||(object.userData?.tree_trunk!==true&&isCollisionDisabled(object)))return;
  for(let parent=object.parent;parent;parent=parent.parent)if(tagged(parent))return;
  const p=object.getWorldPosition(new Vector3()),radius=object.userData?.trunk_radius_m??.25;
  if(!Number.isFinite(radius)||radius<=0||radius>2)throw new Error('Invalid tree trunk radius: '+object.name);
  const box=new Box3(new Vector3(p.x-radius,p.y,p.z-radius),new Vector3(p.x+radius,p.y+3,p.z+radius));box.label=object.name+' trunk';boxes.push(box);
 });return boxes;
}
