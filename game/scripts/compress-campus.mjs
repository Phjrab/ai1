import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {dedup,weld,meshopt} from '@gltf-transform/functions';
import {MeshoptEncoder,MeshoptDecoder} from 'meshoptimizer';
import fs from 'node:fs/promises';
import path from 'node:path';
const input=process.argv[2],output=process.argv[3],args=process.argv.slice(4),materialPath=args.find(a=>!a.startsWith('--')),noCompress=args.includes('--no-compress'),reportPath=args.find(a=>a.startsWith('--report='))?.slice(9);
if(!input||!output)throw new Error('Usage: node scripts/compress-campus.mjs input.glb output.glb [materials.json] [--no-compress] [--report=file.json]');
await MeshoptEncoder.ready;await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.encoder':MeshoptEncoder,'meshopt.decoder':MeshoptDecoder});
const doc=await io.read(input),mapping=materialPath?JSON.parse(await fs.readFile(materialPath,'utf8')).materials:{},materials=doc.getRoot().listMaterials(),matched=[],unmatched=[];
for(const material of materials){const name=material.getName(),p=mapping[name]||mapping[name.replace(/\.\d{3}$/,'')];if(!p){unmatched.push(name);continue;}material.setBaseColorFactor(p.baseColorLinear).setRoughnessFactor(p.roughness).setMetallicFactor(p.metalness).setAlphaMode(p.alphaMode||'OPAQUE');const transmission=material.getExtension('KHR_materials_transmission');transmission?.setTransmissionFactor(p.transmission||0);matched.push(name);}
let foliageNormalPrimitives=0;
for(const mesh of doc.getRoot().listMeshes())for(const primitive of mesh.listPrimitives()){
 const material=primitive.getMaterial(),profile=material&&(mapping[material.getName()]||mapping[material.getName().replace(/\.\d{3}$/,'')]);
 if(profile?.profile!=='foliage')continue;
 const position=primitive.getAttribute('POSITION'),indices=primitive.getIndices()?.getArray();if(!position)continue;const p=position.getArray(),count=position.getCount(),groups=new Map(),groupFor=[];
 for(let i=0;i<count;i++){const key=[p[i*3],p[i*3+1],p[i*3+2]].map(v=>Math.round(v*100000)).join(',');if(!groups.has(key))groups.set(key,[0,0,0]);groupFor[i]=groups.get(key);}
 for(let i=0,n=indices?.length??count;i<n;i+=3){const a=indices?indices[i]:i,b=indices?indices[i+1]:i+1,c=indices?indices[i+2]:i+2,ux=p[b*3]-p[a*3],uy=p[b*3+1]-p[a*3+1],uz=p[b*3+2]-p[a*3+2],vx=p[c*3]-p[a*3],vy=p[c*3+1]-p[a*3+1],vz=p[c*3+2]-p[a*3+2],normal=[uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx];for(const k of [a,b,c])for(let j=0;j<3;j++)groupFor[k][j]+=normal[j];}
 const normals=new Float32Array(count*3);for(let i=0;i<count;i++){const v=groupFor[i],length=Math.hypot(...v)||1;for(let j=0;j<3;j++)normals[i*3+j]=v[j]/length;}const accessor=doc.createAccessor().setType('VEC3').setArray(normals).setBuffer(position.getBuffer());primitive.setAttribute('NORMAL',accessor);foliageNormalPrimitives++;
}
if(!noCompress)await doc.transform(dedup(),weld(),meshopt({encoder:MeshoptEncoder,level:'high',quantizePosition:16}));
await io.write(output,doc);
const report={input:path.basename(input),output:path.basename(output),inputBytes:(await fs.stat(input)).size,outputBytes:(await fs.stat(output)).size,materialCount:materials.length,foliageNormalPrimitives,matched,unmatched,compression:noCompress?'none; material fallback only':'Meshopt with 16-bit position quantization'};
if(reportPath)await fs.writeFile(reportPath,JSON.stringify(report,null,2));console.log(JSON.stringify(report));
