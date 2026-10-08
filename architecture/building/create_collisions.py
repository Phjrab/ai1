import json,os
p=os.path.dirname(__file__);d=json.load(open(p+'/building_contract.json'));b=[]
def box(name,x0,x1,y0,y1,z0,z1):b.append(dict(name=name,min=[x0,y0,z0],max=[x1,y1,z1]))
# Ground-level simplified collision shape in Blender XYZ. Doorways are open.
segments=[(-166,-137.45),(-132.55,-2.45),(2.45,132.55),(137.45,166)]
for i,(a,c) in enumerate(segments):box('front_wall_'+str(i),a,c,-.25,.25,0,3.6)
box('rear_wall',-166,166,16.75,17.25,0,3.6)
box('corridor_classroom_partition',-166,166,3.9,4.1,0,3.6)
box('west_end',-166.2,-165.8,0,17,0,14.5);box('east_end',165.8,166.2,0,17,0,14.5)
for x in [-135,0,135]:
 for dx in [-2.9,2.9]:box('canopy_column',x+dx-.27,x+dx+.27,-4.22,-3.68,0,3.6)
data={'coordinate_system':'Blender Z up, meters. Three glTF maps (x,y,z) -> (x,z,-y).','accuracy':'Simplified GAME collision proxy only, inferred interiors. No surveyed plan.','boxes':b,'walk_surfaces':[{'name':'Ground corridor','bounds':[-165.75,165.75,.3,3.8],'z':.15},{'name':'Outside threshold','bounds':[-166,166,-6,0],'z':.05}],'entries':[{'x':x,'y':-.4,'z':.15,'clear_width':2.4,'clear_height':2.55} for x in [-135,0,135]],'recommended_player_start':[0,-8,1.8],'corridor_camera':{'position':[-10,1.6,1.72],'target':[11,2.1,1.7]},'collections':{'conceptual':'03 INTERIOR | CONCEPTUAL unsurveyed layouts','photo_finish_exemplar':'04 CORRIDOR EXEMPLAR | public photo-based finishes'},'notes':['Ground corridor is the accessible representative interior. No verified full building circulation or upper-floor stairs are supplied.','Collision box for corridor partition intentionally blocks classroom access, matching the illustrative partition mesh. A broader game interior would require its own explicitly fictional plan.']}
json.dump(data,open(p+'/geometry.json','w'),indent=2)
