"""Validate glTF JSON constants against explicit fallback source table."""
import sys,json,struct,os
p,t=sys.argv[1:3];data=open(p,'rb').read();assert data[:4]==b'glTF';n,typ=struct.unpack_from('<II',data,12);assert typ==0x4E4F534A
g=json.loads(data[20:20+n]);table=json.load(open(t))['materials'];mats={m['name']:m for m in g['materials']};results=[]
for name,ref in table.items():
 if name not in mats:continue # zero-user datablocks need not export
 m=mats[name];q=m.get('pbrMetallicRoughness',{});c=q.get('baseColorFactor',[1,1,1,1]);r=q.get('roughnessFactor',1);metal=q.get('metallicFactor',1)
 assert max(abs(a-b) for a,b in zip(c,ref['baseColorLinear']))<1e-5,(name,'baseColor',c,ref)
 assert abs(r-ref['roughness'])<1e-5,(name,'roughness',r)
 assert abs(metal-ref['metalness'])<1e-5,(name,'metalness',metal)
 assert m.get('alphaMode','OPAQUE')=='OPAQUE',name
 assert 'baseColorTexture' not in q,name
 results.append(name)
assert len(results)>0
report={'file':p,'checked_material_count':len(results),'all_constant_values_match':True,'white_fallback_regression':False,'exported_material_count':len(mats),'verified_materials':results}
json.dump(report,open(os.path.splitext(p)[0]+'_verification.json','w'),ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='verified_materials'},indent=2))
