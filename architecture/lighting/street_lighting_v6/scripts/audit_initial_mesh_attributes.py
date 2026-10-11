"""Read-only immediate-load mesh-attribute metadata inventory.

Use on the untouched original native, before importing the preservation helper:
blender -b ORIGINAL.blend --python audit_initial_mesh_attributes.py -- BASELINE.json OUTPUT.json
No per-vertex getters, foreach_get, evaluation, operators or save are used.
Hidden native CustomData (e.g. CD_MDEFORMVERT) is not exposed by mesh.attributes;
use audit_blend_blocks.py as the complementary check for that storage.
"""
import bpy
import json
import sys
import hashlib
from pathlib import Path

args = sys.argv[sys.argv.index('--')+1:]
baseline_path, output_path = map(Path, args)
baseline = json.loads(baseline_path.read_text())
declared_groups={obj.name:len(obj.vertex_groups) for obj in bpy.data.objects if len(obj.vertex_groups)}
rows = {}
for mesh in bpy.data.meshes:
    library = mesh.library.filepath if mesh.library else ''
    key = json.dumps([mesh.bl_rna.identifier, mesh.name, library],ensure_ascii=True,separators=(',',':'))
    rows[key] = {
        attr.name: {'domain':attr.domain,'data_type':attr.data_type,'count':len(attr.data)}
        for attr in mesh.attributes
        if attr.name not in {'.select_vert','.select_edge','.select_poly','.selection'}
        and not attr.name.startswith(('.vs.','.es.'))
    }
differences=[]
original=baseline['datablocks']['meshes']
for key in sorted(set(original)|set(rows)):
    if key not in original or key not in rows:
        differences.append({'mesh':key,'issue':'missing from baseline or source'})
        continue
    before=rows[key]
    after={name:{k:v[k] for k in ('domain','data_type','count')} for name,v in original[key]['attributes'].items()}
    if before != after:
        differences.append({'mesh':key,'source':before,'baseline_after_capture':after})
report={'status':'PASS' if not differences else 'FAIL','loaded_native':bpy.data.filepath,
        'mesh_count':len(rows),'objects_with_declared_vertex_groups':declared_groups,'declared_vertex_group_count':sum(declared_groups.values()),'differences':differences,'initial_attribute_metadata':rows,
        'scope':'Exposed mesh attribute names, domains, types and counts immediately after load; hidden native CustomData excluded.',
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'read_only':True}
output_path.write_text(json.dumps(report,indent=2)+'\n')
print('INITIAL_ATTRIBUTE_INVENTORY',report['status'],'meshes',len(rows),'differences',len(differences),flush=True)
