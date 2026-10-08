"""Source-informed stairs and explicit game walk surfaces. Original mesh only.
Reference photos establish types; unmeasured dimensions/count allocations are estimates.
All JSON coordinates use Blender Z-up metres; polygons face up.
"""
import math,bpy
from mesh_architecture import Mesh,mat,alongbox

def _surface(nav,ident,kind,pts,source,confidence='photo-informed approximate dimensions'):
    if len(pts)==4:
        pts=[list(p) for p in pts]
        cross=(pts[1][0]-pts[0][0])*(pts[2][1]-pts[0][1])-(pts[1][1]-pts[0][1])*(pts[2][0]-pts[0][0])
        if cross<0:pts=list(reversed(pts))
    nav.setdefault('walkableSurfaces',[]).append(dict(id=ident,kind=kind,polygon=pts,triangles=[[0,1,2],[0,2,3]],source=source,confidence=confidence))

def build_central(site,col,nav):
    for ob in list(site.all_objects):
        if ob.name.startswith(('Central 108-step','Stair central commemorative','Central stair handrails','Central upper stair landing','Lower stair landing')):bpy.data.objects.remove(ob,do_unlink=True)
    ma=[mat('STAIRS • honed gray granite',(.46,.465,.44)),mat('STAIRS • granite nosing',(.65,.65,.61)),mat('STAIRS • brushed stainless rail',(.42,.46,.46),.3,.65),mat('STAIRS • memorial plaques',(.12,.15,.15),.45,.25)]
    body,edge,rail,plaques=Mesh(),Mesh(),Mesh(),Mesh()
    # Ascending south to north; photo has broad lower flight and narrower upper staircase.
    # 108 is established site name. Four landings and flight allocation are unmeasured.
    flights=[(18,11.2),(30,7.8),(30,7.8),(30,7.8)]
    landing_lengths=[1.5,1.5,1.5];tread=(65-sum(landing_lengths))/108;rise=18/108
    y=-92.;z=-18.;index=0;center=[]
    source='108-step official photograph; research copy stairs108.jpg'
    for fi,(count,width) in enumerate(flights):
        ya=y;za=z
        for step in range(count):
            z+=rise;yy=y+tread
            body.box((0,(y+yy)/2,z-.40),(width,tread+.012,.80))
            edge.box((0,y+.035,z+.009),(width,.065,.018),1)
            # A fine, physically modelled joint grid rather than an image texture.
            for x in range(-int(width/2),int(width/2)+1):edge.box((x,(y+yy)/2,z+.006),(.012,tread,.009),3)
            for side in (-1,1):
                edge.box((side*(width/2+.13),(y+yy)/2,z+.14),(.26,tread+.012,.38),1)
            if fi>0:
                # The dark center memorial strip is flush; never a collision obstacle.
                plaques.box((0,y+.012,z-rise*.5),(.45,.028,rise*.8),3)
            _surface(nav,f'central108_tread_{index:03d}','stairs',[(-width/2,y,z),(width/2,y,z),(width/2,yy,z),(-width/2,yy,z)],source)
            center.append([0,(y+yy)/2,z]);index+=1;y=yy
        for side in (-1,1):
            x=side*(width/2-.24)
            for zz in (.62,1.02):rail.tube((x,ya,za+zz),(x,y,z+zz),.036 if zz<1 else .047,m=2,n=8)
            n=max(1,math.ceil((y-ya)/1.5))
            for j in range(n+1):
                py=ya+(y-ya)*j/n;pz=za+(z-za)*j/n
                rail.tube((x,py,pz),(x,py,pz+1.02),.032,m=2,n=7)
        if fi<3:
            ll=landing_lengths[fi];nw=7.8
            body.box((0,y+ll/2,z-.35),(max(width,nw),ll,.70))
            _surface(nav,f'central108_landing_{fi}','landing',[(-width/2,y,z),(width/2,y,z),(width/2,y+ll,z),(-width/2,y+ll,z)],source)
            for side in (-1,1):
                rail.tube((side*(width/2-.24),y,z+1.02),(side*(nw/2-.24),y+ll,z+1.02),.047,m=2,n=8)
            center.append([0,y+ll/2,z]);y+=ll
    for ident,cy,ww,dd,zz in [('lower',-94.0,11.8,4.,-18.),('upper',-25.7,9.1,2.6,0.)]:
        body.box((0,cy,zz-.18),(ww,dd,.36))
        _surface(nav,'central108_'+ident,'landing',[(-ww/2,cy-dd/2,zz),(ww/2,cy-dd/2,zz),(ww/2,cy+dd/2,zz),(-ww/2,cy+dd/2,zz)],source)
    for label,me in [('108 individual treads and four approaches',body),('Stone nosings joints and sloping side cheeks',edge),('Continuous side handrails and posts',rail),('Flush central commemorative strip',plaques)]:
        ob=me.object('STAIR_DETAIL | '+label,ma,col);ob['evidence']=source;ob['limits']='Unmeasured width, riser/run, landing allocation. Side cheeks are not an accessible ramp.'
    nav.setdefault('pedestrianPaths',[]).append({'id':'central108','kind':'stairs','width':7.8,'points':[[0,-96,-18]]+center+[[0,-24.4,0]],'maxRiser':rise,'stepCount':108,'landingCount':3,'source':source,'confidence':'photo-informed; 108 total name-backed, flight allocation estimated','smoothTraversal':True})
    nav['stairContract']={'coordinates':'Blender Z-up metres; glTF x,y,z = Blender x,z,-y','walkableSurfaces':'Render-top polygons, authoritative for foot elevation when XY is inside. No collisionBoxes across treads.','pedestrianPaths':'centerlines for nav continuity; smoothTraversal may use an interpolated foot height while render geometry retains individual risers.','maxStepHeight':.20,'unverifiedAccessibility':'Do not call granite side cheeks wheelchair ramps. No central accessible ramp is established by the available photo.'}

