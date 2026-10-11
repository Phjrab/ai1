import {Ray,Vector3} from 'three';

// Only repair float32 cracks at a real finite edge near the preceding foot
// level. This is a query tolerance, not an extra platform or a sticky floor.
export const WALK_EDGE_TOLERANCE=0.0001;
const down=new Vector3(0,-1,0);
function edgeDistanceSquared(x,z,a,b){const dx=b.x-a.x,dz=b.z-a.z,t=Math.max(0,Math.min(1,((x-a.x)*dx+(z-a.z)*dz)/(dx*dx+dz*dz||1)));return (x-a.x-t*dx)**2+(z-a.z-t*dz)**2;}
export function walkingFloorHeight(octree,x,z,previousY){
 const from=previousY+.55,ray=new Ray(new Vector3(x,from,z),down),hit=octree.rayIntersect(ray),direct=hit&&hit.distance<70?hit.position.y:null;
 if(direct!==null&&direct>=previousY-.2)return direct;
 const triangles=[],epsilon=WALK_EDGE_TOLERANCE;
 for(const [dx,dz] of [[0,0],[epsilon,0],[-epsilon,0],[0,epsilon],[0,-epsilon]]){ray.origin.set(x+dx,from,z+dz);octree.getRayTriangles(ray,triangles);}
 let best=direct,nearest=Infinity;
 for(const triangle of new Set(triangles)){
  const {a,b,c}=triangle;
  if(x<Math.min(a.x,b.x,c.x)-epsilon||x>Math.max(a.x,b.x,c.x)+epsilon||z<Math.min(a.z,b.z,c.z)-epsilon||z>Math.max(a.z,b.z,c.z)+epsilon)continue;
  const edgeDistance=Math.min(edgeDistanceSquared(x,z,a,b),edgeDistanceSquared(x,z,b,c),edgeDistanceSquared(x,z,c,a));if(edgeDistance>epsilon*epsilon)continue;
  const normal=triangle.getNormal(new Vector3());if(normal.y<.1)continue;
  const height=a.y-(normal.x*(x-a.x)+normal.z*(z-a.z))/normal.y,change=height-previousY;
  if(change>.5||change<-.56||height>from||direct!==null&&height<=direct+1e-7)continue;
  const continuity=Math.abs(change);if(continuity<nearest){nearest=continuity;best=height;}
 }
 return best;
}
