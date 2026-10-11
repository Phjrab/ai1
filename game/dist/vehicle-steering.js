// Kinematic bicycle at the modeled car's midpoint. The authored wheelbase is
// 2.70 m and track is 1.84 m. The chosen 35-degree low-speed steering parameter
// gives a 4.09 m midpoint radius and 5.49 m outer front wheel-center radius.
// These are simulation dimensions and assumptions, not measured vehicle specs.
export const VEHICLE_STEERING={wheelbase:2.7,rearToCenter:1.35,track:1.84,maxFrontSteer:35*Math.PI/180,lowSpeed:2,highSpeed:8,highSpeedCurvature:.047};
export function steeringState(speed,input){
 const p=VEHICLE_STEERING,t=Math.max(0,Math.min(1,(Math.abs(speed)-p.lowSpeed)/(p.highSpeed-p.lowSpeed))),blend=t*t*(3-2*t);
 const highAngle=Math.atan(p.wheelbase*p.highSpeedCurvature/Math.sqrt(1-(p.rearToCenter*p.highSpeedCurvature)**2));
 const frontAngle=Math.max(-1,Math.min(1,input))*((1-blend)*p.maxFrontSteer+blend*highAngle),slipAngle=Math.atan(p.rearToCenter/p.wheelbase*Math.tan(frontAngle));
 return {frontAngle,slipAngle,curvature:Math.cos(slipAngle)*Math.tan(frontAngle)/p.wheelbase};
}
export function steeringCurvature(speed){return steeringState(speed,1).curvature;}
