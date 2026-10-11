import {Group,Mesh} from 'three';

// Retain only the requested source meshes from the runtime's actual GLB load.
// This avoids decoding the entire campus a second time for independent probes.
// Collider winding changes use separate buffers; these remain render buffers.
export function captureModelMeshes(select){
 const result=new Group();
 globalThis.captureCampusTestGeometry=(name,scene)=>{
  if(name!=='campus.glb')return;
  scene.traverse(object=>{
   if(!object.isMesh||!select(object))return;
   const parent=new Group();parent.name=object.parent?.name||'';
   const mesh=new Mesh(object.geometry,object.material);mesh.name=object.name;
   const ancestors=[];for(let node=object;node;node=node.parent)ancestors.unshift(node);
   mesh.userData=Object.assign({},...ancestors.map(node=>node.userData));
   mesh.matrix.copy(object.matrixWorld);mesh.matrixAutoUpdate=false;
   parent.add(mesh);result.add(parent);
  });
 };
 return result;
}
