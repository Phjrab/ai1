import {Node} from '@gltf-transform/core';
import {dedup,weld,meshopt} from '@gltf-transform/functions';

// Campus-wide terrain, paving and stair meshes contain sub-centimetre clipped
// boundaries. A 16-bit world-spanning grid can shift edges onto another step or
// create narrow road-edge gaps. Keep exact authored Float32 support positions.
export async function compressModel(doc,encoder){
 await doc.transform(dedup(),weld());
 // Quantization normally rebases the mesh and its node matrix. Source-bound
 // tree roots and parked-car poses must keep their authored origin as well as
 // their world shape, so these shared meshes use the same exact-position path.
 const exactNode=n=>n instanceof Node&&(['walkable_support','RV2_walkable_surface','walkable','RV2_parking_walk_surface','RV2_parking_drive_surface','RV2_vehicle_surface','RV2_no_vehicle','tree_trunk'].some(k=>n.getExtras()[k]===true)||/^CAMPUS_CAR[ _]|^CAMPUS_TREE[ _]|^Tree[ _]/.test(n.getName()));
 const protectedMeshes=doc.getRoot().listMeshes().filter(m=>/INFERRED_GAME_WALK_CONNECTORS|CAMPUS_CONTINUOUS|CAMPUS_TERRAIN|CAMPUS_PLAZA/.test(m.getName())||m.listParents().some(exactNode)),originalNodes=new Map(),backup='_SOURCE_POSITION';
 for(const mesh of protectedMeshes){
  for(const node of mesh.listParents().filter(p=>p instanceof Node)){
   if(node.listChildren().length||node.getSkin()||node.getExtension('EXT_mesh_gpu_instancing')||doc.getRoot().listAnimations().some(a=>a.listChannels().some(c=>c.getTargetNode()===node)))throw new Error('Precision-preserved support must be a static leaf: '+node.getName());
   originalNodes.set(node,[...node.getMatrix()]);
  }
  for(const primitive of mesh.listPrimitives()){
   if(primitive.listTargets().length||primitive.getAttribute(backup))throw new Error('Unsupported precise support primitive');
   primitive.setAttribute(backup,primitive.getAttribute('POSITION').clone());
  }
 }
 await doc.transform(meshopt({encoder,level:'high',quantizePosition:16}));
 for(const mesh of protectedMeshes)for(const primitive of mesh.listPrimitives()){
  const position=primitive.getAttribute(backup);if(!(position?.getArray() instanceof Float32Array))throw new Error('Source position precision was lost');
  primitive.setAttribute('POSITION',position).setAttribute(backup,null);
 }
 for(const [node,matrix] of originalNodes)node.setMatrix(matrix);
 return protectedMeshes.map(m=>m.getName());
}
