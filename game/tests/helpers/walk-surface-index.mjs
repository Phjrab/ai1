// Exact metadata-height comparison with bounded candidate lookup. The final
// hospital paths contain tens of thousands of triangles; all-pairs scanning
// would change test duration quadratically without adding coverage.
export function walkSurfaceHeightIndex(surfaces,cell=8){
 const grid=new Map();
 for(const surface of surfaces)for(const face of surface.triangles){const [a,b,c]=face.map(i=>surface.polygon[i]),den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2]);if(Math.abs(den)<1e-9)continue;const row={a,b,c,den},xs=[a[0],b[0],c[0]],zs=[a[2],b[2],c[2]],padding=Math.max(1e-5,(Math.max(...xs)-Math.min(...xs)+Math.max(...zs)-Math.min(...zs))*1e-6);for(let x=Math.floor((Math.min(...xs)-padding)/cell);x<=Math.floor((Math.max(...xs)+padding)/cell);x++)for(let z=Math.floor((Math.min(...zs)-padding)/cell);z<=Math.floor((Math.max(...zs)+padding)/cell);z++){const key=x+':'+z;if(!grid.has(key))grid.set(key,[]);grid.get(key).push(row);}}
 return (x,z,fallback)=>{let top=fallback;for(const {a,b,c,den} of grid.get(Math.floor(x/cell)+':'+Math.floor(z/cell))||[]){const u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/den,v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/den,w=1-u-v;if(Math.min(u,v,w)>=-1e-7)top=Math.max(top,u*a[1]+v*b[1]+w*c[1]);}return top;};
}
