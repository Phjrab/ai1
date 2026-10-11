// A closed, measured envelope for accepted visual tyre contacts, not a route exception.
const triangleKey=t=>t.map(p=>p.map(v=>v.toFixed(5)).join(',')).sort().join('|');
export function assessKnownTyreContacts(route,hits,contract){
 const limit=contract.routes[route],failures=[];let maxDepth=0;
 if(!hits.length)return {accepted:true,maximumRadialOverlapMeters:0,failures};
 if(!limit)return {accepted:false,failures:[{reason:'unlisted contact route'}]};
 if(hits.length>limit.maximumContactPoses)failures.push({reason:'contact pose count increased',actual:hits.length,maximum:limit.maximumContactPoses});
 for(const h of hits){
  const pose=limit.poses.find(p=>Math.hypot(...h.position.map((x,i)=>x-p.position[i]))<=contract.poseDistanceToleranceMeters&&(p.yaw===undefined||Math.abs(Math.atan2(Math.sin(h.yaw-p.yaw),Math.cos(h.yaw-p.yaw)))<=contract.yawToleranceRadians));
  if(!pose)failures.push({reason:'contact outside measured pose range',position:h.position,yaw:h.yaw});
  if(!h.details?.length)failures.push({reason:'missing finite component details'});
  for(const c of h.details||[]){
   if(!c.tyre||c.object!==(limit.object||contract.object))failures.push({reason:'new body, hub or other object contact',contact:c});
   if(pose?.components&&!pose.components.includes(c.component))failures.push({reason:'different tyre assembly',component:c.component});
   if(pose?.maximumRadialOverlapMeters!==undefined&&c.radialOverlapUpperBoundMeters>pose.maximumRadialOverlapMeters+contract.depthRoundoffToleranceMeters)failures.push({reason:'per-pose depth increased',actual:c.radialOverlapUpperBoundMeters,maximum:pose.maximumRadialOverlapMeters});
   if(!limit.triangleKeys.includes(triangleKey(c.triangle)))failures.push({reason:'unmeasured finite contact triangle',contact:c});
   if(!Number.isFinite(c.radialOverlapUpperBoundMeters)||c.radialOverlapUpperBoundMeters>limit.maximumRadialOverlapMeters+contract.depthRoundoffToleranceMeters)failures.push({reason:'contact depth increased',actual:c.radialOverlapUpperBoundMeters,maximum:limit.maximumRadialOverlapMeters});
   maxDepth=Math.max(maxDepth,c.radialOverlapUpperBoundMeters||0);
  }
 }
 return {accepted:!failures.length,maximumRadialOverlapMeters:maxDepth,maximumAllowedContactPoses:limit.maximumContactPoses,maximumAllowedRadialOverlapMeters:limit.maximumRadialOverlapMeters,failures};
}
