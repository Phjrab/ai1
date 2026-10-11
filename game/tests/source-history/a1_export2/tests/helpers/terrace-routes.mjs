import assert from 'node:assert/strict';

// Sample the applied native triangles. Design endpoint elevations are not a
// substitute for the final clipped/graded surface under the vehicle.
export function terraceDriveRoutes(contract,sampleSupport){
 const routes=[];
 for(const zone of contract.transition_zones.filter(z=>z.vehicle_allowed)){
  const input=zone.connection;
  assert.ok(input?.connection_id&&input.centerline_xy?.length>1,'Allowed terrace needs an explicit connection');
  const flats=new Set(contract.parking_zones.filter(z=>zone.adjacent_zone_ids.includes(z.zone_id)).map(z=>z.object)),triangles=[...contract.lane_top_triangles.filter(t=>t.object===zone.object),...contract.surface_top_triangles.filter(t=>flats.has(t.object))].map(t=>t.vertices);
  assert.ok(triangles.length,'Allowed terrace lane lacks applied triangles');
  function height(x,y){
   const hits=[];
   for(const [a,b,c] of triangles){
    const den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1]);if(Math.abs(den)<1e-10)continue;
    const u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den,v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;
    if(u>=-1e-5&&v>=-1e-5&&u+v<=1.00001)hits.push(u*a[2]+v*b[2]+(1-u-v)*c[2]);
   }
   // Existing road tops can replace coplanar terrace triangles. Query their
   // actual GLB geometry inside this transition's bounded height range.
   const top=hits.length?Math.max(...hits):Math.max(...zone.actual_top_z_range),actual=sampleSupport(x,-y,top+.25,Math.max(1,top-Math.min(...zone.actual_top_z_range)+.5));
   assert.ok(actual!==null,'No actual GLB lane support for '+input.connection_id+' at '+[x,y]);
   if(hits.length)assert.ok(Math.abs(actual-top)<.06,'Applied terrace differs from rendered support for '+input.connection_id+' at '+[x,y]);
   assert.ok(actual>=Math.min(...zone.actual_top_z_range)-.1&&actual<=Math.max(...zone.actual_top_z_range)+.1,'Lane support outside applied transition heights');return actual;
  }
  const points=[];
  for(let i=1;i<input.centerline_xy.length;i++){
   const a=input.centerline_xy[i-1],b=input.centerline_xy[i],n=Math.max(1,Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/.25));
   for(let j=0;j<n;j++){const x=a[0]+(b[0]-a[0])*j/n,y=a[1]+(b[1]-a[1])*j/n;points.push([x,height(x,y),-y]);}
  }
  const end=input.centerline_xy.at(-1);points.push([end[0],height(...end),-end[1]]);
  for(const reverse of [false,true])routes.push({id:input.connection_id+(reverse?'_reverse':'_forward'),kind:'parking_terrace_connection',points:reverse?points.toReversed():points,width:input.width_m});
 }
 assert.ok(routes.length,'Applied parking terraces must contain a vehicle connection');return routes;
}
