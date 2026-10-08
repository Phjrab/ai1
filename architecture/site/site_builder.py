"""Original procedural Chosun University surroundings. Blender 4.3+.
API: build_site() -> collection. Does not remove existing scene data.
Coordinate contract: facade y=0, x=-187.5..187.5, entry x=0, grade z=0.
Source-informed spatial layout; terrain, vegetation, cars and counts illustrative.
"""
import bpy, math, random, json, os
from mathutils import Vector
R=random.Random(1946)
ROOT=None

def mat(name,color,rough=.7,metal=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m
class Mesh:
    def __init__(self):self.v=[];self.f=[];self.mi=[]
    def poly(self,v,f,m=0):
        n=len(self.v);self.v.extend(v);self.f.extend([tuple(n+i for i in q) for q in f]);self.mi.extend([m]*len(f))
    def box(self,c,s,m=0):
        x,y,z=c;a,b,d=[q/2 for q in s]
        self.poly([(x+i*a,y+j*b,z+k*d) for i,j,k in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],m)
    def tube(self,a,b,r1,r2=None,m=0,n=10):
        a,b=Vector(a),Vector(b);r2=r1 if r2 is None else r2;w=(b-a).normalized();u=w.cross(Vector((0,0,1)))
        if u.length<.01:u=w.cross(Vector((0,1,0)))
        u.normalize();v=w.cross(u)
        pts=[tuple(c+r*(math.cos(2*math.pi*i/n)*u+math.sin(2*math.pi*i/n)*v)) for c,r in [(a,r1),(b,r2)] for i in range(n)]
        self.poly(pts,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],m)
    def ellipsoid(self,c,s,m=0,seed=0,rings=6,segs=10):
        rnd=random.Random(seed);vs=[]
        for j in range(rings+1):
            t=math.pi*j/rings
            for i in range(segs):
                p=2*math.pi*i/segs;noise=1+rnd.uniform(-.12,.12)
                vs.append((c[0]+math.sin(t)*math.cos(p)*s[0]*noise,c[1]+math.sin(t)*math.sin(p)*s[1]*noise,c[2]+math.cos(t)*s[2]*noise))
        self.poly(vs,[(j*segs+i,j*segs+(i+1)%segs,(j+1)*segs+(i+1)%segs,(j+1)*segs+i) for j in range(rings) for i in range(segs)],m)
    def object(self,name,mats,coll):
        me=bpy.data.meshes.new(name+' mesh');me.from_pydata(self.v,[],self.f);me.materials.clear()
        for m in mats:me.materials.append(m)
        for p,i in zip(me.polygons,self.mi):p.material_index=i
        me.update();ob=bpy.data.objects.new(name,me);coll.objects.link(ob);return ob

def col(name):
    c=bpy.data.collections.new(name);ROOT.children.link(c);return c

def objbox(name,c,s,m,coll):
    b=Mesh();b.box(c,s);return b.object(name,[m],coll)

def front_z(y):return -18*max(0,min(1,(-y-27)/65))
def rear_z(x,y):return max(0,(y-33)*.34)*(1+.12*math.sin(x*.034))

def car_mesh(mats,suv=False):
    b=Mesh();b.box((0,0,.58),(1.83,4.45,.62),0);b.box((0,0,.31),(1.5,3.6,.18),3)
    # Sloping cabin, a compact sedan/SUV silhouette, x width, y length.
    h=1.62 if suv else 1.4
    b.poly([(-.82,-1.34,.88),(.82,-1.34,.88),(.82,1.35,.88),(-.82,1.35,.88),(-.69,-.83,h),(.69,-.83,h),(.69,.73,h),(-.69,.73,h)],[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],1)
    b.box((0,-.03,h+.015),(1.4,1.55,.065),0)
    for x in [-.825,.825]:
        b.box((x,0,1.13),(.05,.09,.58),0)
        b.box((x,-.91,.9),(.09,.08,.24),0)
        for y in [-.38,.7]:b.box((x*1.011,y,.95),(.025,.18,.035),4)
        b.box((x*1.18,-.8,1.09),(.27,.2,.14),0)
    for x in [-.9,.9]:
        for y in [-1.38,1.38]:
            b.tube((x-.12,y,.38),(x+.12,y,.38),.355,m=3,n=16)
            xo=x+(.135 if x>0 else -.135);b.tube((xo-.016,y,.38),(xo+.016,y,.38),.215,m=4,n=12)
    for x in [-.6,.6]:
        b.box((x,-2.236,.73),(.47,.035,.18),2);b.box((x,2.236,.73),(.48,.035,.18),5)
    for y in [-2.25,2.25]:b.box((0,y,.49),(.45,.027,.14),2)
    b.box((0,-2.243,.55),(.65,.03,.19),3)
    return b

