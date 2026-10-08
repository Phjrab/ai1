import bpy,os
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out=os.path.join(root,'delivery',os.path.splitext(os.path.basename(bpy.data.filepath))[0]+'.glb')
bpy.ops.export_scene.gltf(filepath=out,export_format='GLB',export_cameras=False,export_lights=False,export_extras=True,export_apply=True)
print('GLB_READY',out,os.path.getsize(out))
