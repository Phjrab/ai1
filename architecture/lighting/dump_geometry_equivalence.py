import bpy,sys,os,json,hashlib,struct
from mathutils import Vector
out=sys.argv[sys.argv.index('--')+1];data={}
for o in bpy.data.objects:
 if o.type!='MESH':continue
 h=hashlib.sha256();h.update(str(tuple(tuple(v for v in row) for row in o.matrix_world)).encode())
 for v in o.data.vertices:h.update(struct.pack('3f',*v.co))
 for p in o.data.polygons:h.update(struct.pack(f'{len(p.vertices)}i',*p.vertices));h.update(struct.pack('i',p.material_index))
 data[o.name]={'sha256':h.hexdigest(),'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'bbox':[[min((o.matrix_world@Vector(c))[k] for c in o.bound_box) for k in range(3)],[max((o.matrix_world@Vector(c))[k] for c in o.bound_box) for k in range(3)]]}
json.dump({'source':bpy.data.filepath,'source_sha256':hashlib.sha256(open(bpy.data.filepath,'rb').read()).hexdigest(),'objects':data},open(out,'w'),ensure_ascii=False,indent=2)
