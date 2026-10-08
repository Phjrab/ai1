import bpy,os,json,hashlib
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def val(v):
 if isinstance(v,(str,int,float,bool)) or v is None:return v
 try:return [val(x) for x in v]
 except:return getattr(v,'name',type(v).__name__)
def dump(p):
 bpy.ops.wm.open_mainfile(filepath=p);mats={}
 for m in bpy.data.materials:
  d={'diffuse':list(m.diffuse_color),'roughness':m.roughness,'metallic':m.metallic,'use_nodes':m.use_nodes}
  if m.use_nodes:
   d['nodes']=[{'name':n.name,'type':n.bl_idname,'inputs':[(i.name,val(i.default_value)) for i in n.inputs if hasattr(i,'default_value')],'image':n.image.name if hasattr(n,'image') and n.image else None} for n in m.node_tree.nodes];d['links']=[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links]
  mats[m.name]=hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()
 other={}
 for o in bpy.data.objects:
  if o.type!='FONT':continue
  d={'matrix':val(o.matrix_world),'body':o.data.body,'size':o.data.size,'extrude':o.data.extrude,'bevel_depth':o.data.bevel_depth,'align_x':o.data.align_x,'align_y':o.data.align_y};other[o.name]=hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()
 return mats,other
before,bfonts=dump(R+'/lighting/render_prototypes/campus_9627e996.blend');after,afonts=dump(R+'/campus/campus.blend')
report={'before_materials':len(before),'after_materials':len(after),'material_graphs_identical':before==after,'changed_materials':[k for k in before.keys()&after.keys() if before[k]!=after[k]],'added_materials':list(after.keys()-before.keys()),'removed_materials':list(before.keys()-after.keys()),'font_objects_before':len(bfonts),'font_objects_after':len(afonts),'font_objects_identical':bfonts==afonts,'before_material_hashes':before,'after_material_hashes':after,'before_font_hashes':bfonts,'after_font_hashes':afonts}
json.dump(report,open(R+'/delivery/building_catalog/source-material-equivalence.json','w'),ensure_ascii=False,indent=2);print({k:v for k,v in report.items() if 'hashes' not in k});assert before==after and bfonts==afonts
