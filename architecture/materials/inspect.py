import bpy,json
bpy.ops.wm.open_mainfile(filepath='/workspace/shared/chosun_model/delivery/Chosun_Campus.blend')
s=bpy.context.scene
r={'materials':[{'name':m.name,'color':list(m.diffuse_color),'nodes':[(n.type,n.name) for n in m.node_tree.nodes] if m.use_nodes else []} for m in bpy.data.materials], 'cameras':[{'name':o.name,'loc':list(o.location),'rot':list(o.rotation_euler),'scale':o.data.ortho_scale} for o in bpy.data.objects if o.type=='CAMERA'],'lights':[(o.name,o.data.type,o.data.energy) for o in bpy.data.objects if o.type=='LIGHT'],'unit':s.unit_settings.scale_length,'objects':len(bpy.data.objects)}
json.dump(r,open('/workspace/shared/chosun_model/materials/inspection.json','w'),indent=2)
