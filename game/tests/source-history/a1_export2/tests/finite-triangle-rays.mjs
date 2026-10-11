import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {Ray,Vector3,Triangle} from 'three';
import {Octree} from '../dist/vendor/addons/math/Octree.js';
const cv=p=>new Vector3(p[0],p[2],-p[1]),sliver=[[250,-350,-40.0850715637207],[249.38963317871094,-350.6103515625,-40.0850715637207],[249.3896484375,-350.6103515625,-40.0850715637207]],floor=[[254,-346,-41.158573150634766],[256,-346,-41.158573150634766],[255,-344,-41.158573150634766]];
function tri(points){const t=new Triangle(...points.map(cv));if(t.getNormal(new Vector3()).y<0)[t.b,t.c]=[t.c,t.b];return t}
const ray=new Ray(cv([255,-345,-35]),new Vector3(0,-1,0)),only=new Octree();only.addTriangle(tri(sliver));only.build();assert.equal(only.rayIntersect(ray),false,'Finite runtime ray must reject a sliver seven metres away');const all=new Octree();all.addTriangle(tri(sliver));all.addTriangle(tri(floor));all.build();const hit=all.rayIntersect(ray);assert.ok(hit);assert.ok(Math.abs(hit.position.y-floor[0][2])<1e-9);const finiteVertex=new Ray(cv([250,-350,-35]),new Vector3(0,-1,0));assert.ok(only.rayIntersect(finiteVertex),'Actual finite triangle vertex is retained');
const report={passed:true,runtime:'Same Three Octree.rayIntersect used by game.floorHeight; no metadata epsilon in JS.',farSliverRejected:true,actualFloorHeight:hit.position.y,actualVertexRetained:true,geometryChanged:false};await fs.writeFile(new URL('finite-triangle-rays-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log('FINITE_TRIANGLE_RAYS',JSON.stringify(report));
