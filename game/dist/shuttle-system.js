// Deterministic game-only shuttle motion. Coordinates are metric Three.js x/y/z.
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const dist=(a,b)=>Math.hypot(b[0]-a[0],b[1]-a[1],b[2]-a[2]);
const wrap=(v,n)=>((v%n)+n)%n;
export function createRoute({id,label,points,stops=[],cruiseSpeed=6,dwellSeconds=10,closed=true}){
  if(!Array.isArray(points)||points.length<3)throw new Error('A shuttle route needs at least three points');
  const p=points.map(q=>{if(!Array.isArray(q)||q.length!==3||q.some(v=>!Number.isFinite(v)))throw new Error('Invalid route point');return q.slice()});
  if(closed&&dist(p[0],p[p.length-1])>.01)p.push(p[0].slice());
  if(!closed)throw new Error('Supply a complete, validated loop including the return route');
  const segments=[],lengths=[0];let total=0;
  for(let i=1;i<p.length;i++){const length=dist(p[i-1],p[i]);if(length<.01)continue;segments.push({a:p[i-1],b:p[i],start:total,length});total+=length;lengths.push(total)}
  if(total<5)throw new Error('Shuttle loop is too short');
  const sample=distance=>{let s=wrap(distance,total),segment=segments.find(g=>s<g.start+g.length)||segments[segments.length-1];const t=clamp((s-segment.start)/segment.length,0,1),position=segment.a.map((v,i)=>v+(segment.b[i]-v)*t),dx=segment.b[0]-segment.a[0],dz=segment.b[2]-segment.a[2];return {position,yaw:Math.atan2(-dx,-dz),pitch:Math.atan2(segment.b[1]-segment.a[1],Math.hypot(dx,dz))};};
  const project=position=>{let best={distance:0,error:Infinity};for(const g of segments){const d=g.b.map((v,i)=>v-g.a[i]),t=clamp(d.reduce((sum,v,i)=>sum+(position[i]-g.a[i])*v,0)/(g.length*g.length),0,1),q=g.a.map((v,i)=>v+d[i]*t),error=dist(q,position);if(error<best.error)best={distance:g.start+t*g.length,error};}return best;};
  const projected=stops.map(stop=>{const s=Number.isFinite(stop.distance)?{distance:wrap(stop.distance,total),error:0}:project(stop.position);if(s.error>15)throw new Error(`Stop ${stop.id} is too far from the route`);return {...stop,distance:s.distance};}).sort((a,b)=>a.distance-b.distance);
  if(!projected.length)throw new Error('A shuttle route needs at least one stop');
  return {id,label,points:p,segments,total,stops:projected,sample,project,cruiseSpeed:clamp(cruiseSpeed,1,10),dwellSeconds:clamp(dwellSeconds,3,60)};
}
export function createShuttle(route,{id='shuttle',distance=0,startDwelling=true}={}){
  const s=wrap(distance,route.total),next=route.stops.findIndex(stop=>stop.distance>=s-.01),nextStopIndex=next<0?0:next;
  const atStop=Math.abs(route.stops[nextStopIndex].distance-s)<.05;
  return {id,route,distance:s,speed:0,phase:startDwelling&&atStop?'dwelling':'driving',dwellRemaining:startDwelling&&atStop?route.dwellSeconds:0,nextStopIndex,laps:0,stopsVisited:[],...route.sample(s)};
}
export function stepShuttle(state,delta,{obstacleDistance=Infinity,acceleration=1.5,deceleration=2.2,safetyGap=3}={}){
  if(!Number.isFinite(delta)||delta<0)throw new Error('Invalid shuttle timestep');
  let left=Math.min(delta,2);
  while(left>1e-8){const dt=Math.min(left,1/30);left-=dt;
    if(state.phase==='dwelling'){
      state.speed=0;state.dwellRemaining-=dt;
      if(state.dwellRemaining<=0){state.stopsVisited.push(state.route.stops[state.nextStopIndex].id);state.nextStopIndex=(state.nextStopIndex+1)%state.route.stops.length;state.dwellRemaining=0;state.phase='driving';}
      continue;
    }
    const stop=state.route.stops[state.nextStopIndex],remaining=wrap(stop.distance-state.distance,state.route.total),obstacle=Math.max(0,obstacleDistance-safetyGap),distanceToBrake=Math.min(remaining,obstacle),desired=Math.min(state.route.cruiseSpeed,Math.sqrt(2*deceleration*Math.max(0,distanceToBrake-.02)));
    state.speed=desired<state.speed?Math.max(desired,state.speed-deceleration*dt):Math.min(desired,state.speed+acceleration*dt);
    let advance=Math.min(state.speed*dt,remaining,obstacle);
    if(advance<1e-5&&desired<.05){state.speed=0;state.phase='blocked';}else state.phase='driving';
    if(remaining<.06&&obstacle>remaining){advance=remaining;state.speed=0;state.phase='dwelling';state.dwellRemaining=state.route.dwellSeconds;}
    const old=state.distance;state.distance=wrap(state.distance+advance,state.route.total);if(state.distance<old-.01)state.laps++;
    Object.assign(state,state.route.sample(state.distance));
  }
  return state;
}
export function pointInShuttle(position,state,{width=2.5,length=10.5,height=3.5,margin=0}={}){
  const dx=position[0]-state.position[0],dz=position[2]-state.position[2],x=dx*Math.cos(state.yaw)-dz*Math.sin(state.yaw),z=dx*Math.sin(state.yaw)+dz*Math.cos(state.yaw);
  return Math.abs(x)<width/2+margin&&Math.abs(z)<length/2+margin&&position[1]<state.position[1]+height&&position[1]+1.7>state.position[1];
}
export function shuttleBoxOverlap(state,box,{width=2.5,length=10.7,height=3.5,margin=.1}={}){
  if(state.position[1]+height<=box.min[1]||state.position[1]>=box.max[1])return false;
  const dx=(box.min[0]+box.max[0])/2-state.position[0],dz=(box.min[2]+box.max[2])/2-state.position[2],hx=(box.max[0]-box.min[0])/2,hz=(box.max[2]-box.min[2])/2,c=Math.cos(state.yaw),s=Math.sin(state.yaw),a=width/2+margin,b=length/2+margin;
  return Math.abs(dx)<=hx+Math.abs(c)*a+Math.abs(s)*b&&Math.abs(dz)<=hz+Math.abs(s)*a+Math.abs(c)*b&&Math.abs(dx*c-dz*s)<=a+hx*Math.abs(c)+hz*Math.abs(s)&&Math.abs(dx*s+dz*c)<=b+hx*Math.abs(s)+hz*Math.abs(c);
}
export function shuttleVehicleOverlap(a,b,{width=2.5,length=10.7,otherWidth=1.85,otherLength=4.4,margin=.1}={}){
  if(Math.abs(a.position[1]-b.position[1])>3)return false;
  const axes=[[Math.cos(a.yaw),-Math.sin(a.yaw)],[Math.sin(a.yaw),Math.cos(a.yaw)],[Math.cos(b.yaw),-Math.sin(b.yaw)],[Math.sin(b.yaw),Math.cos(b.yaw)]],d=[b.position[0]-a.position[0],b.position[2]-a.position[2]];
  for(const axis of axes){const projection=Math.abs(d[0]*axis[0]+d[1]*axis[1]),ra=(width/2+margin)*Math.abs(axis[0]*axes[0][0]+axis[1]*axes[0][1])+(length/2+margin)*Math.abs(axis[0]*axes[1][0]+axis[1]*axes[1][1]),rb=otherWidth/2*Math.abs(axis[0]*axes[2][0]+axis[1]*axes[2][1])+otherLength/2*Math.abs(axis[0]*axes[3][0]+axis[1]*axes[3][1]);if(projection>ra+rb)return false;}return true;
}