def build_site():
    global ROOT,R
    R=random.Random(1946);ROOT=bpy.data.collections.new('CHOSUN_SITE');bpy.context.scene.collection.children.link(ROOT)
    ROOT['layout_basis']='Chosun University official gallery aerial1/aerial3 and facade side photo. Roads, central stair and wooded terrace source-informed; metric terrain, species, counts and car locations illustrative.'
    ROOT['coordinate_contract']='metres; facade y=0, front -Y; building base z=0; width approx 375m'
    terrain=col('SITE 01 | Sloping ground');roads=col('SITE 02 | Roads and parking');details=col('SITE 03 | Curbs stairs furniture');trees=col('SITE 04 | Linked tree assets');cars=col('SITE 05 | Parked vehicles')
    grass=mat('SITE • muted grass',(.18,.265,.095));earth=mat('SITE • cut earth',(.235,.205,.145));asphalt=mat('SITE • asphalt',(.075,.084,.09));pave=mat('SITE • pale concrete',(.48,.47,.43));curb=mat('SITE • granite curb',(.62,.62,.57));white=mat('SITE • road paint',(.81,.81,.72));yellow=mat('SITE • center line',(.76,.55,.10));stone=mat('SITE • stair granite',(.47,.46,.42));metal=mat('SITE • charcoal painted steel',(.075,.085,.085),.42,.5)
    # Terrain bands retain level facade access and slope toward the lower contour road.
    ground=Mesh();xs=[-235+i*10 for i in range(48)];ys=[-140,-122,-110,-104,-98,-92,-82,-72,-62,-52,-42,-32,-27,0,17,28,33,43,53,63,73,83,93,103,113,123]
    for j in range(len(ys)-1):
        for i in range(len(xs)-1):
            vs=[]
            for x,y in [(xs[i],ys[j]),(xs[i+1],ys[j]),(xs[i+1],ys[j+1]),(xs[i],ys[j+1])]:
                z=front_z(y) if y<0 else rear_z(x,y)
                if y<-118:z-=(-y-118)*.09545454545
                vs.append((x,y,z-.18))
            ground.poly(vs,[(0,1,2,3)])
    ground.object('Wooded terrace and rear hillside',[grass],terrain)
    objbox('Facade pedestrian apron',(0,-5,-.13),(393,10,.26),pave,roads)
    objbox('Facade parking and access road',(0,-17.5,-.1),(409,15,.2),asphalt,roads)
    objbox('Rear service lane and parking',(0,25,-.10),(397,14,.20),asphalt,roads)
    # Subtle expansion joints in broad pavement.
    joints=Mesh()
    for x in range(-195,196,5):joints.box((x,-5,.007),(.028,9.8,.009))
    joints.object('Apron stone joints',[stone],details)
    # Lower road is a gently bent contour road, with end connections to access road.
    curve=[(-228,-104,-18),(-190,-101,-18),(-135,-99,-18),(-75,-98,-18),(0,-99,-18),(75,-99,-18),(135,-101,-18),(190,-104,-18),(228,-110,-18)]
    def ribbon(points,width,material,name,zoff=.025):
        # One continuous mitered ribbon, not disconnected per-segment quads.
        # Dense stations and individual edge elevations hug the terrain slope.
        dense=[]
        for p,q in zip(points,points[1:]):
            p,q=Vector(p),Vector(q);n=max(1,math.ceil((q-p).length/1.5))
            dense.extend([p+(q-p)*(i/n) for i in range(n)])
        dense.append(Vector(points[-1]));verts=[];faces=[]
        for i,p in enumerate(dense):
            d0=(p-dense[max(0,i-1)]) if i>0 else dense[1]-p
            d1=(dense[min(len(dense)-1,i+1)]-p) if i<len(dense)-1 else p-dense[i-1]
            d0.z=0;d1.z=0;d0.normalize();d1.normalize()
            n0=Vector((-d0.y,d0.x,0));n1=Vector((-d1.y,d1.x,0));mit=(n0+n1).normalized()
            offset=mit*(width*.5/max(.25,mit.dot(n1)))
            for side in [-1,1]:
                pos=p+side*offset
                # The road follows the same piecewise-linear slope as ground.
                z=front_z(pos.y) if pos.y<0 else 0
                verts.append((pos.x,pos.y,z+zoff))
        for i in range(len(dense)-1):
            k=2*i;faces.extend([(k,k+2,k+3),(k,k+3,k+1)])
        # Split faces at terrain grade breaks so no chord cuts through ground.
        def clip(poly,bound,keep_above):
            out=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                ina=a[1]>=bound if keep_above else a[1]<=bound
                inb=b[1]>=bound if keep_above else b[1]<=bound
                if ina:out.append(a)
                if ina != inb:
                    t=(bound-a[1])/(b[1]-a[1]);out.append((a[0]+t*(b[0]-a[0]),bound,0))
            return out
        mm=Mesh()
        for face in faces:
            initial=[verts[j] for j in face]
            for lo,hi in [(-1000,-92),(-92,-27),(-27,1000)]:
                poly=clip(clip(initial,lo,True),hi,False)
                if len(poly)>=3:
                    poly=[(x,y,front_z(y)+zoff) for x,y,z in poly]
                    mm.poly(poly,[tuple(range(len(poly)))])
        return mm.object(name,[material],roads)
    ribbon(curve,10,asphalt,'Lower cross-campus contour road')
    for side in [-1,1]:
        path=[(side*198,25,0),(side*198,-15,0),(side*213,-27,0),(side*222,-48,-6),(side*221,-73,-12),(side*217,-92,-18),(side*214,-104,-18)]
        path=[(x,y,front_z(y)) for x,y,z in path]
        ribbon(path,9,asphalt,'End connector road '+str(side),zoff=.045)
    marks=Mesh();kerbs=Mesh()
    for x in range(-200,201,8):marks.box((x,-19,.021),(3.5,.13,.015),1)
    for y in [-10,-25.1]:kerbs.box((0,y,.09),(403,.25,.22))
    for side in [-1,1]:
        for i in range(56):
            x=side*(15+i*3.2)
            marks.box((x,-12.5,.023),(.09,4.9,.017),0)
        marks.box((side*104,-14.95,.023),(179,.09,.017),0)
    for y in [-21.8,-20.2,-18.6,-17,-15.4,-13.8]:marks.box((0,y,.025),(7,.75,.02),0)
    # Lower road centre marks and pedestrian crossing.
    for p,q in zip(curve,curve[1:]):
        d=Vector(q)-Vector(p);n=int(d.length/7)
        for i in range(n):
            c=Vector(p)+d*((i+.3)/n);marks.box((c.x,c.y,c.z+.029),(3,.12,.02),1)
    for y in [-102.5,-101,-99.5,-98,-96.5]:marks.box((0,y,-17.96),(6,.7,.02),0)
    marks.object('Parking bay markings center lines zebra crossings',[white,yellow],roads);kerbs.object('Raised granite road curbs',[curb],details)
    # 108 individual treads following central downhill axis, with small landings.
    stairs=Mesh();rail=Mesh();N=108;run=65/N;rise=18/N
    for i in range(N):
        y=-27-(i+.5)*run;z=-(i+1)*rise
        width=7.8 if i<96 else 11.2
        stairs.box((0,y,z-.14),(width,run+.018,.28))
        # Granite side cheek cap tracks flight without obstructing the central axis.
        for x in [-width/2-.15,width/2+.15]:stairs.box((x,y,z+.06),(.3,run+.02,.43))
    for side in [-1,1]:
        for i in range(0,109,6):
            y=-27-i*run;z=-i*rise;rail.tube((side*3.65,y,z),(side*3.65,y,z+1.03),.032,n=8)
        rail.tube((side*3.65,-27,1.03),(side*3.65,-92,-16.97),.042,n=10)
    stairs.object('Central 108-step descent | schematic grade',[stone],details)
    plaques=Mesh()
    for i in range(0,96,3):
        plaques.box((0,-27-(i+1)*run,-(i+1)*rise+.012),(.48,run*.86,.024))
    plaques.object('Stair central commemorative plaque strip',[metal],details)
    rail.object('Central stair handrails',[metal],details)
    objbox('Central upper stair landing',(0,-25.7,-.09),(9.1,2.6,.18),stone,details)
    objbox('Lower stair landing',(0,-94.5,-18),(10,5,.15),stone,details)
    # Lamps and benches at upper apron and lower walk. Compact merged meshes.
    furn=Mesh()
    for x in range(-180,181,30):
        if abs(x)<10:continue
        furn.tube((x,-24,.02),(x,-24,5),.065,.045,n=10);furn.tube((x,-24,5),(x,-22.8,5.15),.04,n=8);furn.box((x,-22.7,5.15),(.55,1.05,.16))
    furn.object('Access road lamps',[metal],details)
    benches=Mesh()
    for x in [-155,-105,-55,55,105,155]:
        for i in range(4):benches.box((x,-7+i*.13,.46),(1.8,.10,.07),0)
        for i in range(3):benches.box((x,-6.53,.65+i*.13),(1.8,.075,.09),0)
        for dx in [-.65,.65]:benches.box((x+dx,-6.75,.22),(.065,.48,.43),1)
    benches.object('Timber campus benches',[mat('SITE • oiled timber',(.28,.18,.10)),metal],details)
    # Original compact vegetation library: each tree is one shared mesh.
    bark=mat('SITE • bark',(.18,.14,.09));leafm=[mat('SITE • leaf '+str(i),c) for i,c in enumerate([(.105,.20,.067),(.15,.25,.084),(.19,.28,.08),(.10,.18,.09),(.22,.29,.105)])]
    tree_meshes=[]
    for k in range(10):
        b=Mesh();rng=random.Random(100+k);conifer=k>=7
        h=rng.uniform(7.5,11.8);b.tube((0,0,0),(.15,.03,h*.76),.24,.075,0,n=10)
        if not conifer:
            for j in range(14):
                a=j*2.399;rr=rng.uniform(.7,2.8);z=rng.uniform(h*.53,h*.86);cx=math.cos(a)*rr;cy=math.sin(a)*rr
                if j<7:b.tube((.05,0,h*.40),(cx,cy,z),.10,.027,0,n=7)
                b.ellipsoid((cx,cy,z),(rng.uniform(1.2,2),rng.uniform(1.2,2),rng.uniform(1.5,2.3)),1+(j+k)%5,seed=k*100+j)
        else:
            for j in range(14):
                a=j*2.399;rr=2.7*(1-j/18);z=h*.40+j*h*.039;cx=math.cos(a)*rr*.55;cy=math.sin(a)*rr*.55
                b.tube((0,0,z-.7),(cx,cy,z),.07,.02,0,n=7)
                b.ellipsoid((cx,cy,z),(rr,rr*.72,.95),1+(j+k)%5,seed=k*100+j,rings=5,segs=9)
        mesh=b.object('Tree prototype '+str(k),[bark]+leafm,trees);tree_meshes.append(mesh.data)
        for polygon in mesh.data.polygons:polygon.use_smooth=True
        trees.objects.unlink(mesh);bpy.data.objects.remove(mesh)
    count=0
    def tree(x,y,z,scale=1):
        nonlocal count
        ob=bpy.data.objects.new('Tree %03d | illustrative species'%count,tree_meshes[R.randrange(10)]);trees.objects.link(ob);ob.location=(x,y,z);ob.rotation_euler.z=R.random()*math.tau;v=scale*R.uniform(.8,1.18);ob.scale=(v,v,v*R.uniform(.9,1.1));count+=1
    # Front wooded bank has denser clusters but central staircase remains legible.
    for y0 in [-34,-44,-54,-65,-76,-86]:
        for x0 in range(-192,193,10):
            x=x0+R.uniform(-3.6,3.6);y=y0+R.uniform(-3,3)
            if abs(x)<9:continue
            tree(x,y,front_z(y)-.1,R.uniform(.8,1.07))
    # Mature trees bordering façade road, with deliberate gaps before entrances.
    for x in range(-183,184,18):
        if min(abs(x),abs(x-131),abs(x+131))<14:continue
        tree(x,-26.5,0,.73)
    # A contained rear forested slope rather than a flat generic background.
    for y0 in [40,52,65,80,96,113]:
        for x0 in range(-220,221,13):
            x=x0+R.uniform(-4,4);y=y0+R.uniform(-3,3);tree(x,y,rear_z(x,y)-.1,R.uniform(.85,1.25))
    # Sparse foreground copses beneath lower road.
    for y0 in [-118,-132]:
        for x0 in range(-200,201,18):
            if abs(x0)<14:continue
            x=x0+R.uniform(-4,4);y=y0+R.uniform(-3,3);tree(x,y,-18-max(0,-y-118)*.09545454545,R.uniform(.8,1.1))
    # Six shared original vehicle styles/colors, no external models or textures.
    glass=mat('SITE • car tinted glass',(.025,.06,.075),.22,.3);rubber=mat('SITE • tire rubber',(.025,.027,.028));chrome=mat('SITE • alloy wheels',(.38,.40,.42),.28,.8);head=mat('SITE • headlamp',(.78,.81,.78),.17,.25);red=mat('SITE • taillamp',(.37,.015,.009),.25)
    paints=[(.76,.77,.74),(.14,.15,.17),(.29,.33,.36),(.06,.13,.20),(.58,.58,.53),(.29,.055,.035)]
    carmeshes=[]
    for k,c in enumerate(paints):
        body=mat('SITE • vehicle paint '+str(k),c,.27,.55);ob=car_mesh([body,glass,head,rubber,chrome,red],k==4).object('Vehicle prototype '+str(k),[body,glass,head,rubber,chrome,red],cars)
        carmeshes.append(ob.data);cars.objects.unlink(ob);bpy.data.objects.remove(ob)
    ncar=0
    for side in [-1,1]:
        for i in range(54):
            x=side*(16.6+i*3.2)
            if R.random()<.34 or min(abs(x-131),abs(x+131))<7:continue
            k=R.choices(range(6),[35,24,18,8,12,3])[0];ob=bpy.data.objects.new('Parked vehicle %02d'%ncar,carmeshes[k]);cars.objects.link(ob);ob.location=(x,-12.45,.04);ob.rotation_euler.z=math.pi if R.random()<.75 else 0;ncar+=1
    for x in range(-176,177,9):
        if R.random()<.23:continue
        ob=bpy.data.objects.new('Rear parked vehicle %02d'%ncar,carmeshes[R.randrange(5)]);cars.objects.link(ob);ob.location=(x,29,.04);ob.rotation_euler.z=math.pi;ncar+=1
    rear_marks=Mesh()
    for x in range(-184,185,3):rear_marks.box((x,29.3,.024),(.085,4.8,.018))
    rear_marks.object('Rear parking bays',[white],roads)
    ROOT['tree_count']=count;ROOT['vehicle_count']=ncar;ROOT['asset_authorship']='All geometry and materials procedural original; no downloaded model geometry or textures.'
    return ROOT

if __name__=='__main__':
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    root=build_site();scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.world.color=(.6,.6,.6)
    out=os.path.dirname(os.path.abspath(__file__));bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,'site.blend'))
    meshes=[o for o in root.all_objects if o.type=='MESH'];stats={'objects':len(meshes),'trees':root['tree_count'],'vehicles':root['vehicle_count'],'unique_meshes':len({o.data.name for o in meshes}),'instanced_polygons':sum(len(o.data.polygons) for o in meshes),'unique_polygons':sum(len(m.polygons) for m in {o.data for o in meshes}),'nonfinite_vertices':sum(1 for o in meshes for v in o.data.vertices if not all(math.isfinite(x) for x in v.co)),'road_height':0,'lower_road_height':-18,'main_building_clearance':'No vegetation within building footprint x ±190, y 0..30; rear service road at y18..32.'}
    with open(os.path.join(out,'scene_stats.json'),'w') as f:json.dump(stats,f,indent=2)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out,'site.glb'),export_format='GLB',export_yup=True,export_cameras=False,export_lights=False)
    print('SITE_CHECKS',json.dumps(stats))
