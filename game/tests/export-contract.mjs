import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const manifest=JSON.parse(await fs.readFile(new URL('../data/native-export-manifest.json',import.meta.url),'utf8')),results=[];
for(const asset of manifest.exports){
 if(!asset.object_inventory_file)continue;
 const name=asset.file.split('/').at(-1),bytes=await fs.readFile(new URL('../data/native-export-'+name.replace('.glb','')+'-inventory.json',import.meta.url));assert.equal(createHash('sha256').update(bytes).digest('hex'),asset.object_inventory_sha256);
 const inventory=JSON.parse(bytes),web=await fs.readFile(new URL('../dist/assets/'+name,import.meta.url)),json=JSON.parse(web.subarray(20,20+web.readUInt32LE(12)).toString()),nodes=new Set(json.nodes.map(n=>n.name)),missing=inventory.objects.filter(o=>o.type==='MESH'&&!nodes.has(o.name));assert.deepEqual(missing,[],'No selected native mesh may disappear from the web scene');
 const access=inventory.objects.filter(o=>o.entrance_connection);if(name==='campus.glb')assert.ok(access.length>=22,'Evidence-supported entrance collection must be included');results.push({asset:name,selectedObjects:inventory.objects.length,selectedMeshes:inventory.objects.filter(o=>o.type==='MESH').length,entranceConnectionObjects:access.length,missing:missing.length,collections:inventory.collections});
}
assert.equal(results.length,2,'Both split exports need explicit object inventories');await fs.writeFile(new URL('export-contract-results.json',import.meta.url),JSON.stringify({passed:true,nativeSha256:manifest.source_sha256,exporterSha256:manifest.exporter_sha256,results},null,2)+'\n');console.log('EXPORT_CONTRACT',JSON.stringify(results));
