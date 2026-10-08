import bpy,sys,os,json
P=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,P)
import campus_materials as c
cases={
 'REVIEW 130 • observed facade':'brick',
 'REVIEW 131 • observed facade':'stone',
 'REVIEW 159 • observed facade':'white_masonry',
 'REVIEW 153 • observed glazing':'glass',
 'REVIEW • parking sky blue cladding':'painted_metal',
 'REVIEW • chalk stone':'stone',
 'REVIEW • pharmacy ochre stone':'stone',
 'STAIRS • entry pale granite':'stone',
 'STAIRS • honed gray granite':'stone',
 'STAIRS • granite nosing':'stone',
 'STAIRS • metal handrail':'metal',
 'Coach pearl ivory':None,
 'Yellow circular BUS sign':None,
}
for name,expected in cases.items():
 assert c.classify(name)==expected,(name,c.classify(name),expected)
 m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(.83,.51,.24,1)
 m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=m.diffuse_color
c.apply_materials()
for name,expected in cases.items():
 m=bpy.data.materials[name]
 if name.startswith('REVIEW'):assert max(abs(a-b) for a,b in zip(m['campus_fallback_color'],(.83,.51,.24,1)))<1e-6,name
 if expected is None:assert not m.get('campus_pbr_version'),name
assert not c.apply_materials()
json.dump({'cases':cases,'all_passed':True,'photo_colors_preserved':True,'livery_excluded':True,'idempotent':True},open(P+'/material_contract_verification.json','w'),ensure_ascii=False,indent=2)
print('MATERIAL CONTRACT PASSED')
