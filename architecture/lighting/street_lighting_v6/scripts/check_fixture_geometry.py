"""Two shared fixture heights, delta export, and installed CPU-render smoke check."""
import bpy,sys,json,hashlib,struct,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));import luminaire_geometry as g
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
materials=g.create_materials();rows=[];objects=[]
for i,h in enumerate((4.2,6.2)):
 mesh=g.fixture_mesh(h,materials);ob=bpy.data.objects.new('RV6_UNIT_'+str(h),mesh);bpy.context.scene.collection.objects.link(ob);ob.location.x=i*5
 assert abs(min(v.co.z for v in mesh.vertices)+.2)<1e-6;mesh.calc_loop_triangles();assert all(t.area>1e-9 for t in mesh.loop_triangles)
 rows.append({'height':h,'vertices':len(mesh.vertices),'polygons':len(mesh.polygons),'triangles':len(mesh.loop_triangles)});objects.append(ob)
p=ROOT/'qa/fixture_geometry.glb';g.export_fixture_delta(objects,p);data=p.read_bytes();n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n]);assert len(doc['nodes'])==2 and len(doc['meshes'])==2 and len(doc['scenes'])==1
assert 'KHR_lights_punctual' not in doc.get('extensionsUsed',[])
assert any(m['name']==g.MATERIAL_NAMES[-1] and max(m.get('emissiveFactor',[0]))>0 for m in doc['materials'])
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1;s.cycles.use_denoising=False;s.use_nodes=False;s.render.resolution_x=64;s.render.resolution_y=64;s.render.resolution_percentage=100
cd=bpy.data.cameras.new('unit_camera');co=bpy.data.objects.new(cd.name,cd);s.collection.objects.link(co);co.location=(8,-12,7);from mathutils import Vector;co.rotation_euler=(Vector((2.5,0,3))-co.location).to_track_quat('-Z','Y').to_euler();s.camera=co
bpy.ops.render.render()
sha=lambda q:hashlib.sha256(Path(q).read_bytes()).hexdigest()
report={'status':'PASS','geometry_source_sha256':sha(ROOT/'scripts/luminaire_geometry.py'),'checker_sha256':sha(__file__),'fixtures':rows,'glb_sha256':sha(p),'glb_bytes':len(data),'emissive_material_retained':True,'native_spotlights_not_exported':True,'installed_cycles_cpu_render':True,'denoising':False,'blender_version':bpy.app.version_string,'binary_sha256':sha(bpy.app.binary_path),'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
(ROOT/'qa/fixture_geometry.json').write_text(json.dumps(report,indent=2)+'\n');print('FIXTURE_GEOMETRY_PASS',json.dumps(report),flush=True)
