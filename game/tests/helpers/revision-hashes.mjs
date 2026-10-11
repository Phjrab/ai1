import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';

export async function runtimeInputHashes(){
 const root=new URL('../../',import.meta.url),inputs={};
 for(const name of ['dist/assets/building.glb','dist/assets/campus.glb','dist/game.js','dist/shuttle-system.js','dist/transit-config.js','dist/world-config.js','dist/parking-config.js','dist/parking-system.js','dist/revision-colliders.js','dist/vehicle-steering.js','dist/vehicle-surfaces.js','dist/wheel-suspension.js','dist/walking-floor.js','dist/polygon-colliders.js','dist/water-constraints.js']){
  inputs[name]=createHash('sha256').update(await fs.readFile(new URL(name,root))).digest('hex');
 }
 for(const name of (await fs.readdir(new URL('data/',root))).filter(name=>name.endsWith('.json')).sort())inputs['data/'+name]=createHash('sha256').update(await fs.readFile(new URL('data/'+name,root))).digest('hex');
 const native=JSON.parse(await fs.readFile(new URL('data/native-export-manifest.json',root),'utf8'));
 inputs.nativeSourceSha256=native.source_sha256;
 for(const asset of native.exports)inputs['rawGLB/'+asset.file.split('/').at(-1)]=asset.sha256;
 return inputs;
}
