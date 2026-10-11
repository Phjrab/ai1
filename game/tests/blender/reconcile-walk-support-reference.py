"""Blender helper: reconcile inferred metadata against exact visible loop triangles.
Import by path and call reconcile(scene, navigation). It mutates only mismatched
navigation records, retaining IDs/XY support extent. No scene geometry changes.
"""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def area(p):return .5*sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1]))
def clip_value(poly,fn):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        x,y=fn(a),fn(b);inside=x>=-1e-9;next_inside=y>=-1e-9
        if inside:result.append(a)
        if inside!=next_inside:
            t=x/(x-y);result.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
    return result

def intersect(poly,mask):
    if area(mask)<0:mask=list(reversed(mask))
    for a,b in zip(mask,mask[1:]+mask[:1]):
        poly=clip_value(poly,lambda p:(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
        if len(poly)<3:return []
    return poly

def subtract(poly,mask):
    if area(mask)<0:mask=list(reversed(mask))
    result=[];left=poly
    for a,b in zip(mask,mask[1:]+mask[:1]):
        fn=lambda p:(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
        outside=clip_value(left,lambda p:-fn(p))
        if len(outside)>=3 and abs(area(outside))>1e-8:result.append(outside)
        left=clip_value(left,fn)
        if len(left)<3:break
    return result

def plane(v):
    a,b,c=v;ux,uy,uz=[b[i]-a[i] for i in range(3)];vx,vy,vz=[c[i]-a[i] for i in range(3)];nz=ux*vy-uy*vx
    if abs(nz)<1e-9:return None
    A=(uz*vy-uy*vz)/nz;B=(ux*vz-uz*vx)/nz
    return (A,B,a[2]-A*a[0]-B*a[1])
def height(p,xy):return p[0]*xy[0]+p[1]*xy[1]+p[2]

def reconcile(scene,navigation,tolerance=.025):
    vertices=[];faces=[]
    for obj in scene.objects:
        if obj.type!='MESH' or obj.hide_render:continue
        name=obj.name.lower()
        eligible=name.startswith(('campus_terrain','campus_continuous','campus_plaza','inferred_game_walk_connectors')) or 'rv2 foundation floor' in name or (name.startswith(('entry_access','stair_detail','workshop158')) and not any(t in name for t in ('handrail','side rail','stringer','posts')))
        if not eligible:continue
        obj.data.calc_loop_triangles();offset=len(vertices);vertices.extend(tuple(obj.matrix_world@v.co) for v in obj.data.vertices)
        normal=obj.matrix_world.to_3x3()
        for tri in obj.data.loop_triangles:
            if abs((normal@tri.normal).z)>.15:faces.append(tuple(offset+i for i in tri.vertices))
    bvh=BVHTree.FromPolygons(vertices,faces,all_triangles=True)
    changed=[];checked=0
    for sf in navigation.get('walkableSurfaces',[]):
        if not sf['id'].startswith('inferred_walk_connector_'):continue
        checked+=1;poly=sf['polygon'];indices=sf['triangles'];max_gap=0
        for face in indices:
            points=[poly[i] for i in face]
            for weights in ((1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)):
                p=[sum(v[k]*w for v,w in zip(points,weights)) for k in range(3)];hit=bvh.ray_cast(Vector((p[0],p[1],p[2]+3)),Vector((0,0,-1)),6)[0]
                if hit is not None:max_gap=max(max_gap,abs(hit.z-p[2]))
        if max_gap<=tolerance:continue
        xmin,xmax=min(v[0] for v in poly),max(v[0] for v in poly);ymin,ymax=min(v[1] for v in poly),max(v[1] for v in poly);zmin,zmax=min(v[2] for v in poly)-3,max(v[2] for v in poly)+3
        candidates=[]
        for face in faces:
            v=[vertices[i] for i in face]
            if max(p[0] for p in v)<xmin or min(p[0] for p in v)>xmax or max(p[1] for p in v)<ymin or min(p[1] for p in v)>ymax or max(p[2] for p in v)<zmin or min(p[2] for p in v)>zmax:continue
            eq=plane(v)
            if eq:candidates.append(([p[:2] for p in v],eq))
        out_vertices=[];out_faces=[];keys={};total_area=0
        for face in indices:
            mask=[poly[i][:2] for i in face]
            for ci,(xy,eq) in enumerate(candidates):
                start=intersect(xy,mask)
                if len(start)<3 or abs(area(start))<1e-8:continue
                pieces=[start]
                for cj,(other,other_eq) in enumerate(candidates):
                    if ci==cj or not pieces:continue
                    # Equal-height duplicate triangles use a stable first owner.
                    difference=lambda p:height(other_eq,p)-height(eq,p)
                    max_difference=max(difference(p) for p in other)
                    if max_difference<1e-6:
                        if cj>ci or max(abs(difference(p)) for p in other)>1e-6:continue
                        upper=other
                    else:upper=clip_value(other,lambda p:difference(p)-1e-7)
                    if len(upper)<3 or abs(area(upper))<1e-8:continue
                    next_pieces=[]
                    for piece in pieces:
                        overlap=intersect(piece,upper)
                        if len(overlap)<3 or abs(area(overlap))<1e-8:next_pieces.append(piece)
                        else:next_pieces.extend(subtract(piece,upper))
                    pieces=next_pieces
                for piece in pieces:
                    if area(piece)<0:piece.reverse()
                    total_area+=abs(area(piece));ids=[]
                    for x,y in piece:
                        point=(x,y,height(eq,(x,y)));key=tuple(round(n,8) for n in point)
                        if key not in keys:keys[key]=len(out_vertices);out_vertices.append(list(point))
                        ids.append(keys[key])
                    for k in range(1,len(ids)-1):
                        face=[ids[0],ids[k],ids[k+1]];v=[out_vertices[i] for i in face];projected=abs(area([p[:2] for p in v]));longest=max(math.dist(v[j][:2],v[(j+1)%3][:2]) for j in range(3))
                        # Convex clipping can leave repeated or collinear boundary
                        # vertices and sub-millimetre slivers below BVH precision.
                        if projected>1e-8 and 2*projected/max(longest,1e-9)>.0005:out_faces.append(face)
        total_area=sum(abs(area([out_vertices[i][:2] for i in face])) for face in out_faces)
        expected=sum(abs(area([poly[i][:2] for i in face])) for face in indices)
        if not out_faces or abs(total_area-expected)>max(.002,expected*.002):raise ValueError('Incomplete visible support projection for '+sf['id'])
        # Verify actual exported faces against the exact source triangle BVH.
        maximum_error=0
        for face in out_faces:
            p=[sum(out_vertices[i][k] for i in face)/3 for k in range(3)];hit=bvh.ray_cast(Vector((p[0],p[1],p[2]+.1)),Vector((0,0,-1)),.2)[0]
            if hit is None:raise ValueError('No support under reconciled '+sf['id'])
            maximum_error=max(maximum_error,abs(hit.z-p[2]))
        if maximum_error>.005:raise ValueError('Support mismatch after projection for '+sf['id'])
        sf['polygon']=out_vertices;sf['triangles']=out_faces;sf.pop('rv2_visible_surface_correction_m',None);sf['rv2_support']='Exact visible Blender loop-triangle projection, same XY footprint; not a survey.'
        changed.append({'id':sf['id'],'before_max_gap':max_gap,'triangles':len(out_faces),'after_max_error':maximum_error})
    return {'checked':checked,'changed':changed,'geometry_modified':False,'method':'Exact scene loop triangles; no polygon-BVH retriangulation or mean-height correction'}