def entry_access(b,edge_record,col,nav,height,source,steps=5,width=7,add_ramp=False):
    """Outside-wall entrance steps and a continuous optional side ramp."""
    a,bb,le,ux,uy,nx,ny,an=edge_record
    cx,cy=(a[0]+bb[0])/2,(a[1]+bb[1])/2
    width=min(width,le*.75);run=.27 if b['id']==153 else .34;rise=.14;approach=.65 if b['id']==153 else 2.2
    landing=1.35
    # Connect the photographed threshold type to the final earthworked grade.
    # Site dimensions are estimated, so riser count adapts rather than leaving a cliff.
    requested_steps=steps;top=b['base']+(.18 if b['id']==153 else requested_steps*.14+.08)
    for _ in range(5):
        length=landing+steps*run
        gx=cx+nx*(length+.12+approach);gy=cy+ny*(length+.12+approach);gz=height(gx,gy)+.03
        delta=top-gz
        steps=max(1,min(64,math.ceil(abs(delta)/.18)))
    length=landing+steps*run
    gx=cx+nx*(length+.12+approach);gy=cy+ny*(length+.12+approach);gz=height(gx,gy)+.03
    bottom=gz;rise=(top-bottom)/steps
    ma=[mat('STAIRS • entry pale granite',(.66,.65,.59)),mat('STAIRS • entry rail',(.40,.44,.44),.33,.6)]
    me,rails=Mesh(),Mesh()
    def pt(u,v,z):return (cx+ux*u+nx*v,cy+uy*u+ny*v,z)
    def surf(ident,kind,u0,u1,v0,v1,z0,z1=None):
        z1=z0 if z1 is None else z1;p=[pt(u0,v0,z0),pt(u1,v0,z0),pt(u1,v1,z1),pt(u0,v1,z1)]
        me.poly(p,[(0,1,2,3)],0);_surface(nav,ident,kind,p,source)
    ident='entry_'+str(b['id'])+'_'+str(b['osm_id'])
    alongbox(me,pt(0,landing/2+.12,top-.16),(width,landing,.32),an,0)
    surf(ident+'_landing','landing',-width/2,width/2,.12,landing+.12,top)
    center=[list(pt(0,landing/2,top))]
    for i in range(steps):
        v=landing+.12+i*run;z=top-(i+1)*rise
        alongbox(me,pt(0,v+run/2,z-.25),(width,run+.012,.5),an,0)
        surf(ident+'_step_'+str(i),'stairs',-width/2,width/2,v,v+run,z)
        center.append(list(pt(0,v+run/2,z)))
    # Link bottom to surveyed terrain approximation at an exterior footway.
    v0=length+.12;v1=v0+approach;gx,gy,_=pt(0,v1,0);gz=height(gx,gy)+.03
    if b['id']==153:
        # Short tapered entry apron clears the adjacent mapped construction laboratory.
        pp=[pt(-width/2,v0,bottom),pt(width/2,v0,bottom),pt(.60,v1,gz),pt(-.60,v1,gz)]
        me.poly(pp,[(0,1,2,3)],0);_surface(nav,ident+'_approach','walkway',pp,source)
    else:surf(ident+'_approach','walkway',-width/2,width/2,v0,v1,bottom,gz)
    for side in (-1,1):
        u=side*(width/2-.12)
        rails.tube(pt(u,.22,top+1),pt(u,landing,top+1),.037,m=1,n=7)
        rails.tube(pt(u,landing,top+1),pt(u,v0,bottom+1),.037,m=1,n=7)
        for v,z in ((.22,top),(landing,top),(v0,bottom)):rails.tube(pt(u,v,z),pt(u,v,z+1),.028,m=1,n=6)
    if add_ramp:
        # The #144 official image visibly has an adjacent railed ramp; slope is estimated.
        rw=1.45;rl=max(4.5,steps*rise*12);u0=width/2+.22;u1=u0+rw
        surf(ident+'_ramp','ramp',u0,u1,.12,rl+.12,top,gz)
        surf(ident+'_ramp_top','landing',width/2-.1,u1,.12,1.2,top)
        for u in (u0,u1):
            rails.tube(pt(u,.12,top+1),pt(u,rl+.12,gz+1),.037,m=1,n=7)
            for k in range(7):
                t=k/6;v=.12+rl*t;z=top*(1-t)+gz*t;rails.tube(pt(u,v,z),pt(u,v,z+1),.028,m=1,n=6)
    me.object('ENTRY_ACCESS '+str(b['id'])+' | individually modelled treads landing and approach',ma,col)
    rails.object('ENTRY_ACCESS '+str(b['id'])+' | side handrails',ma,col)
    nav.setdefault('pedestrianPaths',[]).append({'id':ident,'kind':'entry_stairs','width':1.2 if b['id']==153 else width,'points':[list(pt(0,v1,gz))]+list(reversed(center)),'maxRiser':abs(rise),'stepCount':steps,'source':source,'confidence':'photo-informed type; exact step count/width/placement estimated','smoothTraversal':True})
    return list(pt(0,v1,gz)),list(pt(0,.2,top))

