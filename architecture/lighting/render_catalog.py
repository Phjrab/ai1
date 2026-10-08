"""Final-source-only building catalog. Never saves source or changes geometry/materials.
blender -b FINAL.blend -t 4 --python render_catalog.py -- --sha SHA --indices 1,2 --width 1600 --samples 32
"""
import bpy,sys,os,json,math,hashlib,argparse,time,itertools
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,ROOT+'/materials')
from campus_materials import setup_presentation
ap=argparse.ArgumentParser();ap.add_argument('--sha',required=True);ap.add_argument('--catalog',default=ROOT+'/campus/building_render_catalog.json');ap.add_argument('--out',default=ROOT+'/delivery/building_catalog');ap.add_argument('--indices',default='');ap.add_argument('--width',type=int,default=1600);ap.add_argument('--samples',type=int,default=32);ap.add_argument('--plan-only',action='store_true');ap.add_argument('--camera-overrides');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
source=bpy.data.filepath;assert sha(source)==args.sha,'Final source SHA does not match approved source'
rows=json.load(open(args.catalog));n=len(rows)
for idx,f in enumerate(['main_building_catalog.json','professor_annex_catalog.json'],n+1):
 r=json.load(open(ROOT+'/campus/'+f));r['index']=idx;rows.append(r)
assert len({r['index'] for r in rows})==len(rows)
os.makedirs(args.out,exist_ok=True)
indices={int(i) for i in args.indices.split(',') if i};overrides=json.load(open(args.camera_overrides)) if args.camera_overrides else {}
s=bpy.context.scene;setup_presentation('catalogue',args.width);s.cycles.samples=args.samples;s.cycles.adaptive_threshold=.035;s.cycles.use_denoising=False
s.render.resolution_y=round(args.width*.75);s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=95;s.render.image_settings.color_mode='RGB'
cam=bpy.data.objects.new('CATALOG | subject framing',bpy.data.cameras.new('CATALOG | subject framing'));s.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.clip_start=.1;cam.data.clip_end=7000;s.camera=cam
bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
def objects_for(r):
 obs=set()
 for name in ([r['collection']] if r.get('collection') else r.get('collections',[])):
  assert name in bpy.data.collections,('missing collection',name)
  obs.update(bpy.data.collections[name].all_objects)
 for prefix in r.get('objects',[]):obs.update(o for o in bpy.data.objects if o.name.startswith(prefix))
 return {o for o in obs if o.type in ('MESH','FONT','CURVE')}
def corners(r):return [Vector(c) for c in itertools.product(*zip(r['bbox']['min'],r['bbox']['max']))]
def aim_and_fit(r,loc,target):
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
 inv=cam.matrix_world.inverted();cs=[inv@v for v in corners(r)];lo=[min(v[k] for v in cs) for k in range(2)];hi=[max(v[k] for v in cs) for k in range(2)]
 offset=cam.rotation_euler.to_matrix()@Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0));cam.location+=offset
 # Blender ortho_scale is image width for landscape framing.
 cam.data.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])/(s.render.resolution_y/s.render.resolution_x))*1.18;bpy.context.view_layer.update()
 return list(cam.location),cam.data.ortho_scale

def visibility(r,obs):
 # Target projected bounding-box grid: classify the first scene intersection.
 # Hits on surrounding meshes count as occlusion; background does not.
 target_names={o.name for o in obs};hit=other=target_rays=0
 inv=cam.matrix_world.inverted();cs=[inv@v for v in corners(r)];lo=[min(v[k] for v in cs) for k in range(2)];hi=[max(v[k] for v in cs) for k in range(2)]
 direction=cam.rotation_euler.to_matrix()@Vector((0,0,-1))
 for i in range(13):
  for j in range(11):
   local=Vector((lo[0]+(hi[0]-lo[0])*(i+.5)/13,lo[1]+(hi[1]-lo[1])*(j+.5)/11,0));origin=cam.matrix_world@local
   tloc,tnormal,tidx,tdist=target_bvh.ray_cast(origin,direction,4000)
   if tloc is None:continue
   target_rays+=1
   ok,loc,normal,idx,obj,matrix=s.ray_cast(deps,origin,direction,distance=4000)
   if ok:
    if obj.name in target_names:hit+=1
    else:other+=1
 return hit/max(1,target_rays),hit,other
