import bpy,copy,hashlib,importlib.util,json,math,resource
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=module('old',Path(__file__).with_name('reconcile-walk-support-reference.py'));new=module('new',ROOT/'scripts/reconcile-walk-support.py')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def mesh(name,vertices,faces):
 data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update();o=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(o);return o
# One dense terrain contains both distant and nearby faces; a second eligible
# distant object tests the complete object skip without opening a campus file.
n=120;vertices=[(i*2-100,j*2-100,0) for j in range(n+1) for i in range(n+1)];faces=[]
for j in range(n):
 for i in range(n):
  a=j*(n+1)+i;faces.extend([(a,a+1,a+n+2),(a,a+n+2,a+n+1)])
terrain=mesh('CAMPUS_TERRAIN fixture',vertices,faces)
terrain.location=(321.125,-540.25,7)
distant=mesh('CAMPUS_PLAZA distant fixture',[(2000,2000,1),(2004,2000,1),(2000,2004,1)],[(0,1,2)])
walk=mesh('INFERRED_GAME_WALK_CONNECTORS rotated nonplanar fixture',[(-2,-2,1),(2,-2,1.15),(2,2,1.4),(-2,2,1.08)],[(0,1,2,3)])
walk.location=(321.125,-540.25,12.125);walk.rotation_euler=(.045,-.025,.31);walk.scale=(1.7,.8,1.2)
upper=mesh('INFERRED_GAME_WALK_CONNECTORS overlapping tread',[(-.4,-.4,1.6),(.8,-.4,1.6),(.8,.8,1.6),(-.4,.8,1.6)],[(0,1,2,3)]);upper.matrix_world=walk.matrix_world.copy()
bpy.context.view_layer.update();upper.matrix_world=walk.matrix_world.copy();bpy.context.view_layer.update()
poly=[list(walk.matrix_world@v.co) for v in walk.data.vertices]
nav={'walkableSurfaces':[{'id':'inferred_walk_connector_fixture','polygon':[[p[0],p[1],p[2]-.2] for p in poly],'triangles':[[0,1,2],[0,2,3]]},{'id':'unrelated_support','polygon':[[0,0,9],[1,0,9],[0,1,9]],'triangles':[[0,1,2]]}]}
def snapshot():return hashlib.sha256(json.dumps([(o.name,list(map(list,o.matrix_world)),[list(v.co) for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons],o.hide_render) for o in bpy.context.scene.objects if o.type=='MESH'],sort_keys=True).encode()).hexdigest()
before=snapshot();a=copy.deepcopy(nav);b=copy.deepcopy(nav);old_report=old.reconcile(bpy.context.scene,a);new_report=new.reconcile(bpy.context.scene,b)
assert a==b,'Metadata output differs from original implementation';assert snapshot()==before,'Source scene geometry changed';assert len(new_report['changed'])==1
stats=new_report['support_collection'];assert stats['retained_triangles']<stats['scanned_loop_triangles']*.01;assert stats['skipped_distant_objects']>=1
again=copy.deepcopy(b);repeat=new.reconcile(bpy.context.scene,again);assert again==b and not repeat['changed']
empty={'walkableSurfaces':[]};assert new.reconcile(bpy.context.scene,empty)==old.reconcile(bpy.context.scene,empty)
report={'passed':True,'fixture':'Dense nearby/distant terrain, transformed nonplanar quad, overlapping upper tread, unrelated record and empty input','metadata_identical_to_previous':True,'source_geometry_unchanged':True,'idempotent':True,'old_result':old_report,'compact_result':new_report,'maximum_RSS_MB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'source_sha256':hashlib.sha256((ROOT/'scripts/reconcile-walk-support.py').read_bytes()).hexdigest()}
out=ROOT/'tests/compact-walk-support-candidate-results.json';out.write_text(json.dumps(report,indent=2)+'\n');print('COMPACT_SUPPORT_FIXTURE',json.dumps(report))