def workshop_stair(b,edge_record,col,nav):
    """#158 photographed straight metal stair with upper landing and rail.
    Exact dimensions and step count are estimated, not extracted as survey data.
    """
    a,bb,le,ux,uy,nx,ny,an=edge_record
    width=1.35;count=24;run=.27;rise=.165;start=le*.35;v=2.5;base=b['base']+.06
    source='https://www3.chosun.ac.kr/campusMap/chosun/158/detailView.do'
    ma=[mat('STAIRS • workshop galvanized steel',(.54,.58,.57),.38,.65),mat('STAIRS • workshop dark tread',(.26,.28,.27),.55,.35)]
    me=Mesh();rail=Mesh();center=[]
    def pos(u,vv,z):return (a[0]+ux*u+nx*vv,a[1]+uy*u+ny*vv,z)
    for k in range(count):
        u=start+k*run;z=base+(k+1)*rise
        alongbox(me,pos(u+run/2,v,z-.045),(run+.01,width,.09),an,1)
        p=[pos(u,v-width/2,z),pos(u+run,v-width/2,z),pos(u+run,v+width/2,z),pos(u,v+width/2,z)]
        _surface(nav,'workshop158_'+str(k),'stairs',p,source);center.append(list(pos(u+run/2,v,z)))
    end=start+count*run;top=base+count*rise
    alongbox(me,pos(end+.8,v,top-.08),(1.6,width,.16),an,0)
    _surface(nav,'workshop158_top','landing',[pos(end,v-width/2,top),pos(end+1.6,v-width/2,top),pos(end+1.6,v+width/2,top),pos(end,v+width/2,top)],source)
    # Landing connects toward facade but is not falsely advertised as an open interior.
    alongbox(me,pos(end+.8,v/2,top-.08),(1.6,v,.16),an,0)
    _surface(nav,'workshop158_bridge','landing',[pos(end,.15,top),pos(end+1.6,.15,top),pos(end+1.6,v,top),pos(end,v,top)],source)
    for side in (-1,1):
        vv=v+side*width/2
        rail.tube(pos(start,vv,base+1),pos(end,vv,top+1),.028,m=0,n=6)
        rail.tube(pos(start,vv,base-.07),pos(end,vv,top-.07),.065,m=0,n=6)
        for k in range(0,count+1,3):
            z=base+k*rise;rail.tube(pos(start+k*run,vv,z),pos(start+k*run,vv,z+1),.025,m=0,n=6)
        rail.tube(pos(end,vv,top),pos(end,vv,b['base']),.065,m=0,n=6)
    me.object('WORKSHOP158 | straight metal treads and upper connecting landing',ma,col)
    rail.object('WORKSHOP158 | stringers vertical posts and rails',ma,col)
    nav.setdefault('pedestrianPaths',[]).append({'id':'workshop158','kind':'stairs','width':width,'points':center+[list(pos(end+.8,v,top))],'stepCount':count,'maxRiser':rise,'smoothTraversal':True,'source':source,'confidence':'Visible stair typology; placement/count/dimensions estimated'})