for r in rows:
 if indices and r['index'] not in indices:continue
 s.render.resolution_y=round(args.width*(.5625 if r['index']==n+1 else .75))
 start=time.time();obs=objects_for(r);assert obs,('no subject objects',r['name']);vertices=[];polys=[]
 for ob in obs:
  ev=ob.evaluated_get(deps);mesh=ev.to_mesh();off=len(vertices);vertices.extend(ob.matrix_world@v.co for v in mesh.vertices);polys.extend(tuple(off+i for i in p.vertices) for p in mesh.polygons);ev.to_mesh_clear()
 target_bvh=BVHTree.FromPolygons(vertices,polys)
 target=Vector(r['target']);base=Vector(r['camera'])-target;dist=max(base.length,100);az=math.atan2(base.y,base.x);elev=math.atan2(base.z,math.hypot(base.x,base.y));candidates=[]
 override=overrides.get(str(r['index']))
 if override:
  if 'rotation' in override:
   cam.location=override['camera'];cam.rotation_euler=override['rotation'];cam.data.ortho_scale=override['orthographic_scale'];bpy.context.view_layer.update();loc=list(cam.location);scale=cam.data.ortho_scale
  else:loc,scale=aim_and_fit(r,override['camera'],override.get('target',target))
  score,hit,other=visibility(r,obs);candidates=[dict(location=loc,rotation=list(cam.rotation_euler),scale=override.get('orthographic_scale',scale),score=score,hit=hit,other=other,azimuth_delta=0,elevation_degrees=math.degrees(elev))]
 else:
  for deg,el in [(0,elev),(0,max(elev,.62)),(-35,max(elev,.48)),(35,max(elev,.48)),(-70,max(elev,.65)),(70,max(elev,.65)),(180,max(elev,.65)),(0,.90)]:
   a=az+math.radians(deg);direction=Vector((math.cos(a)*math.cos(el),math.sin(a)*math.cos(el),math.sin(el)));loc,scale=aim_and_fit(r,target+direction*dist,target);score,hit,other=visibility(r,obs)
   candidates.append(dict(location=loc,rotation=list(cam.rotation_euler),scale=scale,score=score,hit=hit,other=other,azimuth_delta=deg,elevation_degrees=math.degrees(el)))
  # Keep the source-informed front unless another direction materially improves visibility.
  for c in candidates:c['selection_score']=c['score']-.07*abs(c['azimuth_delta'])/35-.05*max(0,c['elevation_degrees']-25)/20
 selected=max(candidates,key=lambda c:c.get('selection_score',c['score']));cam.location=selected['location'];cam.rotation_euler=selected['rotation'];cam.data.ortho_scale=selected['scale'];bpy.context.view_layer.update()
 filename=f"{r['index']:03d}_"+''.join(c if c.isalnum() or c in ' -_()' else '_' for c in r['name'])+'.jpg';path=os.path.join(args.out,filename)
 meta=dict(index=r['index'],name=r['name'],building_id=r.get('id'),osm_id=r.get('osm_id'),catalog_record=r,source=source,source_sha256=args.sha,source_modified=False,geometry_modified=False,materials_modified=False,surrounding_geometry_visible=True,camera=dict(location=list(cam.location),rotation=list(cam.rotation_euler),type='ORTHO',ortho_scale=cam.data.ortho_scale),camera_candidates=candidates,camera_visibility_score=selected['score'],width=args.width,height=s.render.resolution_y,samples=args.samples,denoising=False,engine='CYCLES',format='JPEG',quality=95,visual_review='pending',disclaimer='Photo-informed reconstruction where verified; hidden sides and dimensions approximate. Unverified auxiliary buildings are contextual estimates, not exact reconstructions.')
 if not args.plan_only:
  s.render.filepath=path;bpy.ops.render.render(write_still=True);meta.update(file=filename,file_sha256=sha(path),render_seconds=round(time.time()-start,2))
 json.dump(meta,open(os.path.splitext(path)[0]+'.json','w'),ensure_ascii=False,indent=2);print('CATALOG_COMPLETE',r['index'],r['name'],flush=True)
assert sha(source)==args.sha,'Source changed during render'
