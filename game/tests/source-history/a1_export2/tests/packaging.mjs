// File-workflow regression tests. No browser or GPU is involved.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const temp=await fs.mkdtemp(path.join(os.tmpdir(),'chosun-packaging-'));
const root=path.join(temp,'game');
const digest=b=>createHash('sha256').update(b).digest('hex');
async function write(name,value){const p=path.join(root,name);await fs.mkdir(path.dirname(p),{recursive:true});await fs.writeFile(p,value);}
function python(script,...args){return spawnSync('python3',[path.join(root,'scripts',script),...args],{encoding:'utf8'});}
try {
 for(const script of ['verify-assets.py','export-source.py'])await write('scripts/'+script,await fs.readFile(new URL('../scripts/'+script,import.meta.url)));
 const assets={};for(const name of ['building.glb','campus.glb','shuttle_bus.glb']){const data=Buffer.from('isolated-test:'+name);await write('dist/assets/'+name,data);assets[name]={bytes:data.length,sha256:digest(data)};}
 await write('MODEL_PROVENANCE.json',JSON.stringify({assets}));
 await write('dist/index.html','<!doctype html><title>Packaging fixture</title>');await write('dist/game.js','// packaging fixture');
 await write('.openai/hosting.json','{"private":true}');await write('.env','DO_NOT_EXPORT=fixture');await write('node_modules/ignored.js','// excluded');
 await write('tests/parking-turns-candidate-results.json','{"superseded":true}');
 const clean=python('verify-assets.py');assert.equal(clean.status,0,clean.stderr);
 const first=path.join(temp,'first.zip'),second=path.join(temp,'second.zip');
 assert.equal(python('export-source.py',first).status,0);assert.equal(python('export-source.py',second).status,0);
 assert.equal(digest(await fs.readFile(first)),digest(await fs.readFile(second)),'ZIP bytes must be deterministic for unchanged input');
 const listing=spawnSync('python3',['-c','import sys,zipfile,json; z=zipfile.ZipFile(sys.argv[1]); print(json.dumps(z.namelist()))',first],{encoding:'utf8'});assert.equal(listing.status,0);const names=JSON.parse(listing.stdout);
 assert.ok(names.includes('Chosun_Campus_Walk/dist/assets/campus.glb'),'Standalone ZIP must include runtime binary');
 assert.ok(names.includes('Chosun_Campus_Walk/SOURCE_MANIFEST.json'));
 assert.ok(!names.some(n=>n.includes('.openai')||n.includes('.env')||n.includes('node_modules')),'Private/runtime files must be excluded');
 assert.ok(!names.some(n=>n.endsWith('-candidate-results.json')),'Superseded exploratory QA must not ship as current validation');
 const changed='intentional-local-model-edit';await write('dist/assets/campus.glb',changed);
 const mismatch=python('verify-assets.py');assert.notEqual(mismatch.status,0);assert.equal(await fs.readFile(path.join(root,'dist/assets/campus.glb'),'utf8'),changed,'Verifier must never replace an edited asset');
 await fs.rm(path.join(root,'dist/assets/campus.glb'));const missing=python('verify-assets.py');assert.notEqual(missing.status,0);assert.match(missing.stderr,/Missing current game asset/);
 console.log('PASS: provenance verification, edit preservation, missing-asset failure, runnable ZIP assets, private-file exclusion, deterministic source ZIP.');
} finally {await fs.rm(temp,{recursive:true,force:true});}
