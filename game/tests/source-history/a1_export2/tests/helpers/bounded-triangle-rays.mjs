import {Ray,Vector3} from 'three';
// Exact Octree triangles inside a finite query box, not a resampled heightfield.
// Used to inspect many vertices of one physical tyre without repeating the
// identical octree traversal for every vertex. Backface semantics match runtime.
export function boundedDownRays(octree,bounds){
 const found=new Set(),visit=node=>{if(node.box&&!node.box.intersectsBox(bounds))return;for(const triangle of node.triangles||[])found.add(triangle);for(const child of node.subTrees||[])visit(child);};visit(octree);
 const triangles=[...found],grid=new Map(),ray=new Ray(new Vector3(),new Vector3(0,-1,0)),hit=new Vector3();
 for(const triangle of triangles){const v=[triangle.a,triangle.b,triangle.c],x0=Math.max(Math.floor(bounds.min.x),Math.floor(Math.min(...v.map(p=>p.x))-1e-6)),x1=Math.min(Math.floor(bounds.max.x),Math.floor(Math.max(...v.map(p=>p.x))+1e-6)),z0=Math.max(Math.floor(bounds.min.z),Math.floor(Math.min(...v.map(p=>p.z))-1e-6)),z1=Math.min(Math.floor(bounds.max.z),Math.floor(Math.max(...v.map(p=>p.z))+1e-6));for(let x=x0;x<=x1;x++)for(let z=z0;z<=z1;z++){const key=x+':'+z;if(!grid.has(key))grid.set(key,[]);grid.get(key).push(triangle);}}
 const query=(x,z,from)=>{if(x<bounds.min.x-1e-6||x>bounds.max.x+1e-6||z<bounds.min.z-1e-6||z>bounds.max.z+1e-6||from>bounds.max.y+1e-6)throw new Error('Ray left its declared exact triangle query bounds');ray.origin.set(x,from,z);let highest=null;for(const triangle of grid.get(Math.floor(x)+':'+Math.floor(z))||[])if(ray.intersectTriangle(triangle.a,triangle.b,triangle.c,true,hit)&&hit.y>=bounds.min.y-1e-7&&(highest===null||hit.y>highest))highest=hit.y;return highest;};
 query.triangleCount=triangles.length;return query;
}
